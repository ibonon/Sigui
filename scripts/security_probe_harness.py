import argparse
import asyncio
import json
from dataclasses import dataclass

import httpx


@dataclass
class ProbeCase:
    name: str
    payload: dict
    expected: set[str]


CASES = [
    ProbeCase(
        name="safe_normal_transfer",
        payload={
            "agent_id": "probe_safe",
            "action_type": "transfer",
            "amount_usdc": 0.03,
            "destination": "0xabc12345678901234567890123456789012345678",
            "context": {"frequency_last_minute": 2},
        },
        expected={"ALLOW", "ESCALATE"},
    ),
    ProbeCase(
        name="suspicious_unknown_medium",
        payload={
            "agent_id": "probe_suspicious",
            "action_type": "transfer",
            "amount_usdc": 1.2,
            "destination": "0x9876543210abcdef9876543210abcdef98765432",
            "context": {"frequency_last_minute": 6},
        },
        expected={"ESCALATE", "BLOCK"},
    ),
    ProbeCase(
        name="obvious_attack",
        payload={
            "agent_id": "probe_attack",
            "action_type": "transfer",
            "amount_usdc": 45.0,
            "destination": "0xdead0000000000000000000000000000000000ff",
            "context": {"frequency_last_minute": 15},
        },
        expected={"BLOCK"},
    ),
]


async def run(base_url: str) -> int:
    failures = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        health = (await client.get(f"{base_url}/health")).json()
        if not health.get("demo_mode", False):
            print("Harness requires DEMO_MODE=true unless you provide real x402 payment flow.")
            return 2
        print(f"Health: mode={health.get('mode')} demo_mode={health.get('demo_mode')}")

        for case in CASES:
            resp = await client.post(
                f"{base_url}/evaluate",
                headers={"Content-Type": "application/json", "X-Payment": "0xSIM_probe"},
                json=case.payload,
            )
            data = resp.json()
            decision = data.get("decision", "UNKNOWN")
            ok = decision in case.expected
            status = "OK" if ok else "FAIL"
            print(f"[{status}] {case.name} -> {decision} expected={sorted(case.expected)}")
            if not ok:
                failures.append(
                    {
                        "case": case.name,
                        "decision": decision,
                        "expected": sorted(case.expected),
                        "response": data,
                    }
                )

    if failures:
        print("\nFailures:")
        print(json.dumps(failures, indent=2))
        return 1
    print("\nAll security probes passed.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Sigui security probe harness.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args.base_url)))

