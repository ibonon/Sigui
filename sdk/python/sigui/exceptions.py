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
    def __init__(self, result):
        self.result = result
        super().__init__(
            f"Action BLOCKED by Sigui — "
            f"risk={result.risk_score:.3f} reason={result.reason}"
        )


class SiguiEscalationRequiredError(SiguiError):
    """
    Raised when verdict is ESCALATE and raise_on_escalate=True.
    Contains the original evaluation result.
    """
    def __init__(self, result):
        self.result = result
        super().__init__(
            f"Action requires ESCALATION — "
            f"risk={result.risk_score:.3f} cost=${result.escalation_cost_usdc}"
        )


class SiguiServiceUnavailableError(SiguiError):
    """Sigui service is in EMERGENCY mode or temporarily unavailable (HTTP 503)."""
    pass
