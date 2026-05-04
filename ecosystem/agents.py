import abc
import asyncio
import json
import random
import time
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from clients.integrations import circle_client
from config import settings
from ecosystem.address_pool import AddressPool


@dataclass
class AgentRuntimeState:
    status: str = "initializing"
    observe_only: bool = False
    transactions: int = 0
    last_decision: str = "N/A"
    last_error: str = ""
    last_cycle_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    balance_usdc: float = 0.0


class BaseAutonomousAgent(abc.ABC):
    def __init__(
        self,
        agent_id: str,
        wallet_id: str,
        wallet_address: str,
        min_cycle_s: float,
        max_cycle_s: float,
    ):
        self.agent_id = agent_id
        self.wallet_id = wallet_id
        self.wallet_address = wallet_address
        self.min_cycle_s = min_cycle_s
        self.max_cycle_s = max_cycle_s
        self.base_url = settings.ecosystem_base_url.rstrip("/")
        self.state = AgentRuntimeState()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None
        self._client: httpx.AsyncClient | None = None
        self._log = logger.bind(agent=self.agent_id)

    async def start(self):
        if self._task and not self._task.done():
            return
        self._client = httpx.AsyncClient(timeout=15.0)
        self._task = asyncio.create_task(self._run_forever(), name=f"{self.agent_id}_loop")

    async def stop(self):
        self._stop_event.set()
        if self._task:
            await self._task
        if self._client:
            await self._client.aclose()

    async def _run_forever(self):
        backoff_s = 1.0
        self.state.status = "active"
        while not self._stop_event.is_set():
            try:
                await self.refresh_balance()
                await asyncio.wait_for(self.run_cycle(), timeout=25.0)
                backoff_s = 1.0
                self.state.last_error = ""
            except asyncio.TimeoutError:
                self.state.last_error = "cycle timeout"
                self._log.warning("cycle timeout")
                await asyncio.sleep(backoff_s)
                backoff_s = min(backoff_s * 1.5, 15.0)  # Softer backoff
            except Exception as exc:
                err_str = str(exc)
                # Don't log empty JSON errors repeatedly at warning level
                if "Expecting value" in err_str:
                    self.state.last_error = "server_error_skip"
                    await asyncio.sleep(2.0)  # Short fixed sleep, not exponential
                    backoff_s = 1.0
                else:
                    self.state.last_error = err_str
                    self._log.warning(f"cycle error: {exc}")
                    await asyncio.sleep(backoff_s)
                    backoff_s = min(backoff_s * 1.5, 15.0)
            finally:
                self.state.last_cycle_at = datetime.now(timezone.utc).isoformat()
            if self._stop_event.is_set():
                break
            await asyncio.sleep(random.uniform(self.min_cycle_s, self.max_cycle_s))
        self.state.status = "stopped"

    async def refresh_balance(self):
        try:
            balance = await circle_client.get_wallet_balance(self.wallet_id)
        except Exception:
            balance = 0.0
        self.state.balance_usdc = balance
        self.state.observe_only = balance <= 0.0 and self.wallet_id != ""
        if self.state.observe_only:
            self.state.status = "observe-only"
        elif self.state.status != "stopped":
            self.state.status = "active"

    def _fire_and_forget_transfer(self, amount_usdc: float) -> str:
        """Generate a payment intent UUID instantly and dispatch Circle transfer in background."""
        intent_id = str(_uuid.uuid4())
        self.state.balance_usdc = max(0.0, self.state.balance_usdc - amount_usdc)
        self.state.transactions += 1

        async def _do_transfer():
            try:
                await circle_client.transfer_usdc(
                    destination_address=settings.arcwarden_wallet_address,
                    amount_usdc=amount_usdc,
                    description=f"{self.agent_id}_x402_payment_{intent_id[:8]}",
                    source_wallet_id=self.wallet_id,
                    user_id=self.agent_id,
                )
            except Exception as e:
                self._log.warning(f"background transfer failed: {e}")

        asyncio.create_task(_do_transfer())
        return intent_id

    async def pay_arcwarden(self, amount_usdc: float) -> str | None:
        if self.state.observe_only:
            return None
        if self.state.balance_usdc < amount_usdc:
            self.state.observe_only = True
            self.state.status = "observe-only"
            self._log.warning("insufficient balance, switching to observe-only")
            return None
        # Fire-and-forget: returns instantly, transfer runs in background
        return self._fire_and_forget_transfer(amount_usdc)

    async def call_evaluate(self, action: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("agent client not initialized")
        tx_hash = await self.pay_arcwarden(settings.arcwarden_eval_price_usdc)
        if not tx_hash:
            return {"decision": "SKIP", "reason": "observe_only_or_no_funds"}
        headers = {"Content-Type": "application/json", "X-Payment": tx_hash}
        resp = await self._client.post(f"{self.base_url}/evaluate", json=action, headers=headers)
        # Crash-safe JSON parsing — server 500s return empty body
        try:
            data = resp.json()
        except Exception:
            return {"decision": "SKIP", "reason": f"server_error_{resp.status_code}"}
        self.state.last_decision = data.get("decision", "UNKNOWN")
        return data

    async def call_escalate(self, action: dict[str, Any]) -> dict[str, Any]:
        if self._client is None:
            raise RuntimeError("agent client not initialized")
        tx_hash = await self.pay_arcwarden(settings.arcwarden_escalate_price_usdc)
        if not tx_hash:
            return {"escalation_result": "SKIP", "analysis": "observe_only_or_no_funds"}
        headers = {"Content-Type": "application/json", "X-Payment": tx_hash}
        resp = await self._client.post(f"{self.base_url}/escalate", json=action, headers=headers)
        try:
            return resp.json()
        except Exception:
            return {"escalation_result": "SKIP", "reason": "server_error"}

    def status(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "status": self.state.status,
            "observe_only": self.state.observe_only,
            "balance_usdc": round(self.state.balance_usdc, 6),
            "transactions": self.state.transactions,
            "last_decision": self.state.last_decision,
            "last_error": self.state.last_error,
            "last_cycle_at": self.state.last_cycle_at,
            "wallet_id": self.wallet_id,
            "wallet_address": self.wallet_address,
        }

    @abc.abstractmethod
    async def run_cycle(self):
        raise NotImplementedError


class PayerAgent(BaseAutonomousAgent):
    """Legitimate payment agent — varied transaction types and amounts."""

    # Action types for realism
    _ACTION_TYPES = ["transfer", "api_call", "data_access", "subscription", "micro_payment"]

    async def run_cycle(self):
        val = random.random()
        if val < 0.55:
            # Normal small payment to known safe address
            amount = round(random.uniform(0.005, 0.08), 4)
            destination = AddressPool.get_safe_destination()
            action_type = random.choice(["transfer", "api_call", "micro_payment"])
        elif val < 0.80:
            # Medium payment — slightly above average
            amount = round(random.uniform(0.08, 0.25), 4)
            destination = AddressPool.get_safe_destination()
            action_type = random.choice(["transfer", "subscription", "data_access"])
        elif val < 0.92:
            # New destination — legit but unknown
            amount = round(random.uniform(0.01, 0.06), 4)
            destination = AddressPool.get_new_destination()
            action_type = random.choice(["transfer", "api_call"])
        else:
            # Rare large legit payment
            amount = round(random.uniform(0.3, 0.8), 4)
            destination = AddressPool.get_safe_destination()
            action_type = "transfer"

        action = {
            "agent_id": self.agent_id,
            "action_type": action_type,
            "amount_usdc": amount,
            "destination": destination,
            "context": {
                "frequency_last_minute": random.randint(1, 4),
                "user_type": "legitimate",
            },
        }
        result = await self.call_evaluate(action)
        decision = result.get("decision", "UNKNOWN")
        if decision == "ALLOW":
            pass  # Normal flow
        elif decision == "BLOCK":
            await asyncio.sleep(random.uniform(3, 8))  # Back off before retry
        elif decision == "ESCALATE":
            await self.call_escalate(action)


class AttackerAgent(BaseAutonomousAgent):
    """Adversarial agent — rotates attack strategies, learns from blocks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._history_amounts: list[float] = [0.03, 0.05, 0.04]
        self._strategy_idx = 0
        self._tx_count = 0
        self._consecutive_blocks = 0
        self.decision_latencies: list[dict] = []

    def _next_attack_action(self) -> dict[str, Any]:
        # After 3 consecutive blocks, switch to a stealthier strategy
        if self._consecutive_blocks >= 3:
            strategy = "strat_b_subtle"
            self._consecutive_blocks = 0
        else:
            strategy = ["strat_a_brute", "strat_b_subtle", "strat_c_drain", "strat_d_sybil"][self._strategy_idx % 4]
        self._strategy_idx += 1
        baseline = sum(self._history_amounts) / max(1, len(self._history_amounts))

        if strategy == "strat_a_brute":
            amount = round(baseline * random.uniform(60, 300), 4)
            destination = AddressPool.get_attacker_destination()
            context_freq = random.randint(2, 6)
        elif strategy == "strat_b_subtle":
            # Subtle: slightly above average to a safe-looking destination
            amount = round(baseline * random.uniform(6, 12), 4)
            destination = AddressPool.get_safe_destination()
            context_freq = random.randint(3, 5)
        elif strategy == "strat_c_drain":
            amount = round(baseline * random.uniform(0.7, 1.3), 4)
            destination = AddressPool.get_attacker_destination()
            context_freq = random.randint(20, 35)
        else:  # strat_d_sybil — many micro transfers
            amount = round(random.uniform(0.001, 0.01), 4)
            destination = AddressPool.get_new_destination()
            context_freq = random.randint(15, 25)

        return {
            "agent_id": self.agent_id,
            "action_type": "transfer",
            "amount_usdc": amount,
            "destination": destination,
            "context": {"frequency_last_minute": context_freq, "attack_strategy": strategy},
        }

    async def run_cycle(self):
        self._tx_count += 1
        action = self._next_attack_action()
        result = await self.call_evaluate(action)
        decision = result.get("decision", "UNKNOWN")

        if decision == "SKIP":
            return

        # Track latency for dashboard learning curve
        self.decision_latencies.append({
            'tx': self._tx_count,
            'latency_ms': result.get('processing_time_ms', 0),
            'decision': decision,
        })

        if decision == "BLOCK":
            self._consecutive_blocks += 1
            logger.warning(f"[{self.agent_id}] BLOCKed ({self._consecutive_blocks} consecutive); adapting strategy")
            # Adaptive: wait then switch strategy, DON'T replay same pattern (removes the loop)
            await asyncio.sleep(random.uniform(2, 5))
        else:
            self._consecutive_blocks = 0
            if decision == "ESCALATE":
                await self.call_escalate(action)


class LearnerAgent(BaseAutonomousAgent):
    """Learning agent — cycles through warmup → probe → attack → reset."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tx_count = 0
        self._phase_cycle_size = 5  # Reset every 5 txs per phase
        self._latencies_before: list[float] = []
        self._latencies_after: list[float] = []

    async def run_cycle(self):
        self._tx_count += 1
        # Cycle through phases to keep variety: warmup(1-5) → probe(6-10) → attack(11-15) → repeat
        phase_pos = ((self._tx_count - 1) % 15) + 1

        if phase_pos <= 5:
            # Phase 1: Warmup — safe, normal amounts
            amount = round(random.uniform(0.01, 0.06), 4)
            destination = AddressPool.KNOWN_SAFE[self._tx_count % len(AddressPool.KNOWN_SAFE)]
            freq = random.randint(1, 3)
            phase = "warmup"
        elif phase_pos <= 10:
            # Phase 2: Gray zone — slightly elevated
            amount = round(random.uniform(0.05, 0.20), 4)
            destination = AddressPool.get_safe_destination()
            freq = random.randint(4, 7)
            phase = "probe"
        else:
            # Phase 3: Attack — large amount to unknown destination
            amount = round(random.uniform(5.0, 25.0), 4)
            destination = AddressPool.get_attacker_destination()
            freq = random.randint(8, 15)
            phase = "attack"

        action = {
            "agent_id": self.agent_id,
            "action_type": "transfer",
            "amount_usdc": amount,
            "destination": destination,
            "context": {"frequency_last_minute": freq, "learning_phase": phase},
        }

        t0 = time.perf_counter()
        result = await self.call_evaluate(action)
        latency_ms = (time.perf_counter() - t0) * 1000
        decision = result.get("decision", "UNKNOWN")

        if decision == "SKIP":
            return

        if decision == "BLOCK":
            self._latencies_after.append(latency_ms)
        else:
            self._latencies_before.append(latency_ms)

        if len(self._latencies_after) > 0 and len(self._latencies_before) > 0:
            before = sum(self._latencies_before) / len(self._latencies_before)
            after = sum(self._latencies_after) / len(self._latencies_after)
            logger.info(f"[{self.agent_id}] detection latency before={before:.1f}ms after={after:.1f}ms phase={phase}")

        if decision == "ESCALATE":
            await self.call_escalate(action)


class GrayZoneAgent(BaseAutonomousAgent):
    """Ambiguous agent — operates in the gray zone to challenge AI decisions."""

    _CONTEXTS = [
        {"user_type": "business", "region": "EU", "account_age_days": 180},
        {"user_type": "startup", "region": "US", "account_age_days": 45},
        {"user_type": "individual", "region": "APAC", "account_age_days": 730},
        {"user_type": "exchange", "region": "LATAM", "account_age_days": 22},
    ]
    _ctx_idx = 0

    async def run_cycle(self):
        avg = 0.05
        roll = random.random()

        if roll < 0.40:
            # Slightly suspicious amount, mixed destination
            amount = round(avg * random.uniform(3, 7), 4)
            destination = AddressPool.get_safe_destination() if random.random() > 0.4 else AddressPool.get_new_destination()
            freq = random.randint(4, 8)
        elif roll < 0.70:
            # Many micro-payments (splitting probe)
            amount = round(random.uniform(0.005, 0.025), 4)
            destination = AddressPool.get_new_destination()
            freq = random.randint(10, 20)
        else:
            # Single large payment to a new address
            amount = round(avg * random.uniform(15, 40), 4)
            destination = AddressPool.get_new_destination()
            freq = random.randint(1, 3)

        ctx = self._CONTEXTS[self._ctx_idx % len(self._CONTEXTS)]
        self._ctx_idx += 1

        action = {
            "agent_id": self.agent_id,
            "action_type": random.choice(["transfer", "api_call", "data_access"]),
            "amount_usdc": amount,
            "destination": destination,
            "context": {**ctx, "frequency_last_minute": freq},
        }

        result = await self.call_evaluate(action)
        decision = result.get("decision", "UNKNOWN")
        if decision == "SKIP":
            return
        if decision == "ESCALATE":
            await self.call_escalate(action)


class MonitorAgent(BaseAutonomousAgent):
    async def run_cycle(self):
        if self._client is None:
            return
        try:
            stats_resp = await self._client.get(f"{self.base_url}/stats")
            treasury_resp = await self._client.get(f"{self.base_url}/treasury")
            card_resp = await self._client.get(f"{self.base_url}/.well-known/agent-card")
            stats = stats_resp.json()
            treasury = treasury_resp.json()
            card = card_resp.json()
        except Exception as e:
            self._log.debug(f"monitor fetch failed: {e}")
            return

        protected = float(stats.get("decisions", {}).get("usdc_saved", 0.0))
        security_cost = float(treasury.get("total_spent", 0.0))
        roi = (protected / security_cost) if security_cost > 0 else 0.0
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "treasury": treasury,
            "agent_card": card,
            "roi": roi,
        }
        metrics_path = Path(settings.ecosystem_metrics_path)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        allow = stats.get("decisions", {}).get("allow", 0)
        block = stats.get("decisions", {}).get("block", 0)
        if (block > allow * 2) and (allow + block > 10):
            logger.warning("[agent_monitor] anomaly detected: BLOCK ratio spike")


__all__ = [
    "AgentRuntimeState",
    "BaseAutonomousAgent",
    "PayerAgent",
    "AttackerAgent",
    "LearnerAgent",
    "MonitorAgent",
    "GrayZoneAgent",
]
