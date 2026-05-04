import asyncio
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.loop import AgentMode
from clients.integrations import arc_client
from modules.security_engine import decision_engine, ActionInput, risk_engine


class SecurityMinimalTests(unittest.IsolatedAsyncioTestCase):
    async def test_obvious_attack_is_hard_block(self):
        action = ActionInput(
            agent_id="test_attacker",
            action_type="transfer",
            amount_usdc=45.0,
            destination="0xdead0000000000000000000000000000000000ff",
            context={"frequency_last_minute": 15},
        )
        profile = {"trust_score": 0.95, "tx_count": 40, "avg_amount_usdc": 0.05}
        risk = await risk_engine.score(action, profile, pattern_extra=0.6)
        self.assertTrue(risk.hard_block)
        out = await decision_engine.decide(
            agent_id=action.agent_id,
            action_type=action.action_type,
            amount_usdc=action.amount_usdc,
            destination=action.destination,
            risk=risk,
            arcwarden_mode=AgentMode.NORMAL,
            escalation_available=True,
            agent_profile=profile,
        )
        self.assertEqual(out.decision, "BLOCK")

    async def test_safe_case_not_hard_block(self):
        action = ActionInput(
            agent_id="test_safe",
            action_type="transfer",
            amount_usdc=0.02,
            destination="0xabc12345678901234567890123456789012345678",
            context={"frequency_last_minute": 2},
        )
        profile = {"trust_score": 0.6, "tx_count": 8, "avg_amount_usdc": 0.03}
        risk = await risk_engine.score(action, profile, pattern_extra=0.0)
        self.assertFalse(risk.hard_block)
        self.assertLess(risk.risk_score, 0.35)

    async def test_suspicious_case_reaches_escalate_or_block_zone(self):
        action = ActionInput(
            agent_id="test_suspicious",
            action_type="transfer",
            amount_usdc=0.9,
            destination="0x7777777777777777777777777777777777777777",
            context={"frequency_last_minute": 7},
        )
        profile = {"trust_score": 0.5, "tx_count": 0, "avg_amount_usdc": 0.04}
        risk = await risk_engine.score(action, profile, pattern_extra=0.0)
        self.assertGreaterEqual(risk.risk_score, 0.35)

    async def test_demo_tx_hash_is_marked_simulated(self):
        arc_client.demo_mode = True
        tx = await arc_client.log_decision_onchain("abcd1234", "ALLOW", 0.1)
        self.assertTrue(tx.startswith("0xSIM_"))


if __name__ == "__main__":
    unittest.main()

