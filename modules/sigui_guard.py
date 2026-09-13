"""
modules/sigui_guard.py — Zero-Code Multichain RPC Security Proxy (Sigui Guard)

Deployment modes:
  - LOCAL: Agent sets RPC_URL=http://127.0.0.1:8545 and runs this proxy locally.
  - HOSTED (recommended): Sigui runs this server as a public endpoint.
    Agent ONLY changes one ENV line (no installation whatsoever):
      RPC_URL=https://rpc.sigui.io/v1/ethereum

Supported Chains:
  ┌─────────────┬──────────────────────────────────────────────────────────────┐
  │ EVM Family  │ ethereum, arbitrum, base, polygon, bsc, optimism, avalanche  │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Aptos       │ aptos (REST /v1/transactions)                                │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Solana      │ solana (JSON-RPC sendTransaction / sendRawTransaction)       │
  ├─────────────┼──────────────────────────────────────────────────────────────┤
  │ Starknet    │ starknet (starknet_addInvokeTransaction)                     │
  └─────────────┴──────────────────────────────────────────────────────────────┘

Zero-Code integration for developers:
  # Before (Vulnerable):
  RPC_URL = "https://rpc.ankr.com/eth"

  # After (Protected by Sigui Guard — no installation needed in hosted mode):
  RPC_URL = "https://rpc.sigui.io/v1/ethereum"
"""

import argparse
import base64
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
import rlp
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from loguru import logger

from modules.imina_na_vision import imina_na_vision
from modules.security_engine import ActionInput, decision_engine, risk_engine, add_to_blacklist, _blacklist

# ─────────────────────────────────────────────────────────────────────────────
# Chain Registry
# ─────────────────────────────────────────────────────────────────────────────

CHAIN_REGISTRY: Dict[str, Dict[str, str]] = {
    # EVM-compatible chains (all share JSON-RPC standard)
    "ethereum":  {"type": "evm", "upstream": "https://rpc.ankr.com/eth"},
    "arbitrum":  {"type": "evm", "upstream": "https://rpc.ankr.com/arbitrum"},
    "base":      {"type": "evm", "upstream": "https://rpc.ankr.com/base"},
    "polygon":   {"type": "evm", "upstream": "https://rpc.ankr.com/polygon"},
    "bsc":       {"type": "evm", "upstream": "https://rpc.ankr.com/bsc"},
    "optimism":  {"type": "evm", "upstream": "https://rpc.ankr.com/optimism"},
    "avalanche": {"type": "evm", "upstream": "https://rpc.ankr.com/avalanche"},
    "sepolia":   {"type": "evm", "upstream": "https://rpc.ankr.com/eth_sepolia"},
    # Non-EVM chains
    "aptos":     {"type": "aptos",    "upstream": "https://fullnode.mainnet.aptoslabs.com"},
    "solana":    {"type": "solana",   "upstream": "https://api.mainnet-beta.solana.com"},
    "starknet":  {"type": "starknet", "upstream": "https://starknet-mainnet.public.blastapi.io"},
}

EVM_CHAINS = {k for k, v in CHAIN_REGISTRY.items() if v["type"] == "evm"}

# ─────────────────────────────────────────────────────────────────────────────
# EVM Decoders
# ─────────────────────────────────────────────────────────────────────────────

ERC20_TRANSFER_SIG      = bytes.fromhex("a9059cbb")  # transfer(address,uint256)
ERC20_APPROVE_SIG       = bytes.fromhex("095ea7b3")  # approve(address,uint256)
ERC20_TRANSFER_FROM_SIG = bytes.fromhex("23b87266")  # transferFrom(address,address,uint256)


def _to_hex_address(raw_bytes: bytes) -> str:
    if len(raw_bytes) == 20:
        return "0x" + raw_bytes.hex()
    elif len(raw_bytes) > 20:
        return "0x" + raw_bytes[-20:].hex()
    return "0x" + raw_bytes.hex().zfill(40)


