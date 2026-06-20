"""
Insurance Automation Module
Interfaces with SiguiInsurancePool.vy to automate coverage for high-reputation agents.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from clients.integrations import arc_client
from modules.memory import memory

logger = logging.getLogger(__name__)

class InsuranceAutomation:
    """
    Automates the interaction with the Sigui Insurance Pool.
    Offers and manages policies based on agent reputation and transaction risk.
    """

    def __init__(self):
        self.contract_address = "0xSiguiInsurancePool000000000000000000"
        self.is_enabled = True

    async def offer_insurance(self, agent_address: str, amount_usdc: float, risk_score: float) -> Optional[Dict[str, Any]]:
        """
        Calculates and offers an insurance policy if the agent is eligible.
        Eligibility: Reputation > 700 AND Risk Score < 0.4.
        """
        agent_profile = await memory.get_agent(agent_address)
        trust_score = agent_profile.get("trust_score", 0.5)

        if trust_score < 0.7 or risk_score > 0.4:
            return None

        # Simulate premium calculation (basis points based on risk)
        premium_rate_bps = 50 + int(risk_score * 200) # 0.5% to 1.3%
        premium_amount = (amount_usdc * premium_rate_bps) / 10000

        offer = {
            "policy_type": "TRANSACTION_PROTECTION",
            "coverage_amount": amount_usdc,
            "premium_amount": round(premium_amount, 6),
            "premium_rate_bps": premium_rate_bps,
            "expiry": (datetime.now(timezone.utc)).isoformat(), # Single transaction policy
            "status": "OFFERED"
        }

        logger.info(f"[INSURANCE] Insurance offered to {agent_address} for ${amount_usdc}")
        return offer

    async def auto_claim_check(self, agent_address: str, tx_hash: str, decision: str):
        """
        Checks if a blocked transaction should trigger an automated insurance claim.
        """
        if decision == "BLOCK":
            # In a real scenario, this would verify the block was a 'false positive'
            # or an actual loss event for the agent.
            logger.info(f"[INSURANCE] Analyzing blocked tx {tx_hash} for potential claim...")
            # Simulation: auto-file claim if reputation is Platinum
            agent_profile = await memory.get_agent(agent_address)
            if agent_profile.get("trust_score", 0) > 0.9:
                await self._file_simulated_claim(agent_address, tx_hash)

    async def _file_simulated_claim(self, agent_address: str, tx_hash: str):
        logger.success(f"[INSURANCE] Automated claim filed for Platinum agent {agent_address} (TX: {tx_hash})")
        await asyncio.sleep(1)
        logger.success(f"[INSURANCE] Claim approved. Payout scheduled via SiguiInsurancePool.")

insurance_automation = InsuranceAutomation()
