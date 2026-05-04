"""
ArcWarden v3.0 — ThreatRegistry Contract Client
Calls the deployed ThreatRegistry Vyper contract on Arc L1.

Every BLOCK decision fires record_attack() as a background asyncio task —
it NEVER blocks the critical decision pipeline (fire-and-forget pattern).

Graceful degradation: if the contract is not deployed, not reachable,
or has insufficient gas, the client logs a debug message and returns None.
The decision pipeline is never affected.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Optional

from loguru import logger

from clients.nonce_manager import nonce_lock
from config import settings

# ABI is generated at deployment time by scripts/deploy_contract.py
ABI_PATH = Path(__file__).parent.parent / "contracts" / "ThreatRegistry.abi.json"

# Security layer constants (match the Vyper contract)
LAYER_BEHAVIOR = 1  # amount anomaly, frequency, trust score
LAYER_SPLITTING = 2  # Flow Monitor anti-splitting rules
LAYER_SERVICE = 3  # Service Registry reputation
LAYER_CONTRACT = 4  # Contract Inspector bytecode analysis


class ThreatRegistryClient:
    """
    Async client for the ThreatRegistry smart contract.

    Usage:
        # At startup (main.py lifespan):
        await threat_registry.initialize()

        # After a BLOCK decision (gateway.py) — fire-and-forget:
        asyncio.create_task(threat_registry.record_attack(...))

        # For dashboard stats:
        stats = await threat_registry.get_stats()
    """

    def __init__(self) -> None:
        self._contract = None
        self._w3 = None
        self._abi: Optional[list] = None
        self._enabled = False
        self._session_records = 0  # attacks recorded this session

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def initialize(self) -> bool:
        """
        Connect to the deployed ThreatRegistry contract.
        Returns True if connected, False if contract not configured or unreachable.
        This method never raises — it always degrades gracefully.
        """
        address = settings.threat_registry_address
        if not address or address.lower() in ("", "0x0", "none", "null"):
            logger.info(
                "[THREAT_REGISTRY] THREAT_REGISTRY_ADDRESS not configured — "
                "onchain attack recording disabled. "
                "Run: python scripts/deploy_contract.py"
            )
            return False

        try:
            from web3 import Web3

            # Load ABI (generated at deployment time)
            if not ABI_PATH.exists():
                logger.warning(
                    f"[THREAT_REGISTRY] ABI not found at {ABI_PATH}. "
                    "Deploy the contract first: python scripts/deploy_contract.py"
                )
                return False

            self._abi = json.loads(ABI_PATH.read_text(encoding="utf-8-sig"))

            # Connect to Arc RPC
            self._w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url))
            if not self._w3.is_connected():
                logger.warning(
                    "[THREAT_REGISTRY] Arc RPC unavailable — recording disabled"
                )
                return False

            # Instantiate contract
            checksum_addr = Web3.to_checksum_address(address)
            self._contract = self._w3.eth.contract(
                address=checksum_addr,
                abi=self._abi,
            )

            # Sanity check: call getStats() (read-only, no gas)
            loop = asyncio.get_running_loop()
            stats = await loop.run_in_executor(
                None, lambda: self._contract.functions.getStats().call()
            )
            total = stats[0]
            usdc6 = stats[1]

            # Verify we are the owner (can we write?)
            owner = await loop.run_in_executor(
                None, lambda: self._contract.functions.owner().call()
            )
            signer = (
                settings.arc_signer_address.lower()
                if settings.arc_signer_address
                else ""
            )
            can_write = (owner.lower() == signer) if signer else False

            self._enabled = True

            logger.success(
                f"[THREAT_REGISTRY] ✅ Connected to ThreatRegistry"
                f" | addr={address[:16]}…"
                f" | existing_attacks={total}"
                f" | usdc_protected=${usdc6 / 1_000_000:.4f}"
                f" | can_write={can_write}"
            )
            if not can_write:
                logger.warning(
                    "[THREAT_REGISTRY] ⚠ Signer is NOT the contract owner — "
                    "read-only mode. Attack recording will be skipped."
                )

            return True

        except Exception as exc:
            logger.warning(
                f"[THREAT_REGISTRY] Initialization failed ({exc}) — "
                "onchain recording disabled"
            )
            return False

    @property
    def is_enabled(self) -> bool:
        """True if the client is connected and ready to record."""
        return self._enabled and self._contract is not None

    # ── Write ──────────────────────────────────────────────────────────────────

    async def record_attack(
        self,
        agent_id: str,
        agent_wallet_address: str,
        action_type: str,
        destination: str,
        amount_usdc: float,
        risk_score: float,
        layer: int,
    ) -> Optional[str]:
        """
        Record a blocked attack in the onchain ThreatRegistry.
        FIRE-AND-FORGET: call with asyncio.create_task() from the gateway.
        Never raises — always returns None on failure.

        Args:
            agent_id:             Human-readable agent identifier (for logs)
            agent_wallet_address: Agent's Arc wallet address (cryptographic identity)
            action_type:          Action type that was blocked (transfer, etc.)
            destination:          Destination address
            amount_usdc:          Amount attempted in USDC
            risk_score:           Final risk score [0.0, 1.0]
            layer:                Security layer that triggered (1–4)

        Returns:
            Transaction hash (str) if recorded, None otherwise.
        """
        if not self.is_enabled:
            return None
        if not settings.arc_signer_private_key:
            logger.debug("[THREAT_REGISTRY] No signing key configured — skipping")
            return None
        if settings.demo_mode:
            # In demo mode, simulate recording without actual onchain call
            self._session_records += 1
            logger.debug(
                f"[THREAT_REGISTRY] (demo) simulated record: "
                f"agent={agent_id} layer={layer} R={risk_score:.3f}"
            )
            return f"0xSIM_THREAT_{self._session_records:04d}"

        # Build the pattern hash: keccak256(action_type + destination[:20] + amount_bucket)
        # amount_bucket rounds to nearest 0.01 USDC to group similar amounts
        amount_bucket = round(amount_usdc, 2)
        pattern_data = f"{action_type}:{destination[:20].lower()}:{amount_bucket:.2f}"
        pattern_hash = bytes.fromhex(hashlib.sha256(pattern_data.encode()).hexdigest())

        # Normalize amounts
        amount_usdc6 = int(amount_usdc * 1_000_000)  # 6-decimal USDC
        risk_milli = min(1000, max(0, int(risk_score * 1000)))  # [0, 1000]
        layer_clamped = max(1, min(4, int(layer)))

        # Normalize agent wallet address
        try:
            from web3 import Web3

            agent_addr = Web3.to_checksum_address(agent_wallet_address)
        except Exception:
            # Derive deterministic address from agent_id if wallet address is invalid
            derived = hashlib.sha256(agent_id.encode()).digest()[:20]
            agent_addr = "0x" + derived.hex()
            from web3 import Web3

            agent_addr = Web3.to_checksum_address(agent_addr)

        try:
            async with nonce_lock:
                loop = asyncio.get_running_loop()

                nonce = await loop.run_in_executor(
                    None,
                    lambda: self._w3.eth.get_transaction_count(
                        settings.arc_signer_address, "pending"
                    ),
                )
                gas_price = await loop.run_in_executor(
                    None, lambda: self._w3.eth.gas_price
                )
                # Bump gas price by 15% to ensure testnet priority
                gas_price_bumped = int(gas_price * 1.15)

                # Build the contract call transaction
                tx = self._contract.functions.recordAttack(
                    agent_addr,
                    pattern_hash,
                    amount_usdc6,
                    risk_milli,
                    layer_clamped,
                ).build_transaction(
                    {
                        "chainId": settings.arc_chain_id,
                        "from": settings.arc_signer_address,
                        "nonce": nonce,
                        "gas": 450_000,  # Increased from 400k for safety
                        "gasPrice": gas_price_bumped,
                    }
                )

                from eth_account import Account

                signed = Account.sign_transaction(tx, settings.arc_signer_private_key)
                raw_hash = await loop.run_in_executor(
                    None,
                    lambda: self._w3.eth.send_raw_transaction(signed.raw_transaction),
                )
                tx_hash = self._w3.to_hex(raw_hash)

            # ── Wait for receipt outside the nonce_lock ──
            # This allows other transactions to proceed while we wait for confirmation.
            receipt = await loop.run_in_executor(
                None,
                lambda: self._w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            )

            if receipt.status == 1:
                logger.success(
                    f"[THREAT_REGISTRY] ⛓ Attack RECORDED onchain | "
                    f"agent={agent_id} layer={layer_clamped} R={risk_score:.3f} "
                    f"${amount_usdc:.4f} USDC | "
                    f"{settings.arc_explorer_url}/tx/{tx_hash}"
                )
            else:
                logger.warning(
                    f"[THREAT_REGISTRY] ⛓ Attack transaction REVERTED | "
                    f"agent={agent_id} tx={tx_hash}"
                )

            self._session_records += 1
            return tx_hash

        except Exception as exc:
            # NEVER block the decision pipeline — log and return None
            logger.error(
                f"[THREAT_REGISTRY] ❌ record_attack failed for agent {agent_id}: {exc}"
            )
            return None

    # ── Read ───────────────────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        """
        Return contract statistics for the dashboard and /demo/report.
        Returns a safe dict even if the contract is unreachable.
        """
        address = settings.threat_registry_address or ""
        base = {
            "enabled": self.is_enabled,
            "contract_address": address or None,
            "explorer": (
                f"{settings.arc_explorer_url}/address/{address}" if address else None
            ),
            "session_records": self._session_records,
        }

        if not self.is_enabled:
            return {**base, "guaranty_fund6": 0}

        try:
            loop = asyncio.get_running_loop()
            stats = await loop.run_in_executor(
                None, lambda: self._contract.functions.getStats().call()
            )
            # stats = (total_attacks, total_usdc_protected6, guaranty_fund6)
            total = stats[0]
            usdc6 = stats[1]
            fund6 = stats[2] if len(stats) > 2 else 0

            return {
                **base,
                "total_attacks_onchain": total,
                "total_usdc_protected_usdc": round(usdc6 / 1_000_000, 6),
                "guaranty_fund6": fund6,
                "note": (
                    "Immutable onchain threat intelligence — "
                    "every BLOCK decision permanently recorded by ArcWarden."
                ),
            }
        except Exception as exc:
            logger.error(f"[THREAT_REGISTRY] Failed to fetch stats: {exc}")
            return {**base, "error": str(exc), "guaranty_fund6": 0}

    async def sync_global_threats(self) -> list[dict]:
        """
        Scan the last 1000 blocks for AttackBlocked events from other agents.
        Returns a list of patterns to be learned by the local Oracle.
        """
        if not self.is_enabled:
            return []

        try:
            loop = asyncio.get_running_loop()
            current_block = await loop.run_in_executor(
                None, lambda: self._w3.eth.block_number
            )
            from_block = max(0, current_block - 1000)

            # Get events from the contract
            event_filter = self._contract.events.AttackBlocked.create_filter(
                fromBlock=from_block, toBlock="latest"
            )
            events = await loop.run_in_executor(None, event_filter.get_all_entries)

            threats = []
            for event in events:
                args = event["args"]
                threats.append(
                    {
                        "pattern_hash": self._w3.to_hex(args["pattern"]),
                        "agent": args["agent"],
                        "risk_score": args["risk_milli"] / 1000.0,
                        "layer": args["layer"],
                        "tx_hash": self._w3.to_hex(event["transactionHash"]),
                    }
                )

            if threats:
                logger.info(
                    f"[THREAT_REGISTRY] 🌐 Collective Intelligence: "
                    f"Synced {len(threats)} threats from the blockchain"
                )
            return threats

        except Exception as exc:
            logger.warning(f"[THREAT_REGISTRY] Sync failed: {exc}")
            return []

    async def is_known_attacker_onchain(self, wallet_address: str) -> bool:
        """
        Check if an address is a known attacker per the onchain ThreatRegistry.
        Used by the Contract Inspector and Risk Engine.
        """
        if not self.is_enabled:
            return False
        try:
            from web3 import Web3

            addr = Web3.to_checksum_address(wallet_address)
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._contract.functions.isKnownAttacker(addr).call(),
            )
        except Exception:
            return False

    async def is_pattern_known_onchain(
        self, action_type: str, destination: str, amount_usdc: float
    ) -> bool:
        """
        Check if an attack pattern has been seen before in the onchain registry.
        Returns True if the pattern was previously recorded (known threat).
        """
        if not self.is_enabled:
            return False
        try:
            amount_bucket = round(amount_usdc, 2)
            pattern_data = (
                f"{action_type}:{destination[:20].lower()}:{amount_bucket:.2f}"
            )
            pattern_hash = bytes.fromhex(
                hashlib.sha256(pattern_data.encode()).hexdigest()
            )
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None,
                lambda: self._contract.functions.isPatternKnown(pattern_hash).call(),
            )
        except Exception:
            return False


# ── Singleton ──────────────────────────────────────────────────────────────────
threat_registry = ThreatRegistryClient()
