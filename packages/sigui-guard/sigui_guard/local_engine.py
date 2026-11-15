"""
sigui_guard.local_engine — Moteur de décision local, hors ligne, zéro dépendance.

Port déterministe des règles de `modules/security_engine.py` (RiskEngine + DecisionEngine)
en Python pur : pas de numpy, pas de pydantic, pas de loguru, aucun appel réseau.

⚠️ Limite assumée : sans accès au ThreatRegistry ni au modèle de vision Imina-Na, ce
moteur ne détecte PAS les topologies DRAIN_STAR / MIXING_CHAIN / COORDINATED_CLUSTER.
Ces détections restent disponibles via check_action(engine="hosted") — c'est la couche
protocole (ERC-8259 / Imina-Na / DePIN) qui apporte la valeur ajoutée payante.

Les seuils ci-dessous reprennent ceux de `config.py` (risk_allow_threshold=0.35,
risk_block_threshold=0.65) et ne sont pas réinventés ici.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Constantes de politique (identiques à la plateforme Sigui)
# ─────────────────────────────────────────────────────────────────────────────

WEIGHTS = (0.55, 0.30, 0.15)

DEFAULT_ALLOW_THRESHOLD = 0.35
DEFAULT_BLOCK_THRESHOLD = 0.65

# Sans backend d'escalade (mode local), la plateforme retombe sur ce seuil
# intermédiaire : ESCALATE si score >= 0.50, sinon ALLOW.
# Miroir exact de `DecisionEngine._decide_with_rules` (modules/security_engine.py).
ESCALATE_RISK_MIN_NO_BACKEND = 0.50

# Transfert ≥ 20 USD vers une destination non connue → blocage dur (règle plateforme)
LARGE_TRANSFER_HARD_BLOCK_USD = 20.0
# Nouvel agent (historique < 3 tx) envoyant ≥ 1 USD vers une destination inconnue
NEW_AGENT_TX_THRESHOLD = 3
NEW_AGENT_HIGH_AMOUNT_USD = 1.0

# Destinations de test connues comme malveillantes dans la plateforme.
# Un déploiement réel remplace cette liste par le ThreatRegistry (couche protocole).
KNOWN_BAD_DESTINATIONS = frozenset(
    {
        "0xdead0000000000000000000000000000000000ff",
        "0xbad00000000000000000000000000000000000ff",
    }
)

_SPLIT_KEYWORDS = ("splitting", "cumulative_flow", "multi_dest", "uniform_micro")

_FREQUENCY_WINDOW_S = 60.0
_FREQ_GC_EVERY_N_CALLS = 500
_FREQ_STALE_AFTER_S = 300.0

_FREQ_WINDOWS: dict[str, deque] = {}
_FREQ_LOCK = threading.Lock()
_FREQ_CALLS = 0


# ─────────────────────────────────────────────────────────────────────────────
# Résultat interne
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class LocalResult:
    decision: str
    risk_score: float
    confidence: float
    reason: str
    rules_triggered: list[str] = field(default_factory=list)
    components: dict[str, float] = field(default_factory=dict)
    hard_block_reason: str = ""
    action_hash: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Fréquence glissante par agent (60 s)
# ─────────────────────────────────────────────────────────────────────────────


def reset_frequency_state() -> None:
    """Vide l'état de fréquence en mémoire (utile pour les tests)."""
    with _FREQ_LOCK:
        _FREQ_WINDOWS.clear()


