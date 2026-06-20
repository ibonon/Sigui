"""
Sigui v3.0 — AI Engines
Combines policy critique, crew decision fallback, agent graph logic, and Claude escalation.
"""

import asyncio
import json
from typing import Any, TypedDict

from loguru import logger
from pydantic import BaseModel

from agent.loop import AgentMode
from config import settings
from modules.llm_gateway import LebeGateway, lebe_gateway, llm_gateway
from modules.memory import memory

# Optional dependencies
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("[AI] anthropic SDK not installed")

try:
    from crewai import LLM as CrewLLM
    from crewai import Agent, Crew, Process, Task

    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    CrewLLM = None  # type: ignore

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


# ────────────────────────────────────────────────────────────────────────────────
# Policy Brain (Self-critique & Dynamic Thresholds)
# ────────────────────────────────────────────────────────────────────────────────
class PolicyBrain:
    def __init__(self):
        self.allow_threshold = settings.risk_allow_threshold
        self.block_threshold = settings.risk_block_threshold
        self._lock = asyncio.Lock()

    async def initialize(self):
        # 1. Try loading from Hogonat DAO (on-chain or mock) — governance source of truth
        try:
            from governance.hogonat_client import hogonat_client
            dao_allow, dao_block = await hogonat_client.get_thresholds()
            async with self._lock:
                self.allow_threshold = dao_allow
                self.block_threshold = dao_block
            mode = "on-chain" if not hogonat_client.mock_mode else "mock"
            logger.info(
                f"[POLICY_BRAIN] thresholds from Hogonat ({mode}) "
                f"allow<{dao_allow:.3f} block>={dao_block:.3f}"
            )
        except Exception as exc:
            logger.warning(f"[POLICY_BRAIN] Hogonat unavailable ({exc}) — falling back to memory")
            # 2. Fallback: last recorded policy update in MemoClaw
            latest = await memory.get_latest_policy_update()
            if latest:
                async with self._lock:
                    self.allow_threshold = float(
                        latest.get("allow_threshold", self.allow_threshold)
                    )
                    self.block_threshold = float(
                        latest.get("block_threshold", self.block_threshold)
                    )
                logger.info(
                    f"[POLICY_BRAIN] loaded thresholds from memory "
                    f"allow<{self.allow_threshold:.3f} block>={self.block_threshold:.3f}"
                )

    async def get_thresholds(self) -> tuple[float, float]:
        """Returns thresholds, refreshing from Hogonat DAO if available."""
        try:
            from governance.hogonat_client import hogonat_client
            dao_allow, dao_block = await hogonat_client.get_thresholds()
            async with self._lock:
                self.allow_threshold = dao_allow
                self.block_threshold = dao_block
        except Exception:
            pass  # Use cached values
        async with self._lock:
            return self.allow_threshold, self.block_threshold

    async def _fallback_adjustment(
        self, episodes: list[dict]
    ) -> tuple[float, float, str]:
        allow_th, block_th = await self.get_thresholds()
        risky_allow = sum(
            1
            for e in episodes
            if e["decision"] == "ALLOW" and float(e["risk_score"]) >= block_th
        )
        safe_block = sum(
            1
            for e in episodes
            if e["decision"] == "BLOCK" and float(e["risk_score"]) < allow_th
        )
        if risky_allow > safe_block and risky_allow > 2:
            allow_th = max(0.2, allow_th - 0.02)
            block_th = max(allow_th + 0.1, block_th - 0.01)
            return allow_th, block_th, "tightened after risky ALLOW streak"
        if safe_block > risky_allow and safe_block > 2:
            allow_th = min(0.45, allow_th + 0.01)
            block_th = min(0.8, block_th + 0.01)
            return allow_th, block_th, "relaxed after excessive safe BLOCKs"
        return allow_th, block_th, "no significant drift detected"

    async def self_critique(self):
        """
        AI-driven policy adjustment.
        Only runs if LLM is available and credits are not exhausted.
        """
        episodes = await memory.get_recent_episodes(300)
        if len(episodes) < 20:
            return
        allow_th, block_th = await self.get_thresholds()
        new_allow, new_block, rationale = allow_th, block_th, "unchanged"

        if llm_gateway.is_available():
            prompt = {
                "current_allow_threshold": allow_th,
                "current_block_threshold": block_th,
                "episodes": episodes[:120],
                "constraints": {
                    "allow_range": [0.20, 0.50],
                    "block_range": [0.50, 0.90],
                    "gap_min": 0.10,
                },
            }
            system = "You are Sigui self-critique engine. Return only JSON."

            data, status = await llm_gateway.call_json_model(
                system_prompt=system,
                user_payload=prompt,
                max_tokens=150,
                required_keys={"allow_threshold", "block_threshold", "rationale"},
                timeout=4.0,
                context_id="policy_brain_self_critique",
            )

            if data:
                new_allow = float(data.get("allow_threshold", allow_th))
                new_block = float(data.get("block_threshold", block_th))
                rationale = str(data.get("rationale", "ai_update"))
            else:
                if status == "credits_exhausted":
                    logger.warning("[POLICY_BRAIN] AI critique disabled (Out of credits). Using rule-based fallback.")
                else:
                    logger.warning(f"[POLICY_BRAIN] AI critique fallback: {status}")
                
                new_allow, new_block, rationale = await self._fallback_adjustment(
                    episodes
                )
        else:
            new_allow, new_block, rationale = await self._fallback_adjustment(episodes)

        new_allow = min(0.50, max(0.20, new_allow))
        new_block = min(0.90, max(new_allow + 0.10, new_block))
        changed = (
            abs(new_allow - allow_th) >= 0.001 or abs(new_block - block_th) >= 0.001
        )
        if not changed:
            await memory.record_policy_update(
                allow_th,
                block_th,
                f"observation_only:{rationale}",
                source="self_critique_observe",
            )
            return

        async with self._lock:
            self.allow_threshold = new_allow
            self.block_threshold = new_block
        await memory.record_policy_update(
            new_allow, new_block, rationale, source="self_critique"
        )
        logger.info(
            f"[POLICY_BRAIN] thresholds updated allow<{new_allow:.3f} block>={new_block:.3f} reason={rationale}"
        )


