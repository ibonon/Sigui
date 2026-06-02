"""
Sigui v3.0 — Treasury Manager
Circle DCW integration · P&L tracking · Autonomous mode management
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from loguru import logger

from agent.loop import (
    BALANCE_DEGRADED_THRESHOLD,
    BALANCE_EMERGENCY_THRESHOLD,
    BALANCE_NORMAL_THRESHOLD,
    AgentMode,
    determine_mode,
    is_self_protection,
    should_escalate,
)
from clients.integrations import circle_client
from config import settings


class TreasuryEmptyError(Exception):
    pass


@dataclass
class TreasuryState:
    balances_by_chain: dict[str, float] = field(default_factory=dict)
    total_earned: float = 0.0
    total_spent: float = 0.0
    mode: AgentMode = AgentMode.NORMAL
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def balance(self) -> float:
        return float(sum(self.balances_by_chain.values()))

    @property
    def net_profit(self) -> float:
        return self.total_earned - self.total_spent


class TreasuryManager:
    """
    Autonomous treasury management for Sigui.
    Handles USDC revenues, Claude payments, Arc fees, and mode switching.
    """

    def __init__(self):
        self._state = TreasuryState(
            balances_by_chain={settings.default_chain: settings.initial_balance_usdc}
        )
        self._lock = asyncio.Lock()
        self._db = None  # Set after memory init
        self._mode_change_callbacks = []
        self._last_mode = None
        try:
            self._last_mode = self.operating_mode
        except TreasuryEmptyError:
            self._last_mode = AgentMode.EMERGENCY

    def set_db(self, db):
        """Inject memory reference for treasury logging."""
        self._db = db

    async def recover_from_db(self):
        """
        Reconstruit l'état de la treasury depuis treasury_log au redémarrage.
        Préserve le P&L historique et recalcule le solde réel.
        """
        if not self._db:
            logger.warning(
                "[TREASURY] recover_from_db: no DB available, using initial state"
            )
            return
        try:
            # Use MemoClaw lock to prevent 'database is locked' during recovery
            async with self._db._lock:
                async with self._db._db.execute(
                    """
                    SELECT type, chain, COALESCE(SUM(amount_usdc), 0.0) AS total
                    FROM treasury_log
                    GROUP BY type, chain
                    """
                ) as cursor:
                    rows = await cursor.fetchall()

            earned = 0.0
            spent = 0.0
            balances_by_chain: dict[str, float] = {
                settings.default_chain: settings.initial_balance_usdc
            }
            for row in rows:
                tx_type, chain, total = row[0], row[1] or settings.default_chain, float(
                    row[2]
                )
                if tx_type == "revenue":
                    earned += total
                    balances_by_chain[chain] = balances_by_chain.get(chain, 0.0) + total
                elif tx_type == "expense":
                    spent += total
                    balances_by_chain[chain] = balances_by_chain.get(chain, 0.0) - total

            balances_by_chain = {
                k: round(max(0.0, v), 8) for k, v in balances_by_chain.items()
            }
            reconstructed_balance = float(sum(balances_by_chain.values()))

            async with self._lock:
                self._state.total_earned = earned
                self._state.total_spent = spent
                self._state.balances_by_chain = balances_by_chain
                self._state.last_updated = datetime.utcnow().isoformat()

            # Sync also the circle client simulated balance
            from clients.integrations import circle_client

            if circle_client.demo_mode:
                circle_client._simulated_balances[circle_client.wallet_id] = (
                    balances_by_chain.get(settings.default_chain, reconstructed_balance)
                )

            await self._check_mode_change()
            logger.success(
                f"[TREASURY] ✅ Recovered from DB — "
                f"earned=${earned:.4f} spent=${spent:.4f} "
                f"balance=${reconstructed_balance:.4f} "
                f"mode={self.operating_mode.value if reconstructed_balance > 0.01 else 'EMERGENCY'}"
            )
        except Exception as e:
            logger.warning(
                f"[TREASURY] DB recovery failed ({e}) — keeping initial state"
            )

    def on_mode_change(self, callback):
        self._mode_change_callbacks.append(callback)

    async def _check_mode_change(self):
        try:
            new_mode = self.operating_mode
        except TreasuryEmptyError:
            new_mode = AgentMode.EMERGENCY

        if self._last_mode is not None and self._last_mode != new_mode:
            for cb in self._mode_change_callbacks:
                await cb(self._last_mode.value, new_mode.value)
        self._last_mode = new_mode

    @property
    def balance(self) -> float:
        return self._state.balance

    @property
    def net_profit(self) -> float:
        return self._state.net_profit

    @property
    def operating_mode(self) -> AgentMode:
        if is_self_protection(self._state.balance):
            raise TreasuryEmptyError("Sigui treasury empty — refusing new requests")
        return determine_mode(self._state.balance)

    def get_state(self) -> dict:
        return {
            "balance": round(self._state.balance, 6),
            "balances_by_chain": {
                chain: round(amount, 6)
                for chain, amount in self._state.balances_by_chain.items()
            },
            "total_earned": round(self._state.total_earned, 6),
            "total_spent": round(self._state.total_spent, 6),
            "net_profit": round(self._state.net_profit, 6),
            "mode": self.operating_mode.value
            if self._state.balance > 0.01
            else "EMERGENCY",
            "last_updated": datetime.utcnow().isoformat(),
        }

    async def sync_from_circle(self):
        """Sync balance from Circle API (or demo simulation)."""
        live_balance = await circle_client.get_wallet_balance()
        async with self._lock:
            # FIX #7: Only update the Arc balance — never touch other chains
            # (Ethereum, Solana) that may have accumulated revenue locally.
            # Additionally, only replace if Circle reports a higher value;
            # locally-accumulated revenue between syncs must not be erased.
            current_arc = self._state.balances_by_chain.get(settings.default_chain, 0.0)
            self._state.balances_by_chain[settings.default_chain] = max(current_arc, live_balance)
            self._state.last_updated = datetime.utcnow().isoformat()
        await self._check_mode_change()
        # FIX #18: use operating_mode (dynamic property) instead of _state.mode
        # (_state.mode is the dataclass default field — always NORMAL).
        try:
            _mode_str = self.operating_mode.value
        except TreasuryEmptyError:
            _mode_str = AgentMode.EMERGENCY.value
        logger.debug(
            f"[TREASURY] Sync: balance=${self._state.balance:.6f} mode={_mode_str}"
        )

    async def record_revenue(
        self, amount_usdc: float, description: str = "eval_fee", chain: str = "arc"
    ):
        """Record incoming payment from client agent."""
        async with self._lock:
            self._state.balances_by_chain[chain] = (
                self._state.balances_by_chain.get(chain, 0.0) + amount_usdc
            )
            self._state.total_earned += amount_usdc
            circle_client.add_revenue(amount_usdc)
        if self._db:
            await self._db.log_treasury("revenue", amount_usdc, description, chain=chain)
        await self._check_mode_change()
        logger.debug(
            f"[TREASURY] +${amount_usdc:.6f} ({description}, chain={chain}) "
            f"→ balance=${self._state.balance:.6f}"
        )

    def _pick_spend_chain(self, preferred_chain: str = "arc") -> str:
        if preferred_chain in self._state.balances_by_chain:
            return preferred_chain
        if not self._state.balances_by_chain:
            return settings.default_chain
        return max(self._state.balances_by_chain, key=self._state.balances_by_chain.get)

    async def pay_for_escalation(self) -> bool:
        """
        Sigui pays Claude from its own treasury.
        Returns False if insufficient funds → fallback rule-based activated.
        """
        cost = settings.claude_cost_per_escalation
        async with self._lock:
            if self._state.balance < cost:
                logger.warning(
                    f"[TREASURY] Insufficient funds for escalation "
                    f"(balance=${self._state.balance:.6f} < ${cost}) — fallback activated"
                )
                return False
            spend_chain = self._pick_spend_chain(settings.default_chain)
            self._state.balances_by_chain[spend_chain] = max(
                0.0, self._state.balances_by_chain.get(spend_chain, 0.0) - cost
            )
            self._state.total_spent += cost
            circle_client.spend(cost)

        if self._db:
            await self._db.log_treasury(
                "expense",
                cost,
                "claude_escalation_api",
                chain=settings.default_chain,
            )
        await self._check_mode_change()
        logger.info(
            f"[TREASURY] -${cost:.6f} (claude_escalation) → balance=${self._state.balance:.6f}"
        )
        return True

    async def pay_arc_fee(self, amount: float = 0.000003, chain: str = "arc"):
        """Pay Arc transaction logging fee."""
        async with self._lock:
            spend_chain = self._pick_spend_chain(chain)
            self._state.balances_by_chain[spend_chain] = max(
                0.0, self._state.balances_by_chain.get(spend_chain, 0.0) - amount
            )
            self._state.total_spent += amount
            circle_client.spend(amount)
        if self._db:
            await self._db.log_treasury("expense", amount, "arc_tx_fee", chain=chain)
        await self._check_mode_change()

    def should_escalate(self, risk_score: float) -> bool:
        """Check if escalation is economically viable given current mode."""
        try:
            mode = self.operating_mode
        except TreasuryEmptyError:
            mode = AgentMode.EMERGENCY
        return should_escalate(risk_score, mode)


treasury = TreasuryManager()
