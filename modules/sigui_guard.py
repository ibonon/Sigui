"""
modules/sigui_guard.py — Zero-Code RPC Security Proxy (Sigui Guard)

Acts as a transparent, high-performance local JSON-RPC / REST proxy for AI agents.
Agents point their RPC endpoint to http://127.0.0.1:8545 (EVM) or http://127.0.0.1:8080 (Aptos).

When an agent invokes `eth_sendRawTransaction`, `eth_sendTransaction`, or submits an Aptos payload:
  1. Intercepts and decodes the transaction payload (<3ms)
  2. Extracts the destination contract AND the token recipient (ERC-20/721 transfers)
  3. Audits the destination topology via the Sigui Security Oracle (<30ms)
  4. If ALLOWED: forwards seamlessly to the upstream blockchain node
  5. If BLOCKED: aborts with JSON-RPC error -32003, safeguarding the agent's treasury

Zero code changes needed in the agent logic.
"""

import argparse
import asyncio
import binascii
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from loguru import logger
import rlp

# Import Sigui core modules
from modules.imina_na_vision import imina_na_vision
from modules.security_engine import ActionInput, decision_engine, risk_engine, add_to_blacklist, _blacklist

# ─────────────────────────────────────────────────────────────────────────────
# EVM Calldata & RLP Helpers
# ─────────────────────────────────────────────────────────────────────────────

ERC20_TRANSFER_SIG = bytes.fromhex("a9059cbb")  # transfer(address,uint256)
ERC20_APPROVE_SIG  = bytes.fromhex("095ea7b3")  # approve(address,uint256)
ERC20_TRANSFER_FROM_SIG = bytes.fromhex("23b87266") # transferFrom(address,address,uint256)


def _to_hex_address(raw_bytes: bytes) -> str:
    """Format raw 20-byte address into standard 0x hex string."""
    if len(raw_bytes) == 20:
        return "0x" + raw_bytes.hex()
    elif len(raw_bytes) > 20:
        return "0x" + raw_bytes[-20:].hex()
    return "0x" + raw_bytes.hex().zfill(40)


def extract_erc20_recipient(data_bytes: bytes) -> Optional[str]:
    """
    Extract the actual token beneficiary if transaction data is an ERC-20 transfer/approve.
    """
    if len(data_bytes) < 4:
        return None
    selector = data_bytes[:4]
    
    # transfer(to, amount) or approve(spender, amount)
    if selector in (ERC20_TRANSFER_SIG, ERC20_APPROVE_SIG) and len(data_bytes) >= 36:
        raw_to = data_bytes[4:36]
        return _to_hex_address(raw_to)
    
    # transferFrom(from, to, amount)
    if selector == ERC20_TRANSFER_FROM_SIG and len(data_bytes) >= 68:
        raw_to = data_bytes[36:68]
        return _to_hex_address(raw_to)
        
    return None


def decode_raw_evm_tx(raw_tx_hex: str) -> Tuple[Optional[str], float, Optional[str]]:
    """
    Decodes an EVM raw transaction hex string (supports Legacy, EIP-2930, EIP-1559).
    Returns: (destination_contract, value_eth, token_recipient)
    """
    try:
        raw_hex = raw_tx_hex.strip()
        if raw_hex.startswith("0x") or raw_hex.startswith("0X"):
            raw_hex = raw_hex[2:]
            
        raw_bytes = bytes.fromhex(raw_hex)
        if not raw_bytes:
            return None, 0.0, None

        first_byte = raw_bytes[0]

        # EIP-1559 (Type 2: 0x02) or EIP-2930 (Type 1: 0x01) or EIP-4844 (Type 3: 0x03)
        if first_byte in (1, 2, 3):
            tx_type = first_byte
            rlp_payload = raw_bytes[1:]
            decoded = rlp.decode(rlp_payload)
            
            if tx_type == 2:
                # EIP-1559: [chain_id, nonce, max_priority_fee, max_fee, gas_limit, destination, amount, data, ...]
                if len(decoded) >= 8:
                    raw_dest = decoded[5]
                    raw_val = decoded[6]
                    raw_data = decoded[7]
                    
                    dest = _to_hex_address(raw_dest) if raw_dest else None
                    value_wei = int.from_bytes(raw_val, byteorder="big") if raw_val else 0
                    value_eth = value_wei / 1e18
                    recipient = extract_erc20_recipient(raw_data) if raw_data else None
                    return dest, value_eth, recipient

            elif tx_type == 1:
                # EIP-2930: [chain_id, nonce, gas_price, gas_limit, destination, amount, data, ...]
                if len(decoded) >= 7:
                    raw_dest = decoded[4]
                    raw_val = decoded[5]
                    raw_data = decoded[6]
                    
                    dest = _to_hex_address(raw_dest) if raw_dest else None
                    value_wei = int.from_bytes(raw_val, byteorder="big") if raw_val else 0
                    value_eth = value_wei / 1e18
                    recipient = extract_erc20_recipient(raw_data) if raw_data else None
                    return dest, value_eth, recipient

        # Legacy transaction (Type 0)
        decoded = rlp.decode(raw_bytes)
        # Legacy: [nonce, gas_price, gas_limit, to, value, data, v, r, s]
        if isinstance(decoded, list) and len(decoded) >= 6:
            raw_dest = decoded[3]
            raw_val = decoded[4]
            raw_data = decoded[5]
            
            dest = _to_hex_address(raw_dest) if raw_dest else None
            value_wei = int.from_bytes(raw_val, byteorder="big") if raw_val else 0
            value_eth = value_wei / 1e18
            recipient = extract_erc20_recipient(raw_data) if raw_data else None
            return dest, value_eth, recipient

    except Exception as e:
        logger.warning(f"[SIGUI GUARD] ⚠️ Failed to decode raw EVM transaction: {e}")

    return None, 0.0, None


