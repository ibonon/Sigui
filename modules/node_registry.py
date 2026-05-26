"""
modules/node_registry.py — NexusMind Node Registry

Tracks NexusMind nodes registered as Sigui Workers.
Stores capabilities, real-time stats (evaluations, USDC earned, latency),
and exposes load-balancing helpers for the NexusMind router.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Data model ──────────────────────────────────────────────────────────────


@dataclass
class NodeCapabilities:
    gpu: str = "CPU"
    imina_na: bool = False
    trustformer: bool = False
    max_evaluations_per_hour: int = 100
    min_fee_usdc: float = 0.001
    gpu_allocation_pct: float = 40.0


@dataclass
class NodeStats:
    total_evaluations: int = 0
    evaluations_today: int = 0
    evaluations_this_hour: int = 0
    total_usdc_earned: float = 0.0
    usdc_earned_today: float = 0.0
    avg_latency_ms: float = 0.0
    uptime_pct: float = 99.9
    false_positive_rate: float = 0.018
    accuracy_pct: float = 94.2
    last_evaluation_ts: float = 0.0
    decisions: Dict[str, int] = field(default_factory=lambda: {
        "ALLOW": 0, "BLOCK": 0, "ESCALATE": 0
    })
    # Hourly bucket timestamps — used for per-hour rate limiting
    _hour_bucket: List[float] = field(default_factory=list)


@dataclass
class RegisteredNode:
    node_id: str
    address: str                        # Ethereum-style wallet address
    did: str                            # did:sigui:arc:<address>
    capabilities: NodeCapabilities
    stats: NodeStats = field(default_factory=NodeStats)
    reputation_score: int = 500         # ERC-8259 score (0-1000)
    reputation_confidence: str = "LOW"
    is_sigui_worker: bool = True
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    # Simulated: node is online if heartbeat < 90s ago
    _latency_samples: List[float] = field(default_factory=list)

    # ── TKN compute earnings (classic NexusMind tasks) ───────────────────────
    tkn_balance: float = 0.0
    tkn_earned_today: float = 0.0
    compute_tasks: Dict[str, int] = field(default_factory=lambda: {
        "prime": 0, "hash": 0, "matrix": 0
    })

    @property
    def is_online(self) -> bool:
        return (time.time() - self.last_heartbeat) < 90.0

    @property
    def current_load(self) -> int:
        """Evaluations performed in the last 60 minutes."""
        now = time.time()
        self.stats._hour_bucket = [
            t for t in self.stats._hour_bucket
            if now - t < 3600
        ]
        return len(self.stats._hour_bucket)

    @property
    def is_available(self) -> bool:
        return self.is_online and self.current_load < self.capabilities.max_evaluations_per_hour

    def record_evaluation(
        self,
        decision: str,
        fee_usdc: float,
        latency_ms: float,
    ) -> None:
        s = self.stats
        s.total_evaluations += 1
        s.evaluations_today += 1
        s.evaluations_this_hour += 1
        s.total_usdc_earned += fee_usdc
        s.usdc_earned_today += fee_usdc
        s.last_evaluation_ts = time.time()
        s._hour_bucket.append(time.time())

        d = s.decisions
        if decision in d:
            d[decision] += 1

        # Rolling average latency (last 50 samples)
        self._latency_samples.append(latency_ms)
        if len(self._latency_samples) > 50:
            self._latency_samples = self._latency_samples[-50:]
        s.avg_latency_ms = sum(self._latency_samples) / len(self._latency_samples)

        # Reputation update: good eval → +0.1, avg capped at 1000
        delta = 1 if decision in ("ALLOW", "BLOCK") else 0
        self.reputation_score = min(1000, self.reputation_score + delta)
        self._update_reputation_confidence()

    def _update_reputation_confidence(self) -> None:
        score = self.reputation_score
        if score >= 800:
            self.reputation_confidence = "HIGH"
        elif score >= 600:
            self.reputation_confidence = "MEDIUM"
        elif score >= 400:
            self.reputation_confidence = "LOW"
        else:
            self.reputation_confidence = "INSUFFICIENT"

    def to_dict(self) -> dict:
        s = self.stats
        return {
            "node_id": self.node_id,
            "address": self.address,
            "did": self.did,
            "is_online": self.is_online,
            "is_sigui_worker": self.is_sigui_worker,
            "is_available": self.is_available,
            "reputation_score": self.reputation_score,
            "reputation_confidence": self.reputation_confidence,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "capabilities": {
                "gpu": self.capabilities.gpu,
                "imina_na": self.capabilities.imina_na,
                "trustformer": self.capabilities.trustformer,
                "max_evaluations_per_hour": self.capabilities.max_evaluations_per_hour,
                "min_fee_usdc": self.capabilities.min_fee_usdc,
                "gpu_allocation_pct": self.capabilities.gpu_allocation_pct,
            },
            "stats": {
                "total_evaluations": s.total_evaluations,
                "evaluations_today": s.evaluations_today,
                "evaluations_this_hour": self.current_load,
                "total_usdc_earned": round(s.total_usdc_earned, 4),
                "usdc_earned_today": round(s.usdc_earned_today, 4),
                "avg_latency_ms": round(s.avg_latency_ms, 1),
                "uptime_pct": s.uptime_pct,
                "false_positive_rate": s.false_positive_rate,
                "accuracy_pct": s.accuracy_pct,
                "decisions": s.decisions,
                "last_evaluation_ts": s.last_evaluation_ts,
            },
            "tkn": {
                "balance": round(self.tkn_balance, 4),
                "earned_today": round(self.tkn_earned_today, 4),
                "compute_tasks": self.compute_tasks,
            },
        }


# ── Registry singleton ───────────────────────────────────────────────────────


class NodeRegistry:
    """
    Thread-safe (asyncio) registry of all NexusMind nodes acting as Sigui Workers.
    Holds nodes in memory; persistence can be layered on top via MemoClaw SQLite.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, RegisteredNode] = {}
        self._decisions_log: List[dict] = []  # Rolling last-1000 decisions

        # ── Pre-seed 3 simulated nodes for demo mode ─────────────────────────
        self._seed_demo_nodes()

    def _seed_demo_nodes(self) -> None:
        """Seed realistic demo nodes so the dashboard is never empty."""
        demo_configs = [
            {
                "node_id": "node_001",
                "address": "0x7a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
                "gpu": "AMD MI300X",
                "imina_na": True,
                "max_evals": 500,
                "rep": 742,
                "total_evals": 1247,
                "total_usdc": 1.247,
                "tkn": 1247.83,
                "prime": 1247,
                "hash": 892,
                "matrix": 341,
            },
            {
                "node_id": "node_002",
                "address": "0x1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c",
                "gpu": "CPU",
                "imina_na": False,
                "max_evals": 100,
                "rep": 621,
                "total_evals": 347,
                "total_usdc": 0.347,
                "tkn": 347.20,
                "prime": 420,
                "hash": 315,
                "matrix": 98,
            },
            {
                "node_id": "node_003",
                "address": "0x9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e",
                "gpu": "NVIDIA RTX 4090",
                "imina_na": True,
                "max_evals": 300,
                "rep": 589,
                "total_evals": 89,
                "total_usdc": 0.089,
                "tkn": 89.5,
                "prime": 102,
                "hash": 78,
                "matrix": 31,
            },
        ]
        for cfg in demo_configs:
            caps = NodeCapabilities(
                gpu=cfg["gpu"],
                imina_na=cfg["imina_na"],
                max_evaluations_per_hour=cfg["max_evals"],
            )
            node = RegisteredNode(
                node_id=cfg["node_id"],
                address=cfg["address"],
                did=f"did:sigui:arc:{cfg['address'][:18]}…",
                capabilities=caps,
                reputation_score=cfg["rep"],
                tkn_balance=cfg["tkn"],
                tkn_earned_today=round(cfg["tkn"] * 0.023, 4),
            )
            node._update_reputation_confidence()
            node.stats.total_evaluations = cfg["total_evals"]
            node.stats.evaluations_today = int(cfg["total_evals"] * 0.28)
            node.stats.total_usdc_earned = cfg["total_usdc"]
            node.stats.usdc_earned_today = round(cfg["total_usdc"] * 0.28, 4)
            node.stats.avg_latency_ms = 48.0 if cfg["imina_na"] else 12.0
            node.stats.decisions = {
                "ALLOW": int(cfg["total_evals"] * 0.65),
                "BLOCK": int(cfg["total_evals"] * 0.30),
                "ESCALATE": int(cfg["total_evals"] * 0.05),
            }
            node.compute_tasks = {
                "prime": cfg["prime"],
                "hash": cfg["hash"],
                "matrix": cfg["matrix"],
            }
            # Simulate some hour-bucket activity
            now = time.time()
            evals_this_hour = int(cfg["total_evals"] * 0.04)
            node.stats._hour_bucket = [now - i * 60 for i in range(evals_this_hour)]
            self._nodes[cfg["node_id"]] = node

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def register_node(
        self,
        node_id: Optional[str],
        address: str,
        capabilities: dict,
    ) -> RegisteredNode:
        """Register or update a node. Returns the registered node."""
        nid = node_id or str(uuid.uuid4())[:8]
        caps = NodeCapabilities(
            gpu=capabilities.get("gpu", "CPU"),
            imina_na=capabilities.get("imina_na", False),
            trustformer=capabilities.get("trustformer", False),
            max_evaluations_per_hour=capabilities.get("max_evaluations_per_hour", 100),
            min_fee_usdc=capabilities.get("min_fee_usdc", 0.001),
            gpu_allocation_pct=capabilities.get("gpu_allocation_pct", 40.0),
        )
        if nid in self._nodes:
            # Update capabilities only
            self._nodes[nid].capabilities = caps
            self._nodes[nid].last_heartbeat = time.time()
            return self._nodes[nid]

        node = RegisteredNode(
            node_id=nid,
            address=address,
            did=f"did:sigui:arc:{address[:18]}…",
            capabilities=caps,
        )
        self._nodes[nid] = node
        return node

    def get_node(self, node_id: str) -> Optional[RegisteredNode]:
        return self._nodes.get(node_id)

    def get_all_nodes(self) -> List[RegisteredNode]:
        return list(self._nodes.values())

    def get_active_nodes(self) -> List[RegisteredNode]:
        return [n for n in self._nodes.values() if n.is_online]

    def heartbeat(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        self._nodes[node_id].last_heartbeat = time.time()
        return True

    def update_sigui_settings(
        self,
        node_id: str,
        enabled: bool,
        gpu_allocation_pct: float,
        max_evaluations_per_hour: int,
        min_fee_usdc: float,
    ) -> bool:
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.is_sigui_worker = enabled
        node.capabilities.gpu_allocation_pct = gpu_allocation_pct
        node.capabilities.max_evaluations_per_hour = max_evaluations_per_hour
        node.capabilities.min_fee_usdc = min_fee_usdc
        return True

    # ── Load balancing ───────────────────────────────────────────────────────

    def select_best_node(self, needs_vision: bool = False) -> Optional[RegisteredNode]:
        """
        Select the optimal node for an evaluation request.
        Priority: available → vision-capable if needed → highest reputation.
        """
        candidates = [
            n for n in self._nodes.values()
            if n.is_sigui_worker and n.is_available
        ]
        if needs_vision:
            vision_nodes = [n for n in candidates if n.capabilities.imina_na]
            if vision_nodes:
                candidates = vision_nodes
        if not candidates:
            return None
        return max(candidates, key=lambda n: n.reputation_score)

    # ── Decision log ─────────────────────────────────────────────────────────

    def log_decision(
        self,
        node_id: str,
        agent_id: str,
        decision: str,
        amount_usdc: float,
        pattern: str,
        latency_ms: float,
        fee_usdc: float = 0.001,
    ) -> dict:
        """Record a decision and update node stats. Returns the log entry."""
        entry = {
            "id": str(uuid.uuid4())[:8],
            "ts": time.strftime("%H:%M:%S", time.localtime()),
            "timestamp": time.time(),
            "node_id": node_id,
            "agent_id": agent_id,
            "decision": decision,
            "amount_usdc": amount_usdc,
            "pattern": pattern,
            "latency_ms": latency_ms,
            "fee_usdc": fee_usdc,
        }
        # Update node stats
        node = self._nodes.get(node_id)
        if node:
            node.record_evaluation(decision, fee_usdc, latency_ms)

        self._decisions_log.append(entry)
        if len(self._decisions_log) > 1000:
            self._decisions_log = self._decisions_log[-1000:]
        return entry

    def get_decision_history(self, limit: int = 50) -> List[dict]:
        return list(reversed(self._decisions_log[-limit:]))

    # ── Aggregate stats ──────────────────────────────────────────────────────

    def get_network_stats(self) -> dict:
        nodes = list(self._nodes.values())
        active = [n for n in nodes if n.is_online]

        total_evals_24h = sum(n.stats.evaluations_today for n in nodes)
        total_blocked = sum(n.stats.decisions.get("BLOCK", 0) for n in nodes)
        total_usdc_protected = sum(
            entry["amount_usdc"]
            for entry in self._decisions_log
            if entry["decision"] == "BLOCK"
        )
        usdc_protected_24h = sum(
            entry["amount_usdc"]
            for entry in self._decisions_log
            if entry["decision"] == "BLOCK" and
            (time.time() - entry["timestamp"]) < 86400
        )
        total_usdc_earned = sum(n.stats.total_usdc_earned for n in nodes)
        avg_reputation = (
            sum(n.reputation_score for n in active) // len(active)
            if active else 500
        )
        avg_latency = (
            sum(n.stats.avg_latency_ms for n in active) / len(active)
            if active else 0.0
        )
        block_rate = (
            round(total_blocked / max(1, total_evals_24h) * 100, 1)
            if total_evals_24h > 0 else 0.0
        )

        return {
            "total_nodes": len(nodes),
            "active_nodes": len(active),
            "sigui_worker_nodes": sum(1 for n in active if n.is_sigui_worker),
            "evaluations_24h": total_evals_24h,
            "threats_blocked_24h": total_blocked,
            "block_rate_pct": block_rate,
            "usdc_protected_24h": round(usdc_protected_24h, 2),
            "total_usdc_protected": round(total_usdc_protected, 2),
            "total_usdc_earned_by_nodes": round(total_usdc_earned, 4),
            "avg_reputation_score": avg_reputation,
            "avg_latency_ms": round(avg_latency, 1),
            "imina_na_status": {
                "model": "Imina-Na v2_lora",
                "f1_score": 92.9,
                "avg_latency_ms": 48.0,
                "nodes_with_gpu": sum(
                    1 for n in active if n.capabilities.imina_na
                ),
            },
        }


# ── Module-level singleton ───────────────────────────────────────────────────

node_registry = NodeRegistry()
