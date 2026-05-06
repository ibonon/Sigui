"""
Sigui P2 — Arc adapter (real path via existing Arc client).
"""

from __future__ import annotations

from clients.integrations import arc_client, circle_client

from .base_adapter import ChainAdapter


class ArcAdapter(ChainAdapter):
    chain_name = "arc"
    native_currency = "USDC"

    async def verify_payment(
        self, tx_hash: str, expected_amount: float, expected_to: str
    ) -> bool:
        return await arc_client.verify_payment(tx_hash, expected_amount, expected_to)

    async def log_decision(
        self, decision_hash: str, decision: str, risk_score: float
    ) -> str:
        return await arc_client.log_decision_onchain(decision_hash, decision, risk_score)

    async def get_usdc_balance(self, address: str) -> float:
        # Address routing is handled by Circle wallet IDs in current architecture.
        return await circle_client.get_wallet_balance()