def extract_erc20_recipient(data_bytes: bytes) -> Optional[str]:
    if len(data_bytes) < 4:
        return None
    selector = data_bytes[:4]
    if selector in (ERC20_TRANSFER_SIG, ERC20_APPROVE_SIG) and len(data_bytes) >= 36:
        return _to_hex_address(data_bytes[4:36])
    if selector == ERC20_TRANSFER_FROM_SIG and len(data_bytes) >= 68:
        return _to_hex_address(data_bytes[36:68])
    return None


def decode_raw_evm_tx(raw_tx_hex: str) -> Tuple[Optional[str], float, Optional[str]]:
    """
    Decodes an EVM raw transaction hex string (Legacy, EIP-2930, EIP-1559).
    Returns: (destination_contract, value_eth, token_recipient_or_None)
    """
    try:
        raw_hex = raw_tx_hex.strip()
        if raw_hex.startswith("0x") or raw_hex.startswith("0X"):
            raw_hex = raw_hex[2:]
        raw_bytes = bytes.fromhex(raw_hex)
        if not raw_bytes:
            return None, 0.0, None

        first_byte = raw_bytes[0]

        # EIP-1559 (Type 2) or EIP-2930 (Type 1)
        if first_byte in (1, 2):
            rlp_payload = raw_bytes[1:]
            decoded = rlp.decode(rlp_payload)
            if first_byte == 2 and len(decoded) >= 8:
                dest = _to_hex_address(decoded[5]) if decoded[5] else None
                value_wei = int.from_bytes(decoded[6], "big") if decoded[6] else 0
                recipient = extract_erc20_recipient(decoded[7]) if decoded[7] else None
                return dest, value_wei / 1e18, recipient
            elif first_byte == 1 and len(decoded) >= 7:
                dest = _to_hex_address(decoded[4]) if decoded[4] else None
                value_wei = int.from_bytes(decoded[5], "big") if decoded[5] else 0
                recipient = extract_erc20_recipient(decoded[6]) if decoded[6] else None
                return dest, value_wei / 1e18, recipient

        # Legacy (Type 0)
        decoded = rlp.decode(raw_bytes)
        if isinstance(decoded, list) and len(decoded) >= 6:
            dest = _to_hex_address(decoded[3]) if decoded[3] else None
            value_wei = int.from_bytes(decoded[4], "big") if decoded[4] else 0
            recipient = extract_erc20_recipient(decoded[5]) if decoded[5] else None
            return dest, value_wei / 1e18, recipient

    except Exception as e:
        logger.warning(f"[SIGUI GUARD] ⚠️ EVM decode failed: {e}")

    return None, 0.0, None


# ─────────────────────────────────────────────────────────────────────────────
# Solana Decoders
# ─────────────────────────────────────────────────────────────────────────────

def decode_solana_transaction(tx_param: Any) -> Optional[str]:
    """
    Attempts to extract the first writable non-signer account from a Solana transaction.
    Solana transactions are base58/base64 encoded byte arrays.
    """
    try:
        if isinstance(tx_param, str):
            # Base64 encoded
            if len(tx_param) % 4 == 0 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in tx_param[:20]):
                decoded = base64.b64decode(tx_param)
            else:
                # Try base58 via list encoding fallback
                return None

            # Solana tx structure: signatures_count (compact u16) | message
            # message: header (3 bytes) | accounts (compact u16 + 32-byte pubkeys) | ...
            # We parse the first "writable non-signer" account as the recipient.
            sig_count = decoded[0]  # simplified: single byte compact u16
            sig_bytes = 1 + sig_count * 64
            msg_start = sig_bytes

            header = decoded[msg_start:msg_start + 3]
            num_required_signatures = header[0]
            num_readonly_signed = header[1]
            num_readonly_unsigned = header[2]

            accounts_offset = msg_start + 3
            num_accounts = decoded[accounts_offset]
            accounts_offset += 1

            if num_accounts > 0 and len(decoded) >= accounts_offset + num_accounts * 32:
                # First account is typically fee payer, second is recipient for transfers
                # Find first writable unsigned account (potential recipient)
                writable_signed = num_required_signatures - num_readonly_signed
                writable_unsigned_start = writable_signed
                writable_unsigned_end = num_accounts - num_readonly_unsigned

                if writable_unsigned_start < writable_unsigned_end:
                    account_raw = decoded[accounts_offset + writable_signed * 32:accounts_offset + (writable_signed + 1) * 32]
                    import base58
                    return base58.b58encode(account_raw).decode("utf-8")
    except Exception as e:
        logger.debug(f"[SIGUI GUARD] Solana decode fallback: {e}")
    return None


