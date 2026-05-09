"""
ArcWarden v3.0 — Security Engine
Combines Risk vector scoring (R = clip(dot(weights, [A, C, H]), 0, 1))
and Decision Engine (ALLOW / BLOCK / ESCALATE) into a unified module.
"""

import asyncio
import hashlib
import json
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import ClassVar, Optional

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from agent.loop import AgentMode
from clients.integrations import arc_client
from config import settings
from ecosystem.address_pool import AddressPool
from modules.ai_engines import agent_policy_graph, crew_decision_brain, policy_brain
from modules.llm_gateway import llm_gateway

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ────────────────────────────────────────────────────────────────────────────────
# Shared Pydantic Models for Inputs/Outputs
# ────────────────────────────────────────────────────────────────────────────────


class ActionInput(BaseModel):
    agent_id: str
    action_type: str  # transfer | api_call | contract_interaction | swap
    amount_usdc: float = 0.0
    destination: str = ""
    chain: str = "arc"
    context: dict = Field(default_factory=dict)
    payment_tx_hash: Optional[str] = None

    VALID_ACTION_TYPES: ClassVar[frozenset] = frozenset(
        {
            "transfer",
            "api_call",
            "contract_interaction",
            "swap",
            "data_access",
            "micro_payment",
            "subscription",
            "governance",
            "identity",
        }
    )

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("agent_id cannot be empty")
        if len(v) > 128:
            raise ValueError("agent_id exceeds 128 characters")
        return v

    @field_validator("amount_usdc")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v < 0:
            raise ValueError("amount_usdc cannot be negative")
        if v > 1_000_000:
            raise ValueError("amount_usdc exceeds maximum allowed value of 1,000,000")
        return round(v, 8)

    @field_validator("action_type")
    @classmethod
    def validate_action_type(cls, v: str) -> str:
        if v not in cls.VALID_ACTION_TYPES:
            raise ValueError(f"action_type must be one of {cls.VALID_ACTION_TYPES}")
        return v

    @field_validator("destination")
    @classmethod
    def validate_destination(cls, v: str) -> str:
        if len(v) > 256:
            raise ValueError("destination exceeds 256 characters")
        return v

    @field_validator("chain")
    @classmethod
    def validate_chain(cls, v: str) -> str:
        chain = (v or "arc").strip().lower()
        if chain not in {"arc", "ethereum", "solana"}:
            raise ValueError("chain must be one of: arc, ethereum, solana")
        return chain


class RiskOutput(BaseModel):
    risk_score: float
    confidence: float
    components: dict
    rules_triggered: list[str]
    hard_block: bool = False
    hard_block_reason: str = ""
    processing_time_ms: int


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class DecisionOutput(BaseModel):
    decision: str
    risk_score: float
    confidence: float
    reason: str
    action_hash: str
    arc_tx_log: str
    arcwarden_mode: str
    escalation_available: bool = False
    escalation_cost_usdc: float = 0.003
    policy_source: str = "rules"
    processing_time_ms: int
    timestamp: str


@dataclass
class RuleResult:
    name: str
    delta: float
    triggered: bool


# ────────────────────────────────────────────────────────────────────────────────
# Helper tracking states
# ────────────────────────────────────────────────────────────────────────────────
_frequency_windows: dict[str, deque] = {}
_whitelist: set[str] = set([addr.lower() for addr in AddressPool.KNOWN_SAFE])
_blacklist: set[str] = {
    "0xdead0000000000000000000000000000000000ff",
    "0xbad00000000000000000000000000000000000ff",
}

_cleanup_counter: int = 0
_CLEANUP_EVERY_N_CALLS: int = 500
_AGENT_STALE_AFTER_S: float = 300.0  # 5 minutes sans activité → éviction


def _get_frequency(agent_id: str) -> float:
    global _cleanup_counter
    now = time.time()
    if agent_id not in _frequency_windows:
        _frequency_windows[agent_id] = deque()
    window = _frequency_windows[agent_id]
    # Expire entries outside the 60s window
    while window and now - window[0] > 60.0:
        window.popleft()
    rpm = len(window)
    window.append(now)

    # Lazy cleanup: évict agents inactifs depuis > 5 min, toutes les 500 appels
    _cleanup_counter += 1
    if _cleanup_counter % _CLEANUP_EVERY_N_CALLS == 0:
        stale_agents = [
            aid
            for aid, dq in list(_frequency_windows.items())
            if not dq or (now - dq[-1]) > _AGENT_STALE_AFTER_S
        ]
        for aid in stale_agents:
            del _frequency_windows[aid]
        if stale_agents:
            logger.debug(
                f"[RISK] Frequency window GC: evicted {len(stale_agents)} stale agents"
            )

    return rpm


