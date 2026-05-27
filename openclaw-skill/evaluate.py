#!/usr/bin/env python3
"""
sigui-security/evaluate.py — CLI helper for OpenClaw agents

This script evaluates the security of a blockchain transaction using the Sigui Protocol.
It returns an exit code indicating whether the transaction should be blocked, allowed, or escalated.

Usage:
    python evaluate.py --amount <usdc> --destination <address> \\
                       [--agent <agent_id>] [--action <type>] \\
                       [--chain arc|ethereum|starknet|aptos|solana] \\
                       [--escalate] [--json]

Exit codes:
    0 = ALLOW / ALLOW_WITH_CAP
    1 = BLOCK
    2 = ESCALATE (Deep analysis required)
    3 = Evaluation Error
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Dict, Any

# Optional: rich for beautiful console output
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None

# ── Try to import Sigui SDK ───────────────────────────────────────────────────
try:
    from sigui import SiguiClient
    from sigui.local import start_mock_server
    SIGUI_AVAILABLE = True
except ImportError:
    SIGUI_AVAILABLE = False


def _print_error(msg: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[bold red]❌ Error:[/bold red] {msg}")
    else:
        print(f"❌ Error: {msg}", file=sys.stderr)


def _print_warning(msg: str) -> None:
    if RICH_AVAILABLE:
        console.print(f"[bold yellow]⚠️  Warning:[/bold yellow] {msg}")
    else:
        print(f"⚠️  Warning: {msg}", file=sys.stderr)


def _mock_evaluate(agent_id: str, amount: float, destination: str,
                   action_type: str, chain: str) -> Dict[str, Any]:
    """Fallback mock evaluation when sigui-sdk is not installed or unreachable."""
    import hashlib
    # Heuristic mock logic
    risk = 0.05 if amount < 1000 else 0.45 if amount < 5000 else 0.85
    verdict = "ALLOW" if risk < 0.35 else ("ESCALATE" if risk < 0.80 else "BLOCK")
    h = hashlib.sha256(f"{agent_id}{destination}{amount}".encode()).hexdigest()
    
    return {
        "verdict": verdict,
        "risk_score": risk,
        "confidence": 0.91,
        "reason": ("Normal behavioral pattern" if verdict == "ALLOW" 
                   else "Unusual transaction pattern — deep review required" if verdict == "ESCALATE"
                   else "High probability of drain attack or mixer usage detected"),
        "action_hash": f"0x{h[:40]}",
        "arc_tx_log": f"0xSIM_{h[:16]}",
        "arcwarden_mode": "NORMAL",
        "synthetic_score": int((1.0 - risk) * 1000),
        "chain": chain,
        "onchain_proof": f"https://testnet.arcscan.app/tx/0xSIM_{h[:16]}",
        "mock": True,
    }


async def _run(args: argparse.Namespace) -> int:
    result_dict: Dict[str, Any] = {}
    verdict = "BLOCK"

    if not SIGUI_AVAILABLE:
        _print_warning("sigui-sdk is not installed. Falling back to heuristic mock evaluation.")
        _print_warning("To install: pip install sigui-sdk>=0.3.1")
        result_dict = _mock_evaluate(args.agent, args.amount, args.destination, args.action, args.chain)
        verdict = result_dict["verdict"]
    else:
        server = None
        api_url = args.api_url or os.environ.get("SIGUI_API_URL", "http://127.0.0.1:8765")

        # Auto-start mock server if using default local URL
        if api_url == "http://127.0.0.1:8765":
            try:
                server = start_mock_server(port=8765, host="127.0.0.1")
                if not args.json:
                    _print_warning("Local mock server started on port 8765")
            except Exception as e:
                _print_warning(f"Could not start mock server: {e}")

        client = SiguiClient(api_url=api_url)

        try:
            result = await client.evaluate(
                agent_id=args.agent,
                amount=args.amount,
                destination=args.destination,
                action_type=args.action,
                chain=args.chain,
            )
            
            verdict = result.verdict.value
            result_dict = {
                "verdict": verdict,
                "risk_score": result.risk_score,
                "confidence": result.confidence,
                "reason": result.reason,
                "action_hash": result.action_hash,
                "arc_tx_log": result.arc_tx_log,
                "arcwarden_mode": result.arcwarden_mode,
                "synthetic_score": result.synthetic_score,
                "chain": result.chain,
                "onchain_proof": result.onchain_proof,
                "mock": False,
            }

            # Deep escalation if requested
            if args.escalate and verdict == "ESCALATE":
                try:
                    if not args.json:
                        _print_warning("ESCALATE verdict received. Requesting deep analysis...")
                    
                    esc = await client.escalate(
                        agent_id=args.agent,
                        amount=args.amount,
                        destination=args.destination,
                        action_type=args.action,
                        original_verdict=result,
                    )
                    result_dict["escalation"] = {
                        "verdict": esc.verdict.value,
                        "analysis": esc.analysis,
                        "cap_amount_usdc": esc.cap_amount_usdc,
                        "inference_engine": esc.inference_engine,
                    }
                    verdict = esc.verdict.value
                except Exception as e:
                    _print_error(f"Deep escalation failed: {e}")

        except Exception as e:
            _print_error(f"Sigui API evaluation failed: {e}")
            if server:
                server.stop()
            return 3
        finally:
            if server:
                server.stop()

    # ── Output ──────────────────────────────────────────────────────────────
    if args.json:
        print(json.dumps(result_dict, indent=2, default=str))
    else:
        _pretty_print(result_dict, args)

    # Exit code maps to OpenClaw behavior
    if verdict == "BLOCK":
        return 1
    if verdict == "ESCALATE":
        return 2
    return 0


def _pretty_print(r: Dict[str, Any], args: argparse.Namespace) -> None:
    if not RICH_AVAILABLE:
        # Fallback to plain text
        print("\n--- SIGUI SECURITY EVALUATION ---")
        print(f"Verdict       : {r['verdict']}")
        print(f"Risk Score    : {r['risk_score']:.3f}")
        print(f"Safety Score  : {r['synthetic_score']}/1000")
        print(f"Confidence    : {r.get('confidence', 0):.1%}")
        print(f"Reason        : {r['reason']}")
        print(f"Chain         : {r.get('chain', 'arc')}")
        if r.get("onchain_proof"):
            print(f"Proof         : {r['onchain_proof']}")
        if r.get("escalation"):
            print("\n--- DEEP ANALYSIS ---")
            print(f"Deep Verdict  : {r['escalation']['verdict']}")
            print(f"Analysis      : {r['escalation']['analysis']}")
        print("---------------------------------\n")
        return

    # Rich formatted output
    verdict = r["verdict"]
    color = "green" if verdict in ["ALLOW", "ALLOW_WITH_CAP"] else "yellow" if verdict == "ESCALATE" else "red"
    icon = "✅" if verdict == "ALLOW" else "⚠️" if verdict == "ALLOW_WITH_CAP" else "🔍" if verdict == "ESCALATE" else "🚫"

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Field", style="bold cyan", justify="right")
    table.add_column("Value", style="white")

    table.add_row("Verdict", f"[{color} bold]{icon} {verdict}[/]")
    
    risk = r['risk_score']
    risk_color = "green" if risk < 0.35 else "yellow" if risk < 0.8 else "red"
    table.add_row("Risk Score", f"[{risk_color}]{risk:.3f}[/] (0=safe, 1=critical)")
    table.add_row("Safety Score", f"{r['synthetic_score']}/1000")
    table.add_row("Confidence", f"{r.get('confidence', 0):.1%}")
    table.add_row("Reason", f"[italic]{r['reason']}[/]")
    table.add_row("Chain", f"{r.get('chain', 'arc').upper()}")
    
    if r.get("onchain_proof"):
        table.add_row("Proof", f"[link={r['onchain_proof']}]{r['onchain_proof']}[/link]")

    if r.get("mock"):
        table.add_row("Engine", "[magenta]Local Heuristic Mock (No SDK)[/]")

    panel = Panel(
        table,
        title=f"[bold]Sigui Evaluation for {args.amount} USDC[/bold]",
        border_style=color,
        expand=False
    )
    console.print(panel)

    if r.get("escalation"):
        esc = r["escalation"]
        esc_color = "green" if esc["verdict"] in ["ALLOW", "ALLOW_WITH_CAP"] else "red"
        
        esc_table = Table(show_header=False, box=None, padding=(0, 2))
        esc_table.add_column("Field", style="bold magenta", justify="right")
        esc_table.add_column("Value", style="white")
        
        esc_table.add_row("Verdict", f"[{esc_color} bold]{esc['verdict']}[/]")
        esc_table.add_row("Spending Cap", f"${esc['cap_amount_usdc']:.2f} USDC")
        esc_table.add_row("Engine", f"{esc['inference_engine']}")
        esc_table.add_row("Analysis", f"{esc['analysis']}")

        esc_panel = Panel(
            esc_table,
            title="[bold magenta]🔍 Deep Analysis (Escalation)[/bold magenta]",
            border_style="magenta",
            expand=False
        )
        console.print(esc_panel)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sigui Protocol — AI Blockchain Security Oracle for Agents"
    )
    parser.add_argument("--amount",      required=True, type=float,
                        help="Transaction amount in USDC value")
    parser.add_argument("--destination", required=True,
                        help="Destination wallet, contract, or ENS address")
    parser.add_argument("--agent",       default=os.environ.get("OPENCLAW_AGENT_ID", "openclaw_default"),
                        help="Agent ID (default: OPENCLAW_AGENT_ID env var)")
    parser.add_argument("--action",      default="transfer",
                        choices=["transfer", "contract_call", "approve", "mint", "swap", "bridge"],
                        help="Type of action (default: transfer)")
    parser.add_argument("--chain",       default=os.environ.get("SIGUI_CHAIN", "arc"),
                        choices=["arc", "ethereum", "starknet", "aptos", "solana"],
                        help="Target blockchain (default: arc or SIGUI_CHAIN env var)")
    parser.add_argument("--api-url",     default=None,
                        help="Sigui API URL (default: SIGUI_API_URL or http://127.0.0.1:8765)")
    parser.add_argument("--escalate",    action="store_true",
                        help="Automatically run deep analysis if verdict is ESCALATE")
    parser.add_argument("--json",        action="store_true",
                        help="Output raw JSON for programmatic parsing")
    
    args = parser.parse_args()
    exit_code = asyncio.run(_run(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
