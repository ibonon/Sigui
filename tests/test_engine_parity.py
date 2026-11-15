"""
Test de parité — `sigui_guard.local_engine` vs `modules.security_engine`.

Objectif : garantir que le port hors-ligne du moteur de décision (SDK
`sigui_guard`) rend EXACTEMENT le même verdict et le même risk_score que le
moteur de référence de la plateforme (`RiskEngine.score` + `DecisionEngine.decide`).

Pourquoi ce test existe
-----------------------
`sigui_guard/local_engine.py` est un port délibéré (pas un import direct) afin de
respecter la contrainte projet : le point d'entrée SDK doit rester sans dépendance
lourde (ni FastAPI, ni pydantic, ni numpy, ni réseau). Un port manuel dérive
silencieusement. Ce test est le garde-fou : il échoue dès qu'un seul cas diverge.

Périmètre couvert
-----------------
- Chemin déterministe uniquement : `settings.decision_ai_enabled = False`
  (l'IA/LLM est non déterministe par nature et ne fait pas partie du port).
- `escalation_available = False` (le mode local du SDK ne dispose d'aucun backend
  d'escalade — c'est le cas de référence).
- Seuils lus DEPUIS la source de vérité de la plateforme (`policy_brain.get_thresholds()`,
  alimentée par Hogonat), afin de comparer l'ALGORITHME et non la configuration.

Non couvert (documenté, hors périmètre du port)
-----------------------------------------------
- Le contournement `agent_payer` / `agent_learner` dans l'override anti-splitting
  de `DecisionEngine.decide` (exception de politique plateforme sur des agents
  internes) n'est pas répliqué dans le SDK : les cas ci-dessous n'utilisent pas
  ces identifiants réservés.
"""

from __future__ import annotations

import asyncio

import pytest

import sigui_guard.local_engine as le
from agent.loop import AgentMode
from config import settings
from ecosystem.address_pool import AddressPool
from modules import security_engine as se
from modules.ai_engines import policy_brain
from modules.security_engine import ActionInput

SAFE = AddressPool.KNOWN_SAFE
BLACK = "0xdead0000000000000000000000000000000000ff"

# ─────────────────────────────────────────────────────────────────────────────
# Jeu de cas : mêmes entrées logiques pour les deux moteurs.
#
#   profile  -> security_engine: agent_profile ; local: ctx (avg_amount_usd,
#               tx_count, trust_score)
#   context  -> contexte partagé (frequency_last_minute, cumulative_flow,
#               global_flow, service_eval, contract_eval)
#   pattern_risk -> security_engine: 3e arg de score() ; local: ctx["pattern_risk"]
# ─────────────────────────────────────────────────────────────────────────────

_P = lambda avg, trust, tx: {  # noqa: E731 — fabrique de profil compact
    "avg_amount_usdc": avg,
    "trust_score": trust,
    "tx_count": tx,
}


