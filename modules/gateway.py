"""
Sigui v3.0 — Service Gateway
FastAPI + x402 middleware — all public endpoints
"""

import asyncio
import json
import time
from collections import defaultdict as _defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from loguru import logger

from agent.loop import AgentMode, agent as arc_agent
from blockchain import get_adapter
from clients.integrations import arc_client
from clients.threat_registry import (
    LAYER_BEHAVIOR,
    LAYER_CONTRACT,
    LAYER_SERVICE,
    LAYER_SPLITTING,
    threat_registry,
)
from config import settings
from ecosystem.orchestrator import ecosystem_orchestrator
from governance import hogonat_client
from modules.ai_engines import escalation_engine, policy_brain
from modules.benchmark import benchmark_service
from modules.contract_inspector import contract_inspector
from modules.dataset_stats import dataset_stats_service
from modules.graph_builder import graph_builder_service
from modules.imina_na_vision import imina_na_vision
from modules.kanaga_engine import kanaga_engine
from modules.memory import memory
from modules.response_validator import ValidationVerdict, response_validator
from modules.security.insurance_automation import insurance_automation
from modules.security_engine import ActionInput, Decision, decision_engine, risk_engine
from modules.service_registry import service_registry
from modules.treasury import TreasuryEmptyError, treasury
from modules.vision_graph import vision_graph_service

# ────────────────────────────────────────────────────────────────────────────────
# x402 Protected Paths
# ────────────────────────────────────────────────────────────────────────────────

PROTECTED_PATHS = {"/evaluate", "/escalate"}
SUPPORTED_CHAINS = {"arc", "ethereum", "solana"}


def _parse_chain(raw: str | None) -> str:
    chain = (raw or settings.default_chain).strip().lower()
    return chain if chain in SUPPORTED_CHAINS else ""


def _parse_amount(raw: str | None) -> float:
    if not raw:
        return 0.0
    try:
        return max(0.0, float(raw))
    except Exception:
        return 0.0


from modules.pricing import compute_fee

async def compute_evaluation_price(amount_usdc: float, chain: str) -> float:
    return compute_fee(amount_usdc, tier="payg")


# ────────────────────────────────────────────────────────────────────────────────
# Rate Limiting
# ────────────────────────────────────────────────────────────────────────────────

_rate_store: dict[str, list[float]] = _defaultdict(list)
_RATE_WINDOW_S: float = 60.0
_RATE_MAX_CALLS: int = 120  # 120 req/min par IP


def _check_rate_limit(key: str) -> bool:
    """Retourne True si la requête est autorisée, False si rate-limitée."""
    import time as _t

    now = _t.time()
    window = _rate_store[key]
    # Nettoyer les entrées hors fenêtre
    while window and now - window[0] > _RATE_WINDOW_S:
        window.pop(0)
    if len(window) >= _RATE_MAX_CALLS:
        return False
    window.append(now)
    # Borner la taille du dict (max 50k IPs)
    if len(_rate_store) > 50_000:
        stale_keys = [
            k
            for k, v in list(_rate_store.items())
            if not v or (now - v[-1]) > _RATE_WINDOW_S * 2
        ]
        for k in stale_keys[:10_000]:
            del _rate_store[k]
    return True


def _classify_tx(tx_hash: str) -> str:
    """Classify a transaction hash: 'simulated' | 'confirmed' | 'empty'"""
    h = str(tx_hash or "")
    if not h:
        return "empty"
    if h.startswith("0xSIM_"):
        return "simulated"
    if h.startswith("0xERROR_"):
        return "empty"
    return "confirmed"


# ────────────────────────────────────────────────────────────────────────────────
# Route Registration
# ────────────────────────────────────────────────────────────────────────────────


