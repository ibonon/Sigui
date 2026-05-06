"""
Sigui P2 — Solana adapter (mock realistic).
"""

from __future__ import annotations

import hashlib
import time

from .base_adapter import ChainAdapter


class SolanaAdapter(ChainAdapter):
    chain_name = "solana"
    native_currency = "USDC"

    async def verify_payment(
        self, tx_hash: str, expected_amount: float, expected_to: str
    ) -> bool:
        # P2 mock mode: accepts non-empty hash and positive amount.
        return bool(tx_hash) and expected_amount >= 0.0 and bool(expected_to)

    async def log_decision(
        self, decision_hash: str, decision: str, risk_score: float
    ) -> str:
        raw = f"sol:{decision_hash}:{decision}:{risk_score}:{time.time_ns()}".encode()
        return "5Ux" + hashlib.sha256(raw).hexdigest()[:60]

    async def get_usdc_balance(self, address: str) -> float:
        # Mock fixed balance for demo badges.
        return 1.0