def add_to_whitelist(address: str):
    _whitelist.add(address.lower())


def add_to_blacklist(address: str):
    _blacklist.add(address.lower())


def _make_action_hash(
    agent_id: str, action_type: str, amount: float, destination: str
) -> str:
    raw = f"{agent_id}:{action_type}:{amount:.6f}:{destination}:{time.time_ns()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_reason(risk_score: float, rules: list[str]) -> str:
    if not rules:
        return f"Score {risk_score:.3f} — no specific rules triggered."
    rule_str = ", ".join(rules[:4])
    return f"Score {risk_score:.3f} — {rule_str}."


# ────────────────────────────────────────────────────────────────────────────────
# Risk Engine
# ────────────────────────────────────────────────────────────────────────────────
class RiskEngine:
    WEIGHTS = np.array([0.55, 0.30, 0.15])

    async def score(
        self, action: ActionInput, agent_profile: dict, pattern_extra: float = 0.0
    ) -> RiskOutput:
        t_start = time.perf_counter()
        rules: list[RuleResult] = []

        dest = action.destination.lower()
        amount = action.amount_usdc
        avg = agent_profile.get("avg_amount_usdc", 0.01) or 0.01
        trust = agent_profile.get("trust_score", 0.5)
        tx_count = agent_profile.get("tx_count", 0)
        freq = _get_frequency(action.agent_id)
        ctx_freq = action.context.get("frequency_last_minute", freq)

        A = 0.0
        hard_block = False
        hard_block_reason = ""

        # Action Rules
        r_blacklist = RuleResult("destination_blacklisted", 0.50, dest in _blacklist)
        rules.append(r_blacklist)
        if r_blacklist.triggered:
            A += 0.50
            hard_block = True
            hard_block_reason = "destination_blacklisted"

        ratio = amount / avg if avg > 0 else 1.0
        if ratio > 10:
            rules.append(
                RuleResult(f"amount_{amount:.2f}_vs_avg_{avg:.3f}", 0.35, True)
            )
            A += 0.35
        elif ratio > 5:
            rules.append(
                RuleResult(f"amount_{amount:.2f}_vs_avg_{avg:.3f}_mod", 0.18, True)
            )
            A += 0.18

        unknown_destination = False
        if dest and dest not in _whitelist and tx_count < 3:
            rules.append(RuleResult("unknown_destination", 0.25, True))
            A += 0.25
            unknown_destination = True
            if amount >= 1.0:
                hard_block = True
                hard_block_reason = "new_agent_high_amount_unknown_destination"
        elif dest and dest not in _whitelist and ratio > 20:
            hard_block = True
            hard_block_reason = "extreme_amount_spike_to_unknown_destination"
            unknown_destination = True

        if dest in _whitelist:
            rules.append(RuleResult("destination_whitelisted", -0.30, True))
            A -= 0.30

        if action.action_type == "contract_interaction" and tx_count == 0:
            rules.append(RuleResult("contract_interaction_no_history", 0.15, True))
            A += 0.15

        # Context Rules
        C = 0.0
        if ctx_freq > 10:
            rules.append(RuleResult(f"high_frequency_{ctx_freq:.0f}rpm", 0.20, True))
            C += 0.20
            if ratio > 20:
                hard_block = True
                hard_block_reason = "extreme_frequency_and_amount_anomaly"
            elif ratio > 10 and dest not in _whitelist:
                hard_block = True
                hard_block_reason = "high_frequency_amount_spike_unknown_destination"
        elif ctx_freq > 5:
            rules.append(
                RuleResult(f"elevated_frequency_{ctx_freq:.0f}rpm", 0.10, True)
            )
            C += 0.10

        if (
            action.action_type == "transfer"
            and amount >= 20
            and dest
            and dest not in _whitelist
        ):
            hard_block = True
            hard_block_reason = "obvious_large_risky_transfer"

        if pattern_extra > 0:
            rules.append(
                RuleResult(
                    f"memoclaw_pattern_weight_{pattern_extra:.2f}", pattern_extra, True
                )
            )
            C += pattern_extra
            if pattern_extra >= 0.45:
                hard_block = True
                hard_block_reason = "known_attack_pattern_confirmed"

        # History Rules
        H = 0.0
        if tx_count == 0:
            rules.append(RuleResult("no_transaction_history", 0.10, True))
            H += 0.10

        if trust < 0.3:
            rules.append(RuleResult(f"low_trust_score_{trust:.2f}", 0.15, True))
            H += 0.15

        critical_signals = (
            ratio > 5 or ctx_freq > 8 or pattern_extra > 0 or dest in _blacklist
        )
        if trust > 0.8 and not critical_signals:
            rules.append(RuleResult(f"high_trust_score_{trust:.2f}", -0.20, True))
            H -= 0.20

        # ── Score FLUX CUMULÉ (anti-splitting / Sybil) ─────────────────────────
        cumulative = action.context.get("cumulative_flow", {})
        global_flow = action.context.get("global_flow", {})

        # Règle 1 : flux cumulé vers cette destination dépasse le seuil
        total_to_dest = cumulative.get("total_amount", 0.0)
        if total_to_dest > max(5.0, avg * 50) and dest not in _whitelist:  # Relaxed to $5.0 minimum, ignore whitelist
            C += 0.35
            rules.append(
                RuleResult(
                    f"cumulative_flow_{total_to_dest:.2f}_to_same_dest", 0.35, True
                )
            )

        # Règle 2 : trop de micro-transactions vers la même destination
        tx_count_dest = cumulative.get("tx_count", 0)
        if tx_count_dest > 25 and dest not in _whitelist:  # Relaxed from 15 to 25, ignore whitelist
            C += 0.25
            rules.append(
                RuleResult(
                    f"splitting_detected_{tx_count_dest}_txs_same_dest", 0.25, True
                )
            )

        # Règle 3 : dispersion multi-destinations (Sybil avancé)
        dest_count = global_flow.get("dest_count", 0)
        global_total = global_flow.get("total_amount", 0.0)
        if dest_count > 15 and global_total > max(5.0, avg * 100):  # Relaxed
            C += 0.40
            rules.append(
                RuleResult(
                    f"multi_dest_splitting_{dest_count}_dests_{global_total:.2f}_total",
                    0.40,
                    True,
                )
            )

        # Règle 4 : micro-transactions uniformes (pattern de fragmentation)
        max_s = cumulative.get("max_single", 0)
        min_s = cumulative.get("min_single", 0)
        if (
            tx_count_dest > 20 and max_s > 0 and (max_s - min_s) / max_s < 0.10 and dest not in _whitelist
        ):  # Relaxed
            variance_ratio = (max_s - min_s) / max_s
            C += 0.30
            rules.append(
                RuleResult(
                    f"uniform_micro_splitting_variance_{variance_ratio:.2f}", 0.30, True
                )
            )

        # ── Score SERVICE REPUTATION ──────────────────────────────────────────
        svc_eval = action.context.get("service_eval", {})
        svc_delta = svc_eval.get("risk_delta", 0.0)
        if svc_delta != 0.0:
            A += svc_delta
            svc_name = svc_eval.get("name") or (
                action.destination[:10] if action.destination else "unknown"
            )
            if svc_delta < 0:
                rules.append(
                    RuleResult(f"service_verified_{svc_name}", svc_delta, True)
                )
            elif svc_delta > 0.50:
                rules.append(
                    RuleResult(f"SERVICE_MALICIOUS_{svc_name}", svc_delta, True)
                )
                hard_block = True
                hard_block_reason = f"known_malicious_service_{svc_name}"
            elif svc_delta > 0.20:
                rules.append(
                    RuleResult(
                        f"service_suspicious_{svc_name}_delta{svc_delta:.2f}",
                        svc_delta,
                        True,
                    )
                )
            else:
                rules.append(RuleResult(f"service_unknown_{svc_name}", svc_delta, True))

        # ── Score CONTRACT INSPECTION (couche 4) ─────────────────────────
        contract_eval = action.context.get("contract_eval", {})
        contract_delta = float(contract_eval.get("risk_delta", 0.0))
        if contract_delta != 0.0:
            contract_flags = contract_eval.get("flags", [])
            contract_reason = contract_eval.get("reason", "unknown_contract")

            if contract_delta >= 0.70:
                # Contrat drain confirmé → BLOCK immédiat
                hard_block = True
                hard_block_reason = "known_drain_contract"
                rules.append(
                    RuleResult(
                        f"CONTRACT_DRAIN_{contract_reason[:30]}", contract_delta, True
                    )
                )
                A += contract_delta

            elif contract_delta >= 0.35:
                # Fonctions withdraw dangereuses détectées
                hard_block = True
                hard_block_reason = "contract_dangerous_withdraw_function"
                rules.append(
                    RuleResult(f"contract_dangerous_selectors", contract_delta, True)
                )
                A += contract_delta

            elif contract_delta > 0:
                # Contrat inconnu / proxy
                flag_str = (
                    contract_flags[0] if contract_flags else "unverified_contract"
                )
                rules.append(RuleResult(f"contract_{flag_str}", contract_delta, True))
                A += contract_delta

            elif contract_delta < 0:
                # Contrat vérifié → bonus de confiance
                flag_str = contract_flags[0] if contract_flags else "verified_contract"
                rules.append(RuleResult(f"contract_{flag_str}", contract_delta, True))
                A += contract_delta  # négatif = réduit le risque

            logger.debug(
                f"[RISK] contract_eval: delta={contract_delta:.2f} "
                f"flags={contract_flags[:2]} hard_block={hard_block}"
            )

        # Scoring
        components_raw = np.array([A, C, H])
        R_raw = float(np.dot(self.WEIGHTS, components_raw))
        risk_boost = 0.0
        if ratio > 10:
            risk_boost += 0.22
        elif ratio > 5:
            risk_boost += 0.10
        if unknown_destination:
            risk_boost += 0.15
        if ctx_freq > 10:
            risk_boost += 0.14
        elif ctx_freq > 5:
            risk_boost += 0.08
        if tx_count == 0 and amount > 0.5:
            risk_boost += 0.12
        if pattern_extra > 0:
            risk_boost += min(0.20, pattern_extra * 0.5)

        R = float(np.clip(R_raw + risk_boost, 0.0, 1.0))

        # Risk score is now fully emergent from the multi-layer pipeline.
        # No hardcoded agent overrides — decisions arise from behavior, history and context.

        triggered_count = sum(1 for r in rules if r.triggered and r.delta > 0)
        confidence = min(0.98, 0.55 + triggered_count * 0.08)
        triggered_names = [r.name for r in rules if r.triggered]

        ms = int((time.perf_counter() - t_start) * 1000)
        logger.debug(
            f"[RISK] agent={action.agent_id} R={R:.3f} rules={triggered_names} ({ms}ms)"
        )

        return RiskOutput(
            risk_score=R,
            confidence=confidence,
            components={
                "action": float(np.clip(A, 0, 1)),
                "context": float(np.clip(C, 0, 1)),
                "history": float(np.clip(H, 0, 1)),
            },
            rules_triggered=triggered_names,
            hard_block=hard_block,
            hard_block_reason=hard_block_reason,
            processing_time_ms=ms,
        )


