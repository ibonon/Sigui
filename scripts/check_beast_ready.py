"""
ArcWarden v3.0 — Beast Readiness Checker
Validates all hackathon compliance requirements before submission.

Usage:
    python scripts/check_beast_ready.py
    python scripts/check_beast_ready.py --base-url http://127.0.0.1:8000
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip()
    return values


# ── Keys required when DEMO_MODE=false ───────────────────────────────────────
# NOTE: ARC_USDC_TOKEN_ADDRESS is intentionally excluded.
# On Arc testnet, USDC is the NATIVE gas token (isNative=True, 18 decimals),
# confirmed by Circle API: tokenBalances[].token.isNative=true.
# No ERC-20 contract address is needed for native transfers via tx.value.
# Source: https://docs.arc.network/arc/references/contract-addresses
REQUIRED_WHEN_REAL = [
    "CIRCLE_API_KEY",
    "ARCWARDEN_WALLET_ID",
    "ARCWARDEN_WALLET_ADDRESS",
    "PAYER_WALLET_ID",
    "ATTACKER_WALLET_ID",
    "LEARNER_WALLET_ID",
    "ARC_SIGNER_PRIVATE_KEY",
    "ARC_SIGNER_ADDRESS",
]

# Keys that are fine to be missing (optional / Arc-native)
KNOWN_OPTIONAL = {
    "ARC_USDC_TOKEN_ADDRESS": (
        "USDC is native on Arc (isNative=True, 18 dec) — "
        "no ERC-20 contract address needed for x402 payments."
    ),
    "GRAYZONE_WALLET_ADDRESS": "GrayZone wallet address (populated by setup_grayzone_wallet.js).",
    "MONITOR_WALLET_ADDRESS": "Monitor wallet address (optional — agent has no outbound payments).",
}


def check(base_url: str, env_path: Path, watch: bool = False) -> int:
    """
    Run all readiness checks. Returns 0 if READY, 1 if NOT READY.

    Args:
        base_url: ArcWarden API base URL
        env_path: Path to the .env file
        watch:    If True, poll every 30s until READY (for CI / live monitoring)
    """
    attempt = 0
    while True:
        attempt += 1
        if watch and attempt > 1:
            print(f"\n[WATCH] Attempt {attempt} — waiting 30s for more transactions...")
            time.sleep(30)

        issues: list[str] = []
        notes: list[str] = []
        info: list[str] = []

        # ── 1. .env inspection ───────────────────────────────────────────────
        env = load_env(env_path)
        demo_mode = env.get("DEMO_MODE", "true").lower() == "true"

        if demo_mode:
            issues.append(
                "DEMO_MODE=true — set DEMO_MODE=false for real onchain proof."
            )
        else:
            notes.append("DEMO_MODE=false ✓")

        if not demo_mode:
            for key in REQUIRED_WHEN_REAL:
                v = env.get(key, "")
                if not v or v in {
                    "demo_key",
                    "demo_wallet_id",
                    "demo_payer_wallet_id",
                    "demo_attacker_wallet_id",
                    "demo_learner_wallet_id",
                }:
                    issues.append(f"Missing or placeholder value for {key} in .env")

        # Surface optional keys that are set but not required
        for key, explanation in KNOWN_OPTIONAL.items():
            v = env.get(key, "")
            if not v:
                info.append(f"{key} not set — {explanation}")

        # ── 2. Health check ──────────────────────────────────────────────────
        client = httpx.Client(timeout=12)
        try:
            health = client.get(f"{base_url}/health").json()

            status = health.get("status", "unknown")
            if status not in ("ok", "degraded"):
                issues.append(f"/health returned status={status!r}")
            else:
                notes.append(f"/health status={status} ✓")

            if not demo_mode and health.get("demo_mode", True):
                issues.append("/health still reports demo_mode=true despite .env")

            arc_mode = health.get("arc_runtime_mode", "unknown")
            if not demo_mode and arc_mode != "real":
                issues.append(
                    f"/health arc_runtime_mode={arc_mode!r} — expected 'real'. "
                    "Check ARC_RPC_URL and ARC_SIGNER_PRIVATE_KEY."
                )
            else:
                notes.append(
                    f"arc_runtime_mode={arc_mode} "
                    f"| mode={health.get('mode')} "
                    f"| db_connected={health.get('db_connected', '?')} ✓"
                )

            if not health.get("db_connected", True):
                issues.append(
                    "/health reports db_connected=false — SQLite unavailable."
                )

        except Exception as exc:
            issues.append(f"Cannot reach /health at {base_url}: {exc}")
            client.close()
            _print(issues, notes, info, None)
            return 1

        # ── 3. Stats — behavioral evidence ───────────────────────────────────
        report = None
        try:
            stats_resp = client.get(f"{base_url}/stats").json()
            decisions = stats_resp.get("decisions", {})

            block_count = int(decisions.get("block", 0))
            escalate_count = int(decisions.get("escalate", 0))
            pattern_count = int(decisions.get("patterns_learned", 0))
            total_count = int(decisions.get("total", 0))

            notes.append(
                f"decisions: total={total_count} "
                f"block={block_count} "
                f"escalate={escalate_count} "
                f"patterns={pattern_count}"
            )

            if block_count == 0:
                issues.append(
                    "No BLOCK decisions yet — "
                    "deploy agents and wait for AttackerAgent to trigger blocks."
                )
            if escalate_count == 0:
                issues.append(
                    "No ESCALATE decisions yet — "
                    "deploy GrayZoneAgent or wait for ambiguous-zone transactions."
                )
            if pattern_count == 0:
                issues.append(
                    "No patterns learned yet — "
                    "MemoClaw needs at least one BLOCK to record attack signatures."
                )

        except Exception as exc:
            issues.append(f"Cannot query /stats: {exc}")

        # ── 4. Demo report — onchain proof ────────────────────────────────────
        try:
            report = client.get(f"{base_url}/demo/report").json()
            onchain = report.get("onchain_proof", {})

            confirmed = int(
                onchain.get(
                    "confirmed_onchain_tx_count", onchain.get("valid_tx_count", 0)
                )
            )
            simulated = int(onchain.get("simulated_tx_count", 0))
            target_met = bool(onchain.get("target_50_met", False))

            notes.append(
                f"onchain_proof: confirmed={confirmed} simulated={simulated} "
                f"target_50_met={target_met}"
            )

            # Provide a progress bar for the 50-tx requirement
            bar_filled = min(confirmed, 50)
            bar = "█" * bar_filled + "░" * (50 - bar_filled)
            pct = min(100, round(confirmed / 50 * 100))
            notes.append(f"Progress to 50 tx: [{bar}] {confirmed}/50 ({pct}%)")

            if confirmed < 50:
                issues.append(
                    f"Onchain proof: {confirmed}/50 confirmed transactions "
                    f"({50 - confirmed} more needed). "
                    "Keep the ecosystem running — agents generate ~5 tx/min."
                )
            if not target_met:
                issues.append("target_50_met=false in /demo/report.")

            if not demo_mode and simulated > 0:
                issues.append(
                    f"{simulated} simulated tx found while DEMO_MODE=false — "
                    "these will not count as onchain proof."
                )

            # Treasury health
            treasury = report.get("economics", {}).get("treasury", {})
            if not treasury:
                issues.append(
                    "demo/report missing economics.treasury — check /treasury endpoint."
                )
            else:
                bal = treasury.get("balance", 0)
                profit = treasury.get("net_profit", 0)
                notes.append(
                    f"treasury: balance=${bal:.4f} "
                    f"net_profit=${profit:+.4f} "
                    f"mode={treasury.get('mode', '?')}"
                )
                if bal <= 0.01:
                    issues.append(
                        f"Treasury balance ${bal:.4f} is critically low. "
                        "Call POST /demo/refill-treasury or add funds to the Circle wallet."
                    )

            # Explorer link
            signer_link = onchain.get("signer_explorer", "")
            if signer_link:
                info.append(f"Verify onchain: {signer_link}")

        except Exception as exc:
            issues.append(f"Cannot query /demo/report: {exc}")

        client.close()

        # ── 5. Arc USDC native note (always informational) ───────────────────
        info.append(
            "Arc USDC is the native gas token (18 decimals, isNative=True). "
            "ARC_USDC_TOKEN_ADDRESS is NOT required for x402 native payments."
        )

        # ── Print and decide ──────────────────────────────────────────────────
        _print(issues, notes, info, report)

        if not issues:
            return 0

        if not watch:
            return 1

        # In watch mode: only stop if we've accumulated enough tx
        if not issues or all("50" not in i for i in issues):
            # All issues are non-tx-count related — stop watching
            return 1


def _print(
    issues: list[str],
    notes: list[str],
    info: list[str],
    report: dict | None,
) -> None:
    width = 60
    print()
    print("=" * width)
    print("  🛡️  ArcWarden Beast Readiness v3.0")
    print("=" * width)

    if notes:
        print()
        for note in notes:
            print(f"  [OK]   {note}")

    if info:
        print()
        for i in info:
            print(f"  [INFO] {i}")

    if issues:
        print()
        for issue in issues:
            print(f"  [!!]   {issue}")

    if report:
        pricing = report.get("pricing", {})
        print()
        print(
            f"  [INFO] Pricing: "
            f"evaluate=${pricing.get('evaluate_usdc')} USDC  "
            f"escalate=${pricing.get('escalate_usdc')} USDC  "
            f"constraint_ok={pricing.get('price_constraint_ok')}"
        )

    print()
    ready = not issues
    if ready:
        print("  ✅  Result: READY — safe to submit on lablab.ai")
    else:
        remaining = sum(1 for i in issues if "50" in i or "transaction" in i.lower())
        blocking = len(issues) - remaining
        if remaining > 0 and blocking == 0:
            print(
                f"  ⏳  Result: NOT READY — "
                f"waiting for {remaining} tx-count issue(s) to resolve. "
                f"Run with --watch to monitor automatically."
            )
        else:
            print(
                f"  ❌  Result: NOT READY — "
                f"{len(issues)} issue(s) to resolve "
                f"({blocking} blocking, {remaining} tx-count)."
            )
    print("=" * width)
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check ArcWarden hackathon readiness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/check_beast_ready.py
  python scripts/check_beast_ready.py --watch
  python scripts/check_beast_ready.py --base-url http://127.0.0.1:8000
        """,
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="ArcWarden API base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--env-path",
        default=".env",
        help="Path to .env file (default: .env)",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Poll every 30s until READY (useful while agents accumulate transactions)",
    )
    args = parser.parse_args()
    raise SystemExit(check(args.base_url, Path(args.env_path), watch=args.watch))