def _rolling_frequency(agent_id: str) -> float:
    global _FREQ_CALLS
    now = time.monotonic()
    with _FREQ_LOCK:
        window = _FREQ_WINDOWS.setdefault(agent_id, deque())
        while window and now - window[0] > _FREQUENCY_WINDOW_S:
            window.popleft()
        rpm = float(len(window))
        window.append(now)

        _FREQ_CALLS += 1
        if _FREQ_CALLS % _FREQ_GC_EVERY_N_CALLS == 0:
            stale = [
                aid
                for aid, dq in _FREQ_WINDOWS.items()
                if not dq or (now - dq[-1]) > _FREQ_STALE_AFTER_S
            ]
            for aid in stale:
                del _FREQ_WINDOWS[aid]
        return rpm


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _as_float(value: Any, default: float | None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_int(value: Any, default: int | None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_address_set(value: Any) -> set[str]:
    if not value:
        return set()
    if isinstance(value, str):
        value = [value]
    try:
        return {str(v).strip().lower() for v in value if str(v).strip()}
    except TypeError:
        return set()


def _make_action_hash(action_type: str, amount_usd: float, destination: str) -> str:
    raw = f"{action_type}:{amount_usd:.6f}:{destination.lower()}:{time.time_ns()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_reason(risk_score: float, rules: list[str]) -> str:
    if not rules:
        return f"Score {risk_score:.3f} — aucune règle déclenchée."
    return f"Score {risk_score:.3f} — {', '.join(rules[:4])}."


# ─────────────────────────────────────────────────────────────────────────────
# Moteur
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_local(
    *,
    action_type: str = "transfer",
    amount_usd: float = 0.0,
    destination: str = "",
    agent_context: dict[str, Any] | None = None,
    agent_id: str = "anonymous",
    allow_threshold: float | None = None,
    block_threshold: float | None = None,
) -> LocalResult:
    """Évalue une action sans aucun accès réseau. Retourne un LocalResult."""
    ctx = dict(agent_context or {})
    dest = (destination or "").strip().lower()
    amount = max(0.0, float(amount_usd or 0.0))

    known_safe = _as_address_set(ctx.get("known_safe"))
    blacklist = KNOWN_BAD_DESTINATIONS | _as_address_set(ctx.get("blacklist"))

    avg = _as_float(ctx.get("avg_amount_usd"), None)
    tx_count = _as_int(ctx.get("tx_count"), None)
    trust = _as_float(ctx.get("trust_score"), None)
    pattern_extra = _as_float(ctx.get("pattern_risk"), 0.0) or 0.0

    freq_ctx = _as_float(ctx.get("frequency_last_minute"), None)
    freq = freq_ctx if freq_ctx is not None else _rolling_frequency(agent_id)

    cumulative = ctx.get("cumulative_flow") or {}
    global_flow = ctx.get("global_flow") or {}
    service_eval = ctx.get("service_eval") or {}
    contract_eval = ctx.get("contract_eval") or {}

    ratio = round(amount / avg, 6) if avg and avg > 0 else None

    rules: list[tuple[str, float]] = []
    hard_block = False
    hard_block_reason = ""

    # ── Axe A : action ───────────────────────────────────────────────────────
    A = 0.0

    if dest and dest in blacklist:
        A += 0.50
        rules.append(("destination_blacklisted", 0.50))
        hard_block = True
        hard_block_reason = "destination_blacklisted"

    if ratio is not None:
        if ratio > 10:
            A += 0.35
            rules.append((f"amount_{amount:.2f}_vs_avg_{avg:.3f}", 0.35))
        elif ratio > 5:
            A += 0.18
            rules.append((f"amount_{amount:.2f}_vs_avg_{avg:.3f}_mod", 0.18))

    unknown_destination = False
    if dest and dest not in known_safe:
        if tx_count is not None and tx_count < NEW_AGENT_TX_THRESHOLD:
            A += 0.10
            rules.append(("unknown_destination", 0.10))
            unknown_destination = True
            if amount >= NEW_AGENT_HIGH_AMOUNT_USD:
                hard_block = True
                hard_block_reason = "new_agent_high_amount_unknown_destination"
        elif ratio is not None and ratio > 20:
            hard_block = True
            hard_block_reason = "extreme_amount_spike_to_unknown_destination"
            unknown_destination = True
    elif dest and dest in known_safe:
        A -= 0.30
        rules.append(("destination_whitelisted", -0.30))

    if action_type == "contract_interaction" and tx_count == 0:
        A += 0.15
        rules.append(("contract_interaction_no_history", 0.15))

    # ── Axe C : contexte ─────────────────────────────────────────────────────
    C = 0.0

    if freq > 10:
        C += 0.20
        rules.append((f"high_frequency_{freq:.0f}rpm", 0.20))
        if ratio is not None and ratio > 20:
            hard_block = True
            hard_block_reason = "extreme_frequency_and_amount_anomaly"
        elif ratio is not None and ratio > 10 and dest not in known_safe:
            hard_block = True
            hard_block_reason = "high_frequency_amount_spike_unknown_destination"
    elif freq > 5:
        C += 0.10
        rules.append((f"elevated_frequency_{freq:.0f}rpm", 0.10))

    if action_type == "transfer" and amount >= LARGE_TRANSFER_HARD_BLOCK_USD and dest and dest not in known_safe:
        hard_block = True
        hard_block_reason = "obvious_large_risky_transfer"

    if pattern_extra > 0:
        C += pattern_extra
        rules.append((f"known_pattern_weight_{pattern_extra:.2f}", pattern_extra))
        if pattern_extra >= 0.45:
            hard_block = True
            hard_block_reason = "known_attack_pattern_confirmed"

    # ── Axe H : historique ───────────────────────────────────────────────────
    H = 0.0

    if tx_count == 0:
        H += 0.05
        rules.append(("no_transaction_history", 0.05))

    if trust is not None and trust < 0.3:
        H += 0.15
        rules.append((f"low_trust_score_{trust:.2f}", 0.15))

    critical_signals = (
        (ratio is not None and ratio > 5)
        or freq > 8
        or pattern_extra > 0
        or dest in blacklist
    )
    if trust is not None and trust > 0.8 and not critical_signals:
        H -= 0.20
        rules.append((f"high_trust_score_{trust:.2f}", -0.20))

    # ── Flux cumulé : anti-splitting / Sybil ─────────────────────────────────
    total_to_dest = _as_float(cumulative.get("total_amount"), 0.0) or 0.0
    dest_tx_count = _as_int(cumulative.get("tx_count"), 0) or 0
    max_single = _as_float(cumulative.get("max_single"), 0.0) or 0.0
    min_single = _as_float(cumulative.get("min_single"), 0.0) or 0.0

    baseline = avg or 0.0
    if total_to_dest > max(5.0, baseline * 50) and dest not in known_safe:
        C += 0.35
        rules.append((f"cumulative_flow_{total_to_dest:.2f}_to_same_dest", 0.35))

    if dest_tx_count > 25 and dest not in known_safe:
        C += 0.25
        rules.append((f"splitting_detected_{dest_tx_count}_txs_same_dest", 0.25))

    dest_count = _as_int(global_flow.get("dest_count"), 0) or 0
    global_total = _as_float(global_flow.get("total_amount"), 0.0) or 0.0
    if dest_count > 15 and global_total > max(5.0, baseline * 100):
        C += 0.40
        rules.append(
            (f"multi_dest_splitting_{dest_count}_dests_{global_total:.2f}_total", 0.40)
        )

    if (
        dest_tx_count > 20
        and max_single > 0
        and (max_single - min_single) / max_single < 0.10
        and dest not in known_safe
    ):
        variance_ratio = (max_single - min_single) / max_single
        C += 0.30
        rules.append((f"uniform_micro_splitting_variance_{variance_ratio:.2f}", 0.30))

    # ── Réputation de service (fournie par l'appelant) ───────────────────────
    svc_delta = _as_float(service_eval.get("risk_delta"), 0.0) or 0.0
    if svc_delta != 0.0:
        A += svc_delta
        svc_name = service_eval.get("name") or (dest[:10] if dest else "unknown")
        if svc_delta < 0:
            rules.append((f"service_verified_{svc_name}", svc_delta))
        elif svc_delta > 0.50:
            rules.append((f"SERVICE_MALICIOUS_{svc_name}", svc_delta))
            hard_block = True
            hard_block_reason = f"known_malicious_service_{svc_name}"
        elif svc_delta > 0.20:
            rules.append((f"service_suspicious_{svc_name}_delta{svc_delta:.2f}", svc_delta))
        else:
            rules.append((f"service_unknown_{svc_name}", svc_delta))

    # ── Inspection de contrat (fournie par l'appelant) ───────────────────────
    contract_delta = _as_float(contract_eval.get("risk_delta"), 0.0) or 0.0
    if contract_delta != 0.0:
        contract_flags = contract_eval.get("flags") or []
        contract_reason = contract_eval.get("reason") or "unknown_contract"

        if contract_delta >= 0.70:
            hard_block = True
            hard_block_reason = "known_drain_contract"
            rules.append((f"CONTRACT_DRAIN_{str(contract_reason)[:30]}", contract_delta))
            A += contract_delta
        elif contract_delta >= 0.35:
            hard_block = True
            hard_block_reason = "contract_dangerous_withdraw_function"
            rules.append(("contract_dangerous_selectors", contract_delta))
            A += contract_delta
        elif contract_delta > 0:
            flag_str = contract_flags[0] if contract_flags else "unverified_contract"
            rules.append((f"contract_{flag_str}", contract_delta))
            A += contract_delta
        else:
            flag_str = contract_flags[0] if contract_flags else "verified_contract"
            rules.append((f"contract_{flag_str}", contract_delta))
            A += contract_delta

    # ── Scoring ──────────────────────────────────────────────────────────────
    R_raw = WEIGHTS[0] * A + WEIGHTS[1] * C + WEIGHTS[2] * H

    risk_boost = 0.0
    if ratio is not None and ratio > 10:
        risk_boost += 0.22
    elif ratio is not None and ratio > 5:
        risk_boost += 0.10
    if unknown_destination:
        risk_boost += 0.15
    if freq > 10:
        risk_boost += 0.14
    elif freq > 5:
        risk_boost += 0.08
    if tx_count == 0 and amount > 0.5:
        risk_boost += 0.12
    if pattern_extra > 0:
        risk_boost += min(0.20, pattern_extra * 0.5)

    risk_score = min(1.0, max(0.0, R_raw + risk_boost))

    triggered_names = [name for name, _ in rules]
    positive_count = sum(1 for _, delta in rules if delta > 0)
    confidence = min(0.98, 0.55 + positive_count * 0.08)

    # ── Décision ─────────────────────────────────────────────────────────────
    allow_th = DEFAULT_ALLOW_THRESHOLD if allow_threshold is None else allow_threshold
    block_th = DEFAULT_BLOCK_THRESHOLD if block_threshold is None else block_threshold

    if hard_block:
        decision = "BLOCK"
        reason = f"Règle bloquante : {hard_block_reason}."
    else:
        splitting_rules = [
            name for name in triggered_names if any(k in name for k in _SPLIT_KEYWORDS)
        ]
        if splitting_rules:
            decision = "BLOCK"
            reason = (
                "Fractionnement de transaction détecté. "
                f"Règles : {', '.join(splitting_rules[:2])}."
            )
        elif risk_score < allow_th:
            decision = "ALLOW"
            reason = _build_reason(risk_score, triggered_names)
        elif risk_score >= block_th:
            decision = "BLOCK"
            reason = _build_reason(risk_score, triggered_names)
        else:
            # Miroir de `DecisionEngine._decide_with_rules` quand aucun backend
            # d'escalade n'est disponible (mode local) : dans la zone
            # [allow_th, block_th), un score >= 0.50 escalade, sinon il est autorisé.
            if risk_score >= ESCALATE_RISK_MIN_NO_BACKEND:
                decision = "ESCALATE"
                reason = (
                    f"Zone d'incertitude (score {risk_score:.3f}) — "
                    "aucun backend d'escalade en mode local."
                )
            else:
                decision = "ALLOW"
                reason = _build_reason(risk_score, triggered_names)

    return LocalResult(
        decision=decision,
        risk_score=round(risk_score, 4),
        confidence=round(confidence, 4),
        reason=reason,
        rules_triggered=triggered_names,
        components={
            "action": round(min(1.0, max(0.0, A)), 4),
            "context": round(min(1.0, max(0.0, C)), 4),
            "history": round(min(1.0, max(0.0, H)), 4),
        },
        hard_block_reason=hard_block_reason,
        action_hash=_make_action_hash(action_type, amount, destination or ""),
    )
