"""
sigui_guard.verdict — Résultat retourné par check_action().

Contrat public :
    verdict.decision  -> "ALLOW" | "BLOCK" | "ESCALATE"   (le verdict calculé)
    verdict.blocked    -> bool                            (ce que l'appelant DOIT respecter)
    verdict.engine     -> "local" | "hosted"              (qui a rendu le verdict)
    verdict.reason     -> explication lisible

Règle d'or : pour bloquer une action, l'appelant teste `verdict.blocked`, jamais
`verdict.decision`. En mode "shadow", `decision` reste le verdict calculé mais
`blocked` est toujours False.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


@dataclass
class Verdict:
    """Verdict de sécurité renvoyé par check_action()."""

    decision: str
    reason: str
    engine: str
    mode: str = "enforce"
    risk_score: float = 0.0
    confidence: float = 0.0
    rules_triggered: list[str] = field(default_factory=list)
    latency_ms: int = 0
    action_hash: str = ""
    blocked: bool = False
    components: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True si l'action peut continuer (ALLOW ou ESCALATE)."""
        return self.decision != Decision.BLOCK.value

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def __repr__(self) -> str:
        return (
            f"Verdict(decision={self.decision!r}, blocked={self.blocked}, "
            f"engine={self.engine!r}, risk_score={self.risk_score:.3f}, "
            f"reason={self.reason!r})"
        )