CASES: list[dict] = [
    # — Axe action : destinations connues / inconnues / blacklistées —
    {
        "name": "01_transfer_safe_normal",
        "action_type": "transfer", "amount_usd": 0.5, "destination": SAFE[0],
        "agent_id": "parity_01", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "02_transfer_safe_high_trust_clean",
        "action_type": "transfer", "amount_usd": 3.0, "destination": SAFE[3],
        "agent_id": "parity_02", "profile": _P(10.0, 0.9, 100), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "03_transfer_unknown_known_agent",
        "action_type": "transfer", "amount_usd": 4.0, "destination": "0xnew_a_00000000000000000000000000000001",
        "agent_id": "parity_03", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "04_transfer_large_unknown_hardblock",
        "action_type": "transfer", "amount_usd": 25.0, "destination": "0xnew_b_00000000000000000000000000000002",
        "agent_id": "parity_04", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "05_transfer_exactly_20_unknown_hardblock",
        "action_type": "transfer", "amount_usd": 20.0, "destination": "0xnew_c_00000000000000000000000000000003",
        "agent_id": "parity_05", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "06_destination_blacklisted",
        "action_type": "transfer", "amount_usd": 5.0, "destination": BLACK,
        "agent_id": "parity_06", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    # — Axe action : nouveaux agents / montants vs moyenne —
    {
        "name": "07_new_agent_1usd_unknown_hardblock",
        "action_type": "transfer", "amount_usd": 1.0, "destination": "0xnew_d_00000000000000000000000000000004",
        "agent_id": "parity_07", "profile": _P(10.0, 0.5, 0), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "08_ratio_15x_unknown",
        "action_type": "transfer", "amount_usd": 150.0, "destination": "0xnew_e_00000000000000000000000000000005",
        "agent_id": "parity_08", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "09_ratio_25x_unknown_extreme_hardblock",
        "action_type": "transfer", "amount_usd": 250.0, "destination": "0xnew_f_00000000000000000000000000000006",
        "agent_id": "parity_09", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    # — Axe contexte : fréquence —
    {
        "name": "10_high_frequency_15rpm",
        "action_type": "transfer", "amount_usd": 5.0, "destination": SAFE[1],
        "agent_id": "parity_10", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 15},
    },
    {
        "name": "11_elevated_frequency_7rpm",
        "action_type": "transfer", "amount_usd": 5.0, "destination": SAFE[1],
        "agent_id": "parity_11", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 7},
    },
    # — Axe historique —
    {
        "name": "12_low_trust_known_dest",
        "action_type": "transfer", "amount_usd": 3.0, "destination": SAFE[2],
        "agent_id": "parity_12", "profile": _P(10.0, 0.10, 100), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "13_zero_history_small",
        "action_type": "transfer", "amount_usd": 3.0, "destination": SAFE[2],
        "agent_id": "parity_13", "profile": _P(10.0, 0.5, 0), "context": {"frequency_last_minute": 1},
    },
    # — Autres types d'action —
    {
        "name": "14_contract_interaction_no_history",
        "action_type": "contract_interaction", "amount_usd": 1.0, "destination": "0xnew_g_00000000000000000000000000000007",
        "agent_id": "parity_14", "profile": _P(10.0, 0.5, 0), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "15_api_call_nominal",
        "action_type": "api_call", "amount_usd": 0.2, "destination": "0xnew_h_00000000000000000000000000000008",
        "agent_id": "parity_15", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    {
        "name": "16_swap_safe",
        "action_type": "swap", "amount_usd": 2.0, "destination": SAFE[4],
        "agent_id": "parity_16", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 1},
    },
    # — Anti-splitting / Sybil (règles à mots-clés → override BLOCK) —
    {
        "name": "17_cumulative_flow_same_dest",
        "action_type": "transfer", "amount_usd": 4.0, "destination": "0xnew_i_00000000000000000000000000000009",
        "agent_id": "parity_17", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "cumulative_flow": {"total_amount": 600.0, "tx_count": 5}},
    },
    {
        "name": "18_splitting_many_tx_same_dest",
        "action_type": "transfer", "amount_usd": 4.0, "destination": "0xnew_j_00000000000000000000000000000010",
        "agent_id": "parity_18", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "cumulative_flow": {"total_amount": 40.0, "tx_count": 30}},
    },
    {
        "name": "19_multi_dest_sybil",
        "action_type": "transfer", "amount_usd": 4.0, "destination": "0xnew_k_00000000000000000000000000000011",
        "agent_id": "parity_19", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "global_flow": {"dest_count": 20, "total_amount": 2000.0}},
    },
    {
        "name": "20_uniform_micro_splitting",
        "action_type": "transfer", "amount_usd": 4.0, "destination": "0xnew_l_00000000000000000000000000000012",
        "agent_id": "parity_20", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "cumulative_flow": {"total_amount": 25.0, "tx_count": 25, "max_single": 1.0, "min_single": 0.98}},
    },
    # — Réputation de service —
    {
        "name": "21_service_verified",
        "action_type": "transfer", "amount_usd": 5.0, "destination": "0xnew_m_00000000000000000000000000000013",
        "agent_id": "parity_21", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "service_eval": {"risk_delta": -0.25, "name": "oracleA"}},
    },
    {
        "name": "22_service_suspicious",
        "action_type": "transfer", "amount_usd": 5.0, "destination": "0xnew_n_00000000000000000000000000000014",
        "agent_id": "parity_22", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "service_eval": {"risk_delta": 0.30, "name": "svcX"}},
    },
    {
        "name": "23_service_malicious_hardblock",
        "action_type": "transfer", "amount_usd": 5.0, "destination": "0xnew_o_00000000000000000000000000000015",
        "agent_id": "parity_23", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "service_eval": {"risk_delta": 0.60, "name": "evil"}},
    },
    # — Inspection de contrat —
    {
        "name": "24_contract_verified",
        "action_type": "contract_interaction", "amount_usd": 2.0, "destination": "0xnew_p_00000000000000000000000000000016",
        "agent_id": "parity_24", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "contract_eval": {"risk_delta": -0.30, "flags": ["verified"]}},
    },
    {
        "name": "25_contract_drain_hardblock",
        "action_type": "contract_interaction", "amount_usd": 2.0, "destination": "0xnew_q_00000000000000000000000000000017",
        "agent_id": "parity_25", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "contract_eval": {"risk_delta": 0.70, "reason": "drain"}},
    },
    {
        "name": "26_contract_dangerous_selectors_hardblock",
        "action_type": "contract_interaction", "amount_usd": 2.0, "destination": "0xnew_r_00000000000000000000000000000018",
        "agent_id": "parity_26", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1, "contract_eval": {"risk_delta": 0.40}},
    },
    # — Pattern MemoClaw —
    {
        "name": "27_pattern_risk_mid",
        "action_type": "transfer", "amount_usd": 4.0, "destination": "0xnew_s_00000000000000000000000000000019",
        "agent_id": "parity_27", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1}, "pattern_risk": 0.25,
    },
    {
        "name": "28_pattern_risk_high_hardblock",
        "action_type": "transfer", "amount_usd": 4.0, "destination": "0xnew_t_00000000000000000000000000000020",
        "agent_id": "parity_28", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 1}, "pattern_risk": 0.50,
    },
    # — Zone grise (teste la sémantique d'escalade sans backend) —
    {
        "name": "29_gray_band_low",
        "action_type": "transfer", "amount_usd": 100.0, "destination": "0xnew_u_00000000000000000000000000000021",
        "agent_id": "parity_29", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 7},
    },
    {
        "name": "30_gray_band_upper",
        "action_type": "transfer", "amount_usd": 180.0, "destination": "0xnew_v_00000000000000000000000000000022",
        "agent_id": "parity_30", "profile": _P(10.0, 0.4, 50), "context": {"frequency_last_minute": 12},
    },
    # — Zone grise RÉELLE [allow, 0.50) : hors transfert (pas de hard block montant) —
    {
        "name": "31_gray_band_R040_escalate_semantics",
        "action_type": "swap", "amount_usd": 100.0, "destination": "0xnew_w_00000000000000000000000000000023",
        "agent_id": "parity_31", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 12},
    },
    {
        "name": "32_gray_band_R060_both_escalate",
        "action_type": "swap", "amount_usd": 180.0, "destination": "0xnew_x_00000000000000000000000000000024",
        "agent_id": "parity_32", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 12},
    },
    {
        "name": "33_above_block_R072_both_block",
        "action_type": "swap", "amount_usd": 180.0, "destination": "0xnew_y_00000000000000000000000000000025",
        "agent_id": "parity_33", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 12, "contract_eval": {"risk_delta": 0.20, "flags": ["unverified"]}},
    },
    # — Bande ESCALATE réelle [0.50, 0.70) : ratio>10 mais fréquence <= 10 => pas de hard block —
    {
        "name": "34_gray_band_R052_both_escalate",
        "action_type": "swap", "amount_usd": 150.0, "destination": "0xnew_z_00000000000000000000000000000026",
        "agent_id": "parity_34", "profile": _P(10.0, 0.5, 50), "context": {"frequency_last_minute": 7},
    },
    {
        "name": "35_gray_band_R063_both_escalate",
        "action_type": "swap", "amount_usd": 150.0, "destination": "0xnew_z2_0000000000000000000000000000027",
        "agent_id": "parity_35", "profile": _P(10.0, 0.5, 50),
        "context": {"frequency_last_minute": 7, "contract_eval": {"risk_delta": 0.20, "flags": ["unverified"]}},
    },
]


