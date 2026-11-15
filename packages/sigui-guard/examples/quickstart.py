"""
Preuve d'usage externe — un développeur qui découvre `sigui-guard` pour la
première fois : installation locale, puis dix lignes, puis un vrai verdict.

    pip install ./packages/sigui-guard
    python packages/sigui-guard/examples/quickstart.py

Aucune clé, aucun wallet, aucun réseau : le moteur local répond hors ligne.
Le script mesure le temps de réponse réel de chaque verdict.
"""

from __future__ import annotations

import time

from sigui_guard import check_action

SAFE = "0x1111222233334444555566667777888899990000"       # destination de confiance
UNKNOWN = "0xabc12345678901234567890123456789012345678"   # destination jamais vue


def show(label: str, verdict, elapsed_ms: float) -> None:
    print(
        f"[{label:<5}] decision={verdict.decision:<8} blocked={str(verdict.blocked):<5} "
        f"engine={verdict.engine:<6} risk={verdict.risk_score:.3f} "
        f"latency={elapsed_ms:.2f}ms"
    )
    print(f"         reason: {verdict.reason}")


def main() -> None:
    t0 = time.perf_counter()
    allowed = check_action(
        "transfer",
        amount_usd=5.0,
        destination=SAFE,
        agent_context={"avg_amount_usd": 12.0, "tx_count": 240, "trust_score": 0.9},
    )
    t1 = time.perf_counter()

    blocked = check_action("transfer", amount_usd=500.0, destination=UNKNOWN)
    t2 = time.perf_counter()

    show("ALLOW", allowed, (t1 - t0) * 1000)
    show("BLOCK", blocked, (t2 - t1) * 1000)
    print(f"\n2 verdicts rendus en {(t2 - t0) * 1000:.2f} ms au total.")


if __name__ == "__main__":
    main()
