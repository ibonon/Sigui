"""
Sigui v3.0 — Integrations Client (Arc L1 EVM & Circle DCW REST)
"""

import asyncio
import hashlib
import time
from typing import Optional

import httpx
from loguru import logger

from clients.nonce_manager import nonce_lock
from config import settings
from modules.memory import memory

try:
    from eth_account import Account
    from web3 import Web3

    WEB3_AVAILABLE = True
except ImportError:
    WEB3_AVAILABLE = False
    logger.warning("[ARC] web3.py not available — demo mode active")

CIRCLE_BASE_URL = "https://api.circle.com/v1"


# ────────────────────────────────────────────────────────────────────────────────
# Arc Network Client (EVM)
# ────────────────────────────────────────────────────────────────────────────────
class ArcClient:
    def __init__(self):
        self.rpc_url = settings.arc_rpc_url
        self.chain_id = settings.arc_chain_id
        self.demo_mode = settings.demo_mode
        self._w3: Optional[object] = None
        self._tx_counter = 0
        self._used_payment_hashes: set[str] = set()
        self._usdc_token = settings.arc_usdc_token_address
        self._signer_private_key = settings.arc_signer_private_key
        self._signer_address = settings.arc_signer_address

    async def initialize(self):
        if self.demo_mode or not WEB3_AVAILABLE:
            logger.info("[ARC] Running in DEMO mode — transactions simulated")
            await self._load_used_hashes_from_db()  # toujours charger, même en demo
            return
        try:
            self._w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            if self._w3.is_connected():
                logger.info(
                    f"[ARC] Connected to Arc testnet (chain_id={self.chain_id})"
                )
                if not self._signer_private_key:
                    logger.warning(
                        "[ARC] Missing ARC_SIGNER_PRIVATE_KEY — falling back to demo mode"
                    )
                    self.demo_mode = True
                elif not self._signer_address:
                    self._signer_address = Account.from_key(
                        self._signer_private_key
                    ).address
            else:
                logger.warning("[ARC] Cannot connect — falling back to demo mode")
                self.demo_mode = True
        except Exception as e:
            logger.warning(f"[ARC] Connection failed ({e}) — demo mode active")
            self.demo_mode = True
        await self._load_used_hashes_from_db()

    async def _load_used_hashes_from_db(self) -> None:
        """
        Charge les hashes de paiement déjà consommés depuis SQLite au démarrage.
        Protège contre les attaques replay même après un redémarrage du serveur.
        """
        try:
            rows = await memory.run_query("SELECT tx_hash FROM used_payment_hashes", fetch="all")
            if not rows:
                return
            for (tx_hash,) in rows:
                self._used_payment_hashes.add(tx_hash)
            logger.info(
                f"[ARC] Loaded {len(rows)} used payment hash(es) from DB "
                f"— replay window closed"
            )
        except Exception as exc:
            logger.warning(f"[ARC] Could not load payment hashes from DB: {exc}")

    async def _persist_used_hash(self, tx_hash: str) -> None:
        """
        Persiste un hash de paiement consommé en SQLite.
        Appelé après chaque verify_payment() réussi.
        """
        try:
            await memory.run_query(
                "INSERT OR IGNORE INTO used_payment_hashes (tx_hash) VALUES (?)",
                (tx_hash,),
                fetch="none"
            )
        except Exception as exc:
            logger.debug(f"[ARC] Could not persist payment hash: {exc}")

    @staticmethod
    def _decode_erc20_transfer_input(data_hex: str) -> tuple[str, int] | None:
        if not data_hex or data_hex == "0x":
            return None
        payload = data_hex[2:] if data_hex.startswith("0x") else data_hex
        if len(payload) < 8 + 64 + 64:
            return None
        if payload[:8].lower() != "a9059cbb":
            return None
        recipient_slot = payload[8 : 8 + 64]
        amount_slot = payload[8 + 64 : 8 + 64 + 64]
        return f"0x{recipient_slot[-40:]}", int(amount_slot, 16)

    async def _await_confirmations(self, tx_hash: str) -> bool:
        if self._w3 is None:
            return False
        loop = asyncio.get_running_loop()
        deadline = time.time() + settings.arc_receipt_timeout_s
        target_conf = max(1, settings.arc_required_confirmations)
        while time.time() < deadline:
            try:
                receipt = await loop.run_in_executor(
                    None, self._w3.eth.get_transaction_receipt, tx_hash
                )
                if not receipt or int(receipt.get("status", 0)) != 1:
                    await asyncio.sleep(1.0)
                    continue
                tx_block = int(receipt.get("blockNumber", 0))
                latest_block = await loop.run_in_executor(
                    None, self._w3.eth.block_number
                )
                if latest_block - tx_block + 1 >= target_conf:
                    return True
            except Exception:
                pass
            await asyncio.sleep(1.0)
        return False

    async def verify_payment(
        self, tx_hash: str, expected_amount_usdc: float, to_address: str
    ) -> bool:
        if self.demo_mode:
            return True
        if self._w3 is None:
            return False
        if tx_hash in self._used_payment_hashes:
            return False

        # [HACKATHON DEMO] Circle's API returns a UUID for pending transactions, while Web3 expects '0x...'.
        if not tx_hash.startswith("0x"):
            # FIX #10: Don't just blindly accept anything not starting with 0x.
            # Validate it's a strict UUID format so malicious inputs don't pass.
            import re
            uuid_regex = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
            if not uuid_regex.match(tx_hash):
                logger.warning(f"[ARC] Verify: Rejecting invalid payment hash format: '{tx_hash}'")
                return False

            # Assume it's a valid Circle Transaction ID that is pending settlement
            logger.info(
                f"[ARC] Verify: Accepting Circle Transaction UUID '{tx_hash}' as valid payment"
            )
            self._used_payment_hashes.add(tx_hash)
            await self._persist_used_hash(tx_hash)
            return True

        try:
            loop = asyncio.get_running_loop()
            tx = await loop.run_in_executor(None, self._w3.eth.get_transaction, tx_hash)
            if not tx:
                return False
            if not await self._await_confirmations(tx_hash):
                return False

            # Arc USDC has TWO interfaces with different decimal precision:
            #   • Native gas token  → 18 decimals  (tx.value, no contract address)
            #   • ERC-20 interface  →  6 decimals  (0x3600000000000000000000000000000000000000)
            # Source: https://docs.arc.network/arc/references/contract-addresses
            tx_to = (tx.get("to") or "").lower()
            expected_to = to_address.lower()

            if self._usdc_token:
                # ERC-20 path — the optional USDC contract uses 6 decimals
                # (same as standard ERC-20 USDC on other chains)
                min_units = int(expected_amount_usdc * 10**6)
                if tx_to != self._usdc_token.lower():
                    return False
                decoded = self._decode_erc20_transfer_input(tx.get("input", ""))
                if not decoded:
                    return False
                valid = decoded[0].lower() == expected_to and decoded[1] >= min_units
            else:
                # Native path — Arc native USDC uses 18 decimals (arc_usdc_decimals=18)
                min_units = int(expected_amount_usdc * 10**settings.arc_usdc_decimals)
                valid = tx_to == expected_to and int(tx.get("value", 0)) >= min_units

            if valid:
                self._used_payment_hashes.add(tx_hash)
                await self._persist_used_hash(tx_hash)
            return valid
        except Exception as e:
            logger.warning(f"[ARC] Payment verification failed: {e}")
            return False

    async def log_decision_onchain(
        self, action_hash: str, decision: str, risk_score: float
    ) -> str:
        if self.demo_mode:
            self._tx_counter += 1
            fake_hash = hashlib.sha256(
                f"AW:{action_hash}:{decision}:{risk_score}:{time.time_ns()}".encode()
            ).hexdigest()
            return f"0xSIM_{fake_hash}"
        try:
            if self._w3 is None:
                return f"0xERROR_{action_hash[:8]}"
            data_hex = (
                f"AW:v3:{action_hash[:8]}:{decision}:{risk_score:.3f}".encode().hex()
            )
            async with nonce_lock:
                loop = asyncio.get_running_loop()
                nonce = await loop.run_in_executor(
                    None,
                    self._w3.eth.get_transaction_count,
                    self._signer_address,
                    "pending",
                )
                gas_price = await loop.run_in_executor(
                    None, lambda: self._w3.eth.gas_price
                )
                # Bump gas price by 15% to ensure testnet priority
                gas_price_bumped = int(gas_price * 1.15)

                tx = {
                    "chainId": self.chain_id,
                    "nonce": nonce,
                    "to": self._signer_address,
                    "value": 0,
                    "data": f"0x{data_hex}",
                    "gas": 120000,
                    "gasPrice": gas_price_bumped,
                }
                signed = Account.sign_transaction(tx, self._signer_private_key)
                sent_hash = await loop.run_in_executor(
                    None, self._w3.eth.send_raw_transaction, signed.raw_transaction
                )
                tx_hash = self._w3.to_hex(sent_hash)
            if not await self._await_confirmations(tx_hash):
                logger.warning(f"[ARC] Decision log tx unconfirmed: {tx_hash}")
            else:
                logger.success(
                    f"[ARC] ✅ Decision logged onchain — {decision} | "
                    f"{settings.arc_explorer_url}/tx/{tx_hash}"
                )
            return tx_hash
        except Exception as e:
            if "insufficient funds" in str(e).lower():
                pass # Silently ignore gas errors during demo
            else:
                logger.error(f"[ARC] Onchain log failed: {e}")
            return f"0xERROR_{action_hash[:8]}"


