"""
tests/test_sigui_guard.py — Test Suite for Multichain Zero-Code RPC Security Proxy (Sigui Guard v3.2)
"""

import asyncio
import base64
import pytest
from httpx import AsyncClient, ASGITransport
import rlp

from modules.sigui_guard import (
    SiguiGuardProxy,
    decode_raw_evm_tx,
    extract_erc20_recipient,
    decode_starknet_invoke,
    ERC20_TRANSFER_SIG,
    _to_hex_address,
)
from modules.security_engine import add_to_blacklist, _blacklist


# ─────────────────────────────────────────────────────────────────────────────
# Unit Tests: Decoders
# ─────────────────────────────────────────────────────────────────────────────

def test_extract_erc20_recipient():
    """ERC-20 transfer calldata correctly extracts recipient address."""
    target_addr = "3806aeb76edd2e22d3cf66a163113c4b24243b29"
    padded_addr = bytes.fromhex(target_addr.zfill(64))
    amount_hex = (500 * 10**6).to_bytes(32, byteorder="big")
    calldata = ERC20_TRANSFER_SIG + padded_addr + amount_hex

    recipient = extract_erc20_recipient(calldata)
    assert recipient is not None
    assert recipient.lower() == "0x3806aeb76edd2e22d3cf66a163113c4b24243b29"


def test_decode_raw_evm_tx_legacy():
    """Legacy EVM raw transaction decodes destination and value correctly."""
    to_bytes = bytes.fromhex("742d35cc6634c0532925a3b844bc454e4438f44e")
    mock_rlp = rlp.encode([
        b'\x00',          # nonce (as bytes, not int)
        b'\x04\xa8\x17\xc8\x00',  # gasPrice = 20 gwei
        b'\x52\x08',      # gasLimit = 21000
        to_bytes,
        b'\x0d\xe0\xb6\xb3\xa7\x64\x00\x00',  # value = 1 ETH
        b'',              # data
        b'\x1b', b'', b''  # v, r, s
    ])
    hex_str = "0x" + mock_rlp.hex()
    dest, val, recip = decode_raw_evm_tx(hex_str)
    assert dest is not None
    assert dest.lower() == "0x742d35cc6634c0532925a3b844bc454e4438f44e"
    assert recip is None