# ─────────────────────────────────────────────────────────────────────────────
# Proxy Core Server Class
# ─────────────────────────────────────────────────────────────────────────────

class SiguiGuardProxy:
    """
    High-performance RPC firewall proxy.
    """

    def __init__(
        self,
        upstream_url: str = "https://rpc.ankr.com/eth",
        network: str = "ethereum",
        fail_closed: bool = True,
        enable_zk: bool = True,
    ):
        self.upstream_url = upstream_url.rstrip("/")
        self.network = network
        self.fail_closed = fail_closed
        self.enable_zk = enable_zk
        self.client = httpx.AsyncClient(timeout=30.0)
        self.app = FastAPI(title="Sigui Guard Zero-Code RPC Proxy", version="3.1.0")
        self._setup_routes()

    def _setup_routes(self):
        # Universal JSON-RPC / REST endpoint
        self.app.post("/")(self.handle_json_rpc)
        self.app.get("/")(self.handle_health)
        self.app.get("/health")(self.handle_health)
        self.app.get("/status")(self.handle_status)
        
        # Aptos REST endpoints
        self.app.post("/v1/transactions")(self.handle_aptos_transactions)
        self.app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])(self.handle_fallback_proxy)

    async def handle_health(self):
        return {
            "status": "healthy",
            "proxy": "Sigui Guard v3.1.0",
            "network": self.network,
            "upstream": self.upstream_url,
            "fail_closed": self.fail_closed,
        }

    async def handle_status(self):
        return {
            "proxy": "Sigui Guard",
            "mode": "Zero-Code RPC Interceptor",
            "upstream": self.upstream_url,
            "network": self.network,
            "blacklisted_targets": len(_blacklist),
            "fail_closed": self.fail_closed,
        }

    async def audit_destination(self, target_address: str, amount_usdc: float = 0.0) -> Dict[str, Any]:
        """
        Queries Sigui Security Engine and Imina-Na Vision model.
        Returns evaluation dict with 'decision', 'pattern', 'risk_score', 'reason'.
        """
        norm_target = target_address.lower()

        # 1. Quick check against dynamic blacklist
        if norm_target in _blacklist:
            return {
                "decision": "BLOCK",
                "pattern": "DRAIN_STAR",
                "risk_score": 0.99,
                "reason": f"Destination {target_address[:12]}… is listed in the Sigui dynamic threat blacklist.",
            }

        # 2. Heuristic and Vision evaluation
        action_input = ActionInput(
            agent_id="sigui_guard_agent",
            action_type="transfer",
            amount_usdc=amount_usdc,
            destination=target_address,
            chain=self.network,
        )

        try:
            # Evaluate via Imina-Na Vision
            vision_res = await imina_na_vision.analyze(
                action={"action_type": "transfer", "amount_usdc": amount_usdc, "chain": self.network},
                target_address=target_address,
            )

            # Heuristic decision
            risk_out = await risk_engine.score(action_input, {"avg_amount_usdc": 100.0, "trust_score": 0.8})
            dec_out = decision_engine.decide(risk_out)

            # Fuse vision findings: if vision detects attack topology, override to BLOCK
            if vision_res.pattern in ("DRAIN_STAR", "MIXING_CHAIN", "COORDINATED_CLUSTER") and vision_res.confidence >= 0.70:
                return {
                    "decision": "BLOCK",
                    "pattern": vision_res.pattern,
                    "risk_score": max(dec_out.risk_score, vision_res.confidence),
                    "reason": f"Attack pattern {vision_res.pattern} detected by Imina-Na V2 Vision Model (Confidence: {vision_res.confidence*100:.1f}%)",
                }

            return {
                "decision": dec_out.decision.value,
                "pattern": vision_res.pattern,
                "risk_score": dec_out.risk_score,
                "reason": dec_out.reason,
            }
        except Exception as e:
            logger.error(f"[SIGUI GUARD] ❌ Oracle audit error: {e}")
            if self.fail_closed:
                return {
                    "decision": "BLOCK",
                    "pattern": "UNKNOWN_ERROR",
                    "risk_score": 1.0,
                    "reason": f"Sigui Oracle unavailable ({e}). Fail-closed policy active.",
                }
            return {
                "decision": "ALLOW",
                "pattern": "NORMAL",
                "risk_score": 0.1,
                "reason": "Oracle bypassed due to fail-open setting.",
            }

    async def handle_json_rpc(self, request: Request):
        """
        Intercepts EVM JSON-RPC requests.
        """
        try:
            body_bytes = await request.body()
            if not body_bytes:
                return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status_code=400)
            
            payload = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            return JSONResponse({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}, status_code=400)

        # Batch JSON-RPC support
        is_batch = isinstance(payload, list)
        items = payload if is_batch else [payload]
        responses = []

        for item in items:
            method = item.get("method", "")
            req_id = item.get("id")
            params = item.get("params", [])

            # ── 1. Intercept `eth_sendRawTransaction` ─────────────────────
            if method == "eth_sendRawTransaction" and params:
                raw_tx = params[0]
                dest, value_eth, recipient = decode_raw_evm_tx(raw_tx)
                
                # Check both destination contract and token recipient
                targets_to_check = []
                if dest: targets_to_check.append(("contract", dest))
                if recipient and recipient != dest: targets_to_check.append(("token_recipient", recipient))

                blocked = False
                block_info = None

                for target_type, target_addr in targets_to_check:
                    logger.info(f"[SIGUI GUARD] 🛡️ Intercepted {method} -> Auditing {target_type}: {target_addr}")
                    verdict = await self.audit_destination(target_addr, amount_usdc=value_eth * 3000.0)

                    if verdict.get("decision") == "BLOCK":
                        blocked = True
                        block_info = (target_addr, verdict)
                        break

                if blocked and block_info:
                    addr, v = block_info
                    logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED transaction to {addr}! Pattern: {v['pattern']} — Risk: {v['risk_score']*100:.0f}%")
                    err_response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32003,
                            "message": f"Transaction rejected by Sigui Guard: {v['pattern']} threat detected at destination {addr}",
                            "data": {
                                "sigui_verdict": "BLOCK",
                                "target": addr,
                                "pattern": v.get("pattern"),
                                "risk_score": v.get("risk_score"),
                                "reason": v.get("reason"),
                            },
                        },
                    }
                    responses.append(err_response)
                    continue

            # ── 2. Intercept `eth_sendTransaction` (un-signed) ────────────
            elif method == "eth_sendTransaction" and params and isinstance(params[0], dict):
                tx_dict = params[0]
                to_addr = tx_dict.get("to")
                data_hex = tx_dict.get("data", "")
                
                targets_to_check = []
                if to_addr: targets_to_check.append(("contract", to_addr))
                
                if data_hex and len(data_hex) > 10:
                    try:
                        raw_data = bytes.fromhex(data_hex[2:] if data_hex.startswith("0x") else data_hex)
                        recip = extract_erc20_recipient(raw_data)
                        if recip and recip != to_addr:
                            targets_to_check.append(("token_recipient", recip))
                    except Exception:
                        pass

                blocked = False
                block_info = None

                for target_type, target_addr in targets_to_check:
                    logger.info(f"[SIGUI GUARD] 🛡️ Intercepted {method} -> Auditing {target_type}: {target_addr}")
                    verdict = await self.audit_destination(target_addr)
                    if verdict.get("decision") == "BLOCK":
                        blocked = True
                        block_info = (target_addr, verdict)
                        break

                if blocked and block_info:
                    addr, v = block_info
                    logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED eth_sendTransaction to {addr}! Pattern: {v['pattern']}")
                    err_response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32003,
                            "message": f"Transaction rejected by Sigui Guard: {v['pattern']} threat detected at {addr}",
                            "data": {
                                "sigui_verdict": "BLOCK",
                                "decision": "BLOCK",
                                "target": addr,
                                "pattern": v.get("pattern"),
                                "risk_score": v.get("risk_score"),
                                "reason": v.get("reason"),
                            },
                        },
                    }
                    responses.append(err_response)
                    continue

            # ── 3. Passthrough to Upstream Node ───────────────────────────
            try:
                resp = await self.client.post(self.upstream_url, json=item)
                responses.append(resp.json())
            except Exception as e:
                logger.error(f"[SIGUI GUARD] Upstream forwarding error: {e}")
                responses.append({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32603, "message": f"Upstream RPC error: {str(e)}"},
                })

        return JSONResponse(content=responses if is_batch else responses[0])

    async def handle_aptos_transactions(self, request: Request):
        """
        Intercepts Aptos REST API transaction submissions (/v1/transactions).
        """
        try:
            body_bytes = await request.body()
            payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            
            # Inspect payload arguments for recipient
            func_payload = payload.get("payload", {})
            arguments = func_payload.get("arguments", [])
            function_name = func_payload.get("function", "")

            target_addr = None
            if arguments and isinstance(arguments[0], str) and arguments[0].startswith("0x"):
                target_addr = arguments[0]

            if target_addr:
                logger.info(f"[SIGUI GUARD] 🛡️ Intercepted Aptos transaction -> Function: {function_name} -> Destination: {target_addr}")
                verdict = await self.audit_destination(target_addr)

                if verdict.get("decision") == "BLOCK":
                    logger.warning(f"[SIGUI GUARD] 🚨 BLOCKED Aptos transaction to {target_addr}! Pattern: {verdict['pattern']}")
                    return JSONResponse(
                        status_code=403,
                        content={
                            "message": f"Transaction blocked by Sigui Guard: {verdict['pattern']} threat detected",
                            "error_code": "SIGUI_SECURITY_BLOCK",
                            "sigui_verdict": verdict,
                        },
                    )

            # Forward to upstream Aptos node
            resp = await self.client.post(
                f"{self.upstream_url}/v1/transactions",
                content=body_bytes,
                headers={"Content-Type": "application/json"},
            )
            return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

        except Exception as e:
            logger.error(f"[SIGUI GUARD] Aptos proxy error: {e}")
            return JSONResponse(status_code=500, content={"error": str(e)})

    async def handle_fallback_proxy(self, request: Request, path: str):
        """
        Transparently forwards all other REST/RPC methods to upstream.
        """
        url = f"{self.upstream_url}/{path}"
        body = await request.body()
        try:
            resp = await self.client.request(
                method=request.method,
                url=url,
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

def create_guard_app(upstream_url: str = "https://rpc.ankr.com/eth", network: str = "ethereum") -> FastAPI:
    proxy = SiguiGuardProxy(upstream_url=upstream_url, network=network)
    return proxy.app


def main():
    parser = argparse.ArgumentParser(description="Sigui Guard — Zero-Code RPC Security Proxy for AI Agents")
    parser.add_argument("--port", type=int, default=8545, help="Port to listen on (default: 8545)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--upstream", type=str, default="https://rpc.ankr.com/eth", help="Upstream RPC URL")
    parser.add_argument("--network", type=str, default="ethereum", choices=["ethereum", "aptos", "starknet", "sepolia"], help="Blockchain network")
    parser.add_argument("--fail-open", action="store_true", help="Bypass block on oracle failure (default: fail-closed)")
    args = parser.parse_args()

    import uvicorn

    print("=" * 65)
    print("  🛡️  SIGUI GUARD — Zero-Code AI Agent RPC Security Proxy")
    print("=" * 65)
    print(f"  • Local Endpoint : http://{args.host}:{args.port}")
    print(f"  • Upstream Node  : {args.upstream}")
    print(f"  • Network        : {args.network}")
    print(f"  • Fail-Closed    : {not args.fail_open}")
    print("=" * 65)
    print("  Ready! Direct your agent's RPC_URL to this local endpoint.")
    print("  Transactions will be pre-audited in <30ms before on-chain dispatch.\n")

    guard = SiguiGuardProxy(
        upstream_url=args.upstream,
        network=args.network,
        fail_closed=not args.fail_open,
    )
    uvicorn.run(guard.app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
