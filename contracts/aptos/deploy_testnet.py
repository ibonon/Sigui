#!/usr/bin/env python3
"""
deploy_aptos_testnet.py — Sigui Protocol Aptos Testnet Deployment Script
Deploys agent_reputation and threat_registry modules to Aptos Testnet.
"""

import subprocess
import json
import sys
import time

NETWORK   = "testnet"
PROFILE   = "sigui_deployer"
CONTRACTS_DIR = "contracts/aptos"

def run(cmd, capture=True, check=True):
    print(f"\n$ {cmd}")
    result = subprocess.run(
        cmd, shell=True, capture_output=capture, text=True
    )
    if capture:
        if result.stdout: print(result.stdout)
        if result.stderr: print(result.stderr, file=sys.stderr)
    if check and result.returncode != 0:
        print(f"\n❌ Command failed (exit {result.returncode})")
        sys.exit(1)
    return result

def main():
    print("=" * 60)
    print("  Sigui Protocol — Aptos Testnet Deployment")
    print("=" * 60)

    # ── Step 1: Check profile exists ──────────────────────────────
    print("\n[1/5] Checking Aptos profile...")
    r = run(f"aptos config show-profiles --profile {PROFILE} 2>&1", check=False)
    if "Error" in (r.stdout or "") or r.returncode != 0:
        print(f"\n⚠️  Profile '{PROFILE}' not found. Creating it now...")
        print("   This will generate a new testnet account for you.")
        run(
            f"aptos init --profile {PROFILE} --network {NETWORK} --assume-yes",
            capture=False,
            check=True
        )
    else:
        print(f"✅ Profile '{PROFILE}' found.")

    # ── Step 2: Get account address ───────────────────────────────
    print("\n[2/5] Getting deployer account address...")
    r = run(f"aptos account list --profile {PROFILE} 2>&1", check=False)
    time.sleep(1)

    # Get address from config
    r2 = run("aptos config show-profiles 2>&1", check=False)
    print(r2.stdout)

    # ── Step 3: Fund account via faucet ───────────────────────────
    print("\n[3/5] Funding account via Aptos Testnet faucet...")
    r = run(
        f"aptos account fund-with-faucet --profile {PROFILE} --amount 200000000 2>&1",
        check=False
    )
    if "Error" in (r.stdout or ""):
        print("⚠️  Faucet funding failed — account may already have funds. Continuing...")
    else:
        print("✅ Account funded with 2 APT (testnet)")

    # ── Step 4: Compile contracts ─────────────────────────────────
    print("\n[4/5] Compiling Move contracts...")
    run(
        f"aptos move compile --package-dir {CONTRACTS_DIR} --named-addresses sigui=default 2>&1",
        capture=False
    )
    print("✅ Contracts compiled successfully.")

    # ── Step 5: Publish modules ───────────────────────────────────
    print("\n[5/5] Publishing modules to Aptos Testnet...")
    r = run(
        f"aptos move publish "
        f"--package-dir {CONTRACTS_DIR} "
        f"--profile {PROFILE} "
        f"--named-addresses sigui=default "
        f"--assume-yes 2>&1",
        check=False
    )

    if "Transaction submitted" in (r.stdout or "") or "Success" in (r.stdout or ""):
        print("\n" + "=" * 60)
        print("✅ DEPLOYMENT SUCCESSFUL!")
        print("=" * 60)
        # Extract tx hash if present
        for line in (r.stdout or "").splitlines():
            if "hash" in line.lower() or "0x" in line:
                print(f"   {line.strip()}")
    else:
        print("\n" + "=" * 60)
        print("⚠️  Deployment output:")
        print(r.stdout)
        print(r.stderr)
        print("\nCheck the output above for the transaction hash.")
        print("If you see a transaction hash, the deployment succeeded!")

    print("\n📍 View your contracts on Aptos Explorer:")
    print("   https://explorer.aptoslabs.com/?network=testnet")
    print("\n📍 Search for your address to see deployed modules.")

if __name__ == "__main__":
    main()