def test_decode_raw_evm_tx_eip1559_with_erc20():
    """EIP-1559 raw transaction with ERC-20 transfer decodes both contract and token recipient."""
    usdc_contract = bytes.fromhex("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    recipient_bytes = bytes.fromhex("3806aeb76edd2e22d3cf66a163113c4b24243b29")

    # Build proper ERC-20 calldata: selector + padded_to (32 bytes) + amount (32 bytes)
    padded_to = b'\x00' * 12 + recipient_bytes  # 32 bytes total
    amount = (100 * 10**6).to_bytes(32, byteorder="big")
    calldata = ERC20_TRANSFER_SIG + padded_to + amount

    # EIP-1559: [chain_id, nonce, max_priority_fee, max_fee, gas_limit, to, value, data, access_list, y, r, s]
    rlp_inner = rlp.encode([
        b'\x01',                    # chain_id = 1
        b'\x05',                    # nonce = 5
        b'\x3b\x9a\xca\x00',        # max_priority_fee = 1 gwei
        b'\x06\xfc\x23\xac\x00',    # max_fee = 30 gwei
        b'\xfd\xe8',                # gas_limit = 65000
        usdc_contract,
        b'',                        # value = 0
        calldata,
        [],                         # access_list
        b'',                        # y_parity
        b'',                        # r
        b'',                        # s
    ])
    raw_tx_bytes = b"\x02" + rlp_inner
    hex_str = "0x" + raw_tx_bytes.hex()

    dest, val, recip = decode_raw_evm_tx(hex_str)
    assert dest is not None
    assert dest.lower() == "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
    assert recip is not None
    assert recip.lower() == "0x3806aeb76edd2e22d3cf66a163113c4b24243b29"


def test_decode_starknet_invoke():
    """Starknet invoke transaction extracts calldata[1] as recipient."""
    params = [{
        "type": "INVOKE",
        "sender_address": "0xabc",
        "calldata": ["0x1", "0xdeadbeef1234567890abcdef", "0x2", "0x0"],
    }]
    result = decode_starknet_invoke(params)
    assert result == "0xdeadbeef1234567890abcdef"


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests: Multichain Interceptor
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_guard_blocks_blacklisted_destination_evm():
    """eth_sendTransaction to blacklisted contract is blocked with JSON-RPC -32003."""
    guard = SiguiGuardProxy(fail_closed=True)
    drain_contract = "0xdeadbeef00000000000000000000000000000001"
    add_to_blacklist(drain_contract)

    rpc_payload = {
        "jsonrpc": "2.0", "id": 42,
        "method": "eth_sendTransaction",
        "params": [{"from": "0x1111111111111111111111111111111111111111", "to": drain_contract, "value": "0xde0b6b3a7640000"}]
    }

    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/ethereum", json=rpc_payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32003
        assert data["error"]["data"]["sigui_verdict"] == "BLOCK"


@pytest.mark.asyncio
async def test_guard_blocks_blacklisted_erc20_recipient_raw_tx():
    """eth_sendRawTransaction with blacklisted ERC-20 recipient is blocked."""
    guard = SiguiGuardProxy(fail_closed=True)
    drain_recipient = "0xdeadbeefc001cafe000000000000000000000099"
    add_to_blacklist(drain_recipient)

    token_contract = bytes.fromhex("a0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
    padded_to = b'\x00' * 12 + bytes.fromhex(drain_recipient[2:])
    calldata = ERC20_TRANSFER_SIG + padded_to + (500 * 10**6).to_bytes(32, byteorder="big")

    mock_rlp = rlp.encode([
        b'\x00', b'\x04\xa8\x17\xc8\x00', b'\xea\x60',
        token_contract, b'', calldata, b'\x1b', b'', b''
    ])
    raw_tx_hex = "0x" + mock_rlp.hex()

    rpc_payload = {"jsonrpc": "2.0", "id": 99, "method": "eth_sendRawTransaction", "params": [raw_tx_hex]}

    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/ethereum", json=rpc_payload)
        data = resp.json()
        assert "error" in data
        assert data["error"]["code"] == -32003


@pytest.mark.asyncio
async def test_guard_aptos_blocks_threat_destination():
    """Aptos /v1/aptos/transactions to blacklisted address returns HTTP 403."""
    guard = SiguiGuardProxy(fail_closed=True)
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
        resp = await client.post("/v1/aptos/transactions", json=aptos_payload)
        assert resp.status_code == 403
        data = resp.json()
        assert data["error_code"] == "SIGUI_SECURITY_BLOCK"


@pytest.mark.asyncio
async def test_guard_starknet_blocks_blacklisted():
    """starknet_addInvokeTransaction to blacklisted recipient is blocked."""
    guard = SiguiGuardProxy(fail_closed=True)
    drain_stark = "0xdeadbeefcafe0000000000000000000000000000000000000000000000dead"
    add_to_blacklist(drain_stark)

    starknet_payload = {
        "jsonrpc": "2.0", "id": 1,
        "method": "starknet_addInvokeTransaction",
        "params": [{
            "type": "INVOKE",
            "sender_address": "0xabc",
            "calldata": ["0x1", drain_stark, "0x2", "0x100"],
        }]
    }

    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/v1/starknet", json=starknet_payload)
        data = resp.json()
        assert "error" in data
        # Starknet uses code 63 for reject
        assert data["error"]["code"] == 63
        assert data["error"]["data"]["sigui_verdict"] == "BLOCK"


@pytest.mark.asyncio
async def test_guard_health_and_status():
    """Health and status endpoints return expected multichain metadata."""
    guard = SiguiGuardProxy()
    transport = ASGITransport(app=guard.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
        assert resp.json()["mode"] == "multichain"

        resp2 = await client.get("/chains")
        data = resp2.json()
        assert "ethereum" in data["chains"]
        assert "solana" in data["chains"]
        assert "aptos" in data["chains"]
        assert "starknet" in data["chains"]
        assert "arbitrum" in data["chains"]
