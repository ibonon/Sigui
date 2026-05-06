"""
Sigui P2 — Adapter registry / selector.
"""

from __future__ import annotations

from .arc_adapter import ArcAdapter
from .base_adapter import ChainAdapter
from .eth_adapter import EthereumAdapter
from .sol_adapter import SolanaAdapter

_ADAPTERS: dict[str, ChainAdapter] = {
    "arc": ArcAdapter(),
    "ethereum": EthereumAdapter(),
    "solana": SolanaAdapter(),
}


def get_adapter(chain: str) -> ChainAdapter:
    return _ADAPTERS.get(chain, _ADAPTERS["arc"])