async def _reference(case: dict, allow: float, block: float) -> tuple[str, float]:
    """Verdict + score du moteur de référence (plateforme)."""
    action = ActionInput(
        agent_id=case["agent_id"],
        action_type=case["action_type"],
        amount_usdc=case["amount_usd"],
        destination=case["destination"],
        context=dict(case.get("context", {})),
    )
    risk = await se.risk_engine.score(
        action, dict(case["profile"]), case.get("pattern_risk", 0.0)
    )
    out = await se.decision_engine.decide(
        agent_id=case["agent_id"],
        action_type=case["action_type"],
        amount_usdc=case["amount_usd"],
        destination=case["destination"],
        risk=risk,
        sigui_mode=AgentMode.NORMAL,
        escalation_available=False,
        agent_profile=dict(case["profile"]),
        skip_onchain_log=True,
    )
    return out.decision, round(float(out.risk_score), 4)


def _local(case: dict, allow: float, block: float) -> tuple[str, float]:
    """Verdict + score du moteur local du SDK (mêmes entrées logiques)."""
    profile = case["profile"]
    ctx = dict(case.get("context", {}))
    ctx.update(
        {
            "avg_amount_usd": profile.get("avg_amount_usdc"),
            "tx_count": profile.get("tx_count"),
            "trust_score": profile.get("trust_score"),
            "known_safe": AddressPool.KNOWN_SAFE,
        }
    )
    if "pattern_risk" in case:
        ctx["pattern_risk"] = case["pattern_risk"]
    r = le.evaluate_local(
        action_type=case["action_type"],
        amount_usd=case["amount_usd"],
        destination=case["destination"],
        agent_context=ctx,
        agent_id=case["agent_id"],
        allow_threshold=allow,
        block_threshold=block,
    )
    return r.decision, round(float(r.risk_score), 4)


