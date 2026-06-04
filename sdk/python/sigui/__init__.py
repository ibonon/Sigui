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
    GitHub:        https://github.com/Ibonon/Sigui
    HuggingFace:   https://huggingface.co/Ibonon/Imina-Na-V2
    Dataset:       https://huggingface.co/datasets/Ibonon/sigui-depin-1m
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
from .models import Chain, EscalationResult, EvaluationResult, TreasuryState, Verdict, Decision
from .x402 import CircleWallet, DemoWallet, WalletAdapter
from .protect import protect
from .config import SiguiConfig
from .session import SiguiSession
from .discovery import NodeDiscovery

__version__ = "1.0.0"
__author__ = "Eric Warma"
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
    "WalletAdapter",
    # Exceptions
    "SiguiError",
    "SiguiConnectionError",
    "SiguiPaymentError",
    "SiguiAuthError",
    "SiguiRateLimitError",
    "SiguiBlockedError",
    "SiguiEscalationRequiredError",
    "SiguiEscalateError",
    "SiguiServiceUnavailableError",
    # v1.0 Core
    "protect",
    "SiguiConfig",
    "SiguiSession",
    "Decision",
    # Local & Pretrained
    "start_mock_server",
    "from_pretrained",
]

# Imports différés pour éviter la dépendance stricte
def start_mock_server(*args, **kwargs):
    from .local import start_mock_server as _start
    return _start(*args, **kwargs)

async def from_pretrained(*args, **kwargs):
    from .pretrained import from_pretrained as _from_pt
    return await _from_pt(*args, **kwargs)