def decode_solana_pubkey(tx_param: Any) -> Optional[str]:
    """
    Lightweight extraction: for Solana JSON-RPC sendTransaction or sendRawTransaction.
    Returns the first writable non-signer public key found (simplified heuristic).
    """
    try:
        if isinstance(tx_param, list) and len(tx_param) >= 2:
            return decode_solana_transaction(tx_param[0])
        elif isinstance(tx_param, str):
            return decode_solana_transaction(tx_param)
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Starknet Decoders
# ─────────────────────────────────────────────────────────────────────────────

def decode_starknet_invoke(params: List[Any]) -> Optional[str]:
    """
    Extracts recipient from a Starknet invoke transaction.
    starknet_addInvokeTransaction params[0] = {
        "type": "INVOKE",
        "sender_address": "0x...",
        "calldata": ["0x...", ...],  # first call: [to, selector, calldata_len, ...args]
        ...
    }
    """
    try:
        if not params:
            return None
        invoke = params[0]
        calldata = invoke.get("calldata", [])
        # Starknet __execute__ multicall format:
        # calldata[0] = number_of_calls
        # calldata[1] = to (first call target address)
        if len(calldata) >= 2:
            return str(calldata[1])
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Multichain Proxy Core
# ─────────────────────────────────────────────────────────────────────────────

