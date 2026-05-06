"""
sigui — SDK Python pour le Sigui Protocol

Sigui est le réseau d'infrastructure de sécurité pour l'économie agentique.
Ce SDK permet à n'importe quel agent IA de protéger ses paiements USDC
en 2 lignes de code, avec paiement x402 entièrement automatique.

Quickstart:
    from sigui import SiguiClient

    async with SiguiClient(api_url="http://localhost:8000") as client:
        result = await client.evaluate(
            amount=5.0,
            destination="0xRecipient",
        )
        if result.is_safe:
            print("✅ Transaction authorized")

Links:
    Documentation: https://docs.sigui.io
    GitHub:        https://github.com/diass/Sigui
    HuggingFace:   https://huggingface.co/datasets/sigui/dogon-threats
"""

from .client import SiguiClient, SiguiClientSync
from .exceptions import (
    SiguiAuthError,
    SiguiBlockedError,
    SiguiConnectionError,
    SiguiError,
    SiguiEscalationRequiredError,
    SiguiPaymentError,
    SiguiRateLimitError,
    SiguiServiceUnavailableError,
)
from .models import Chain, EscalationResult, EvaluationResult, TreasuryState, Verdict
from .x402 import CircleWallet, DemoWallet

__version__ = "0.1.0"
__author__ = "Sigui Protocol"
__license__ = "MIT"

__all__ = [
    # Clients
    "SiguiClient",
    "SiguiClientSync",
    # Models
    "EvaluationResult",
    "EscalationResult",
    "TreasuryState",
    "Verdict",
    "Chain",
    # Wallets
    "DemoWallet",
    "CircleWallet",
    # Exceptions
    "SiguiError",
    "SiguiConnectionError",
    "SiguiPaymentError",
    "SiguiAuthError",
    "SiguiRateLimitError",
    "SiguiBlockedError",
    "SiguiEscalationRequiredError",
    "SiguiServiceUnavailableError",
]
