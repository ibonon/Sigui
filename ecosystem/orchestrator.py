import asyncio
from typing import Any

from loguru import logger

from ecosystem.agents import AttackerAgent, LearnerAgent, MonitorAgent, PayerAgent, GrayZoneAgent
from ecosystem.wallet_factory import wallet_factory
from modules.treasury import treasury

async def on_mode_change(old, new):
    logger.warning(f"🔄 MODE CHANGE: {old} → {new}")
    impact = "Escalation désactivée" if new == "EMERGENCY" else "Escalation réduite" if new == "DEGRADED" else "Fonctionnement normal"
    logger.warning(f"   Impact: {impact}")


class EcosystemOrchestrator:
    def __init__(self):
        self._agents: dict[str, Any] = {}
        self._running = False

    async def start(self):
        if self._running:
            return
        wallets = await wallet_factory.initialize_agent_wallets()
        self._agents = {
            "agent_payer": PayerAgent(
                agent_id="agent_payer",
                wallet_id=wallets["payer"].wallet_id,
                wallet_address=wallets["payer"].wallet_address,
                min_cycle_s=2,
                max_cycle_s=5,
            ),
            "agent_attacker": AttackerAgent(
                agent_id="agent_attacker",
                wallet_id=wallets["attacker"].wallet_id,
                wallet_address=wallets["attacker"].wallet_address,
                min_cycle_s=3,
                max_cycle_s=7,
            ),
            "agent_monitor": MonitorAgent(
                agent_id="agent_monitor",
                wallet_id=wallets["monitor"].wallet_id,
                wallet_address=wallets["monitor"].wallet_address,
                min_cycle_s=5,
                max_cycle_s=10,
            ),
            "agent_learner": LearnerAgent(
                agent_id="agent_learner",
                wallet_id=wallets["learner"].wallet_id,
                wallet_address=wallets["learner"].wallet_address,
                min_cycle_s=3,
                max_cycle_s=8,
            ),
            "agent_grayzone": GrayZoneAgent(
                agent_id="agent_grayzone",
                wallet_id=wallets["grayzone"].wallet_id,
                wallet_address=wallets["grayzone"].wallet_address,
                min_cycle_s=4,
                max_cycle_s=9,
            ),
        }
        treasury.on_mode_change(on_mode_change)
        await asyncio.gather(*(agent.start() for agent in self._agents.values()), return_exceptions=True)
        self._running = True
        logger.info("[ECOSYSTEM] 5 autonomous agents started")

    async def stop(self):
        if not self._running:
            return
        await asyncio.gather(*(agent.stop() for agent in self._agents.values()), return_exceptions=True)
        self._running = False
        logger.info("[ECOSYSTEM] stopped")

    def get_status(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "agents": {name: agent.status() for name, agent in self._agents.items()},
        }


ecosystem_orchestrator = EcosystemOrchestrator()

