"""
tests/test_sigui_guard.py — Test Suite for Zero-Code RPC Security Proxy (Sigui Guard)
"""

import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
import rlp

from modules.sigui_guard import (
    SiguiGuardProxy,
    decode_raw_evm_tx,
    extract_erc20_recipient,
    ERC20_TRANSFER_SIG,
    _to_hex_address,
)
from modules.security_engine import add_to_blacklist, _blacklist


# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests: Decoders & Calldata
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_erc20_recipient():
    # ERC-20 transfer(0x3806aeb76eDD2E22D3cF66A163113c4b24243b29, 500000000)
    target_addr = "3806aeb76edd2e22d3cf66a163113c4b24243b29"
    padded_addr = bytes.fromhex(target_addr.zfill(64))
    amount_hex = (500 * 10**6).to_bytes(32, byteorder="big")
    calldata = ERC20_TRANSFER_SIG + padded_addr + amount_hex

    recipient = extract_erc20_recipient(calldata)
    assert recipient is not None
    assert recipient.lower() == "0x3806aeb76edd2e22d3cf66a163113c4b24243b29"


def test_decode_raw_evm_tx_legacy():
    # Create valid mock legacy transaction payload: [nonce, gasprice, gaslimit, to, value, data, v, r, s]
    to_bytes = bytes.fromhex("742d35cc6634c0532925a3b844bc454e4438f44e")
    mock_rlp = rlp.encode([
        0,  # nonce
        20 * 10**9,  # gasPrice
        21000,  # gasLimit
        to_bytes,  # to
        10**18,  # value (1 ETH)
        b"",  # data
        27, 0, 0  # v, r, s
    ])
    hex_str = "0x" + mock_rlp.hex()

    dest, val, recip = decode_raw_evm_tx(hex_str)
    assert dest is not None
    assert dest.lower() == "0x742d35cc6634c0532925a3b844bc454e4438f44e"
    assert val == 1.0
    assert recip is None


def test_decode_raw_evm_tx_eip1559_with_erc20():
    # Create valid mock EIP-1559 payload: 0x02 || rlp([chain_id, nonce, max_prio, max_fee, gas_limit, to, value, data, access_list, y_parity, r, s])
    usdc_contract = bytes.fromhex("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    recipient_addr = bytes.fromhex("3806aeb76edd2e22d3cf66a163113c4b24243b29")
    
    # ERC20 transfer data
    calldata = ERC20_TRANSFER_SIG + bytes.fromhex(recipient_addr.hex().zfill(64)) + (100 * 10**6).to_bytes(32, byteorder="big")

    rlp_inner = rlp.encode([
        1,  # chain_id
        5,  # nonce
        10**9,  # max_priority_fee
        30 * 10**9,  # max_fee
        65000,  # gas_limit
        usdc_contract,  # to (USDC token contract)
        0,  # value
        calldata,  # data (ERC-20 transfer)
        [],  # access_list
        0, 0, 0  # sig
    ])
    raw_tx_bytes = b"\x02" + rlp_inner
    hex_str = "0x" + raw_tx_bytes.hex()

    dest, val, recip = decode_raw_evm_tx(hex_str)
    assert dest is not None
    assert dest.lower() == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert recip is not None
    assert recip.lower() == "0x3806aeb76edd2e22d3cf66a163113c4b24243b29"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: Interceptor & Blacklist Blocking
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guard_blocks_blacklisted_destination():
    # Setup guard proxy
    guard = SiguiGuardProxy(upstream_url="https://rpc.ankr.com/eth", network="ethereum", fail_closed=True)
    
    # Add target drain star to dynamic blacklist
    drain_contract = "0xdeadbeef00000000000000000000000000000001"
    add_to_blacklist(drain_contract)

    # Build transaction directly targeting the blacklisted address
    tx_dict = {
        "from": "0x1111111111111111111111111111111111111111",
        "to": drain_contract,
        "value": "0xde0b6b3a7640000",  # 1 ETH
    }
    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 42,
        "method": "eth_sendTransaction",
        "params": [tx_dict]
    }

    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/", json=rpc_payload)
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify JSON-RPC error interception with -32003
        assert "error" in data
        assert data["error"]["code"] == -32003
        assert "rejected by Sigui Guard" in data["error"]["message"]
        assert data["error"]["data"]["sigui_verdict"] == "BLOCK" or data["error"]["data"]["decision"] == "BLOCK"


@pytest.mark.asyncio
async def test_guard_blocks_blacklisted_erc20_recipient_raw_tx():
    guard = SiguiGuardProxy(upstream_url="https://rpc.ankr.com/eth", network="ethereum", fail_closed=True)
    
    drain_recipient = "0xdeadbeefc001cafe000000000000000000000099"
    add_to_blacklist(drain_recipient)

    # Transfer USDC to drain_recipient
    token_contract = bytes.fromhex("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    calldata = ERC20_TRANSFER_SIG + bytes.fromhex(drain_recipient[2:].zfill(64)) + (500 * 10**6).to_bytes(32, byteorder="big")

    mock_rlp = rlp.encode([
        0, 20 * 10**9, 60000,
        token_contract,
        0,
        calldata,
        27, 0, 0
    ])
    raw_tx_hex = "0x" + mock_rlp.hex()

    rpc_payload = {
        "jsonrpc": "2.0",
        "id": 99,
        "method": "eth_sendRawTransaction",
        "params": [raw_tx_hex]
    }

    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/", json=rpc_payload)
        assert resp.status_code == 200
        data = resp.json()

        # Intercepted!
        assert "error" in data
        assert data["error"]["code"] == -32003
        assert "DRAIN_STAR" in data["error"]["message"] or "rejected by Sigui Guard" in data["error"]["message"]


@pytest.mark.asyncio
async def test_guard_aptos_blocks_threat_destination():
    guard = SiguiGuardProxy(upstream_url="https://fullnode.testnet.aptoslabs.com", network="aptos", fail_closed=True)
    
    drain_aptos = "0x9999999999999999999999999999999999999999999999999999999999999999"
    add_to_blacklist(drain_aptos)

    aptos_payload = {
        "sender": "0x123",
        "payload": {
            "type": "entry_function_payload",
            "function": "0x1::aptos_account::transfer",
            "arguments": [drain_aptos, "5000000"]
        }
    }

    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/transactions", json=aptos_payload)
        # Blocked with 403 Forbidden
        assert resp.status_code == 403
        data = resp.json()
        assert data["error_code"] == "SIGUI_SECURITY_BLOCK"
        assert "DRAIN_STAR" in data["message"] or "blocked by Sigui Guard" in data["message"]


@pytest.mark.asyncio
async def test_guard_health_and_status():
    guard = SiguiGuardProxy(upstream_url="https://rpc.ankr.com/eth", network="ethereum")
    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

        resp2 = await client.get("/status")
        assert resp2.status_code == 200
        assert resp2.json()["mode"] == "Zero-Code RPC Interceptor"