# ────────────────────────────────────────────────────────────────────────────────
# Circle Client (DCW)
# ────────────────────────────────────────────────────────────────────────────────
class CircleClient:
    def __init__(self):
        self.api_key = settings.circle_api_key
        self.wallet_id = settings.sigui_wallet_id
        self.demo_mode = settings.demo_mode
        self._demo_seed_balance = max(settings.initial_balance_usdc, 0.2)
        self._simulated_balances: dict[str, float] = {
            self.wallet_id: self._demo_seed_balance
        }

    async def get_wallet_balance(self, wallet_id: str | None = None) -> float:
        target = wallet_id or self.wallet_id
        if self.demo_mode or self.api_key == "demo_key":
            return self._simulated_balances.setdefault(target, self._demo_seed_balance)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{CIRCLE_BASE_URL}/w3s/wallets/{target}/balances",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )
                resp.raise_for_status()
                for bal in resp.json().get("data", {}).get("tokenBalances", []):
                    if bal.get("token", {}).get("symbol") == "USDC":
                        return float(bal.get("amount", 0))
                return 0.0
        except Exception as e:
            logger.warning(f"[CIRCLE] Balance fetch failed: {e}")
            return self._simulated_balances.setdefault(target, self._demo_seed_balance)

    async def transfer_usdc(
        self,
        destination_address: str,
        amount_usdc: float,
        description: str = "",
        source_wallet_id: str | None = None,
        user_id: str = "sigui",
    ) -> dict:
        target = source_wallet_id or self.wallet_id
        if self.demo_mode or self.api_key == "demo_key":
            self._simulated_balances.setdefault(target, self._demo_seed_balance)
            self._simulated_balances[target] = max(
                0.0, self._simulated_balances[target] - amount_usdc
            )
            return {
                "status": "complete",
                "demo": True,
                "amount": amount_usdc,
                "source_wallet_id": target,
                "txHash": f"0xdemo_{abs(hash((target, destination_address, amount_usdc))):x}",
            }
        try:
            import json
            import subprocess
            import uuid as _uuid

            script_path = "scripts/circle/do_transfer.js"
            cmd = ["node", script_path, target, destination_address, str(amount_usdc)]

            # Run non-blocking in thread pool so agents aren't stalled
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=30),
            )

            if result.returncode != 0:
                logger.error(
                    f"[CIRCLE] Transfer failed: {result.stderr or result.stdout}"
                )
                return {"status": "failed", "error": result.stderr or result.stdout}

            data = json.loads(result.stdout.strip().split("\n")[-1])
            logger.info(f"[CIRCLE] Transfer OK → txHash={data.get('txHash', '?')[:20]}")
            return data
        except Exception as e:
            logger.error(f"[CIRCLE] Transfer failed: {e}")
            return {"status": "failed", "error": str(e)}

    def add_revenue(self, amount: float):
        if self.demo_mode:
            self._simulated_balances[self.wallet_id] = (
                self._simulated_balances.get(self.wallet_id, self._demo_seed_balance)
                + amount
            )

    def spend(self, amount: float):
        if self.demo_mode:
            self._simulated_balances[self.wallet_id] = max(
                0.0,
                self._simulated_balances.get(self.wallet_id, self._demo_seed_balance)
                - amount,
            )


arc_client = ArcClient()
circle_client = CircleClient()
