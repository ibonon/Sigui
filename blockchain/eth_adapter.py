"""
Sigui P2 — Ethereum adapter (mock realistic).
"""

from __future__ import annotations

import hashlib
import time

from .base_adapter import ChainAdapter


class EthereumAdapter(ChainAdapter):
    chain_name = "ethereum"
    native_currency = "USDC"

    async def verify_payment(
        self, tx_hash: str, expected_amount: float, expected_to: str
    ) -> bool:
        # P2 mock mode: accepts non-empty hash and positive amount.
        return bool(tx_hash) and expected_amount >= 0.0 and bool(expected_to)

    async def log_decision(
        self, decision_hash: str, decision: str, risk_score: float
    ) -> str:
        raw = f"eth:{decision_hash}:{decision}:{risk_score}:{time.time_ns()}".encode()
        return "0xETH_" + hashlib.sha256(raw).hexdigest()

    async def get_usdc_balance(self, address: str) -> float:
        # Mock fixed balance for demo badges.
        return 1.0
