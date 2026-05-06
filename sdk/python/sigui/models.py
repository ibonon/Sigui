"""
sigui.models — Types de données du SDK Sigui Protocol
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Verdict(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"
    ALLOW_WITH_CAP = "ALLOW_WITH_CAP"


class Chain(str, Enum):
    ARC = "arc"
    ETHEREUM = "ethereum"
    SOLANA = "solana"


@dataclass
class EvaluationResult:
    """
    Result of a POST /evaluate call.
    
    Attributes:
        verdict:        Security decision — ALLOW, BLOCK, or ESCALATE.
        risk_score:     Float [0.0, 1.0] — higher means riskier.
        confidence:     Model confidence in the decision.
        reason:         Human-readable explanation.
        action_hash:    Unique identifier for this evaluation.
        arc_tx_log:     On-chain proof tx hash (if applicable).
        arcwarden_mode: Operating mode — NORMAL, DEGRADED, or EMERGENCY.
        escalation_available: True if escalation endpoint is open.
        escalation_cost_usdc: Cost of calling /escalate.
        policy_source:  Which decision layer made the call.
        processing_time_ms: Backend evaluation time.
        vision_pattern: Visual attack pattern detected (if any).
        vision_confidence: Vision model confidence.
        evaluation_price_usdc: x402 fee paid for this evaluation.
        chain:          Chain on which the evaluation ran.
        raw:            Full raw response dict for advanced users.
    """
    verdict: Verdict
    risk_score: float
    confidence: float
    reason: str
    action_hash: str
    arc_tx_log: str = ""
    arcwarden_mode: str = "NORMAL"
    escalation_available: bool = False
    escalation_cost_usdc: float = 0.003
    policy_source: str = "unknown"
    processing_time_ms: int = 0
    vision_pattern: str = "NORMAL"
    vision_confidence: float = 0.0
    evaluation_price_usdc: float = 0.001
    chain: str = "arc"
    raw: dict = field(default_factory=dict)

    # ── Convenience properties ─────────────────────────────────────────────

    @property
    def is_safe(self) -> bool:
        """True if the action is safe to proceed with (ALLOW)."""
        return self.verdict == Verdict.ALLOW

    @property
    def is_blocked(self) -> bool:
        """True if the action is blocked by Sigui."""
        return self.verdict == Verdict.BLOCK

    @property
    def needs_escalation(self) -> bool:
        """True if the action requires human / deep-AI review."""
        return self.verdict == Verdict.ESCALATE

    @property
    def onchain_proof(self) -> Optional[str]:
        """Returns the Arc explorer URL for the on-chain proof, if available."""
        if not self.arc_tx_log or self.arc_tx_log.startswith("0xSIM_"):
            return None
        return f"https://testnet.arcscan.app/tx/{self.arc_tx_log}"

    def __repr__(self) -> str:
        return (
            f"EvaluationResult(verdict={self.verdict.value}, "
            f"risk={self.risk_score:.3f}, "
            f"reason={self.reason[:60]!r})"
        )


@dataclass
class EscalationResult:
    """
    Result of a POST /escalate call.
    Deep analysis by Lebe (Qwen2.5 AMD) or Claude.
    """
    verdict: Verdict
    cap_amount_usdc: float
    analysis: str
    confidence: float
    paid_by_arcwarden: bool = False
    claude_cost_usdc: float = 0.0
    arc_tx_log: str = ""
    fallback_used: bool = False
    degraded_mode: bool = False
    reason: str = ""
    inference_engine: str = "rule_based"
    inference_device: str = "CPU"
    raw: dict = field(default_factory=dict)

    @property
    def is_allowed_with_cap(self) -> bool:
        return self.verdict == Verdict.ALLOW_WITH_CAP

    def __repr__(self) -> str:
        return (
            f"EscalationResult(verdict={self.verdict.value}, "
            f"engine={self.inference_engine}, "
            f"analysis={self.analysis[:60]!r})"
        )


@dataclass
class TreasuryState:
    balance: float
    total_earned: float
    total_spent: float
    net_profit: float
    mode: str
    balances_by_chain: dict[str, float] = field(default_factory=dict)


@dataclass
class PaymentInfo:
    """x402 payment instructions returned by the server."""
    amount_usdc: float
    amount_units: int
    pay_to: str
    asset: str
    network: str
    decimals: int
    is_native: bool
    resource: str
    description: str