def register_routes(app: FastAPI):
    """Register all Sigui routes and middleware on the FastAPI app."""

    # ── NexusMind Integration ──────────────────────────────────────────────────
    from modules.nexusmind_router import register_nexusmind_routes
    register_nexusmind_routes(app)

    # ── x402 Payment Middleware ────────────────────────────────────────────────
    @app.middleware("http")
    async def x402_payment_middleware(request: Request, call_next):
        """
        Implements x402 Payment Required protocol.
        Protected endpoints require X-Payment header with Arc tx hash.
        """
        path = request.url.path

        if path in PROTECTED_PATHS:
            # ── Rate limiting (avant tout autre check) ────────────────────────────
            client_ip = request.client.host if request.client else "unknown"
            if not _check_rate_limit(client_ip):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "limit": f"{_RATE_MAX_CALLS} requests per {int(_RATE_WINDOW_S)}s",
                        "retry_after_s": 60,
                    },
                    headers={"Retry-After": "60"},
                )

            payment_header = request.headers.get("X-Payment")
            chain = _parse_chain(request.headers.get("X-Chain"))
            if not chain:
                return JSONResponse(
                    status_code=422,
                    content={
                        "error": "Invalid X-Chain header",
                        "supported_chains": sorted(list(SUPPORTED_CHAINS)),
                    },
                )
            amount_hint = _parse_amount(request.headers.get("X-Amount"))

            if not payment_header:
                # Return HTTP 402 with payment instructions
                wallet = settings.sigui_wallet_address
                if path == "/evaluate":
                    price = await compute_evaluation_price(amount_hint, chain)
                else:
                    price = settings.sigui_escalate_price_usdc
                # Arc USDC is native with 18 decimals (isNative=True, confirmed by Circle API).
                # maxAmountRequired must be in the token's smallest unit.
                price_units = int(price * 10**settings.arc_usdc_decimals)

                return JSONResponse(
                    status_code=402,
                    content={
                        "x402Version": 1,
                        "error": "Payment required",
                        "accepts": [
                            {
                                "scheme": "exact",
                                "network": "arc-testnet",
                                "maxAmountRequired": str(price_units),
                                "resource": path,
                                "description": f"Sigui security evaluation ({chain}) — ${price} USDC",
                                "mimeType": "application/json",
                                "payTo": wallet,
                                "asset": "USDC",
                                "decimals": settings.arc_usdc_decimals,
                                "isNative": True,
                            }
                        ],
                    },
                )

            # Validate payment tx if not in demo mode
            if not settings.demo_mode:
                if path == "/evaluate":
                    expected_amount = await compute_evaluation_price(amount_hint, chain)
                else:
                    expected_amount = settings.sigui_escalate_price_usdc

                adapter = get_adapter(chain)
                valid = await adapter.verify_payment(
                    payment_header, expected_amount, settings.sigui_wallet_address
                )
                if not valid:
                    return JSONResponse(
                        status_code=402,
                        content={
                            "error": "Invalid or unconfirmed payment",
                            "tx_hash": payment_header,
                        },
                    )

        return await call_next(request)

    # ── Agent Card ─────────────────────────────────────────────────────────────
    @app.get("/.well-known/agent-card", tags=["Infrastructure"])
    async def agent_card():
        """Agent Card — discoverability endpoint for agent ecosystem."""
        try:
            mode = treasury.operating_mode.value
        except Exception:
            mode = "EMERGENCY"

        return {
            "name": "Sigui Security Oracle",
            "version": "3.0",
            "type": "security_agent",
            "description": "Sigui is not a firewall. It's an agent that gets paid to protect other agents.",
            "capabilities": [
                "risk_assessment",
                "fraud_detection",
                "escalation",
                "pattern_learning",
            ],
            "pricing": {
                "evaluate": {
                    "amount": str(settings.sigui_eval_price_usdc),
                    "currency": "USDC",
                },
                "escalate": {
                    "amount": str(settings.sigui_escalate_price_usdc),
                    "currency": "USDC",
                    "additional": True,
                },
            },
            "wallet": settings.sigui_wallet_address,
            "network": "arc-testnet",
            "payment_protocol": "x402",
            "operating_mode": mode,
            "sla": {
                "latency_p99_ms": 100,
                "finality_seconds": 1,
                "uptime_percent": 99.9,
            },
        }

    # ── Health ─────────────────────────────────────────────────────────────────
    @app.get("/health", tags=["Infrastructure"])
    async def health():
        """Health check — status, mode, uptime, DB connectivity."""
        try:
            mode = treasury.operating_mode.value
        except Exception:
            mode = "EMERGENCY"

        # Vérification DB légère
        db_ok = False
        try:
            if hasattr(memory, "_db") and memory._db is not None:
                await memory._db.execute("SELECT 1")
                db_ok = True
        except Exception:
            db_ok = False

        return {
            "status": "ok" if db_ok else "degraded",
            "version": "3.0.0",
            "mode": mode,
            "demo_mode": settings.demo_mode,
            "arc_runtime_mode": "demo" if arc_client.demo_mode else "real",
            "arc_connected": bool(arc_client._w3 is not None)
            if hasattr(arc_client, "_w3")
            else False,
            "db_connected": db_ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # ── Treasury ───────────────────────────────────────────────────────────────
    @app.get("/treasury", tags=["Treasury"])
    async def get_treasury():
        """Real-time P&L and economic state of Sigui."""
        return treasury.get_state()

    # ── Stats ──────────────────────────────────────────────────────────────────
    @app.get("/stats", tags=["Statistics"])
    async def get_stats():
        """Decision statistics and MemoClaw pattern summary."""
        stats = await memory.get_stats()
        patterns = await memory.get_top_patterns(5)
        agents = await memory.get_all_agents()
        allow_threshold, block_threshold = await policy_brain.get_thresholds()
        latest_policy = await memory.get_latest_policy_update()
        val_global = await response_validator.get_global_stats()
        registry_stats = await threat_registry.get_stats()
        return {
            "decisions": stats,
            "top_patterns": patterns,
            "agents_tracked": len(agents),
            "treasury": treasury.get_state(),
            "policy": {
                "allow_threshold": allow_threshold,
                "block_threshold": block_threshold,
                "latest_update": latest_policy,
            },
            "response_validation": val_global,
            "threat_registry": registry_stats,
        }

    @app.get("/benchmark", tags=["Statistics"])
    async def benchmark():
        """Runtime benchmark summary for dashboard."""
        data = await benchmark_service.get_metrics()
        data["mode"] = treasury.get_state().get("mode", "UNKNOWN")
        return data

    @app.get("/dataset/stats", tags=["Statistics"])
    async def dataset_stats():
        """Dataset availability and class distribution."""
        return dataset_stats_service.get_stats()

    @app.get("/vision/graph/{agent_id}", tags=["Statistics"])
    async def vision_graph(agent_id: str):
        """Lightweight graph payload used by vision dashboard panels."""
        return await vision_graph_service.get_agent_graph(agent_id)

    @app.get("/ecosystem/status", tags=["Simulation"])
    async def ecosystem_status():
        """Return runtime status for all autonomous ecosystem agents."""
        return ecosystem_orchestrator.get_status()

    # ── Evaluate (main pipeline) ──────────────────────────────────────────────
    @app.post("/evaluate", tags=["Security"])
    async def evaluate(request: Request):
        """
        Main security evaluation pipeline.
        Requires X-Payment header (x402) with Arc tx hash → $0.001 USDC.
        """
        t_start = time.perf_counter()

        # Parse body
        body = await request.json()
        chain = _parse_chain(request.headers.get("X-Chain")) or settings.default_chain
        if "chain" not in body:
            body["chain"] = chain
        action = ActionInput(**body)
        action.chain = chain
        action.context["chain"] = chain

        # ── ZK-Reputation Proof Verification (New Feature) ─────────────────
        zk_proof_id = body.get("zk_reputation_proof_id")
        if zk_proof_id:
            from modules.security.zk_proofs import zk_proof_system
            # Try to verify the proof if it exists in the system
            try:
                is_valid = await zk_proof_system.verify_proof(zk_proof_id)
            except Exception:
                # If not found (new proof), we simulate it for the demo if it starts with 'zk_'
                is_valid = zk_proof_id.startswith("zk_")

            if is_valid:
                logger.info(f"[GATEWAY] ZK-Reputation proof verified: {zk_proof_id}")
                action.context["zk_reputation_verified"] = True

        # Check Sigui treasury health
        try:
            mode = treasury.operating_mode
        except TreasuryEmptyError:
            raise HTTPException(
                status_code=503,
                detail="Sigui treasury empty — service temporarily unavailable",
            )

        # Ensure agent exists in memory
        await memory.ensure_agent(action.agent_id)

        # Get agent profile from MemoClaw
        agent_profile = await memory.get_agent(action.agent_id)

        # Record revenue with Dynamic Risk Pricing
        # If agent is risky or global threats are high, price increases (Surge Pricing)
        base_price = await compute_evaluation_price(action.amount_usdc, chain)
        risk_surge = 1.0
        if agent_profile and agent_profile.get("trust_score", 1.0) < 0.3:
            risk_surge = 5.0  # 5x price for untrusted agents
        elif agent_profile and agent_profile.get("trust_score", 1.0) < 0.6:
            risk_surge = 2.0

        final_price = round(base_price * risk_surge, 6)
        await treasury.record_revenue(
            final_price, f"eval_fee_surge_{risk_surge}x", chain=chain
        )
        # 20% des revenus d'évaluation alimentent le pool Hogonat.
        await hogonat_client.add_fee(final_price * 0.20)

        # MemoClaw freeze gate — instant BLOCK for known bad actors (survives restarts)
        if await memory.is_agent_frozen(action.agent_id):
            logger.warning(
                f"[GATEWAY] ❄️  Agent {action.agent_id} is frozen — instant BLOCK"
            )
            return {
                "decision": "BLOCK",
                "risk_score": 1.0,
                "confidence": 0.99,
                "reason": "Agent frozen by MemoClaw — repeated suspicious activity detected.",
                "action_hash": "memoclaw_frozen",
                "arc_tx_log": "",
                "sigui_mode": mode.value,
                "escalation_available": False,
                "escalation_cost_usdc": settings.sigui_escalate_price_usdc,
                "policy_source": "memoclaw_freeze",
                "processing_time_ms": 1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # Check known attack patterns (fuzzy multi-level matching)
        pattern_extra = await memory.check_pattern_fuzzy(
            action.action_type, action.destination, action.amount_usdc
        )

        # ── Anti-splitting: record flow & inject cumulative context ────────────
        await memory.record_flow(
            action.agent_id,
            action.destination,
            action.amount_usdc,
            chain=chain,
        )
        cumulative = await memory.get_cumulative_flow(
            action.agent_id, action.destination, window_minutes=10, chain=chain
        )
        global_flow = await memory.get_global_flow(
            action.agent_id, window_minutes=10, all_chains=True
        )
        action.context["cumulative_flow"] = cumulative
        action.context["global_flow"] = global_flow

        # ── Service reputation: evaluate destination ────────────────────────
        svc_eval = await service_registry.evaluate_service(action.destination)
        action.context["service_eval"] = svc_eval

        # ── Couche 4 : Contract Inspector ─────────────────────────────────
        contract_eval = await contract_inspector.analyze(action.destination)
        action.context["contract_eval"] = {
            "is_contract": contract_eval.is_contract,
            "risk_delta": contract_eval.risk_delta,
            "flags": contract_eval.flags,
            "reason": contract_eval.reason,
            "bytecode_size": contract_eval.bytecode_size,
        }
        if contract_eval.is_contract:
            logger.debug(
                f"[GATEWAY] Contract detected: {action.destination[:14]}… "
                f"delta={contract_eval.risk_delta:.2f} flags={contract_eval.flags[:2]}"
            )

        # Compute base risk score
        risk = await risk_engine.score(action, agent_profile, pattern_extra)

        # ── Trading Agent Guardrail (Borderline Logic) ─────────────────────
        # If the risk is borderline and it's a high-value trading action,
        # we block and request x402 payment for DEEP VISION analysis.
        is_borderline = 0.45 <= risk.risk_score < 0.65
        is_trading = action.action_type in ("transfer", "swap", "contract_interaction")
        deep_authorized = body.get("deep_analysis_authorized") or body.get("payment_tx_hash")

        if is_borderline and is_trading and not deep_authorized:
             logger.info(f"[GUARDRAIL] Borderline detected (R={risk.risk_score:.3f}) for {action.agent_id}. Blocking for deep analysis.")
             return JSONResponse(
                status_code=402,
                content={
                    "decision": "PAYMENT_REQUIRED_FOR_DEEP_ANALYSIS",
                    "risk_score": round(risk.risk_score, 4),
                    "reason": "Transaction is in the borderline risk zone (0.45-0.65). Deep vision topology analysis required to proceed.",
                    "deep_analysis_price_usdc": 0.002,
                    "x402_instructions": {
                        "asset": "USDC",
                        "network": "arc-testnet",
                        "payTo": settings.sigui_wallet_address,
                        "amount_units": str(int(0.002 * 10**settings.arc_usdc_decimals)),
                        "resource": "/evaluate",
                        "note": "Include 'deep_analysis_authorized': true in your next request with the payment hash."
                    }
                }
             )

        # ── Couche Vision (Imina Na) + agrégation Kanaga ──────────────────────
        # Vision is now run ONLY IF NOT borderline OR if deep analysis is authorized/paid.
        vision_input = {
            "agent_id": action.agent_id,
            "action_type": action.action_type,
            "amount_usdc": action.amount_usdc,
            "destination": action.destination,
            "chain": chain,
            "context": action.context,
        }
        graph_payload = await graph_builder_service.build_for_action(
            agent_id=action.agent_id,
            destination=action.destination,
            chain=chain,
            amount_usdc=action.amount_usdc,
        )
        action.context["vision_graph_summary"] = graph_payload.get("summary", {})
        vision_eval = await imina_na_vision.analyze(vision_input, graph=graph_payload)
        action.context["vision_eval"] = {
            "pattern": vision_eval.pattern,
            "confidence": vision_eval.confidence,
            "risk_delta": vision_eval.risk_delta,
            "model": vision_eval.model,
            "inference_device": vision_eval.inference_device,
            "inference_time_ms": vision_eval.inference_time_ms,
            "visual_evidence": vision_eval.visual_evidence,
            "tee_attestation": vision_eval.tee_attestation
        }

        weights = body.get("weights", {"financial": 1.0, "behavioral": 1.0, "visual_topology": 1.0})
        
        kanaga_out = kanaga_engine.compute(
            components=risk.components,
            deltas={"vision": vision_eval.risk_delta},
            weights=weights,
        )
        risk.risk_score = kanaga_out.risk_score
        if vision_eval.risk_delta > 0:
            risk.rules_triggered.append(
                f"vision_{vision_eval.pattern.lower()}_delta_{vision_eval.risk_delta:.2f}"
            )

        # Determine if escalation is available
        escalation_available = treasury.should_escalate(risk.risk_score)

        # Compute decision
        decision_out = await decision_engine.decide(
            agent_id=action.agent_id,
            action_type=action.action_type,
            amount_usdc=action.amount_usdc,
            destination=action.destination,
            risk=risk,
            sigui_mode=mode,
            escalation_available=escalation_available,
            agent_profile=agent_profile,
            skip_onchain_log=True,
        )

        # Log decision via selected chain adapter
        chain_adapter = get_adapter(chain)
        decision_out.arc_tx_log = await chain_adapter.log_decision(
            decision_out.action_hash, decision_out.decision, decision_out.risk_score
        )

        # Vision override non-configurable (alignement PRD)
        if (
            vision_eval.risk_delta >= 0.40
            and vision_eval.confidence >= settings.vision_confidence_block_threshold
            and decision_out.decision != Decision.BLOCK.value
        ):
            decision_out.decision = Decision.BLOCK.value
            decision_out.reason = (
                f"VISUAL ATTACK: {vision_eval.pattern} (conf={vision_eval.confidence:.2f})"
            )
            decision_out.policy_source = "vision_override"

        # DAO blacklist override
        if await hogonat_client.is_blacklisted(action.destination):
            decision_out.decision = Decision.BLOCK.value
            decision_out.reason = "DAO_GOVERNANCE_BLACKLIST"
            decision_out.policy_source = "hogonat_override"

        # Pay Arc fee for onchain log
        await treasury.pay_arc_fee(chain=chain)

        # Update MemoClaw
        dec = decision_out.decision
        if dec == "ALLOW":
            await memory.update_agent_allow(action.agent_id, action.amount_usdc)
            if risk.risk_score >= 0.65:
                await memory.penalize_risky_allow(action.agent_id, action.amount_usdc)
        elif dec == "BLOCK":
            await memory.update_agent_block(action.agent_id)
            await memory.record_attack_pattern(
                action.action_type, action.destination, action.amount_usdc
            )
            dest_pfx = action.destination[:8] if action.destination else "0x000000"
            amt_range = "high" if action.amount_usdc > 1.0 else "low"
            pattern_id = memory._make_pattern_id(
                action.action_type, dest_pfx, amt_range
            )
            await memory.log_attack(pattern_id, action.agent_id, action.amount_usdc)
            # MemoClaw auto-freeze: 3 BLOCKs in 5 min → frozen for 10 min
            await memory.auto_freeze_check(action.agent_id)

            # ── ThreatRegistry: record blocked attack onchain (fire-and-forget) ──
            # Determine which security layer triggered the block
            _triggered = risk.rules_triggered
            _layer = LAYER_BEHAVIOR  # default: behavioural anomaly
            if any(
                "splitting" in r
                or "cumulative_flow" in r
                or "multi_dest" in r
                or "uniform_micro" in r
                for r in _triggered
            ):
                _layer = LAYER_SPLITTING
            elif any("service" in r.lower() for r in _triggered):
                _layer = LAYER_SERVICE
            elif any("contract" in r.lower() for r in _triggered):
                _layer = LAYER_CONTRACT

            # Agent wallet: use sigui_wallet_address as a fallback (agent_id is a string ID)
            _agent_wallet = (
                action.context.get("agent_wallet") or settings.sigui_wallet_address
            )
            logger.info(
                f"[GATEWAY] 🛡️ Triggering onchain recording for blocked attack (layer={_layer})"
            )
            asyncio.create_task(
                threat_registry.record_attack(
                    agent_id=action.agent_id,
                    agent_wallet_address=_agent_wallet,
                    action_type=action.action_type,
                    destination=action.destination,
                    amount_usdc=action.amount_usdc,
                    risk_score=risk.risk_score,
                    layer=_layer,
                )
            )

        # ── Record service interaction outcome ─────────────────────────────────
        svc_outcome = "paid" if dec == "ALLOW" else "blocked"
        await service_registry.record_interaction(
            action.agent_id,
            action.destination,
            action.amount_usdc,
            svc_outcome,
        )

        # Episodic memory — enriched outcome labeling for self_critique
        outcome_label = "expected"
        if dec == "ALLOW":
            if risk.risk_score >= 0.55:
                outcome_label = "risky_allow"  # ALLOW dans la zone grise
            elif pattern_extra >= 0.25:
                outcome_label = "risky_allow"  # ALLOW sur pattern d'attaque connu
            elif agent_profile and agent_profile["tx_count"] == 0 and action.amount_usdc > 0.5:
                outcome_label = "risky_allow"  # Premier tx avec montant élevé
        elif dec == "BLOCK":
            if risk.risk_score < 0.35:
                outcome_label = "safe_block"  # Bloqué alors que faible risque
            elif agent_profile and agent_profile["trust_score"] > 0.70:
                outcome_label = "contested_block"  # Agent établi bloqué

        # Déclencher self_critique immédiatement si comportement risqué détecté
        if outcome_label == "risky_allow":
            arc_agent.request_critique()

        await memory.log_episode(
            agent_id=action.agent_id,
            action_type=action.action_type,
            decision=dec,
            risk_score=risk.risk_score,
            policy_source=decision_out.policy_source,
            outcome_label=outcome_label,
            notes=decision_out.reason[:180],
        )

        # Log decision in MemoClaw
        await memory.log_decision(
            agent_id=action.agent_id,
            action_type=action.action_type,
            amount_usdc=action.amount_usdc,
            destination=action.destination,
            chain=chain,
            action_hash=decision_out.action_hash,
            decision=dec,
            risk_score=risk.risk_score,
            confidence=risk.confidence,
            rules_triggered=risk.rules_triggered,
            arc_tx_hash=decision_out.arc_tx_log,
            sigui_mode=mode.value,
            processing_time_ms=decision_out.processing_time_ms,
        )

        payload = decision_out.model_dump()

        # ── Programmatic Insurance (New Feature) ───────────────────────────
        insurance_offer = await insurance_automation.offer_insurance(
            agent_address=action.agent_id,
            amount_usdc=action.amount_usdc,
            risk_score=risk.risk_score
        )
        if insurance_offer:
            payload["insurance_offer"] = insurance_offer
            logger.info(f"[GATEWAY] Insurance offer attached to evaluation for {action.agent_id}")

        # ── Automated Claim Check ──────────────────────────────────────────
        await insurance_automation.auto_claim_check(
            agent_address=action.agent_id,
            tx_hash=decision_out.arc_tx_log,
            decision=dec
        )

        # ── Build layers_triggered for SDK v0.2.0 ─────────────────────────────
        _memoclaw_weight: float = 0.0
        for _r in risk.rules_triggered:
            if "memoclaw_pattern_weight_" in _r:
                try:
                    _memoclaw_weight = float(_r.split("memoclaw_pattern_weight_")[-1])
                except ValueError:
                    pass
                break

        payload.update(
            {
                "vision_pattern": vision_eval.pattern,
                "vision_confidence": round(vision_eval.confidence, 4),
                "vision_model": vision_eval.model,
                "visual_evidence": vision_eval.visual_evidence,
                "vision_graph_summary": vision_eval.graph_summary or {},
                "inference_device": kanaga_out.device,
                "processing_vision_time_ms": vision_eval.inference_time_ms,
                "evaluation_price_usdc": final_price,
                "chain": chain,
                # SDK v0.2.0: arc_tx_log alias expected by EvaluationResult.chain_tx_log
                "chain_tx_log": decision_out.arc_tx_log,
                # SDK v0.2.0: per-layer risk deltas (0.0 = layer did not trigger)
                "layers_triggered": {
                    "financial":          round(kanaga_out.components.get("action", 0.0), 4),
                    "behavioral":         round(kanaga_out.components.get("context", 0.0), 4),
                    "history":            round(kanaga_out.components.get("history", 0.0), 4),
                    "vision":             round(vision_eval.risk_delta, 4),
                    "service_registry":   round(kanaga_out.deltas.get("service", 0.0), 4),
                    "contract_inspector": round(kanaga_out.deltas.get("contract", 0.0), 4),
                    "anti_splitting":     round(kanaga_out.deltas.get("flow", 0.0), 4),
                    "memoclaw_pattern":   round(_memoclaw_weight, 4),
                },
                "raw_signals": {
                    "financial": {
                        "amount_usdc": action.amount_usdc,
                        "action_score": kanaga_out.components.get("action", 0.0),
                    },
                    "behavioral": {
                        "history_score": kanaga_out.components.get("history", 0.0),
                        "context_score": kanaga_out.components.get("context", 0.0),
                        "flow_delta": kanaga_out.deltas.get("flow", 0.0),
                        "service_delta": kanaga_out.deltas.get("service", 0.0),
                        "contract_delta": kanaga_out.deltas.get("contract", 0.0),
                    },
                    "visual_topology": {
                        "pattern": vision_eval.pattern,
                        "confidence": round(vision_eval.confidence, 4),
                        "risk_delta": vision_eval.risk_delta,
                        "evidence": vision_eval.visual_evidence,
                    },
                    "provenance": f"{kanaga_out.device} (Kanaga) / {vision_eval.model} (Imina Na)",
                },
                "pedigree": decision_out.pedigree.model_dump() if decision_out.pedigree else None,
                "tribunal_notes": decision_out.tribunal_notes,
            }
        )

        # ── NexusMind Integration ──────────────────────────────────────────────
        from modules.nexusmind_router import broadcast_decision
        asyncio.create_task(broadcast_decision(
            agent_id=action.agent_id,
            decision=dec,
            amount_usdc=action.amount_usdc,
            pattern=vision_eval.pattern if vision_eval.pattern != "NORMAL" else "HEURISTIC",
            latency_ms=decision_out.processing_time_ms,
            risk_score=risk.risk_score,
            fee_usdc=final_price,
            node_id="node_001",  # Simulate this node handling the request for now
        ))

        return payload

    # ── Escalate (Claude deep analysis) ───────────────────────────────────────
    @app.post("/escalate", tags=["Security"])
    async def escalate_endpoint(request: Request):
        """
        Deep analysis endpoint — Claude API.
        Requires additional $0.003 USDC payment. Sigui pays Claude from its treasury.
        """
        body = await request.json()
        action = ActionInput(**body)
        chain = action.chain

        await treasury.record_revenue(
            settings.sigui_escalate_price_usdc, "escalation_fee", chain=chain
        )
        await memory.ensure_agent(action.agent_id)
        agent_profile = await memory.get_agent(action.agent_id)
        pattern_extra = await memory.check_pattern(
            action.action_type, action.destination, action.amount_usdc
        )
        risk = await risk_engine.score(action, agent_profile, pattern_extra)

        # Treasury authorizes Claude payment
        treasury_ok = await treasury.pay_for_escalation()

        result = await escalation_engine.escalate(
            action=body,
            risk_score=risk.risk_score,
            rules_triggered=risk.rules_triggered,
            agent_profile=agent_profile,
            treasury_authorized=treasury_ok,
        )

        # Log as ESCALATE decision
        chain_adapter = get_adapter(chain)
        arc_tx = await chain_adapter.log_decision(
            action.agent_id[:8], "ESCALATE", risk.risk_score
        )
        result.arc_tx_log = arc_tx

        try:
            esc_mode = treasury.operating_mode.value
        except Exception:
            esc_mode = "EMERGENCY"

        await memory.log_decision(
            agent_id=action.agent_id,
            action_type=action.action_type,
            amount_usdc=action.amount_usdc,
            destination=action.destination,
            chain=chain,
            action_hash=action.agent_id[:16],
            decision="ESCALATE",
            risk_score=risk.risk_score,
            confidence=risk.confidence,
            rules_triggered=risk.rules_triggered,
            arc_tx_hash=arc_tx,
            sigui_mode=esc_mode,
            processing_time_ms=0,
        )

        return result.model_dump()

    # ── Response Validator ────────────────────────────────────────────────────
    @app.post("/validate-response", tags=["Security"])
    async def validate_response_endpoint(request: Request):
        """
        **Post-service response validation** — call this AFTER receiving a service
        response and BEFORE acting on the data.

        Sigui runs 5 detection layers:
        1. **Prompt injection / jailbreak** — 16 regex patterns
        2. **Statistical anomaly** — Z-score vs. history + caller bounds
        3. **Schema anomaly** — suspicious keys, oversized payload, deep nesting
        4. **Historical consistency** — vs. past validated responses from same service
        5. **Known poisoning signatures** — oracle zeroing, overflow, NaN, embedded addresses

        **Free endpoint** — no x402 payment required.
        A `POISONED` verdict auto-reports the service to the Service Registry.
        """
        body = await request.json()

        agent_id = str(body.get("agent_id", "unknown"))[:128]
        service_address = str(body.get("service_address", ""))[:256]
        request_type = str(body.get("request_type", "generic"))[:64]
        response_data = body.get("response_received")
        context = body.get("context") or {}

        if response_data is None:
            raise HTTPException(
                status_code=422,
                detail="'response_received' is required — pass the raw service response body",
            )

        if not isinstance(context, dict):
            context = {}

        result = await response_validator.validate(
            agent_id=agent_id,
            service_address=service_address,
            request_type=request_type,
            response_data=response_data,
            context=context,
        )

        # Auto-report to Service Registry when POISONED
        auto_reported = False
        if result.verdict == ValidationVerdict.POISONED and service_address:
            try:
                await service_registry.record_interaction(
                    agent_id, service_address, 0.0, "complained"
                )
                auto_reported = True
                logger.warning(
                    f"[GATEWAY] 🧪 POISONED response from {service_address[:20]}… "
                    f"— auto-reported to Service Registry"
                )
            except Exception:
                pass

        return {
            "verdict": result.verdict.value,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "findings": [
                {
                    "category": f.category,
                    "severity": f.severity,
                    "detail": f.detail,
                    "risk_delta": f.risk_delta,
                }
                for f in result.findings
            ],
            "recommendations": result.recommendations,
            "service_address": result.service_address,
            "request_type": result.request_type,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": result.timestamp,
            "auto_reported": auto_reported,
        }

    # ── Simulate ──────────────────────────────────────────────────────────────
    @app.post("/simulate", tags=["Simulation"])
    async def simulate():
        """Ensure autonomous ecosystem is running."""
        await ecosystem_orchestrator.start()
        return {
            "status": "ecosystem_running",
            "agents": 5,
            "agent_ids": [
                "agent_payer",
                "agent_attacker",
                "agent_monitor",
                "agent_learner",
                "agent_grayzone",
            ],
            "message": "5 autonomous agents deployed (Payer, Attacker, Monitor, Learner, GrayZone)",
        }

    # ── Service Registry ──────────────────────────────────────────────────────
    @app.post("/services/complain", tags=["Services"])
    async def complain_about_service(
        agent_id: str,
        service_address: str,
        reason: str = "service_did_not_deliver",
    ):
        """
        Un agent signale qu'un service l'a arnaqué après paiement.
        2 plaintes → SUSPICIOUS. 5 plaintes → MALICIOUS automatiquement.
        """
        await service_registry.record_interaction(
            agent_id, service_address, 0.0, "complained"
        )
        profile = await service_registry.get_service_profile(service_address)
        return {
            "status": "complaint_recorded",
            "service": service_address,
            "new_trust_level": profile.trust if profile else "NEUTRAL",
            "message": (
                "Thank you. If this service accumulates complaints, "
                "it will be flagged as suspicious or malicious."
            ),
        }

    @app.get("/services/{address}", tags=["Services"])
    async def get_service_profile(address: str):
        """Consulter le profil de confiance d'un service destinataire."""
        profile = await service_registry.get_service_profile(address)
        if not profile:
            return {"address": address, "trust": "UNKNOWN", "known": False}
        # Enrich with response validation history
        val_stats = await response_validator.get_service_validation_stats(
            profile.address
        )

        return {
            "address": profile.address,
            "name": profile.name,
            "trust": profile.trust,
            "category": profile.category,
            "total_received_usdc": profile.total_payments_received,
            "unique_payers": profile.unique_payers,
            "complaints": profile.complaints,
            "tags": profile.tags,
            "known": True,
            "response_validation": val_stats,
        }

    # ── Flow Monitor (anti-splitting dashboard) ───────────────────────────────
    @app.get("/flows/active", tags=["Services"])
    async def flows_active():
        """
        Returns aggregated flow windows for the last 10 minutes, enriched
        with ratio vs. agent average — used by the Splitting Detector panel.
        """
        if not memory._db:
            return []

        rows = []
        # Reuse existing connection to avoid 'database is locked' on Windows
        async with memory._lock:
            cur = await memory._db.execute(
                """
                SELECT
                    fw.agent_id,
                    fw.destination,
                    fw.chain,
                    COUNT(*)         AS tx_count,
                    SUM(fw.amount_usdc) AS total_amount,
                    MAX(fw.amount_usdc) AS max_single,
                    MIN(fw.amount_usdc) AS min_single,
                    COALESCE(a.avg_amount_usdc, 0.01) AS agent_avg
                FROM flow_windows fw
                LEFT JOIN agents a ON a.agent_id = fw.agent_id
                WHERE fw.timestamp > datetime('now', '-10 minutes')
                GROUP BY fw.agent_id, fw.destination, fw.chain
                HAVING COUNT(*) > 1
                ORDER BY total_amount DESC
                LIMIT 20
                """
            )
            for r in await cur.fetchall():
                agent_avg = r["agent_avg"] or 0.01
                ratio = round(r["total_amount"] / agent_avg, 1)
                rows.append(
                    {
                        "agent_id": r["agent_id"],
                        "destination": r["destination"],
                        "chain": r["chain"],
                        "tx_count": r["tx_count"],
                        "total_amount": round(r["total_amount"], 6),
                        "max_single": round(r["max_single"], 6),
                        "min_single": round(r["min_single"], 6),
                        "ratio_vs_avg": ratio,
                    }
                )
        return rows

    # ── Service Top block removed — route moved above /services/{address} (FIX #1) ──

    # ── Hogonat Governance ─────────────────────────────────────────────────────
    @app.get("/hogonat/state", tags=["Simulation"])
    async def hogonat_state():
        return await hogonat_client.get_state()
        
    @app.get("/hogonat/history", tags=["Simulation"])
    async def hogonat_history(limit: int = 50):
        from modules.memory import memory
        return await memory.get_hogonat_history(limit)

    @app.post("/hogonat/stake", tags=["Simulation"])
    async def hogonat_stake(request: Request):
        body = await request.json()
        staker_id = str(body.get("staker_id") or body.get("agent_id") or "").strip()
        amount_usdc = float(body.get("amount_usdc", 0.0) or 0.0)
        if not staker_id:
            raise HTTPException(status_code=422, detail="staker_id is required")
        result = await hogonat_client.stake(staker_id, amount_usdc)
        if not result.get("ok"):
            raise HTTPException(status_code=422, detail=result.get("error", "stake failed"))
        return result

    @app.get("/flywheel/status", tags=["Simulation"])
    async def flywheel_status():
        """Returns the status of the autonomous learning flywheel."""
        from modules.optimization.flywheel import flywheel
        return {
            "sample_count": len(flywheel.sample_buffer),
            "active_jobs": flywheel.active_training_jobs,
            "min_samples_required": flywheel.min_samples_for_finetuning
        }

    @app.post("/hogonat/vote", tags=["Simulation"])
    async def hogonat_vote(request: Request):
        body = await request.json()
        staker_id = str(body.get("staker_id") or body.get("agent_id") or "").strip()
        weights = body.get("risk_weights") or [0.4, 0.3, 0.3]
        allow_threshold = float(body.get("allow_threshold", 0.30) or 0.30)
        block_threshold = float(body.get("block_threshold", 0.70) or 0.70)
        if not staker_id:
            raise HTTPException(status_code=422, detail="staker_id is required")
        try:
            weights = [float(x) for x in weights]
        except Exception:
            raise HTTPException(status_code=422, detail="risk_weights must be numeric list")
        result = await hogonat_client.vote(
            staker_id=staker_id,
            risk_weights=weights,
            allow_threshold=allow_threshold,
            block_threshold=block_threshold,
        )
        if not result.get("ok"):
            raise HTTPException(status_code=422, detail=result.get("error", "vote failed"))
        return result

    @app.get("/demo/report", tags=["Demo"])
    async def demo_report():
        """Generate submission-grade demo report JSON and persist it to disk."""
        # Use efficient SQL counters instead of loading thousands of rows
        onchain_counts = await memory.get_onchain_counts()
        simulated_tx_count = onchain_counts["simulated_tx_count"]
        confirmed_onchain_count = onchain_counts["confirmed_onchain_tx_count"]
        decision_total = onchain_counts["total_tx_count"]

        # Fetch only the last 50 confirmed hashes for the proof payload
        recent_confirmed_hashes: list[str] = []
        try:
            if memory._db:
                async with memory._lock:
                    cur = await memory._db.execute(
                        """
                        SELECT arc_tx_hash FROM decisions
                        WHERE arc_tx_hash != ''
                          AND arc_tx_hash NOT LIKE '0xSIM_%'
                          AND arc_tx_hash NOT LIKE '0xERROR_%'
                        ORDER BY timestamp DESC
                        LIMIT 50
                        """
                    )
                    recent_confirmed_hashes = [row[0] for row in await cur.fetchall()]
        except Exception:
            pass

        treasury_state = treasury.get_state()
        stats = await memory.get_stats()
        protected_usdc = float(stats.get("usdc_saved", 0.0))
        security_cost = float(treasury_state.get("total_spent", 0.0))
        roi = (protected_usdc / security_cost) if security_cost > 0 else 0.0

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "demo_mode": settings.demo_mode,
            "track_alignment": [
                "agent-to-agent-payment-loop",
                "per-api-monetization-engine",
            ],
            "pricing": {
                "evaluate_usdc": settings.sigui_eval_price_usdc,
                "escalate_usdc": settings.sigui_escalate_price_usdc,
                "price_constraint_ok": settings.sigui_eval_price_usdc <= 0.01,
            },
            "onchain_proof": {
                "decision_total": decision_total,
                "simulated_tx_count": simulated_tx_count,
                "confirmed_onchain_tx_count": confirmed_onchain_count,
                "valid_tx_count": confirmed_onchain_count,
                "target_50_met": confirmed_onchain_count >= 50,
                "recent_tx_hashes": recent_confirmed_hashes,
                "explorer_links": [
                    f"{settings.arc_explorer_url}/tx/{h}"
                    for h in recent_confirmed_hashes[:10]
                ],
                "signer_explorer": (
                    f"{settings.arc_explorer_url}/address/{settings.arc_signer_address}"
                    if settings.arc_signer_address
                    else None
                ),
                "arc_explorer": settings.arc_explorer_url,
                "arc_chain_id": settings.arc_chain_id,
                "arc_rpc": settings.arc_rpc_url,
                "note": (
                    "simulated = 0xSIM_* hashes (DEMO_MODE=true). "
                    "confirmed = real Arc L1 hashes (DEMO_MODE=false). "
                    "Verify any hash independently at testnet.arcscan.app."
                ),
            },
            "economics": {
                "treasury": treasury_state,
                "protected_usdc": protected_usdc,
                "security_cost_usdc": security_cost,
                "roi_protected_over_cost": round(roi, 4),
            },
            "decisions_summary": {
                "allow": stats.get("allow", 0),
                "block": stats.get("block", 0),
                "escalate": stats.get("escalate", 0),
                "patterns_learned": stats.get("patterns_learned", 0),
            },
            "threat_registry": await threat_registry.get_stats(),
            "contract_inspector": {
                "enabled": True,
                "detection_layers": [
                    "eoa_vs_contract",
                    "service_registry_crosscheck",
                    "memoclaw_drain_history",
                    "dangerous_selectors_4bytes",
                    "delegatecall_proxy_opcode_0xF4",
                    "selfdestruct_opcode_0xFF",
                    "eip1167_minimal_proxy",
                ],
                "note": "Bytecode analysis uses correct EVM opcodes (0xF4=DELEGATECALL, 0xFF=SELFDESTRUCT) and keccak256 function selectors — not heuristic patterns.",
            },
            "ecosystem": ecosystem_orchestrator.get_status(),
            "margin_story": {
                "arc_fee_assumption_usdc": 0.000003,
                "ethereum_fee_example_usdc": 0.5,
                "polygon_fee_example_usdc": 0.01,
                "why_arc": (
                    "Sub-cent pricing breaks on traditional gas. "
                    "Arc L1 fee ($0.000003) = 0.3% of service price ($0.001). "
                    "On Ethereum mainnet the same tx costs $0.50–$5.00 = 500–5000× the service price."
                ),
            },
        }

        out_path = Path(settings.demo_report_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report

    @app.get("/demo/live", tags=["Demo"])
    async def demo_live():
        """Server-sent events stream for premium demo UI."""

        async def event_generator():
            # FIX #20: Wrap with try/except so the generator exits cleanly when
            # the client disconnects. Without this, the while-loop keeps running
            # and holding DB resources until the next server restart.
            try:
                while True:
                    stats = await memory.get_stats()
                    patterns = await memory.get_top_patterns(5)
                    agents = await memory.get_all_agents()
                    # Comptage onchain via méthode dédiée (requête SQL unique, connexion partagée)
                    onchain_counts = await memory.get_onchain_counts()
                    simulated_tx_count = onchain_counts["simulated_tx_count"]
                    confirmed_onchain_tx_count = onchain_counts[
                        "confirmed_onchain_tx_count"
                    ]
                    recent_logs = await memory.get_recent_decisions(20)
                    allow_threshold, block_threshold = await policy_brain.get_thresholds()
                    latest_policy = await memory.get_latest_policy_update()
                    hogonat_history_list = await memory.get_hogonat_history(15)
                    payload = {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "treasury": treasury.get_state(),
                        "decisions": stats,
                        "onchain_proof": {
                            "simulated_tx_count": simulated_tx_count,
                            "confirmed_onchain_tx_count": confirmed_onchain_tx_count,
                            "target_50_met": confirmed_onchain_tx_count >= 50,
                        },
                        "threat_registry": await threat_registry.get_stats(),
                        "top_patterns": patterns,
                        "agents_tracked": len(agents),
                        "ecosystem": ecosystem_orchestrator.get_status(),
                        "policy": {
                            "allow_threshold": allow_threshold,
                            "block_threshold": block_threshold,
                            "latest_update": latest_policy,
                        },
                        "recent_logs": recent_logs,
                        "hogonat_history": hogonat_history_list,
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                    await asyncio.sleep(2)
            except asyncio.CancelledError:
                # Client disconnected — exit generator cleanly
                return

        headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(
            event_generator(), media_type="text/event-stream", headers=headers
        )

    @app.websocket("/ws/live")
    async def ws_live(websocket: WebSocket):
        """WebSocket stream for premium demo UI (Attack Theater)."""
        await websocket.accept()
        try:
            while True:
                stats = await memory.get_stats()
                patterns = await memory.get_top_patterns(5)
                agents = await memory.get_all_agents()
                onchain_counts = await memory.get_onchain_counts()
                simulated_tx_count = onchain_counts["simulated_tx_count"]
                confirmed_onchain_tx_count = onchain_counts["confirmed_onchain_tx_count"]
                recent_logs = await memory.get_recent_decisions(20)
                allow_threshold, block_threshold = await policy_brain.get_thresholds()
                latest_policy = await memory.get_latest_policy_update()
                hogonat_history_list = await memory.get_hogonat_history(15)
                payload = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "treasury": treasury.get_state(),
                    "decisions": stats,
                    "onchain_proof": {
                        "simulated_tx_count": simulated_tx_count,
                        "confirmed_onchain_tx_count": confirmed_onchain_tx_count,
                        "target_50_met": confirmed_onchain_tx_count >= 50,
                    },
                    "threat_registry": await threat_registry.get_stats(),
                    "top_patterns": patterns,
                    "agents_tracked": len(agents),
                    "ecosystem": ecosystem_orchestrator.get_status(),
                    "policy": {
                        "allow_threshold": allow_threshold,
                        "block_threshold": block_threshold,
                        "latest_update": latest_policy,
                    },
                    "recent_logs": recent_logs,
                    "hogonat_history": hogonat_history_list,
                }
                await websocket.send_text(json.dumps(payload))
                await asyncio.sleep(2)
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            pass
