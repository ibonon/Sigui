#!/usr/bin/env python3
"""
Sigui v3.0 — ThreatRegistry Deployment Script
Compiles ThreatRegistry.vy with Vyper and deploys to Arc testnet.

Usage:
    python scripts/deploy_contract.py

Requirements:
    - vyper >= 0.3.10 (pip install vyper)
    - ARC_SIGNER_PRIVATE_KEY in .env
    - ARC_RPC_URL in .env (default: https://rpc.testnet.arc.network)
    - Minimum ~0.05 USDC native for deployment gas
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONTRACT_FILE = ROOT / "contracts" / "ThreatRegistry.vy"
ABI_OUT = ROOT / "contracts" / "ThreatRegistry.abi.json"
ENV_FILE = ROOT / ".env"


# ── Helpers ────────────────────────────────────────────────────────────────────


def load_env() -> dict[str, str]:
    """Parse .env into a dict. Ignores comments and blank lines."""
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
    """Upsert a key=value line in .env."""
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


def ensure_vyper() -> None:
    """Install Vyper if not already present."""
    try:
        result = subprocess.run(
            ["vyper", "--version"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        print(f"  Vyper: {result.stdout.strip()}")
    except FileNotFoundError:
        print("  Vyper not found - installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "vyper>=0.3.10,<0.5.0"],
            check=True,
            timeout=120,
        )
        print("  Vyper installed [OK]")


def compile_contract() -> tuple[str, list]:
    """Compile ThreatRegistry.vy -> (bytecode_hex, abi_list)."""
    print(f"\n[Compiling] {CONTRACT_FILE.name}...")

    # ABI
    abi_proc = subprocess.run(
        ["vyper", "-f", "abi", str(CONTRACT_FILE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if abi_proc.returncode != 0:
        print(f"[Error] ABI compilation error:\n{abi_proc.stderr}")
        sys.exit(1)
    abi = json.loads(abi_proc.stdout)

    # Bytecode
    bc_proc = subprocess.run(
        ["vyper", "-f", "bytecode", str(CONTRACT_FILE)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if bc_proc.returncode != 0:
        print(f"[Error] Bytecode compilation error:\n{bc_proc.stderr}")
        sys.exit(1)
    bytecode = bc_proc.stdout.strip()

    # Remove trailing whitespace/newlines Vyper sometimes adds
    if not bytecode.startswith("0x"):
        bytecode = "0x" + bytecode.lstrip()

    size_bytes = (len(bytecode) - 2) // 2
    print(f"  [OK] Compiled: {size_bytes:,} bytes - {len(abi)} ABI entries")
    return bytecode, abi


# ── Deployment ─────────────────────────────────────────────────────────────────


def deploy(bytecode: str, abi: list, env: dict[str, str]) -> str:
    """Deploy to Arc testnet. Returns the deployed contract address."""
    try:
        from eth_account import Account
        from web3 import Web3
    except ImportError:
        print("[Error] web3 or eth_account not installed")
        sys.exit(1)

    rpc_url = env.get("ARC_RPC_URL", "https://rpc.testnet.arc.network")
    private_key = env.get("ARC_SIGNER_PRIVATE_KEY", "")
    chain_id = int(env.get("ARC_CHAIN_ID", "5042002"))
    explorer = env.get("ARC_EXPLORER_URL", "https://testnet.arcscan.app")

    if not private_key:
        print("[Error] ARC_SIGNER_PRIVATE_KEY is not set in .env")
        sys.exit(1)

    print(f"\n[Connecting] Arc testnet: {rpc_url}")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print("[Error] Cannot connect to Arc RPC")
        sys.exit(1)

    block = w3.eth.block_number
    print(f"  [OK] Connected - latest block #{block:,}")

    account = Account.from_key(private_key)
    bal_wei = w3.eth.get_balance(account.address)
    bal_usdc = float(w3.from_wei(bal_wei, "ether"))
    gas_price = w3.eth.gas_price
    gwei = float(w3.from_wei(gas_price, "gwei"))
    print(f"  Deployer:  {account.address}")
    print(f"  Balance:   {bal_usdc:.4f} USDC native")
    print(f"  Gas price: {gwei:.2f} Gwei")

    if bal_usdc < 0.005:
        print("[Error] Balance too low - need at least 0.005 USDC for deployment gas")
        print(f"   Fund {account.address} at https://faucet.circle.com")
        sys.exit(1)

    # Build constructor transaction
    Contract = w3.eth.contract(abi=abi, bytecode=bytecode)
    try:
        gas_est = Contract.constructor().estimate_gas({"from": account.address})
        gas_limit = int(gas_est * 1.25)  # 25% safety buffer
    except Exception as exc:
        print(f"  [Warn] Gas estimation failed ({exc}) - using 1_500_000 default")
        gas_limit = 1_500_000

    deploy_cost = float(w3.from_wei(gas_limit * gas_price, "ether"))
    print(f"  Est. gas:  {gas_limit:,} @ {gwei:.2f} Gwei ~ {deploy_cost:.6f} USDC")

    print("\n[Deploying] ThreatRegistry...")
    nonce = w3.eth.get_transaction_count(account.address, "pending")
    tx = Contract.constructor().build_transaction(
        {
            "chainId": chain_id,
            "from": account.address,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": int(gas_price),
        }
    )

    signed = Account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    tx_hex = w3.to_hex(tx_hash)
    print(f"  Tx hash: {tx_hex}")
    print("  Waiting for confirmation...")

    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=90)

    if receipt.status != 1:
        print(f"[Error] Deployment reverted (status={receipt.status})")
        print(f"   Tx: {explorer}/tx/{tx_hex}")
        sys.exit(1)

    contract_address = receipt.contractAddress
    print(f"\n  [OK] Deployed at block #{receipt.blockNumber:,}")
    print(f"  Contract:  {contract_address}")
    print(f"  ArcScan:   {explorer}/address/{contract_address}")
    print(f"  Tx:        {explorer}/tx/{tx_hex}")

    # Quick sanity check: call getStats()
    try:
        deployed = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )
        stats = deployed.functions.getStats().call()
        total = stats[0]
        usdc6 = stats[1]
        print(f"  Sanity check: getStats() = ({total}, {usdc6}) [OK]")
    except Exception as exc:
        print(f"  [Warn] getStats() sanity check failed: {exc}")

    return contract_address


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> None:
    print()
    print("=" * 58)
    print("  Sigui - ThreatRegistry Deployment")
    print("=" * 58)

    if not CONTRACT_FILE.exists():
        print(f"[Error] Contract source not found: {CONTRACT_FILE}")
        sys.exit(1)

    env = load_env()

    # Warn if already deployed
    existing = env.get("THREAT_REGISTRY_ADDRESS", "")
    if existing and existing not in ("", "0x0", "none", "None"):
        print(f"\n[Warn] Contract already deployed at: {existing}")
        ans = input("   Redeploy and overwrite? [y/N]: ").strip().lower()
        if ans != "y":
            print("   Keeping existing deployment.")
            return

    # Step 1 - Ensure Vyper
    ensure_vyper()

    # Step 2 - Compile
    bytecode, abi = compile_contract()

    # Step 3 - Save ABI
    ABI_OUT.parent.mkdir(parents=True, exist_ok=True)
    ABI_OUT.write_text(json.dumps(abi, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ABI saved: {ABI_OUT}")

    # Step 4 - Deploy
    address = deploy(bytecode, abi, env)

    # Step 5 - Persist address in .env
    patch_env("THREAT_REGISTRY_ADDRESS", address)
    print(f"\n  .env updated: THREAT_REGISTRY_ADDRESS={address}")

    print()
    print("=" * 58)
    print("  Deployment complete!")
    print()
    print("  Next steps:")
    print("  1. Restart Sigui: uvicorn main:app --reload --port 8000")
    print("  2. Deploy agents:  POST /simulate")
    print("  3. Watch attacks appear in:")
    explorer = env.get("ARC_EXPLORER_URL", "https://testnet.arcscan.app")
    print(f"     {explorer}/address/{address}")
    print("=" * 58)
    print()


if __name__ == "__main__":
    main()
