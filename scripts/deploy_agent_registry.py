#!/usr/bin/env python3
"""
Sigui v3.0 — ERC-8259 AgentIdentityRegistry Deployment Script
Compiles AgentIdentityRegistry.vy with Vyper and deploys to Sepolia testnet.

Usage:
    python scripts/deploy_agent_registry.py

Requirements:
    - vyper >= 0.3.10 (pip install vyper)
    - SEPOLIA_PRIVATE_KEY in .env
    - SEPOLIA_RPC_URL in .env (e.g. https://eth-sepolia.g.alchemy.com/v2/YOUR_API_KEY)
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONTRACT_FILE = ROOT / "contracts" / "ethereum" / "AgentIdentityRegistry.vy"
ABI_OUT = ROOT / "contracts" / "ethereum" / "AgentIdentityRegistry.abi.json"
ENV_FILE = ROOT / ".env"


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()
    return env

def patch_env(key: str, value: str) -> None:
    content = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f"{key}={value}", content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"{key}={value}\n"
    ENV_FILE.write_text(content, encoding="utf-8")


# ── Compilation ────────────────────────────────────────────────────────────────

def compile_contract() -> tuple[str, list]:
    print(f"\n[Compiling] {CONTRACT_FILE.name}...")
    abi_proc = subprocess.run(["vyper", "-f", "abi", str(CONTRACT_FILE)], capture_output=True, text=True)
    if abi_proc.returncode != 0:
        print(f"[Error] ABI compilation error:\n{abi_proc.stderr}")
        sys.exit(1)
    abi = json.loads(abi_proc.stdout)

    bc_proc = subprocess.run(["vyper", "-f", "bytecode", str(CONTRACT_FILE)], capture_output=True, text=True)
    if bc_proc.returncode != 0:
        print(f"[Error] Bytecode compilation error:\n{bc_proc.stderr}")
        sys.exit(1)
    bytecode = bc_proc.stdout.strip()
    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode.lstrip()

    print(f"  [OK] Compiled: {(len(bytecode) - 2) // 2:,} bytes - {len(abi)} ABI entries")
    return bytecode, abi


# ── Deployment ─────────────────────────────────────────────────────────────────

def deploy(bytecode: str, abi: list, env: dict[str, str]) -> str:
    try:
        from eth_account import Account
        from web3 import Web3
    except ImportError:
        print("[Error] web3 or eth_account not installed (pip install web3)")
        sys.exit(1)

    rpc_url = env.get("SEPOLIA_RPC_URL", "")
    private_key = env.get("SEPOLIA_PRIVATE_KEY", "")
    chain_id = 11155111 # Sepolia
    explorer = "https://sepolia.etherscan.io"

    if not rpc_url or not private_key:
        print("[Error] SEPOLIA_RPC_URL and SEPOLIA_PRIVATE_KEY must be set in .env")
        print("Get an RPC URL from Alchemy/Infura and some Sepolia ETH from a faucet.")
        sys.exit(1)

    print(f"\n[Connecting] Sepolia testnet...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("[Error] Cannot connect to Sepolia RPC")
        sys.exit(1)

    account = Account.from_key(private_key)
    bal_wei = w3.eth.get_balance(account.address)
    bal_eth = float(w3.from_wei(bal_wei, "ether"))
    gas_price = w3.eth.gas_price
    gwei = float(w3.from_wei(gas_price, "gwei"))
    print(f"  Deployer:  {account.address}")
    print(f"  Balance:   {bal_eth:.4f} ETH")

    if bal_eth < 0.005:
        print("[Error] Balance too low - need Sepolia ETH for deployment gas.")
        sys.exit(1)

    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    # The AgentIdentityRegistry constructor might take arguments. Let's assume no args for now.
    # If it fails, you might need to pass `Contract.constructor(admin_address)` depending on the vyper code.
    try:
        gas_est = Contract.constructor().estimate_gas({"from": account.address})
        gas_limit = int(gas_est * 1.25)
    except Exception as exc:
        print(f"  [Warn] Gas estimation failed ({exc}) - using 3_000_000 default")
        gas_limit = 3_000_000

    print("\n[Deploying] AgentIdentityRegistry (ERC-8259)...")
    nonce = w3.eth.get_transaction_count(account.address, "latest")
    tx = Contract.constructor().build_transaction({
        "chainId": chain_id,
        "from": account.address,
        "nonce": nonce,
        "gas": gas_limit,
        "gasPrice": int(gas_price * 1.5),
    })

    signed = Account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = w3.to_hex(tx_hash)
    print(f"  Tx hash: {tx_hex}")
    print("  Waiting for confirmation (Sepolia takes ~15-30s)...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    if receipt.status != 1:
        print(f"[Error] Deployment reverted (status={receipt.status})")
        sys.exit(1)

    contract_address = receipt.contractAddress
    print(f"\n  [OK] Deployed at block #{receipt.blockNumber:,}")
    print(f"  Contract:  {contract_address}")
    print(f"  Etherscan: {explorer}/address/{contract_address}")
    return contract_address

def main() -> None:
    print("=" * 60)
    print("  Deploying ERC-8259 AgentIdentityRegistry to Sepolia")
    print("=" * 60)

    if not CONTRACT_FILE.exists():
        print(f"[Error] Source not found: {CONTRACT_FILE}")
        sys.exit(1)

    env = load_env()
    bytecode, abi = compile_contract()
    
    # Save ABI
    ABI_OUT.parent.mkdir(parents=True, exist_ok=True)
    ABI_OUT.write_text(json.dumps(abi, indent=2), encoding="utf-8")
    
    address = deploy(bytecode, abi, env)
    patch_env("ERC8259_REGISTRY_ADDRESS_SEPOLIA", address)
    print(f"\n  .env updated: ERC8259_REGISTRY_ADDRESS_SEPOLIA={address}")

if __name__ == "__main__":
    main()
