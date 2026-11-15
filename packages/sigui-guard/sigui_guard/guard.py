"""
sigui_guard.guard — Point d'entrée public : check_action().

    from sigui_guard import check_action

    verdict = check_action(
        action_type="transfer",
        amount_usd=500,
        destination="0xabc...",
        agent_context={"avg_amount_usd": 12.0, "tx_count": 240, "trust_score": 0.9},
    )
    if verdict.blocked:
        raise RuntimeError(verdict.reason)

Modes :
  engine="local"  (défaut)  → règles embarquées, hors ligne, aucune clé, réseau inutile.
  engine="hosted"           → couche protocole Sigui (Imina-Na V2, ThreatRegistry, MemoClaw).
  mode="shadow"             → le verdict est calculé et journalisé, mais jamais appliqué.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from typing import Any

from sigui_guard.local_engine import evaluate_local
from sigui_guard.verdict import Decision, Verdict

logger = logging.getLogger("sigui_guard")

VALID_MODES = ("enforce", "shadow")
VALID_ENGINES = ("local", "hosted")
VALID_HOSTED_FAILURE_POLICIES = ("fallback_local", "block")

DEFAULT_HOSTED_ENDPOINT = "https://api.sigui.io"


def check_action(
    action_type: str,
    amount_usd: float = 0.0,
    destination: str = "",
    agent_context: dict[str, Any] | None = None,
    *,
    agent_id: str = "anonymous",
    chain: str = "ethereum",
    mode: str = "enforce",
    engine: str = "local",
    endpoint: str | None = None,
    api_key: str | None = None,
    timeout_s: float = 2.0,
    on_hosted_failure: str = "fallback_local",
    allow_threshold: float | None = None,
    block_threshold: float | None = None,
) -> Verdict:
    """Évalue une action d'agent et retourne un Verdict.

    Args:
        action_type: "transfer", "swap", "contract_interaction", "api_call", ...
        amount_usd: montant en USD (0 si non applicable).
        destination: adresse ou identifiant de la cible.
        agent_context: historique et signaux disponibles. Clés reconnues :
            avg_amount_usd, tx_count, trust_score, frequency_last_minute,
            cumulative_flow, global_flow, service_eval, contract_eval,
            known_safe, blacklist, pattern_risk.
        mode: "enforce" (applique) ou "shadow" (observe sans bloquer).
        engine: "local" (hors ligne) ou "hosted" (couche protocole Sigui).
        on_hosted_failure: "fallback_local" (défaut) ou "block" si le service
            hébergé est injoignable.

    Returns:
        Verdict. Pour bloquer une action, tester `verdict.blocked`.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {VALID_MODES}, got {mode!r}")
    if engine not in VALID_ENGINES:
        raise ValueError(f"engine must be one of {VALID_ENGINES}, got {engine!r}")
    if on_hosted_failure not in VALID_HOSTED_FAILURE_POLICIES:
        raise ValueError(
            f"on_hosted_failure must be one of {VALID_HOSTED_FAILURE_POLICIES}, "
            f"got {on_hosted_failure!r}"
        )

    t_start = time.perf_counter()

    if engine == "hosted":
        verdict = _check_action_hosted(
            action_type=action_type,
            amount_usd=amount_usd,
            destination=destination,
            agent_context=agent_context,
            agent_id=agent_id,
            chain=chain,
            endpoint=endpoint,
            api_key=api_key,
            timeout_s=timeout_s,
            on_hosted_failure=on_hosted_failure,
            allow_threshold=allow_threshold,
            block_threshold=block_threshold,
        )
    else:
        verdict = _local_verdict(
            action_type=action_type,
            amount_usd=amount_usd,
            destination=destination,
            agent_context=agent_context,
            agent_id=agent_id,
            allow_threshold=allow_threshold,
            block_threshold=block_threshold,
        )

    verdict.mode = mode
    verdict.blocked = mode == "enforce" and verdict.decision == Decision.BLOCK.value
    verdict.latency_ms = int((time.perf_counter() - t_start) * 1000)

    if mode == "shadow" and verdict.decision == Decision.BLOCK.value:
        logger.warning(
            "[SIGUI] shadow — aurait bloqué %s %.2f USD → %s (%s)",
            action_type,
            amount_usd,
            destination or "n/a",
            verdict.reason,
        )
    else:
        logger.info(
            "[SIGUI] %s %s %.2f USD → %s | engine=%s | %.1fms | %s",
            verdict.decision,
            action_type,
            amount_usd,
            destination or "n/a",
            verdict.engine,
            verdict.latency_ms,
            verdict.reason,
        )

    return verdict


def _local_verdict(
    *,
    action_type: str,
    amount_usd: float,
    destination: str,
    agent_context: dict[str, Any] | None,
    agent_id: str,
    allow_threshold: float | None,
    block_threshold: float | None,
) -> Verdict:
    result = evaluate_local(
        action_type=action_type,
        amount_usd=amount_usd,
        destination=destination,
        agent_context=agent_context,
        agent_id=agent_id,
        allow_threshold=allow_threshold,
        block_threshold=block_threshold,
    )
    return Verdict(
        decision=result.decision,
        reason=result.reason,
        engine="local",
        risk_score=result.risk_score,
        confidence=result.confidence,
        rules_triggered=list(result.rules_triggered),
        action_hash=result.action_hash,
        components=dict(result.components),
    )


def _check_action_hosted(
    *,
    action_type: str,
    amount_usd: float,
    destination: str,
    agent_context: dict[str, Any] | None,
    agent_id: str,
    chain: str,
    endpoint: str | None,
    api_key: str | None,
    timeout_s: float,
    on_hosted_failure: str,
    allow_threshold: float | None,
    block_threshold: float | None,
) -> Verdict:
    base = (endpoint or DEFAULT_HOSTED_ENDPOINT).rstrip("/")
    payload = {
        "action_type": action_type,
        "amount_usdc": amount_usd,
        "destination": destination,
        "agent_id": agent_id,
        "chain": chain,
        "context": dict(agent_context or {}),
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        request = urllib.request.Request(
            f"{base}/v2/evaluate",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        # OSError : DNS, connexion refusée, timeout. ValueError : réponse non-JSON.
        logger.warning("[SIGUI] hosted indisponible (%s) — politique: %s", exc, on_hosted_failure)
        if on_hosted_failure == "block":
            return Verdict(
                decision=Decision.BLOCK.value,
                reason=f"Service Sigui hébergé injoignable ({exc}). Politique fail-closed.",
                engine="hosted",
                risk_score=1.0,
                confidence=1.0,
                rules_triggered=["hosted_unavailable"],
            )
        fallback = _local_verdict(
            action_type=action_type,
            amount_usd=amount_usd,
            destination=destination,
            agent_context=agent_context,
            agent_id=agent_id,
            allow_threshold=allow_threshold,
            block_threshold=block_threshold,
        )
        fallback.reason = f"[repli local — hosted injoignable: {exc}] {fallback.reason}"
        return fallback

    if not isinstance(data, dict):
        data = {}

    decision = str(data.get("decision", "ESCALATE")).upper()
    if decision not in {d.value for d in Decision}:
        decision = Decision.ESCALATE.value

    return Verdict(
        decision=decision,
        reason=str(data.get("reason", "Verdict du service Sigui hébergé.")),
        engine="hosted",
        risk_score=float(data.get("risk_score", 0.0) or 0.0),
        confidence=float(data.get("confidence", 0.0) or 0.0),
        rules_triggered=list(data.get("rules_triggered") or []),
        action_hash=str(data.get("action_hash") or ""),
        raw=data,
    )
