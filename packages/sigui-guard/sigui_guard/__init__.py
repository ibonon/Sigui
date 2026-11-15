"""
sigui_guard — la porte d'entrée simple de Sigui.

Une fonction. Un verdict. Rien d'autre.

    from sigui_guard import check_action

    verdict = check_action(
        action_type="transfer",
        amount_usd=500,
        destination="0xabc...",
        agent_context={"trust_score": 0.9, "tx_count": 240, "avg_amount_usd": 12.0},
    )

    if verdict.blocked:          # None bloquant : pas de compte, pas de wallet, pas de clé
        raise RuntimeError(verdict.reason)

Zéro blockchain. Zéro DID. Zéro clé privée. Zéro enregistrement.
Le mode par défaut ("local") fonctionne hors ligne, sans aucune dépendance externe.

Architecture en couches :
    - `engine="local"`  → règles embarquées (offline, gratuit).
    - `engine="hosted"` → couche protocole Sigui : Imina-Na V2 (vision topologique),
      ThreatRegistry, MemoClaw. C'est là que vivent ERC-8259 / ZK / DePIN, en upgrade
      optionnel — jamais en prérequis.
"""

from sigui_guard.guard import check_action
from sigui_guard.local_engine import (
    KNOWN_BAD_DESTINATIONS,
    LocalResult,
    evaluate_local,
    reset_frequency_state,
)
from sigui_guard.verdict import Decision, Verdict

__version__ = "0.1.0"

__all__ = [
    "KNOWN_BAD_DESTINATIONS",
    "Decision",
    "LocalResult",
    "Verdict",
    "__version__",
    "check_action",
    "evaluate_local",
    "reset_frequency_state",
]
