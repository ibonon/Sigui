"""
openclaw_skill_sigui — Sigui Security Skill for OpenClaw Autonomous Agents
"""

import os
import json
import urllib.request
from typing import Dict, Any

class SiguiSecuritySkill:
    """Pre-execution security audit skill for OpenClaw framework."""

    def __init__(self, api_key: str = None, endpoint: str = None):
        self.api_key = api_key or os.getenv("SIGUI_API_KEY", "sigui_live_key_alpha")
        self.endpoint = (endpoint or os.getenv("SIGUI_ENDPOINT", "http://127.0.0.1:8000")).rstrip("/")

    def audit_transaction(self, destination: str, amount_usdc: float = 0.0, chain: str = "ethereum") -> Dict[str, Any]:
        """Audits a transaction before OpenClaw agent executes financial tools."""
        url = f"{self.endpoint}/v2/evaluate?zk=true"
        payload = json.dumps({
            "action_type": "transfer",
            "destination": destination,
            "amount_usdc": amount_usdc,
            "chain": chain
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "allowed": data.get("decision") != "BLOCK",
                    "decision": data.get("decision"),
                    "risk_score": data.get("risk_score"),
                    "reason": data.get("reason"),
                    "zk_proof": data.get("zk_proof")
                }
        except Exception as e:
            # Default fail-closed for safety
            return {
                "allowed": False,
                "decision": "BLOCK",
                "risk_score": 1.0,
                "reason": f"Sigui oracle offline: {str(e)}"
            }
