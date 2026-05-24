"""
sigui.exceptions — Custom exceptions du SDK Sigui Protocol
"""
from __future__ import annotations


class SiguiError(Exception):
    """Base exception for all Sigui SDK errors."""
    pass


class SiguiConnectionError(SiguiError):
    """Cannot reach the Sigui API."""
    def __init__(self, url: str, reason: str = ""):
        self.url = url
        msg = f"Cannot connect to Sigui API at {url}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class SiguiPaymentError(SiguiError):
    """x402 payment failed or was rejected."""
    def __init__(self, amount: float, reason: str = ""):
        self.amount = amount
        msg = f"x402 payment of ${amount:.6f} USDC failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)


class SiguiAuthError(SiguiError):
    """Invalid or missing API key / wallet credentials."""
    pass


class SiguiRateLimitError(SiguiError):
    """Rate limit exceeded (HTTP 429)."""
    def __init__(self, retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after}s.")


class SiguiBlockedError(SiguiError):
    """
    Raised when verdict is BLOCK and raise_on_block=True.
    Allows agents to use try/except instead of checking verdict manually.
    """
    def __init__(self, reason, risk_score: float = 0.0, vision_pattern: str | None = None, decision=None):
        if hasattr(reason, "reason"):
            result = reason
            self.result = result
            self.decision = result
            self.reason = result.reason
            self.risk_score = result.risk_score
            self.vision_pattern = getattr(result, "vision_pattern", None)
            msg = f"Action BLOCKED by Sigui — risk={result.risk_score:.3f} reason={result.reason}"
        else:
            self.reason = reason
            self.risk_score = risk_score
            self.vision_pattern = vision_pattern
            self.decision = decision
            self.result = decision
            msg = f"Transaction blocked by Sigui: {reason}"
        super().__init__(msg)


class SiguiEscalateError(SiguiError):
    """
    Raised when verdict is ESCALATE and raise_on_escalate=True.
    Contains the original evaluation decision.
    """
    def __init__(self, decision):
        self.decision = decision
        self.result = decision
        super().__init__(f"Transaction requires escalation (score={decision.risk_score:.2f})")

SiguiEscalationRequiredError = SiguiEscalateError


class SiguiServiceUnavailableError(SiguiError):
    """Sigui service is in EMERGENCY mode or temporarily unavailable (HTTP 503)."""
    pass
