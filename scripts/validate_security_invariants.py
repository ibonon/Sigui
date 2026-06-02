import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.loop import AgentMode
from modules.security_engine import decision_engine, ActionInput, risk_engine


async def run():
    obvious_attack = ActionInput(
        agent_id="attacker_test",
        action_type="transfer",
        amount_usdc=45.0,
        destination="0xdead0000000000000000000000000000000000ff",
        context={"frequency_last_minute": 15},
    )
    profile = {"trust_score": 0.95, "tx_count": 100, "avg_amount_usdc": 0.05}
    risk = await risk_engine.score(obvious_attack, profile, pattern_extra=0.6)
    out = await decision_engine.decide(
        agent_id=obvious_attack.agent_id,
        action_type=obvious_attack.action_type,
        amount_usdc=obvious_attack.amount_usdc,
        destination=obvious_attack.destination,
        risk=risk,
        sigui_mode=AgentMode.NORMAL,
        escalation_available=True,
        agent_profile=profile,
    )
    assert out.decision == "BLOCK", f"Expected BLOCK for obvious attack, got {out.decision}"
    print("OK: obvious attack blocked")


if __name__ == "__main__":
    asyncio.run(run())

