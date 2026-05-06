"""
Sigui v2.0 — Hogonat Governance Client (Dual-Mode)

Mock mode (default):
  In-memory state. Safe for demo / no blockchain required.
  Active when HOGONAT_CONTRACT_ADDRESS is empty.

On-chain mode:
  Reads state from + writes state to the deployed Hogonat.vy contract
  on Arc L1 testnet via web3.py.
  Activated automatically when HOGONAT_CONTRACT_ADDRESS is set in .env.

Architecture:
  HogonatClient                     ← public API (used by gateway.py)
    ├─ _mock_*()                    ← in-memory operations
    └─ HogonatOnChainAdapter        ← web3 operations (lazy-init)
          ├─ stake()                → ERC20.approve + Hogonat.stake()
          ├─ vote_weights()         → Hogonat.vote_weights()
          ├─ vote_thresholds()      → Hogonat.vote_thresholds()
          └─ sync_state()           ← read-only: sync local state from chain
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from loguru import logger

from config import settings
from modules.memory import MemoClaw


# ─────────────────────────────────────────────────────────────────────────────
# On-Chain Adapter (web3.py)
# ─────────────────────────────────────────────────────────────────────────────

_ABI_PATH = Path(__file__).parent.parent / "contracts" / "Hogonat.abi.json"
_ERC20_APPROVE_ABI = [
    {
        "name": "approve",
        "type": "function",
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
    }
]

try:
    from eth_account import Account
    from web3 import Web3

    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning("[HOGONAT] web3.py not available — on-chain mode disabled")


class HogonatOnChainAdapter:
    """
    Thin adapter between HogonatClient and the deployed Hogonat.vy Vyper contract.
    All write operations are signed transactions submitted via Arc RPC.
    State reads are gas-free view calls.
    """

    def __init__(self):
        self._w3: Optional[object] = None
        self._contract: Optional[object] = None
        self._usdc_contract: Optional[object] = None
        self._signer_pk = settings.arc_signer_private_key
        self._signer_addr = settings.arc_signer_address
        self._contract_address = settings.hogonat_contract_address
        self._usdc_address = settings.hogonat_usdc_token_address
        self._usdc_decimals = settings.hogonat_usdc_decimals
        self._chain_id = settings.arc_chain_id
        self._initialized = False

    def _init_web3(self) -> bool:
        """Lazy-initialize web3 connection. Returns True on success."""
        if self._initialized:
            return self._contract is not None
        self._initialized = True

        if not WEB3_AVAILABLE:
            logger.error("[HOGONAT] web3.py not installed — cannot use on-chain mode")
            return False
        if not self._signer_pk:
            logger.error("[HOGONAT] ARC_SIGNER_PRIVATE_KEY not set — cannot sign transactions")
            return False
        if not self._contract_address:
            logger.error("[HOGONAT] HOGONAT_CONTRACT_ADDRESS not set")
            return False

        try:
            self._w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url))
            if not self._w3.is_connected():
                logger.error(f"[HOGONAT] Cannot connect to Arc RPC: {settings.arc_rpc_url}")
                return False

            abi = json.loads(_ABI_PATH.read_text())
            self._contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(self._contract_address),
                abi=abi,
            )
            if self._usdc_address:
                self._usdc_contract = self._w3.eth.contract(
                    address=Web3.to_checksum_address(self._usdc_address),
                    abi=_ERC20_APPROVE_ABI,
                )

            if not self._signer_addr:
                self._signer_addr = Account.from_key(self._signer_pk).address

            logger.success(
                f"[HOGONAT] ✅ On-chain adapter ready — "
                f"contract={self._contract_address[:10]}… "
                f"signer={self._signer_addr[:10]}…"
            )
            return True
        except Exception as exc:
            logger.error(f"[HOGONAT] Init failed: {exc}")
            return False

    def _amount_to_units(self, amount_usdc: float) -> int:
        """Convert USDC float → integer token units using configured decimals."""
        return int(amount_usdc * 10 ** self._usdc_decimals)

    async def _send_tx(self, fn, label: str) -> dict:
        """Sign and broadcast a contract function call. Returns tx receipt."""
        if not self._w3 or not self._signer_pk:
            return {"ok": False, "error": "web3 not initialized"}

        loop = asyncio.get_running_loop()
        try:
            nonce = await loop.run_in_executor(
                None,
                lambda: self._w3.eth.get_transaction_count(self._signer_addr, "pending"),
            )
            gas_price = await loop.run_in_executor(None, lambda: self._w3.eth.gas_price)
            gas_price_bumped = int(gas_price * 1.15)

            tx = fn.build_transaction(
                {
                    "chainId": self._chain_id,
                    "from": self._signer_addr,
                    "nonce": nonce,
                    "gasPrice": gas_price_bumped,
                }
            )
            gas_estimate = await loop.run_in_executor(
                None, lambda: self._w3.eth.estimate_gas(tx)
            )
            tx["gas"] = int(gas_estimate * 1.3)

            signed = Account.sign_transaction(tx, self._signer_pk)
            raw_hash = await loop.run_in_executor(
                None,
                lambda: self._w3.eth.send_raw_transaction(signed.raw_transaction),
            )
            tx_hash = self._w3.to_hex(raw_hash)
            logger.success(f"[HOGONAT] ✅ {label} tx={tx_hash[:14]}…")
            return {"ok": True, "tx_hash": tx_hash}
        except Exception as exc:
            logger.error(f"[HOGONAT] {label} failed: {exc}")
            return {"ok": False, "error": str(exc)}

    async def stake(self, amount_usdc: float) -> dict:
        """Approve USDC spend then call Hogonat.stake(amount)."""
        if not self._init_web3():
            return {"ok": False, "error": "on-chain adapter not initialized"}

        units = self._amount_to_units(amount_usdc)

        # Step 1: ERC-20 approve (if USDC contract is configured)
        if self._usdc_contract:
            approve_fn = self._usdc_contract.functions.approve(
                Web3.to_checksum_address(self._contract_address), units
            )
            approve_result = await self._send_tx(approve_fn, "USDC.approve")
            if not approve_result.get("ok"):
                return approve_result

        # Step 2: Hogonat.stake(amount)
        stake_fn = self._contract.functions.stake(units)
        return await self._send_tx(stake_fn, f"Hogonat.stake({amount_usdc} USDC)")

    async def vote_weights(self, new_weights_bp: list[int]) -> dict:
        """Call Hogonat.vote_weights([w0_bp, w1_bp, w2_bp]).
        weights in basis points: [4000, 3000, 3000] = [0.40, 0.30, 0.30]
        """
        if not self._init_web3():
            return {"ok": False, "error": "on-chain adapter not initialized"}
        fn = self._contract.functions.vote_weights(new_weights_bp)
        return await self._send_tx(fn, f"Hogonat.vote_weights({new_weights_bp})")

    async def vote_thresholds(self, allow_milli: int, block_milli: int) -> dict:
        """Call Hogonat.vote_thresholds(allow_milli, block_milli).
        Values in milli-units: 300 = 0.30, 700 = 0.70
        """
        if not self._init_web3():
            return {"ok": False, "error": "on-chain adapter not initialized"}
        fn = self._contract.functions.vote_thresholds(allow_milli, block_milli)
        return await self._send_tx(
            fn, f"Hogonat.vote_thresholds(allow={allow_milli}, block={block_milli})"
        )

    async def sync_state(self) -> dict:
        """Read current contract state (gas-free view calls). Returns raw onchain state."""
        if not self._init_web3():
            return {}

        loop = asyncio.get_running_loop()
        try:
            total_staked_raw = await loop.run_in_executor(
                None, self._contract.functions.total_staked().call
            )
            fee_pool_raw = await loop.run_in_executor(
                None, self._contract.functions.fee_pool().call
            )
            risk_weights_raw = await loop.run_in_executor(
                None, self._contract.functions.risk_weights().call
            )
            allow_milli = await loop.run_in_executor(
                None, self._contract.functions.allow_threshold_milli().call
            )
            block_milli = await loop.run_in_executor(
                None, self._contract.functions.block_threshold_milli().call
            )
            divisor = 10 ** self._usdc_decimals
            total_bp = sum(risk_weights_raw) or 10_000
            return {
                "total_staked_usdc": total_staked_raw / divisor,
                "fee_pool_usdc": fee_pool_raw / divisor,
                "risk_weights": [w / total_bp for w in risk_weights_raw],
                "allow_threshold": allow_milli / 1_000,
                "block_threshold": block_milli / 1_000,
            }
        except Exception as exc:
            logger.warning(f"[HOGONAT] sync_state failed: {exc}")
            return {}


# ─────────────────────────────────────────────────────────────────────────────
# State Dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class HogonatState:
    total_staked_usdc: float = 0.0
    stakers_count: int = 0
    fee_pool_usdc: float = 0.0
    risk_weights: list[float] = field(default_factory=lambda: [0.4, 0.3, 0.3])
    allow_threshold: float = 0.30
    block_threshold: float = 0.70
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─────────────────────────────────────────────────────────────────────────────
# Main Client (dual-mode)
# ─────────────────────────────────────────────────────────────────────────────

class HogonatClient:
    """
    Public governance client used by gateway.py and other modules.

    Automatically selects mock or on-chain mode based on config:
      - HOGONAT_CONTRACT_ADDRESS empty  → mock mode (in-memory, default)
      - HOGONAT_CONTRACT_ADDRESS set    → on-chain mode (Arc L1 testnet)
    """

    def __init__(self):
        self.enabled = settings.hogonat_enabled
        # on-chain mode is auto-activated by the presence of a contract address
        self.mock_mode = not settings.hogonat_is_onchain

        self._lock = asyncio.Lock()
        weights = [
            float(x.strip()) for x in settings.hogonat_initial_weights_csv.split(",")
        ]
        if len(weights) != 3:
            weights = [0.4, 0.3, 0.3]

        self._state = HogonatState(
            risk_weights=weights,
            allow_threshold=settings.hogonat_allow_threshold,
            block_threshold=settings.hogonat_block_threshold,
        )
        self._stakers: dict[str, float] = {}
        self._blacklist: set[str] = set()
        self._onchain = HogonatOnChainAdapter() if not self.mock_mode else None

        mode_label = "MOCK" if self.mock_mode else f"ON-CHAIN ({settings.hogonat_contract_address[:12]}…)"
        logger.info(f"[HOGONAT] Initialized — mode={mode_label}")

    @property
    def memory(self) -> MemoClaw:
        from modules.memory import memory
        return memory

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_state(self) -> dict:
        """Return current governance state (syncs from chain if on-chain mode)."""
        if not self.mock_mode and self._onchain:
            await self._sync_from_chain()
        async with self._lock:
            self._state.updated_at = datetime.now(timezone.utc).isoformat()
            return {
                "enabled": self.enabled,
                "mock_mode": self.mock_mode,
                "total_staked_usdc": round(self._state.total_staked_usdc, 6),
                "stakers_count": self._state.stakers_count,
                "fee_pool_usdc": round(self._state.fee_pool_usdc, 6),
                "risk_weights": [round(w, 4) for w in self._state.risk_weights],
                "allow_threshold": round(self._state.allow_threshold, 4),
                "block_threshold": round(self._state.block_threshold, 4),
                "updated_at": self._state.updated_at,
                "onchain_contract": settings.hogonat_contract_address or None,
            }

    async def get_current_weights(self) -> list[float]:
        async with self._lock:
            return list(self._state.risk_weights)

    async def get_thresholds(self) -> tuple[float, float]:
        async with self._lock:
            return self._state.allow_threshold, self._state.block_threshold

    async def stake(self, staker_id: str, amount_usdc: float) -> dict:
        if amount_usdc < settings.hogonat_min_stake_usdc:
            return {
                "ok": False,
                "error": f"minimum stake is {settings.hogonat_min_stake_usdc} USDC",
            }

        if not self.mock_mode and self._onchain:
            # On-chain: submit real transaction
            result = await self._onchain.stake(amount_usdc)
            if not result.get("ok"):
                logger.warning(f"[HOGONAT] On-chain stake failed: {result.get('error')} — updating mock state anyway")
        else:
            result = {"ok": True}

        # Always update local state (optimistic update for on-chain, primary for mock)
        async with self._lock:
            self._stakers[staker_id] = self._stakers.get(staker_id, 0.0) + amount_usdc
            self._state.total_staked_usdc += amount_usdc
            self._state.stakers_count = len(self._stakers)
            self._state.updated_at = datetime.now(timezone.utc).isoformat()

        await self.memory.log_hogonat_action("STAKE", staker_id, amount_usdc, "Staked successfully")
        return {
            "ok": result.get("ok", True),
            "staker_id": staker_id,
            "amount_staked_usdc": round(amount_usdc, 6),
            "total_staked_usdc": round(self._state.total_staked_usdc, 6),
            "tx_hash": result.get("tx_hash"),
            "mode": "on-chain" if not self.mock_mode else "mock",
        }

    async def vote(
        self,
        staker_id: str,
        risk_weights: list[float],
        allow_threshold: float,
        block_threshold: float,
    ) -> dict:
        if len(risk_weights) != 3:
            return {"ok": False, "error": "risk_weights must have 3 values"}
        total = sum(risk_weights)
        if total <= 0:
            return {"ok": False, "error": "invalid risk_weights sum"}
        if allow_threshold >= block_threshold:
            return {"ok": False, "error": "allow_threshold must be < block_threshold"}

        async with self._lock:
            voting_power = self._stakers.get(staker_id, 0.0)
            if voting_power <= 0 and self.mock_mode:
                return {"ok": False, "error": "not a staker"}

            normalized = [w / total for w in risk_weights]
            alpha = min(0.5, max(0.05, voting_power / max(1.0, self._state.total_staked_usdc)))
            self._state.risk_weights = [
                round((1 - alpha) * old + alpha * new, 6)
                for old, new in zip(self._state.risk_weights, normalized)
            ]
            self._state.allow_threshold = round(
                (1 - alpha) * self._state.allow_threshold + alpha * allow_threshold, 6
            )
            self._state.block_threshold = round(
                (1 - alpha) * self._state.block_threshold + alpha * block_threshold, 6
            )
            self._state.updated_at = datetime.now(timezone.utc).isoformat()

        onchain_results: dict = {}
        if not self.mock_mode and self._onchain:
            # Convert float weights to basis points (total = 10 000)
            w_bp = [int(w * 10_000) for w in normalized]
            # Adjust last weight to ensure sum = 10000
            w_bp[2] = 10_000 - w_bp[0] - w_bp[1]

            allow_milli = int(allow_threshold * 1_000)
            block_milli = int(block_threshold * 1_000)

            w_result = await self._onchain.vote_weights(w_bp)
            t_result = await self._onchain.vote_thresholds(allow_milli, block_milli)
            onchain_results = {
                "vote_weights_tx": w_result.get("tx_hash"),
                "vote_thresholds_tx": t_result.get("tx_hash"),
            }
            if not w_result.get("ok") or not t_result.get("ok"):
                logger.warning("[HOGONAT] On-chain vote partially failed — local state still updated")

        details = json.dumps(
            {
                "weights": self._state.risk_weights,
                "allow": self._state.allow_threshold,
                "block": self._state.block_threshold,
            }
        )
        await self.memory.log_hogonat_action("VOTE", staker_id, 0.0, f"Updated policy: {details}")

        result = {"ok": True, "voting_power": round(voting_power, 6), "state": await self.get_state()}
        result.update(onchain_results)
        return result

    async def add_fee(self, amount_usdc: float):
        """Record fee revenue into the DAO pool (local tracking only)."""
        async with self._lock:
            self._state.fee_pool_usdc += max(0.0, amount_usdc)
            self._state.updated_at = datetime.now(timezone.utc).isoformat()

    async def is_blacklisted(self, destination: str) -> bool:
        return destination.lower() in self._blacklist

    async def blacklist_destination(self, destination: str):
        self._blacklist.add(destination.lower())

    # ── Private ───────────────────────────────────────────────────────────────

    async def _sync_from_chain(self):
        """Sync local state from on-chain contract (read-only)."""
        if not self._onchain:
            return
        chain_state = await self._onchain.sync_state()
        if not chain_state:
            return
        async with self._lock:
            if "total_staked_usdc" in chain_state:
                self._state.total_staked_usdc = chain_state["total_staked_usdc"]
            if "fee_pool_usdc" in chain_state:
                self._state.fee_pool_usdc = chain_state["fee_pool_usdc"]
            if "risk_weights" in chain_state:
                self._state.risk_weights = chain_state["risk_weights"]
            if "allow_threshold" in chain_state:
                self._state.allow_threshold = chain_state["allow_threshold"]
            if "block_threshold" in chain_state:
                self._state.block_threshold = chain_state["block_threshold"]
            self._state.updated_at = datetime.now(timezone.utc).isoformat()
        logger.debug(f"[HOGONAT] State synced from chain — staked=${self._state.total_staked_usdc:.4f}")


hogonat_client = HogonatClient()
