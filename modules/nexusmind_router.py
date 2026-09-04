"""
modules/nexusmind_router.py — NexusMind × Sigui Integration Routes

All /nexusmind/* FastAPI endpoints + WebSocket manager for the live
threat feed that powers the Security Dashboard.

Register via: register_routes(app) in modules/gateway.py
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel

from modules.node_registry import node_registry

# FIX #19: _swarms lives at module scope so it survives multiple calls to
# register_nexusmind_routes() (e.g. during test teardown/setup) and is
# accessible from outside the closure if needed.
_swarms: dict = {}


# ── WebSocket connection manager ─────────────────────────────────────────────


class _WSManager:
    """Broadcast manager for the live threat-decision WebSocket feed."""

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)
        logger.info(f"[NEXUSMIND·WS] Client connected — total={len(self._connections)}")

    def disconnect(self, ws: WebSocket) -> None:
        self._connections = [c for c in self._connections if c is not ws]
        logger.info(f"[NEXUSMIND·WS] Client disconnected — total={len(self._connections)}")

    async def broadcast(self, payload: dict) -> None:
        dead: List[WebSocket] = []
        msg = json.dumps(payload)
        for ws in self._connections:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


ws_manager = _WSManager()


# ── Public helper — called by gateway.py after every /evaluate decision ──────


async def broadcast_decision(
    agent_id: str,
    decision: str,
    amount_usdc: float,
    pattern: str,
    latency_ms: float,
    risk_score: float,
    node_id: str = "node_001",
    fee_usdc: float = 0.001,
) -> None:
    """
    Called from gateway.py after every /evaluate to push the decision
    to the NexusMind dashboard in real time.
    Also updates node statistics.
    """
    if not ws_manager.connection_count:
        # Still log to registry even with no WS clients
        node_registry.log_decision(
            node_id=node_id,
            agent_id=agent_id,
            decision=decision,
            amount_usdc=amount_usdc,
            pattern=pattern,
            latency_ms=latency_ms,
            fee_usdc=fee_usdc,
        )
        return

    entry = node_registry.log_decision(
        node_id=node_id,
        agent_id=agent_id,
        decision=decision,
        amount_usdc=amount_usdc,
        pattern=pattern,
        latency_ms=latency_ms,
        fee_usdc=fee_usdc,
    )
    await ws_manager.broadcast({
        "type": "decision",
        "data": entry,
        "network_stats": node_registry.get_network_stats(),
    })


async def broadcast_vision_inference(event: dict) -> None:
    """
    Broadcast a vision_inference event to all WebSocket clients.
    Called automatically by imina_na_vision after each real-or-mock inference.
    """
    if ws_manager.connection_count:
        await ws_manager.broadcast(event)


def setup_vision_broadcast_hook() -> None:
    """
    Wire the broadcast_vision_inference coroutine into the Imina Na vision module
    so that every inference (GPU or heuristic) is pushed to the live WebSocket feed.
    Call once from main.py lifespan after routes are registered.
    """
    try:
        from modules.imina_na_vision import set_vision_broadcast_hook
        set_vision_broadcast_hook(broadcast_vision_inference)
        logger.info("[NEXUSMIND] ✅ Vision broadcast hook wired to Imina Na")
    except Exception as exc:
        logger.warning(f"[NEXUSMIND] Could not wire vision hook: {exc}")


# ── Pydantic request models ──────────────────────────────────────────────────


class RegisterNodeRequest(BaseModel):
    node_id: Optional[str] = None
    address: str
    capabilities: dict = {}


class UpdateSiguiSettingsRequest(BaseModel):
    enabled: bool = True
    gpu_allocation_pct: float = 40.0
    max_evaluations_per_hour: int = 100
    min_fee_usdc: float = 0.001


# ── Route registration ───────────────────────────────────────────────────────


def register_nexusmind_routes(app: FastAPI) -> None:
    """
    Register all /nexusmind/* routes on the FastAPI app.
    Called from modules/gateway.py → register_routes().
    """

    # ── Node management ──────────────────────────────────────────────────────

    @app.post("/nexusmind/nodes/register", tags=["NexusMind"])
    async def register_node(body: RegisterNodeRequest):
        """
        Register a NexusMind node as a Sigui Worker.
        Returns the full node descriptor including DID and initial reputation.
        """
        node = node_registry.register_node(
            node_id=body.node_id,
            address=body.address,
            capabilities=body.capabilities,
        )
        logger.info(f"[NEXUSMIND] Node registered: {node.node_id} addr={body.address[:18]}…")
        return {
            "success": True,
            "node": node.to_dict(),
            "message": f"Node {node.node_id} registered as Sigui Worker",
        }

    @app.get("/nexusmind/nodes", tags=["NexusMind"])
    async def list_nodes():
        """List all registered NexusMind nodes with their Sigui Worker stats."""
        nodes = node_registry.get_all_nodes()
        return {
            "nodes": [n.to_dict() for n in nodes],
            "total": len(nodes),
            "active": sum(1 for n in nodes if n.is_online),
        }

    @app.get("/nexusmind/nodes/{node_id}", tags=["NexusMind"])
    async def get_node(node_id: str):
        """Get full details for a specific NexusMind node."""
        node = node_registry.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return node.to_dict()

    @app.post("/nexusmind/nodes/{node_id}/heartbeat", tags=["NexusMind"])
    async def node_heartbeat(node_id: str):
        """Node heartbeat — keeps the node marked as online."""
        ok = node_registry.heartbeat(node_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        return {"ok": True, "node_id": node_id, "ts": time.time()}

    @app.put("/nexusmind/nodes/{node_id}/sigui-settings", tags=["NexusMind"])
    async def update_sigui_settings(node_id: str, body: UpdateSiguiSettingsRequest):
        """Update Sigui Worker settings for a node (GPU %, max evals, fee)."""
        ok = node_registry.update_sigui_settings(
            node_id=node_id,
            enabled=body.enabled,
            gpu_allocation_pct=body.gpu_allocation_pct,
            max_evaluations_per_hour=body.max_evaluations_per_hour,
            min_fee_usdc=body.min_fee_usdc,
        )
        if not ok:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        node = node_registry.get_node(node_id)
        return {"success": True, "node": node.to_dict() if node else {}}

    @app.get("/nexusmind/nodes/{node_id}/earnings", tags=["NexusMind"])
    async def get_node_earnings(node_id: str):
        """Get USDC + TKN earnings breakdown for a node."""
        node = node_registry.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
        s = node.stats
        return {
            "node_id": node_id,
            "tkn": {
                "balance": node.tkn_balance,
                "earned_today": node.tkn_earned_today,
                "compute_tasks": node.compute_tasks,
            },
            "usdc": {
                "total_earned": round(s.total_usdc_earned, 4),
                "earned_today": round(s.usdc_earned_today, 4),
                "total_evaluations": s.total_evaluations,
                "evaluations_today": s.evaluations_today,
                "avg_fee_per_eval": round(
                    s.total_usdc_earned / max(1, s.total_evaluations), 6
                ),
            },
        }

    # ── Security / Network stats ─────────────────────────────────────────────

    @app.get("/nexusmind/stats", tags=["NexusMind"])
    async def get_network_stats():
        """Aggregated security stats for the NexusMind × Sigui network."""
        return node_registry.get_network_stats()

    @app.get("/nexusmind/threats/history", tags=["NexusMind"])
    async def get_threats_history(limit: int = 50):
        """Last N security decisions across all nodes (newest first)."""
        limit = min(limit, 200)
        return {
            "decisions": node_registry.get_decision_history(limit),
            "total_logged": len(node_registry._decisions_log),
        }

    @app.get("/nexusmind/model/status", tags=["NexusMind"])
    async def get_model_status():
        """
        Imina-Na vision model status — version, F1, latency, GPU availability.
        """
        try:
            from modules.imina_na_vision import imina_na_vision
            gpu_ready = getattr(imina_na_vision, "_gpu_ready", False)
            model_name = getattr(imina_na_vision, "_model_name", "imina-na-v2-lora")
        except Exception:
            gpu_ready = False
            model_name = "imina-na-v2-lora"

        nodes = node_registry.get_active_nodes()
        gpu_nodes = [n for n in nodes if n.capabilities.imina_na]

        return {
            "model": "Imina-Na v2_lora",
            "model_id": model_name,
            "f1_score": 92.9,
            "precision": 93.7,
            "recall": 92.1,
            "avg_latency_ms": 48.0,
            "gpu_active": gpu_ready,
            "hardware": "AMD MI300X" if gpu_ready else "CPU heuristic fallback",
            "serving": "vLLM" if gpu_ready else "rule-based",
            "nodes_running_vision": len(gpu_nodes),
            "attack_patterns": ["DRAIN_STAR", "MIXING_CHAIN", "COORDINATED_CLUSTER", "NORMAL"],
            "dataset_size": 1_000_000,
            "training_framework": "LLaMA-Factory LoRA",
        }

    @app.post("/nexusmind/security/audit", tags=["NexusMind"])
    async def run_security_audit():
        """
        Launch a network-wide security audit.
        Analyzes nodes for suspicious evaluation patterns.
        """
        nodes = node_registry.get_all_nodes()
        results = []
        for node in nodes:
            s = node.stats
            total = s.total_evaluations or 1
            block_rate = s.decisions.get("BLOCK", 0) / total
            # Flag nodes with suspiciously high or low block rates
            if block_rate > 0.6:
                status = "SUSPICIOUS_HIGH_BLOCK"
            elif block_rate < 0.01 and s.total_evaluations > 50:
                status = "SUSPICIOUS_LOW_BLOCK"
            else:
                status = "HEALTHY"
            results.append({
                "node_id": node.node_id,
                "status": status,
                "block_rate": round(block_rate, 3),
                "total_evaluations": s.total_evaluations,
                "avg_latency_ms": round(s.avg_latency_ms, 1),
                "reputation_score": node.reputation_score,
            })

        healthy = sum(1 for r in results if r["status"] == "HEALTHY")
        suspicious = len(results) - healthy

        return {
            "audit_id": f"audit_{int(time.time())}",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "nodes_audited": len(results),
            "healthy": healthy,
            "suspicious": suspicious,
            "results": results,
            "summary": (
                f"Network audit complete. {healthy}/{len(results)} nodes healthy. "
                f"{suspicious} node(s) flagged for review."
            ),
        }

    # ── Wallet ───────────────────────────────────────────────────────────────

    @app.get("/nexusmind/wallet/balance", tags=["NexusMind"])
    async def get_wallet_balance(node_id: str = "node_001"):
        """TKN + USDC balance for a node's dual wallet."""
        node = node_registry.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        s = node.stats
        return {
            "node_id": node_id,
            "tkn": {
                "balance": node.tkn_balance,
                "approx_usdc": round(node.tkn_balance * 0.01, 2),
                "earned_7d": round(node.tkn_balance * 0.68, 4),
                "staking_rewards_7d": round(node.tkn_balance * 0.01, 4),
            },
            "usdc": {
                "balance": round(s.total_usdc_earned, 4),
                "earned_7d": round(s.usdc_earned_today * 7, 4),
                "source": "sigui_evaluations",
                "circle_wallet": node.address,
            },
        }

    @app.get("/nexusmind/wallet/earnings", tags=["NexusMind"])
    async def get_wallet_earnings(node_id: str = "node_001", period: str = "7d"):
        """
        Historical earnings breakdown (TKN + USDC) for chart rendering.

        NOTE: Returns **simulated** data generated with a fixed seed (random.seed(42)).
        Values are identical on every call and are used for dashboard visualisation only.
        Replace with real DB queries when historical earnings storage is implemented.
        """
        import random
        random.seed(42)
        days = 30 if period == "30d" else 7
        data = []
        for i in range(days):
            data.append({
                "day": i,
                "label": f"Day -{days - i}",
                "tkn": round(random.uniform(80, 180), 1),
                "usdc": round(random.uniform(0.04, 0.18), 4),
            })
        return {"period": period, "data": data, "simulated": True}

    # ── Identity / ERC-8259 ──────────────────────────────────────────────────

    @app.get("/nexusmind/identity/{node_id}", tags=["NexusMind"])
    async def get_node_identity(node_id: str):
        """ERC-8259 identity and reputation data for a node."""
        node = node_registry.get_node(node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Node not found")
        s = node.stats

        # Build reputation history (simulated sparkline)
        import random
        random.seed(node.reputation_score)
        history = []
        score = max(400, node.reputation_score - 180)
        for i in range(30):
            score = min(1000, score + random.randint(-3, 8))
            history.append({"day": i, "score": score})

        return {
            "node_id": node_id,
            "did": node.did,
            "address": node.address,
            "reputation": {
                "score": node.reputation_score,
                "max": 1000,
                "confidence": node.reputation_confidence,
                "normalized_pct": round(node.reputation_score / 10, 1),
            },
            "breakdown": {
                "evaluations_accuracy_pct": s.accuracy_pct,
                "uptime_30d_pct": s.uptime_pct,
                "false_positive_rate_pct": round(s.false_positive_rate * 100, 2),
                "stake_collateral_tkn": 10.0,
            },
            "model_hash": "0x8f3ac2d1e4b5a6f7c8d9e0a1b2c3d4e5f6a7b8c9",
            "model_name": "Imina-Na v2_lora",
            "verification_tier": "SILVER" if node.reputation_score >= 600 else "BRONZE",
            "registered_at": node.registered_at,
            "history": history,
        }

    # ── Marketplace ──────────────────────────────────────────────────────────

    @app.get("/nexusmind/marketplace/plans", tags=["NexusMind"])
    async def get_marketplace_plans():
        """Sigui API subscription plans for the Marketplace module."""
        return {
            "plans": [
                {
                    "id": "free",
                    "name": "Free Tier",
                    "price_usdc_month": 0,
                    "evaluations_month": 100,
                    "vision_layer": False,
                    "rate_limit_per_minute": 5,
                    "priority_routing": False,
                    "sla_ms": None,
                    "current": True,
                },
                {
                    "id": "hogon",
                    "name": "Hogon",
                    "price_usdc_month": 29,
                    "evaluations_month": 10_000,
                    "vision_layer": True,
                    "rate_limit_per_minute": 100,
                    "priority_routing": False,
                    "sla_ms": None,
                    "current": False,
                },
                {
                    "id": "enterprise",
                    "name": "Sigui Enterprise",
                    "price_usdc_month": 199,
                    "evaluations_month": -1,  # unlimited
                    "vision_layer": True,
                    "rate_limit_per_minute": -1,  # unlimited
                    "priority_routing": True,
                    "sla_ms": 50,
                    "current": False,
                },
            ],
            "ai_models": [
                {
                    "id": "imina_na_v2",
                    "name": "Imina-Na v2_lora",
                    "description": "Vision model for topology-based attack detection",
                    "available": True,
                    "license": "MIT",
                },
                {
                    "id": "trustformer",
                    "name": "Trustformer",
                    "description": "Transformer-based cross-chain reputation scoring",
                    "available": False,
                    "coming_soon": True,
                },
            ],
        }

    # ── Swarm / Research ─────────────────────────────────────────────────────
    # FIX #19: _swarms is now a module-level variable (see top of file)

    @app.get("/nexusmind/swarm", tags=["NexusMind"])
    async def list_swarms():
        """List active research swarms protected by Sigui."""
        return {"swarms": list(_swarms.values()), "total": len(_swarms)}

    @app.post("/nexusmind/swarm", tags=["NexusMind"])
    async def create_swarm(body: dict):
        """Create a new agent swarm with Sigui protection enabled."""
        import uuid as _uuid
        swarm_id = f"swarm_{str(_uuid.uuid4())[:6]}"
        swarm = {
            "id": swarm_id,
            "name": body.get("name", f"Swarm {len(_swarms) + 1}"),
            "framework": body.get("framework", "langchain"),
            "agent_count": body.get("agent_count", 3),
            "sigui_protection": body.get("sigui_protection", True),
            "threshold": body.get("threshold", 0.70),
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "status": "active",
            "stats": {
                "transactions_today": 0,
                "blocked_today": 0,
                "usdc_protected": 0.0,
            },
        }
        _swarms[swarm_id] = swarm
        logger.info(f"[NEXUSMIND] Swarm created: {swarm_id}")
        return {"success": True, "swarm": swarm}

    @app.get("/nexusmind/swarm/{swarm_id}/integration-code", tags=["NexusMind"])
    async def get_swarm_integration_code(swarm_id: str):
        """Auto-generate sigui-sdk integration code for a swarm."""
        swarm = _swarms.get(swarm_id)
        if not swarm:
            raise HTTPException(status_code=404, detail="Swarm not found")
        framework = swarm.get("framework", "langchain")

        if framework == "langchain":
            code = f'''from sigui import SiguiClient
from sigui.integrations.langchain import create_langchain_tool

client = SiguiClient(
    api_url="https://network.sigui.io",
    agent_id="{swarm_id}_agent_alice",
)
sigui_tool = create_langchain_tool(client)
# Add sigui_tool to your LangChain agent tools list'''
        elif framework == "crewai":
            code = f'''from sigui import SiguiClient
from sigui.integrations.crewai import SiguiCrewTool

client = SiguiClient(
    api_url="https://network.sigui.io",
    agent_id="{swarm_id}_crew_agent",
)
sigui_tool = SiguiCrewTool(client=client)'''
        else:
            code = f'''from sigui import SiguiClient

async with SiguiClient(
    api_url="https://network.sigui.io",
    agent_id="{swarm_id}_agent",
) as client:
    result = await client.evaluate(amount=100.0, destination="0xabc...")
    if result.is_safe:
        # proceed'''

        return {"swarm_id": swarm_id, "framework": framework, "code": code}

    @app.delete("/nexusmind/swarm/{swarm_id}", tags=["NexusMind"])
    async def stop_swarm(swarm_id: str):
        if swarm_id not in _swarms:
            raise HTTPException(status_code=404, detail="Swarm not found")
        _swarms[swarm_id]["status"] = "stopped"
        return {"success": True, "swarm_id": swarm_id}

    # ── WebSocket — Live Decision Feed ───────────────────────────────────────

    @app.websocket("/nexusmind/ws/decisions")
    async def ws_decisions(websocket: WebSocket):
        """
        WebSocket endpoint for the NexusMind live threat feed.
        Sends real decisions from /evaluate + periodic heartbeats.
        """
        await ws_manager.connect(websocket)
        # Send current network state immediately on connect
        try:
            await websocket.send_text(json.dumps({
                "type": "init",
                "network_stats": node_registry.get_network_stats(),
                "recent_decisions": node_registry.get_decision_history(20),
                "nodes": [n.to_dict() for n in node_registry.get_all_nodes()],
            }))
            # Keep alive loop — send heartbeat every 15s
            while True:
                await asyncio.sleep(15)
                await websocket.send_text(json.dumps({
                    "type": "heartbeat",
                    "ts": time.time(),
                    "network_stats": node_registry.get_network_stats(),
                }))
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)
    # ── WebSocket — Tracker for Real P2P Nodes ───────────────────────────────

    class _TrackerManager:
        def __init__(self):
            self.nodes = {}  # port -> websocket

        async def connect(self, port: int, ws: WebSocket):
            await ws.accept()
            self.nodes[port] = ws
            await self.broadcast_peers()

        # FIX #5: disconnect() is now async so asyncio.create_task() is never
        # called from a synchronous context (which would raise RuntimeError if
        # no event loop is running). Callers must await disconnect().
        async def disconnect(self, port: int):
            if port in self.nodes:
                del self.nodes[port]
            await self.broadcast_peers()

        async def broadcast_peers(self):
            peers = list(self.nodes.keys())
            dead = []
            for p, ws in self.nodes.items():
                try:
                    await ws.send_text(json.dumps({"type": "peer_list", "peers": peers}))
                except:
                    dead.append(p)
            for d in dead:
                await self.disconnect(d)

        async def dispatch_task(self):
            """Continuously send real compute tasks to connected nodes."""
            import random
            import uuid
            while True:
                await asyncio.sleep(random.uniform(2, 5))
                if not self.nodes:
                    continue

                target_port = random.choice(list(self.nodes.keys()))
                ws = self.nodes[target_port]
                task_id = f"compute_{str(uuid.uuid4())[:8]}"
                task_type = random.choice(["prime", "hash", "matrix"])

                try:
                    await ws.send_text(json.dumps({
                        "type": "task",
                        "task_id": task_id,
                        "task_type": task_type,
                        "payload": {"target": random.randint(5000, 15000)} if task_type == "prime" else {"data": "sigui_block", "difficulty": random.randint(3, 5)}
                    }))
                    logger.info(f"[TRACKER] Dispatched {task_type} task {task_id} to node on port {target_port}")
                except Exception:
                    await self.disconnect(target_port)

    tracker = _TrackerManager()

    # Store at module level so start_tracker_dispatch() can access it (FIX #4)
    import modules.nexusmind_router as _self_module
    _self_module._tracker_instance = tracker

    # FIX #4: removed @app.on_event("startup") — deprecated since FastAPI 0.93
    # and unsafe when register_nexusmind_routes() is called after app creation.
    # tracker.dispatch_task() is now started from main.py lifespan instead via
    # start_tracker_dispatch().

    @app.websocket("/nexusmind/ws/tracker")
    async def ws_tracker(websocket: WebSocket):
        """Bootstrap and Tracker endpoint for real P2P NexusMind nodes."""
        await websocket.accept()
        # Wait for announce
        try:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg.get("type") == "announce":
                port = msg.get("port")
                node_id = msg.get("node_id")
                tracker.nodes[port] = websocket
                await tracker.broadcast_peers()
                logger.info(f"[TRACKER] Node {node_id} joined on port {port}")

                while True:
                    res_data = await websocket.receive_text()
                    res = json.loads(res_data)
                    if res.get("type") == "task_result":
                        logger.success(f"[TRACKER] Node {res['node_id']} completed {res['task_id']} in {res['latency_ms']:.1f}ms")
                        # Broadcast this back to the UI dashboard
                        await ws_manager.broadcast({
                            "type": "compute_result",
                            "node_id": res["node_id"],
                            "task_id": res["task_id"],
                            "latency_ms": res["latency_ms"]
                        })
        except WebSocketDisconnect:
            # FIX #5: await async disconnect
            if msg.get("port") in tracker.nodes:
                await tracker.disconnect(msg.get("port"))
        except Exception as e:
            logger.error(f"[TRACKER] WS Error: {e}")

    logger.info("[NEXUSMIND] Routes registered — /nexusmind/* + ws://…/nexusmind/ws/decisions + /ws/tracker")

# Module-level holder for the tracker created inside register_nexusmind_routes()
_tracker_instance = None


async def start_tracker_dispatch() -> None:
    """Launch the tracker dispatch loop.

    Call this once from main.py lifespan AFTER register_nexusmind_routes() has run.
    This replaces the deprecated @app.on_event("startup") handler (FIX #4).
    """
    if _tracker_instance is not None:
        asyncio.create_task(_tracker_instance.dispatch_task())
        logger.info("[NEXUSMIND] Tracker dispatch loop started")
    else:
        logger.warning("[NEXUSMIND] start_tracker_dispatch() called before routes were registered")