class SiguiGuardProxy:
    """
    Multichain Zero-Code RPC Security Proxy for AI Agents.

    Hosted mode (zero-install):
        Agent sets: RPC_URL = "https://rpc.sigui.io/v1/ethereum"
        Sigui Guard runs in the cloud — completely transparent to the agent.

    Local mode (dev/testing):
        Run: python -m modules.sigui_guard --port 8545 --network ethereum
        Agent sets: RPC_URL = "http://127.0.0.1:8545"
    """

    def __init__(self, fail_closed: bool = True, enable_zk: bool = True):
        self.fail_closed = fail_closed
        self.enable_zk = enable_zk
        self.client = httpx.AsyncClient(timeout=30.0, limits=httpx.Limits(max_connections=500))
        self.app = FastAPI(title="Sigui Guard — Multichain Zero-Code RPC Security Proxy", version="3.2.0")
        self._setup_routes()

    def _setup_routes(self):
        # ── Health & Status ──────────────────────────────────────────────────
        self.app.get("/health")(self.handle_health)
        self.app.get("/status")(self.handle_status)
        self.app.get("/chains")(self.handle_chains)

        # ── Hosted Multichain Routing ────────────────────────────────────────
        # Pattern: /v1/{chain} — developer sets RPC_URL=https://rpc.sigui.io/v1/ethereum
        self.app.post("/v1/{chain}")(self.handle_v1_rpc)

        # Aptos REST sub-paths: /v1/{chain}/transactions
        self.app.post("/v1/{chain}/transactions")(self.handle_v1_aptos_tx)

        # ── Local Single-Chain Mode ──────────────────────────────────────────
        # Fallback to single-chain when running as local proxy on a fixed port
        self.app.post("/")(self.handle_auto_rpc)
        self.app.post("/v1/transactions")(self.handle_single_aptos_tx)
        self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])(self.handle_fallback)

    # ── Health & Info Endpoints ──────────────────────────────────────────────

    async def handle_health(self):
        return {"status": "healthy", "proxy": "Sigui Guard v3.2.0", "mode": "multichain"}

    async def handle_status(self):
        return {
            "proxy": "Sigui Guard",
            "version": "3.2.0",
            "supported_chains": list(CHAIN_REGISTRY.keys()),
            "evm_chains": sorted(EVM_CHAINS),
            "fail_closed": self.fail_closed,
            "blacklisted_targets": len(_blacklist),
            "hosted_endpoint_template": "https://rpc.sigui.io/v1/{chain}",
            "zero_install": True,
        }

    async def handle_chains(self):
        return {
            "chains": {
                name: {"type": meta["type"], "upstream": meta["upstream"]}
                for name, meta in CHAIN_REGISTRY.items()
            }
        }

    # ── Audit Core ───────────────────────────────────────────────────────────

    async def audit_destination(self, target_address: str, chain: str = "ethereum", amount_usdc: float = 0.0) -> Dict[str, Any]:
        norm_target = target_address.lower()
        if norm_target in _blacklist:
            return {
                "decision": "BLOCK",
                "sigui_verdict": "BLOCK",
                "pattern": "DRAIN_STAR",
                "risk_score": 0.99,
                "reason": f"Destination {target_address[:14]}… is in the Sigui dynamic threat blacklist.",
            }
        try:
            action_input = ActionInput(
                agent_id="sigui_guard",
                action_type="transfer",
                amount_usdc=amount_usdc,
                destination=target_address,
                chain=chain,
            )
            vision_res = await imina_na_vision.analyze(
                action={"action_type": "transfer", "amount_usdc": amount_usdc, "chain": chain},
                target_address=target_address,
            )
            risk_out = await risk_engine.score(action_input, {"avg_amount_usdc": 100.0, "trust_score": 0.8})
            dec_out = decision_engine.decide(risk_out)

            if vision_res.pattern in ("DRAIN_STAR", "MIXING_CHAIN", "COORDINATED_CLUSTER") and vision_res.confidence >= 0.70:
                return {
                    "decision": "BLOCK",
                    "sigui_verdict": "BLOCK",
                    "pattern": vision_res.pattern,
                    "risk_score": max(dec_out.risk_score, vision_res.confidence),
                    "reason": f"{vision_res.pattern} detected by Imina-Na V2 ({vision_res.confidence*100:.1f}% confidence)",
                }

            return {
                "decision": dec_out.decision.value,
                "sigui_verdict": dec_out.decision.value,
                "pattern": vision_res.pattern,
                "risk_score": dec_out.risk_score,
                "reason": dec_out.reason,
            }
        except Exception as e:
            logger.error(f"[SIGUI GUARD] Oracle error on {chain}: {e}")
            if self.fail_closed:
                return {
                    "decision": "BLOCK",
                    "sigui_verdict": "BLOCK",
                    "pattern": "ORACLE_UNAVAILABLE",
                    "risk_score": 1.0,
                    "reason": f"Sigui Oracle unavailable ({e}). Fail-closed policy active.",
                }
            return {"decision": "ALLOW", "sigui_verdict": "ALLOW", "pattern": "NORMAL", "risk_score": 0.0, "reason": "Fail-open."}

    def _block_evm_response(self, req_id: Any, addr: str, verdict: Dict) -> Dict:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32003,
                "message": f"Transaction rejected by Sigui Guard: {verdict.get('pattern', 'THREAT')} threat at {addr[:14]}…",
                "data": {
                    "sigui_verdict": "BLOCK",
                    "decision": "BLOCK",
                    "target": addr,
                    "chain": verdict.get("chain", ""),
                    "pattern": verdict.get("pattern"),
                    "risk_score": verdict.get("risk_score"),
                    "reason": verdict.get("reason"),
                    "sigui_docs": "https://ibonon.github.io/Sigui/sentinel.html",
                },
            },
        }

    # ── EVM JSON-RPC Interceptor ─────────────────────────────────────────────

    async def _handle_evm_rpc(self, payload: Any, upstream: str, chain: str) -> Any:
        is_batch = isinstance(payload, list)
        items = payload if is_batch else [payload]
        responses = []

        for item in items:
            method = item.get("method", "")
            req_id = item.get("id")
            params = item.get("params", [])

            # ── eth_sendRawTransaction ────────────────────────────────────────
            if method == "eth_sendRawTransaction" and params:
                dest, val_eth, recipient = decode_raw_evm_tx(params[0])
                targets = []
                if dest: targets.append(("contract", dest))
                if recipient and recipient != dest: targets.append(("token_recipient", recipient))

                blocked = False
                for target_type, addr in targets:
                    logger.info(f"[SIGUI GUARD] 🛡️ [{chain.upper()}] {method} → Auditing {target_type}: {addr}")
                    verdict = await self.audit_destination(addr, chain=chain, amount_usdc=val_eth * 3000.0)
                    if verdict.get("decision") == "BLOCK":
                        logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED [{chain.upper()}] → {addr} | Pattern: {verdict.get('pattern')}")
                        verdict["chain"] = chain
                        responses.append(self._block_evm_response(req_id, addr, verdict))
                        blocked = True
                        break
                if blocked:
                    continue

            # ── eth_sendTransaction ───────────────────────────────────────────
            elif method == "eth_sendTransaction" and params and isinstance(params[0], dict):
                tx_dict = params[0]
                to_addr = tx_dict.get("to")
                targets = []
                if to_addr: targets.append(("contract", to_addr))

                data_hex = tx_dict.get("data", "")
                if data_hex and len(data_hex) > 10:
                    try:
                        raw_data = bytes.fromhex(data_hex.lstrip("0x"))
                        recip = extract_erc20_recipient(raw_data)
                        if recip and recip != to_addr: targets.append(("token_recipient", recip))
                    except Exception:
                        pass

                blocked = False
                for target_type, addr in targets:
                    logger.info(f"[SIGUI GUARD] 🛡️ [{chain.upper()}] {method} → Auditing {target_type}: {addr}")
                    verdict = await self.audit_destination(addr, chain=chain)
                    if verdict.get("decision") == "BLOCK":
                        logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED [{chain.upper()}] → {addr}")
                        verdict["chain"] = chain
                        responses.append(self._block_evm_response(req_id, addr, verdict))
                        blocked = True
                        break
                if blocked:
                    continue

            # ── Transparent passthrough ───────────────────────────────────────
            try:
                resp = await self.client.post(upstream, json=item)
                responses.append(resp.json())
            except Exception as e:
                responses.append({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": f"Upstream error: {e}"}})

        return responses if is_batch else responses[0]

    # ── Solana JSON-RPC Interceptor ─────────────────────────────────────────

    async def _handle_solana_rpc(self, payload: Any, upstream: str) -> Any:
        is_batch = isinstance(payload, list)
        items = payload if is_batch else [payload]
        responses = []

        for item in items:
            method = item.get("method", "")
            req_id = item.get("id")
            params = item.get("params", [])

            if method in ("sendTransaction", "sendRawTransaction") and params:
                recipient = decode_solana_pubkey(params)
                if recipient:
                    logger.info(f"[SIGUI GUARD] 🛡️ [SOLANA] {method} → Auditing: {recipient}")
                    verdict = await self.audit_destination(recipient, chain="solana")
                    if verdict.get("decision") == "BLOCK":
                        logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED [SOLANA] → {recipient}")
                        responses.append({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": -32003,
                                "message": f"Transaction rejected by Sigui Guard (Solana): {verdict.get('pattern')} at {recipient[:14]}…",
                                "data": {"sigui_verdict": "BLOCK", "target": recipient, **verdict},
                            },
                        })
                        continue

            try:
                resp = await self.client.post(upstream, json=item)
                responses.append(resp.json())
            except Exception as e:
                responses.append({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": f"Upstream error: {e}"}})

        return responses if is_batch else responses[0]

    # ── Starknet JSON-RPC Interceptor ───────────────────────────────────────

    async def _handle_starknet_rpc(self, payload: Any, upstream: str) -> Any:
        is_batch = isinstance(payload, list)
        items = payload if is_batch else [payload]
        responses = []

        for item in items:
            method = item.get("method", "")
            req_id = item.get("id")
            params = item.get("params", [])

            if method == "starknet_addInvokeTransaction" and params:
                recipient = decode_starknet_invoke(params)
                if recipient:
                    logger.info(f"[SIGUI GUARD] 🛡️ [STARKNET] {method} → Auditing: {recipient}")
                    verdict = await self.audit_destination(recipient, chain="starknet")
                    if verdict.get("decision") == "BLOCK":
                        logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED [STARKNET] → {recipient}")
                        responses.append({
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {
                                "code": 63,  # Starknet standard reject code
                                "message": f"Transaction rejected by Sigui Guard (Starknet): {verdict.get('pattern')}",
                                "data": {"sigui_verdict": "BLOCK", "target": recipient, **verdict},
                            },
                        })
                        continue

            try:
                resp = await self.client.post(upstream, json=item)
                responses.append(resp.json())
            except Exception as e:
                responses.append({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": f"Upstream error: {e}"}})

        return responses if is_batch else responses[0]

    # ── Aptos REST Interceptor ────────────────────────────────────────────────

    async def _handle_aptos_tx(self, body_bytes: bytes, upstream: str) -> Response:
        try:
            aptos_payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            func_payload = aptos_payload.get("payload", {})
            arguments = func_payload.get("arguments", [])

            target_addr = None
            if arguments and isinstance(arguments[0], str) and arguments[0].startswith("0x"):
                target_addr = arguments[0]

            if target_addr:
                logger.info(f"[SIGUI GUARD] 🛡️ [APTOS] transaction → Auditing: {target_addr}")
                verdict = await self.audit_destination(target_addr, chain="aptos")
                if verdict.get("decision") == "BLOCK":
                    logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED [APTOS] → {target_addr}")
                    return JSONResponse(status_code=403, content={
                        "message": f"Transaction blocked by Sigui Guard (Aptos): {verdict.get('pattern')}",
                        "error_code": "SIGUI_SECURITY_BLOCK",
                        "sigui_verdict": verdict,
                    })

            resp = await self.client.post(f"{upstream}/v1/transactions", content=body_bytes, headers={"Content-Type": "application/json"})
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
        except Exception as e:
            return JSONResponse(status_code=502, content={"error": str(e)})

    # ── Route Handlers ────────────────────────────────────────────────────────

    async def handle_v1_rpc(self, chain: str, request: Request):
        """Handles: POST /v1/{chain} — hosted multichain mode."""
        chain = chain.lower()
        if chain not in CHAIN_REGISTRY:
            return JSONResponse(
                status_code=404,
                content={
                    "error": f"Unsupported chain '{chain}'.",
                    "supported_chains": list(CHAIN_REGISTRY.keys()),
                    "example": "POST /v1/ethereum",
                },
            )
        meta = CHAIN_REGISTRY[chain]
        upstream = meta["upstream"]
        body_bytes = await request.body()

        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        if meta["type"] == "evm":
            result = await self._handle_evm_rpc(payload, upstream, chain)
        elif meta["type"] == "solana":
            result = await self._handle_solana_rpc(payload, upstream)
        elif meta["type"] == "starknet":
            result = await self._handle_starknet_rpc(payload, upstream)
        else:
            # Passthrough unknown types
            resp = await self.client.post(upstream, content=body_bytes)
            return Response(content=resp.content, status_code=resp.status_code)

        return JSONResponse(content=result)

    async def handle_v1_aptos_tx(self, chain: str, request: Request):
        """Handles: POST /v1/{chain}/transactions — Aptos REST in hosted mode."""
        if chain.lower() != "aptos":
            return JSONResponse(status_code=404, content={"error": "Only aptos chain supports /transactions REST endpoint."})
        body_bytes = await request.body()
        return await self._handle_aptos_tx(body_bytes, CHAIN_REGISTRY["aptos"]["upstream"])

    async def handle_auto_rpc(self, request: Request):
        """Handles: POST / — local single-chain mode (auto-detect protocol from payload)."""
        body_bytes = await request.body()
        try:
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        # Detect chain from JSON-RPC method name
        items = payload if isinstance(payload, list) else [payload]
        method = items[0].get("method", "") if items else ""

        if method.startswith("starknet_"):
            result = await self._handle_starknet_rpc(payload, CHAIN_REGISTRY["starknet"]["upstream"])
        elif method in ("sendTransaction", "sendRawTransaction", "getAccountInfo"):
            result = await self._handle_solana_rpc(payload, CHAIN_REGISTRY["solana"]["upstream"])
        else:
            # Default to Ethereum
            result = await self._handle_evm_rpc(payload, CHAIN_REGISTRY["ethereum"]["upstream"], "ethereum")

        return JSONResponse(content=result)

    async def handle_single_aptos_tx(self, request: Request):
        """Handles: POST /v1/transactions — single Aptos mode for local proxy."""
        body_bytes = await request.body()
        return await self._handle_aptos_tx(body_bytes, CHAIN_REGISTRY["aptos"]["upstream"])

    async def handle_fallback(self, request: Request, path: str):
        """Transparent proxy for all non-intercepted paths."""
        chain = path.split("/")[0].lower()
        upstream = CHAIN_REGISTRY.get(chain, CHAIN_REGISTRY["ethereum"])["upstream"]
        body = await request.body()
        try:
            resp = await self.client.request(
                method=request.method,
                url=f"{upstream}/{path.split('/', 1)[-1] if '/' in path else ''}",
                content=body,
                headers={k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")},
                params=request.query_params,
            )
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))
        except Exception as e:
            return JSONResponse(status_code=502, content={"error": f"Upstream proxy failed: {e}"})


# ─────────────────────────────────────────────────────────────────────────────
# Factory & CLI Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def create_guard_app() -> FastAPI:
    return SiguiGuardProxy().app


def main():
    parser = argparse.ArgumentParser(description="Sigui Guard — Multichain Zero-Code RPC Security Proxy")
    parser.add_argument("--port", type=int, default=8545)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--fail-open", action="store_true", help="Allow transactions when oracle is down (default: fail-closed)")
    args = parser.parse_args()

    import uvicorn

    print("=" * 70)
    print("  🛡️  SIGUI GUARD v3.2.0 — Multichain Zero-Code RPC Security Proxy")
    print("=" * 70)
    print(f"  • Local Endpoint    : http://{args.host}:{args.port}/v1/{{chain}}")
    print(f"  • Hosted Endpoint   : https://rpc.sigui.io/v1/{{chain}}")
    print(f"  • Fail-Closed Mode  : {not args.fail_open}")
    print(f"  • Supported Chains  : {', '.join(CHAIN_REGISTRY.keys())}")
    print("=" * 70)
    print("  ✅ ZERO-CODE: Developers only set one ENV variable:")
    print("     RPC_URL=http://127.0.0.1:{args.port}/v1/ethereum  (local)")
    print("     RPC_URL=https://rpc.sigui.io/v1/ethereum          (hosted)\n")

    guard = SiguiGuardProxy(fail_closed=not args.fail_open)
    uvicorn.run(guard.app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