async def _run_all() -> list[dict]:
    allow, block = await policy_brain.get_thresholds()
    le.reset_frequency_state()
    rows: list[dict] = []
    for case in CASES:
        ref_dec, ref_score = await _reference(case, allow, block)
        loc_dec, loc_score = _local(case, allow, block)
        rows.append(
            {
                "name": case["name"],
                "ref_dec": ref_dec,
                "loc_dec": loc_dec,
                "ref_score": ref_score,
                "loc_score": loc_score,
                "dec_ok": ref_dec == loc_dec,
                "score_ok": abs(ref_score - loc_score) <= 1e-9,
                "allow_threshold": allow,
                "block_threshold": block,
            }
        )
    return rows


def test_engine_parity(monkeypatch):
    """20+ cas doivent produire un verdict et un risk_score identiques."""
    # Chemin déterministe : on neutralise l'IA/LLM (non déterministe, hors port).
    monkeypatch.setattr(settings, "decision_ai_enabled", False)

    rows = asyncio.run(_run_all())

    header = f"{'CAS':<34} {'REF':<9} {'LOCAL':<9} {'R_REF':>7} {'R_LOC':>7}  OK"
    print("\n" + header)
    print("-" * len(header))
    divergences: list[dict] = []
    for r in rows:
        ok = r["dec_ok"] and r["score_ok"]
        if not ok:
            divergences.append(r)
        print(
            f"{r['name']:<34} {r['ref_dec']:<9} {r['loc_dec']:<9} "
            f"{r['ref_score']:>7.4f} {r['loc_score']:>7.4f}  {'oui' if ok else 'NON'}"
        )

    total = len(rows)
    matched = total - len(divergences)
    print("-" * len(header))
    print(
        f"Concordance : {matched}/{total}  "
        f"(seuils de référence policy_brain : allow<{rows[0]['allow_threshold']}, "
        f"block>={rows[0]['block_threshold']})"
    )

    assert not divergences, (
        f"{len(divergences)}/{total} cas divergent entre local_engine et security_engine :\n"
        + "\n".join(
            f"  - {d['name']}: ref={d['ref_dec']}/{d['ref_score']:.4f} "
            f"vs local={d['loc_dec']}/{d['loc_score']:.4f}"
            for d in divergences
        )
    )