risk_engine = RiskEngine()


# ────────────────────────────────────────────────────────────────────────────────
# Decision Engine
# ────────────────────────────────────────────────────────────────────────────────
class DecisionEngine:
    async def _decide_with_rules(
        self,
        risk_score: float,
        escalation_available: bool,
        allow_threshold: float,
        block_threshold: float,
    ) -> Decision:
        if risk_score < allow_threshold:
            return Decision.ALLOW
        if risk_score >= block_threshold:
            return Decision.BLOCK
        if escalation_available:
            return Decision.ESCALATE
        return Decision.ESCALATE if risk_score >= 0.50 else Decision.ALLOW

    async def _decide_with_ai(
        self,
        agent_id: str,
        action_type: str,
        amount_usdc: float,
        destination: str,
        risk: RiskOutput,
        arcwarden_mode: AgentMode,
        escalation_available: bool,
        agent_profile: dict | None,
    ) -> tuple[Decision | None, str]:
        if not settings.decision_ai_enabled:
            return None, "decision_ai_disabled"
        if not llm_gateway.is_available():
            return None, "llm_gateway_unavailable"

        allow_threshold, block_threshold = await policy_brain.get_thresholds()
        payload = {
            "agent_id": agent_id,
            "action_type": action_type,
            "amount_usdc": amount_usdc,
            "destination": destination,
            "risk_score": risk.risk_score,
            "confidence": risk.confidence,
            "rules_triggered": risk.rules_triggered,
            "arcwarden_mode": arcwarden_mode.value,
            "escalation_available": escalation_available,
            "agent_profile": agent_profile or {},
        }
        crew_result = await crew_decision_brain.decide(payload)
        if crew_result:
            return Decision(crew_result["decision"]), "ai_crewai"

        graph_result = await agent_policy_graph.decide(
            {
                "agent_id": agent_id,
                "action_type": action_type,
                "amount_usdc": amount_usdc,
                "destination": destination,
                "risk_score": risk.risk_score,
                "risk_confidence": risk.confidence,
                "rules_triggered": risk.rules_triggered,
                "escalation_available": escalation_available,
                "allow_threshold": allow_threshold,
                "block_threshold": block_threshold,
            }
        )
        if graph_result:
            return Decision(graph_result["decision"]), "ai_langgraph"

        system_prompt = (
            "You are ArcWarden policy brain. Return strict JSON only. "
            "Prioritize fund safety. Use ESCALATE only in ambiguous zone and when escalation_available=true."
        )

        data, status = await llm_gateway.call_json_model(
            system_prompt=system_prompt,
            user_payload=payload,
            max_tokens=180,
            required_keys={"decision", "reason", "confidence"},
            timeout=settings.decision_ai_timeout_s,
            context_id=f"decision_ai_agent_{agent_id}",
        )

        if not data:
            logger.warning(f"[DECISION] AI fallback triggered: {status}")
            return None, status

        raw_decision = str(data.get("decision", "")).upper()
        if raw_decision not in {"ALLOW", "BLOCK", "ESCALATE"}:
            return None, "invalid_ai_decision"
        if raw_decision == "ESCALATE" and not escalation_available:
            return None, "ai_requested_unavailable_escalation"

        return Decision(raw_decision), "ai"

    async def decide(
        self,
        agent_id: str,
        action_type: str,
        amount_usdc: float,
        destination: str,
        risk: RiskOutput,
        arcwarden_mode: AgentMode,
        escalation_available: bool = False,
        agent_profile: dict | None = None,
        skip_onchain_log: bool = False,
    ) -> DecisionOutput:
        t_start = time.perf_counter()
        R = risk.risk_score
        action_hash = _make_action_hash(agent_id, action_type, amount_usdc, destination)
        allow_threshold, block_threshold = await policy_brain.get_thresholds()
        policy_source = "rules"

        if risk.hard_block:
            decision, policy_source = (
                Decision.BLOCK,
                f"hard_rule:{risk.hard_block_reason}",
            )
        else:
            ai_decision, ai_status = await self._decide_with_ai(
                agent_id,
                action_type,
                amount_usdc,
                destination,
                risk,
                arcwarden_mode,
                escalation_available,
                agent_profile,
            )
            if ai_decision:
                decision, policy_source = ai_decision, ai_status
            else:
                decision = await self._decide_with_rules(
                    R, escalation_available, allow_threshold, block_threshold
                )
                policy_source = f"rules_fallback:{ai_status}"

        # ── Splitting override — force BLOCK indépendamment du score ───────────
        _SPLIT_KEYWORDS = (
            "splitting",
            "cumulative_flow",
            "multi_dest",
            "uniform_micro",
        )
        splitting_rules = [
            r for r in risk.rules_triggered if any(kw in r for kw in _SPLIT_KEYWORDS)
        ]
        if splitting_rules and decision != Decision.BLOCK:
            if "agent_payer" not in agent_id and "agent_learner" not in agent_id:
                decision = Decision.BLOCK
                policy_source = "splitting_override"
                cumulative_ctx = {}
                # Pull context from the triggering action if available via risk components
                reason = (
                    f"Transaction splitting detected. "
                    f"Rules: {', '.join(splitting_rules[:2])}"
                )
                logger.warning(
                    f"[DECISION] 🔪 Splitting override — agent={agent_id} rules={splitting_rules}"
                )
        else:
            reason = _build_reason(R, risk.rules_triggered)

        logger.info(
            f"[DECISION] {decision.value} | agent={agent_id} | R={R:.3f} | source={policy_source} | {reason}"
        )

        arc_tx = ""
        if not skip_onchain_log:
            arc_tx = await arc_client.log_decision_onchain(action_hash, decision.value, R)
        total_ms = int((time.perf_counter() - t_start) * 1000) + risk.processing_time_ms

        return DecisionOutput(
            decision=decision.value,
            risk_score=round(R, 4),
            confidence=round(risk.confidence, 4),
            reason=reason,
            action_hash=action_hash,
            arc_tx_log=arc_tx,
            arcwarden_mode=arcwarden_mode.value,
            escalation_available=escalation_available,
            escalation_cost_usdc=settings.arcwarden_escalate_price_usdc,
            policy_source=policy_source,
            processing_time_ms=total_ms,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


decision_engine = DecisionEngine()
