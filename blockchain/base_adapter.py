"""
Sigui P2 — Blockchain abstraction base interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class ChainAdapter(ABC):
    chain_name: str
    native_currency: str

    @abstractmethod
    async def verify_payment(
        self, tx_hash: str, expected_amount: float, expected_to: str
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def log_decision(
        self, decision_hash: str, decision: str, risk_score: float
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def get_usdc_balance(self, address: str) -> float:
        raise NotImplementedError
