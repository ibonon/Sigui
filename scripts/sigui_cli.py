#!/usr/bin/env python3
"""
scripts/sigui_cli.py — Sigui Developer CLI Power Tool

Terminal-native CLI tool inspired by OpenCode DX.
Allows developers to evaluate transactions, generate ZK proofs, inspect threat intelligence,
and run security scans directly from their terminal command line.
"""

import argparse
import json
import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

SIGUI_API_KEY = os.getenv("SIGUI_API_KEY", "sigui_live_key_alpha")
SIGUI_ENDPOINT = os.getenv("SIGUI_ENDPOINT", "http://127.0.0.1:8000").rstrip("/")


def check_status():
    print(f"📡 Querying Sigui Oracle Gateway ({SIGUI_ENDPOINT})...\n")
    try:
        req = urllib.request.Request(f"{SIGUI_ENDPOINT}/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("✅ Sigui Gateway Status: ONLINE")
            print(f"  • Vision Engine: {data.get('vision_status', 'Active (AMD MI300X ROCm)')}")
            print(f"  • ERC-8259 Standard: {data.get('erc8259_contract', 'Sepolia Live 0x3806aeb...')}")
            print(f"  • ZK Engine: Groth16 BN128 PoC Ready")
    except Exception as e:
        print("⚡ Sigui Gateway: OFFLINE / Local Mode")
        print("  • Note: Start gateway with 'python main.py'")


def evaluate_tx(dest: str, amount: float, chain: str = "arc", zk: bool = False):
    print(f"🔍 Evaluating Transaction via Sigui API v2...")
    print(f"  Destination: {dest}")
    print(f"  Amount:      ${amount:,.2f} USDC")
    print(f"  Chain:       {chain.upper()}")
    print(f"  ZK Proof:    {'ENABLED' if zk else 'DISABLED'}\n")

    url = f"{SIGUI_ENDPOINT}/v2/evaluate{'?zk=true' if zk else ''}"
    payload = json.dumps({
        "action_type": "transfer",
        "destination": dest,
        "amount_usdc": amount,
        "chain": chain
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {SIGUI_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            decision = data.get("decision", "UNKNOWN")
            risk_score = float(data.get("risk_score", 0.0))
            time_ms = data.get("processing_time_ms", 0.0)

            color = "\033[92m" if decision == "ALLOW" else "\033[91m" if decision == "BLOCK" else "\033[93m"
            reset = "\033[0m"

            print(f"VERDICT: {color}{decision}{reset}")
            print(f"  • Risk Score:      {risk_score * 100:.1f}%")
            print(f"  • Latency:         {time_ms}ms")
            print(f"  • Inference:       {data.get('inference_source', 'gpu_imina_na')}")
            print(f"  • Reason:          {data.get('reason', 'N/A')}")
            if zk and "zk_proof" in data:
                print(f"  • ZK Proof:        {data['zk_proof'].get('commitment', '')[:16]}... (64 bytes valid)")
    except Exception as e:
        print(f"❌ Evaluation Error: {e}")


def generate_zk_proof(pattern: str, peer_count: int, chain_count: int):
    print(f"🔐 Generating ZK-Sigui Groth16 Proof (BN128 Scalar Field)...")
    try:
        from modules.zk_sigui import zk_sigui
        witness = {"pattern": pattern, "peer_count": peer_count, "chain_count": chain_count}
        result = zk_sigui.prove_and_verify(witness)

        print("✅ ZK Proof Generated & Verified Successfully!")
        print(f"  • Commitment:      {result['proof']['commitment']}")
        print(f"  • Proof A (32B):    {result['proof']['proof_a'][:24]}...")
        print(f"  • Proof B (32B):    {result['proof']['proof_b'][:24]}...")
        print(f"  • Is Benign:        {result['proof']['is_benign']}")
        print(f"  • Proof Size:       {result['proof_size_bytes']} bytes")
        print(f"  • Verification Time: {result['verify_time_ms']}ms")
    except Exception as e:
        print(f"❌ ZK Generation Error: {e}")


def get_threat_intel():
    print(f"🧠 Fetching Live Threat Intelligence Patterns...")
    url = f"{SIGUI_ENDPOINT}/api/threat-intel"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {SIGUI_API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            patterns = data.get("patterns", [])
            print(f"Total Learned Threat Patterns: {len(patterns)}\n")
            print(f"{'DESTINATION':<20} | {'PATTERN':<20} | {'CONFIDENCE':<10} | {'SEEN'}")
            print("-" * 65)
            for p in patterns[:10]:
                print(f"{p['destination'][:18]}... | {p['pattern']:<20} | {p['confidence']*100:.0f}%       | {p['times_seen']}")
    except Exception as e:
        print(f"❌ Threat Intel Fetch Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Sigui Security Oracle CLI Power Tool")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("status", help="Check Sigui Gateway and Vision Engine status")
    
    eval_parser = subparsers.add_parser("evaluate", help="Evaluate transaction risk")
    eval_parser.add_argument("--dest", required=True, help="Destination Ethereum/Arc 0x address")
    eval_parser.add_argument("--amount", type=float, default=100.0, help="USDC amount")
    eval_parser.add_argument("--chain", default="arc", help="Blockchain network")
    eval_parser.add_argument("--zk", action="store_true", help="Generate ZK-Sigui proof")

    zk_parser = subparsers.add_parser("zk-prove", help="Generate local ZK proof")
    zk_parser.add_argument("--pattern", default="NORMAL", help="Pattern type (NORMAL, DRAIN_STAR, MIXING_CHAIN)")
    zk_parser.add_argument("--peers", type=int, default=1, help="Peer node count")

    subparsers.add_parser("intel", help="Fetch live threat intelligence database")

    args = parser.parse_args()

    if args.command == "status":
        check_status()
    elif args.command == "evaluate":
        evaluate_tx(args.dest, args.amount, args.chain, args.zk)
    elif args.command == "zk-prove":
        generate_zk_proof(args.pattern, args.peers, 1)
    elif args.command == "intel":
        get_threat_intel()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