# ────────────────────────────────────────────────────────────────────────────────
# CrewBrain (Multiple AI Agents Fallback)
# ────────────────────────────────────────────────────────────────────────────────
class CrewDecisionBrain:
    def __init__(self):
        self.available = CREWAI_AVAILABLE and settings.crewai_enabled

    async def decide(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self.available:
            return None
        if not ANTHROPIC_AVAILABLE or settings.anthropic_api_key == "demo_key":
            return None
        if CrewLLM is None:
            return None

        # ── Build Claude LLM via CrewAI native LLM class ─────────────────
        try:
            crew_llm = CrewLLM(
                model=f"anthropic/{settings.decision_ai_model}",
                api_key=settings.anthropic_api_key,
                timeout=settings.decision_ai_timeout_s + 3,
                max_tokens=512,
            )
        except Exception as exc:
            logger.warning(f"[CREW_BRAIN] Failed to build CrewLLM: {exc}")
            return None

        episodes = await memory.get_recent_episodes(100)
        recent_for_agent = [
            e for e in episodes if e.get("agent_id") == payload.get("agent_id")
        ][:15]
        memory_note = (
            f"episodes={len(recent_for_agent)}, "
            f"risky_allow={sum(1 for e in recent_for_agent if e.get('outcome_label') == 'risky_allow')}, "
            f"safe_block={sum(1 for e in recent_for_agent if e.get('outcome_label') == 'safe_block')}"
        )

        attacker = Agent(
            role="Red Team Attacker",
            goal="Identify potential security exploits, fraud patterns, or policy violations.",
            backstory="Expert in blockchain forensic analysis and exploit detection. Your job is to be paranoid and find any reason why this transaction could be malicious.",
            allow_delegation=False,
            verbose=False,
            llm=crew_llm,
        )
        defender = Agent(
            role="Blue Team Defender",
            goal="Identify legitimate use cases and justify why the transaction is benign.",
            backstory="Expert in blockchain UX and decentralized finance applications. Your job is to find plausible reasons why this transaction is legitimate and safe.",
            allow_delegation=False,
            verbose=False,
            llm=crew_llm,
        )
        judge = Agent(
            role="Tribunal Judge",
            goal="Synthesize arguments from Attacker and Defender to provide a final balanced verdict.",
            backstory="Experienced security auditor and supreme judge of the Sigui protocol. You prioritize fund safety but avoid unnecessary friction. You must return strict JSON.",
            allow_delegation=False,
            verbose=False,
            llm=crew_llm,
        )

        attack_task = Task(
            description=(
                "Analyze this action for potential threats. Find any reason to BLOCK it. "
                f"Input JSON: {json.dumps(payload)}. Memory note: {memory_note}"
            ),
            expected_output="A list of specific security risks and exploit patterns found.",
            agent=attacker,
        )
        defense_task = Task(
            description=(
                "Analyze this action for legitimacy. Find any reason to ALLOW it. "
                f"Input JSON: {json.dumps(payload)}. Memory note: {memory_note}"
            ),
            expected_output="A list of reasons why this transaction is likely legitimate or follows safe patterns.",
            agent=defender,
        )
        judgment_task = Task(
            description=(
                "Evaluate the arguments from the Attacker and Defender. "
                "Provide a final decision (ALLOW/BLOCK/ESCALATE) with confidence and a short synthesized reason. "
                "PRIORITIZE FUND SAFETY. Return final JSON only. "
                "Include the key points from the attacker and defender in the 'tribunal_notes' field."
            ),
            expected_output='JSON: {"decision":"ALLOW|BLOCK|ESCALATE","confidence":0.0,"reason":"...", "tribunal_notes": {"attacker": "...", "defender": "..."}}',
            agent=judge,
            context=[attack_task, defense_task],
        )

        crew = Crew(
            agents=[attacker, defender, judge],
            tasks=[attack_task, defense_task, judgment_task],
            process=Process.sequential,
            verbose=False,
        )

        try:
            async with asyncio.timeout(settings.decision_ai_timeout_s + 3):
                logger.debug(
                    f"[CREW_BRAIN] Launching 3-agent crew for agent={payload.get('agent_id')} R={payload.get('risk_score', 0):.3f}"
                )
                result = await crew.kickoff_async()
            text = str(result).strip()
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                return None
            data = json.loads(text[start : end + 1])
            decision = str(data.get("decision", "")).upper()
            if decision not in {"ALLOW", "BLOCK", "ESCALATE"}:
                return None
            if decision == "ESCALATE" and not bool(
                payload.get("escalation_available", False)
            ):
                return None
            return {
                "decision": decision,
                "reason": str(data.get("reason", "CrewAI final decision"))[:140],
                "confidence": float(data.get("confidence", 0.7)),
                "source": "crewai",
                "tribunal_notes": data.get("tribunal_notes")
            }
        except Exception as exc:
            logger.warning(f"[CREW_BRAIN] execution failed: {exc}")
            return None


# ────────────────────────────────────────────────────────────────────────────────
# Agent Graph (Logic Nodes)
# ────────────────────────────────────────────────────────────────────────────────
class DecisionState(TypedDict, total=False):
    agent_id: str
    action_type: str
    amount_usdc: float
    destination: str
    risk_score: float
    risk_confidence: float
    rules_triggered: list[str]
    escalation_available: bool
    allow_threshold: float
    block_threshold: float
    memory_summary: str
    decision: str
    reason: str
    llm_confidence: float


class AgentPolicyGraph:
    def __init__(self):
        self.available = LANGGRAPH_AVAILABLE
        self._graph = self._build_graph() if self.available else None

    def _build_graph(self):
        graph = StateGraph(DecisionState)
        graph.add_node("retrieve_memory", self._retrieve_memory)
        graph.add_node("reason_and_decide", self._reason_and_decide)
        graph.add_edge("retrieve_memory", "reason_and_decide")
        graph.add_edge("reason_and_decide", END)
        graph.set_entry_point("retrieve_memory")
        return graph.compile()

    async def _retrieve_memory(self, state: DecisionState) -> DecisionState:
        episodes = await memory.get_recent_episodes(120)
        agent_id = state.get("agent_id", "")
        recent = [e for e in episodes if e.get("agent_id") == agent_id][:20]
        if not recent:
            summary = "No prior episodic records for this agent."
        else:
            allow_n = sum(1 for e in recent if e.get("decision") == "ALLOW")
            block_n = sum(1 for e in recent if e.get("decision") == "BLOCK")
            risky_allow = sum(
                1 for e in recent if e.get("outcome_label") == "risky_allow"
            )
            safe_block = sum(
                1 for e in recent if e.get("outcome_label") == "safe_block"
            )
            summary = (
                f"Recent episodes={len(recent)}, allow={allow_n}, block={block_n}, "
                f"risky_allow={risky_allow}, safe_block={safe_block}"
            )
        return {"memory_summary": summary}

    async def _reason_and_decide(self, state: DecisionState) -> DecisionState:
        risk = float(state.get("risk_score", 0.0))
        allow_threshold = float(state.get("allow_threshold", 0.35))
        block_threshold = float(state.get("block_threshold", 0.65))
        escalation_available = bool(state.get("escalation_available", False))

        if not llm_gateway.is_available():
            if risk < allow_threshold:
                decision = "ALLOW"
            elif risk >= block_threshold:
                decision = "BLOCK"
            elif escalation_available:
                decision = "ESCALATE"
            else:
                decision = "BLOCK" if risk >= 0.55 else "ALLOW"
            return {
                "decision": decision,
                "reason": "Graph fallback heuristic decision.",
                "llm_confidence": 0.6,
            }

        payload = {
            "action": {
                "agent_id": state.get("agent_id"),
                "action_type": state.get("action_type"),
                "amount_usdc": state.get("amount_usdc"),
                "destination": state.get("destination"),
            },
            "risk": {
                "score": risk,
                "confidence": state.get("risk_confidence"),
                "rules_triggered": state.get("rules_triggered", []),
            },
            "policy": {
                "allow_threshold": allow_threshold,
                "block_threshold": block_threshold,
                "escalation_available": escalation_available,
            },
            "memory_summary": state.get("memory_summary", ""),
        }
        system = "You are Sigui policy graph node. Return ONLY JSON."

        data, status = await llm_gateway.call_json_model(
            system_prompt=system,
            user_payload=payload,
            max_tokens=180,
            required_keys={"decision", "reason", "confidence"},
            timeout=settings.decision_ai_timeout_s,
            context_id=f"agent_graph_decision",
        )

        if not data:
            return {
                "decision": "BLOCK",
                "reason": f"Graph model fallback ({status})",
                "llm_confidence": 0.6,
            }

        return {
            "decision": str(data.get("decision", "BLOCK")).upper(),
            "reason": str(data.get("reason", "Graph model decision"))[:120],
            "llm_confidence": float(data.get("confidence", 0.7)),
        }

    async def decide(self, state: DecisionState) -> dict[str, Any] | None:
        if not self.available or self._graph is None:
            return None
        try:
            out = await self._graph.ainvoke(state)
            decision = str(out.get("decision", "")).upper()
            if decision not in {"ALLOW", "BLOCK", "ESCALATE"}:
                return None
            if decision == "ESCALATE" and not bool(
                state.get("escalation_available", False)
            ):
                return None
            return {
                "decision": decision,
                "reason": out.get("reason", "Graph decision"),
                "confidence": float(out.get("llm_confidence", 0.7)),
                "source": "langgraph",
            }
        except Exception as exc:
            logger.warning(f"[AGENT_GRAPH] graph execution failed: {exc}")
            return None


# ────────────────────────────────────────────────────────────────────────────────
# Escalation Engine (Claude deep analysis)
# ────────────────────────────────────────────────────────────────────────────────
ESCALATION_PROMPT = """Tu es le système d'escalation de Sigui, un agent de sécurité autonome
qui protège les paiements USDC des agents IA sur le réseau Arc.

Analyse l'action soumise et retourne UNIQUEMENT un objet JSON valide :
{
  "decision": "ALLOW" | "BLOCK" | "ALLOW_WITH_CAP",
  "cap_amount_usdc": 0.0,
  "analysis": "string — max 80 mots, en anglais",
  "confidence": 0.0
}

Règles absolues :
- Prioritise la protection des fonds sur la disponibilité du service
- ALLOW_WITH_CAP quand l'intention semble légitime mais le montant est suspect
- Justifie ta décision sur la base des patterns observables
- Ne jamais retourner autre chose que le JSON demandé
- Ne jamais inclure de markdown ou de texte en dehors du JSON"""


class EscalationResult(BaseModel):
    escalation_result: str
    cap_amount_usdc: float = 0.0
    analysis: str
    confidence: float
    paid_by_sigui: bool = False
    claude_cost_usdc: float = 0.0
    arc_tx_log: str = ""
    fallback_used: bool = False
    degraded_mode: bool = False
    reason: str = ""
    # Provenance tracking (Feature 1 — Lebe integration)
    inference_engine: str = "rule_based"  # "lebe_qwen25" | "claude_fallback" | "rule_based"
    inference_device: str = "CPU"          # "AMD MI300X" | "REMOTE" | "CPU"


class EscalationEngine:
    def _rule_based_fallback(
        self, action: dict, agent_profile: dict
    ) -> EscalationResult:
        """Rule-based fallback when Claude is unavailable or treasury empty."""
        amount = action.get("amount_usdc", 0)
        avg = agent_profile.get("avg_amount_usdc", 0.01) or 0.01
        tx_count = agent_profile.get("tx_count", 0)

        if amount > avg * 5 or tx_count == 0:
            return EscalationResult(
                escalation_result="BLOCK",
                analysis="Rule-based fallback: suspicious amount relative to history or no prior transactions.",
                confidence=0.70,
                fallback_used=True,
            )

        cap = min(amount, avg * 3)
        return EscalationResult(
            escalation_result="ALLOW_WITH_CAP",
            cap_amount_usdc=cap,
            analysis=f"Rule-based fallback: moderate risk, capped at avg×3 (${cap:.4f}) to limit exposure.",
            confidence=0.65,
            fallback_used=True,
        )

    async def escalate(
        self,
        action: dict,
        risk_score: float,
        rules_triggered: list[str],
        agent_profile: dict,
        treasury_authorized: bool,
    ) -> EscalationResult:
        from modules.treasury import TreasuryEmptyError, treasury

        try:
            current_mode = treasury.operating_mode
        except TreasuryEmptyError:
            current_mode = AgentMode.EMERGENCY

        is_degraded = current_mode in (AgentMode.DEGRADED, AgentMode.EMERGENCY)

        if not treasury_authorized:
            logger.info("[ESCALATION] Treasury not authorized — rule-based fallback")
            result = self._rule_based_fallback(action, agent_profile)
            if is_degraded:
                result.degraded_mode = True
                result.reason = "Treasury below threshold — escalation skipped"
            return result

        user_content = json.dumps(
            {
                "action": action,
                "risk_score": risk_score,
                "rules_triggered": rules_triggered,
                "agent_history": {
                    "tx_count": agent_profile.get("tx_count", 0),
                    "avg_amount_usdc": agent_profile.get("avg_amount_usdc", 0.0),
                    "trust_score": agent_profile.get("trust_score", 0.5),
                    "total_blocked": agent_profile.get("total_blocked", 0),
                },
            },
            indent=2,
        )

        # ── Step 1: Try Lebe (Qwen2.5 on AMD MI300X) — primary engine ─────────
        lebe_data: dict | None = None
        lebe_status = "lebe_skipped"

        if lebe_gateway.is_available() and settings.lebe_enabled:
            logger.info(
                f"[ESCALATION] 🧠 Calling Lebe (Qwen2.5 AMD) for "
                f"agent={action.get('agent_id')} R={risk_score:.3f}"
            )
            lebe_data, lebe_status = await lebe_gateway.call_json_model(
                system_prompt=ESCALATION_PROMPT,
                user_payload=user_content,
                max_tokens=256,
                required_keys={"decision", "analysis", "confidence"},
                timeout=settings.lebe_timeout_s,
                context_id=f"lebe_escalation_{action.get('agent_id', 'unknown')}",
            )

        if lebe_data:
            logger.info(
                f"[ESCALATION] ✅ Lebe → {lebe_data.get('decision')} "
                f"(conf={lebe_data.get('confidence')}) device=AMD_MI300X"
            )
            return EscalationResult(
                escalation_result=lebe_data.get("decision", "BLOCK"),
                cap_amount_usdc=float(lebe_data.get("cap_amount_usdc", 0.0)),
                analysis=lebe_data.get("analysis", "No analysis provided."),
                confidence=float(lebe_data.get("confidence", 0.75)),
                paid_by_sigui=True,
                claude_cost_usdc=0.0,  # Lebe runs locally — no API cost
                degraded_mode=is_degraded,
                reason="Operating in DEGRADED mode" if is_degraded else "",
                inference_engine="lebe_qwen25",
                inference_device="AMD MI300X",
            )

        # ── Step 2: Fallback to Claude (Anthropic API) ─────────────────────────
        if lebe_status not in ("lebe_skipped",):
            logger.warning(
                f"[ESCALATION] Lebe failed ({lebe_status}) — "
                f"{'falling back to Claude' if settings.lebe_fallback_to_claude and llm_gateway.is_available() else 'rule-based fallback'}"
            )

        if settings.lebe_fallback_to_claude and llm_gateway.is_available():
            logger.info(
                f"[ESCALATION] 🔁 Calling Claude for "
                f"agent={action.get('agent_id')} R={risk_score:.3f}"
            )
            claude_data, claude_status = await llm_gateway.call_json_model(
                system_prompt=ESCALATION_PROMPT,
                user_payload=user_content,
                max_tokens=256,
                required_keys={"decision", "analysis", "confidence"},
                timeout=5.0,
                context_id=f"claude_escalation_{action.get('agent_id', 'unknown')}",
            )
            if claude_data:
                logger.info(
                    f"[ESCALATION] ✅ Claude → {claude_data.get('decision')} "
                    f"(conf={claude_data.get('confidence')})"
                )
                return EscalationResult(
                    escalation_result=claude_data.get("decision", "BLOCK"),
                    cap_amount_usdc=float(claude_data.get("cap_amount_usdc", 0.0)),
                    analysis=claude_data.get("analysis", "No analysis provided."),
                    confidence=float(claude_data.get("confidence", 0.75)),
                    paid_by_sigui=True,
                    claude_cost_usdc=settings.claude_cost_per_escalation,
                    degraded_mode=is_degraded,
                    reason="Operating in DEGRADED mode" if is_degraded else "",
                    inference_engine="claude_fallback",
                    inference_device="REMOTE",
                )

        # ── Step 3: Rule-based fallback (always available) ─────────────────────
        logger.warning("[ESCALATION] All LLM engines unavailable — rule-based fallback")
        result = self._rule_based_fallback(action, agent_profile)
        result.paid_by_sigui = treasury_authorized
        result.degraded_mode = is_degraded
        result.inference_engine = "rule_based"
        result.inference_device = "CPU"
        return result


# Instances
policy_brain = PolicyBrain()
crew_decision_brain = CrewDecisionBrain()
agent_policy_graph = AgentPolicyGraph()
escalation_engine = EscalationEngine()
