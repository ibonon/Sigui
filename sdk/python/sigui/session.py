from __future__ import annotations
from typing import Any
from .models import Decision

class SiguiSession:
    """Context manager for grouping evaluations within a single session."""
    def __init__(self, agent_id: str, config=None):
        self.agent_id = agent_id
        self.config = config
        self._decisions: list[Decision] = []

    async def __aenter__(self) -> SiguiSession:
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def decisions(self) -> list[Decision]:
        return self._decisions
        
    def add_decision(self, decision: Decision):
        self._decisions.append(decision)

    @property
    def blocked_count(self) -> int:
        return sum(1 for d in self._decisions if d.verdict == "BLOCK")

    @property
    def usdc_protected(self) -> float:
        return 0.0

    @property
    def session_report(self) -> dict:
        return {
            "decisions": len(self._decisions),
            "blocked": self.blocked_count,
            "protected": self.usdc_protected
        }

    async def run(self, agent: Any, task: Any, **kwargs):
        """Run an agent inside this session"""
        import asyncio
        if hasattr(agent, "run"):
            run_meth = getattr(agent, "run")
            if asyncio.iscoroutinefunction(run_meth):
                return await run_meth(task, **kwargs)
            else:
                return run_meth(task, **kwargs)
        elif hasattr(agent, "arun"):
            return await agent.arun(task, **kwargs)
        elif hasattr(agent, "ainvoke"):
            return await agent.ainvoke(task, **kwargs)
        elif hasattr(agent, "invoke"):
            return agent.invoke(task, **kwargs)
        else:
            raise ValueError(f"Agent {agent} has no known run method")
