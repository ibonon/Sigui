"""
Sigui v2.0 — Deploy Hogonat.vy to Arc L1 Testnet

Usage:
    python scripts/deploy_hogonat.py

Prerequisites:
    - ARC_SIGNER_PRIVATE_KEY set in .env
    - ARC_RPC_URL pointing to Arc testnet
    - HOGONAT_USDC_TOKEN_ADDRESS set to the USDC contract on Arc
    - Signer wallet has enough native ARC for gas

After deployment:
    Copy the printed HOGONAT_CONTRACT_ADDRESS into your .env file
    and restart the backend to activate on-chain mode.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# ── Bootstrap path ────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from config import settings

try:
    from eth_account import Account
    from web3 import Web3
except ImportError:
    print("❌  web3.py not installed. Run: pip install web3")
    sys.exit(1)


# ── Paths ─────────────────────────────────────────────────────────────────────
ABI_PATH = ROOT / "contracts" / "Hogonat.abi.json"
BYTECODE_PATH = ROOT / "contracts" / "Hogonat.bytecode.txt"


def _load_bytecode() -> str:
    """Load pre-compiled bytecode from contracts/Hogonat.bytecode.txt."""
    if BYTECODE_PATH.exists():
        bytecode = BYTECODE_PATH.read_text().strip()
        if bytecode.startswith("0x"):
            return bytecode
        return "0x" + bytecode

    # If no bytecode file, try to compile with vyper CLI
    print("⚙️  No Hogonat.bytecode.txt found — attempting compilation with vyper...")
    try:
        import subprocess
        vy_path = ROOT / "contracts" / "Hogonat.vy"
        result = subprocess.run(
            ["vyper", "-f", "bytecode", str(vy_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        bytecode = result.stdout.strip()
        BYTECODE_PATH.write_text(bytecode)
        print(f"✅ Compiled Hogonat.vy → {BYTECODE_PATH}")
        return bytecode
    except FileNotFoundError:
        print("❌  vyper compiler not found. Install: pip install vyper==0.4.3")
        print("   Or compile manually and place the output in contracts/Hogonat.bytecode.txt")
        sys.exit(1)


def _write_env_update(contract_address: str):
    """Update .env with the deployed contract address."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        print(f"\n⚠️  .env file not found. Create it and add:")
        print(f"   HOGONAT_CONTRACT_ADDRESS={contract_address}")
        return

    lines = env_path.read_text().splitlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("HOGONAT_CONTRACT_ADDRESS="):
            new_lines.append(f"HOGONAT_CONTRACT_ADDRESS={contract_address}")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"\nHOGONAT_CONTRACT_ADDRESS={contract_address}")

    env_path.write_text("\n".join(new_lines) + "\n")
    print(f"\n✅ .env updated with HOGONAT_CONTRACT_ADDRESS={contract_address}")


def deploy():
    # ── Validate config ───────────────────────────────────────────────────────
    if not settings.arc_signer_private_key:
        print("❌  ARC_SIGNER_PRIVATE_KEY is not set in .env")
        sys.exit(1)

    usdc_address = settings.hogonat_usdc_token_address
    if not usdc_address or usdc_address == "0x0000000000000000000000000000000000000000":
        print("⚠️  HOGONAT_USDC_TOKEN_ADDRESS not set — using zero address (testing only)")
        usdc_address = "0x0000000000000000000000000000000000000000"

    # ── Connect to Arc ────────────────────────────────────────────────────────
    print(f"\n🔗 Connecting to Arc RPC: {settings.arc_rpc_url}")
    w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url))
    if not w3.is_connected():
        print(f"❌  Cannot connect to Arc RPC: {settings.arc_rpc_url}")
        sys.exit(1)

    signer = Account.from_key(settings.arc_signer_private_key)
    signer_addr = signer.address
    balance = w3.eth.get_balance(signer_addr)
    print(f"✅ Connected — chain_id={w3.eth.chain_id}")
    print(f"   Signer: {signer_addr}")
    print(f"   Balance: {w3.from_wei(balance, 'ether')} ARC")

    if balance == 0:
        print("❌  Signer wallet has no ARC for gas. Fund it first.")
        sys.exit(1)

    # ── Load contract artifacts ───────────────────────────────────────────────
    abi = json.loads(ABI_PATH.read_text())
    bytecode = _load_bytecode()

    print(f"\n📦 Deploying Hogonat.vy...")
    print(f"   USDC address: {usdc_address}")

    # ── Build deployment transaction ──────────────────────────────────────────
    contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    nonce = w3.eth.get_transaction_count(signer_addr, "pending")
    gas_price = int(w3.eth.gas_price * 1.15)

    constructor_fn = contract.constructor(Web3.to_checksum_address(usdc_address))

    try:
        gas_estimate = constructor_fn.estimate_gas({"from": signer_addr})
    except Exception as e:
        print(f"⚠️  Gas estimation failed: {e} — using 3_000_000 as default")
        gas_estimate = 3_000_000

    tx = constructor_fn.build_transaction(
        {
            "chainId": settings.arc_chain_id,
            "from": signer_addr,
            "nonce": nonce,
            "gas": int(gas_estimate * 1.3),
            "gasPrice": gas_price,
        }
    )

    # ── Sign & send ───────────────────────────────────────────────────────────
    signed = Account.sign_transaction(tx, settings.arc_signer_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hash_hex = w3.to_hex(tx_hash)
    print(f"   Tx sent: {tx_hash_hex}")
    print(f"   Explorer: {settings.arc_explorer_url}/tx/{tx_hash_hex}")
    print("   ⏳ Waiting for confirmation...")

    # ── Wait for receipt ──────────────────────────────────────────────────────
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

    if receipt.get("status") != 1:
        print(f"❌  Deployment failed! Receipt: {dict(receipt)}")
        sys.exit(1)

    contract_address = receipt["contractAddress"]
    print(f"\n✅ Hogonat deployed at: {contract_address}")
    print(f"   Block: {receipt['blockNumber']}")
    print(f"   Gas used: {receipt['gasUsed']}")
    print(f"   Explorer: {settings.arc_explorer_url}/address/{contract_address}")

    # ── Save to contracts/ and update .env ────────────────────────────────────
    deploy_info = {
        "contract_address": contract_address,
        "tx_hash": tx_hash_hex,
        "block": receipt["blockNumber"],
        "deployer": signer_addr,
        "usdc_token": usdc_address,
        "chain_id": settings.arc_chain_id,
    }
    deploy_path = ROOT / "contracts" / "Hogonat.deployed.json"
    deploy_path.write_text(json.dumps(deploy_info, indent=2))
    print(f"\n📄 Deployment info saved: {deploy_path}")

    _write_env_update(contract_address)

    print("\n" + "=" * 60)
    print("  🎉  Hogonat DAO is now deployed!")
    print(f"  Contract: {contract_address}")
    print("  Restart the backend to activate on-chain mode.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    deploy()
