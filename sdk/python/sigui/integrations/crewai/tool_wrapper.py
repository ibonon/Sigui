"""
sigui.integrations.crewai — CrewAI native integration.

This module is safe to import even when crewai is NOT installed.
``SiguiEvaluationTool`` raises a clear ImportError only when instantiated.

Install:
    pip install "sigui-sdk[crewai]"

Usage:
    from sigui import SiguiClientSync
    from sigui.integrations.crewai import SiguiEvaluationTool

    client = SiguiClientSync(api_url="http://localhost:8000", agent_id="crewai_agent")
    tool   = SiguiEvaluationTool(sigui_client=client, auto_escalate=True)

    agent  = Agent(role="Payment Agent", tools=[tool], ...)
"""
from __future__ import annotations

import asyncio
from typing import Any

from ...client import SiguiClient, SiguiClientSync
from .._common import SiguiGuard

DEFAULT_CREWAI_DESCRIPTION = (
    "Evaluate a payment or agent action with Sigui before execution. "
    "Use this before any transfer, swap, bridge, treasury, or payout action."
)

# ── Optional crewai import ────────────────────────────────────────────────────

try:
    from crewai.tools import BaseTool as _BaseTool
    from pydantic import BaseModel as _BaseModel
    from pydantic import ConfigDict as _ConfigDict
    from pydantic import Field as _Field
    from pydantic import PrivateAttr as _PrivateAttr
    _CREWAI_AVAILABLE = True
except ImportError:
    _CREWAI_AVAILABLE = False
    _BaseTool = None
    _BaseModel = None
    _ConfigDict = None
    _Field = None
    _PrivateAttr = None


# ── Input schema (defined only when pydantic is available via crewai) ─────────

if _CREWAI_AVAILABLE:
    class SiguiEvaluationInput(_BaseModel):  # type: ignore[valid-type,misc]
        destination: str = _Field(..., description="Recipient address or service identifier")  # type: ignore[call-overload]
        amount_usdc: float = _Field(..., gt=0, description="Amount to evaluate in USDC")  # type: ignore[call-overload]
        chain: str = _Field(default="arc", description="Target chain: arc, ethereum, or solana")  # type: ignore[call-overload]
        action_type: str = _Field(  # type: ignore[call-overload]
            default="transfer",
            description="Action type such as transfer, swap, bridge, or stake",
        )
        reason: str = _Field(default="", description="Why the action is being attempted")  # type: ignore[call-overload]
        context_json: str = _Field(  # type: ignore[call-overload]
            default="",
            description="Optional JSON object serialized as a string and merged into context",
        )

    class SiguiEvaluationTool(_BaseTool):  # type: ignore[valid-type,misc]
        """
        CrewAI BaseTool wrapping Sigui security evaluation.

        Attributes:
            sigui_client:   A configured SiguiClient or SiguiClientSync.
            auto_escalate:  If True, auto-escalates ESCALATE verdicts to /escalate.

        Example::

            from sigui import SiguiClientSync
            from sigui.integrations.crewai import SiguiEvaluationTool

            client = SiguiClientSync(api_url="http://localhost:8000")
            tool   = SiguiEvaluationTool(sigui_client=client)
            agent  = Agent(role="Payment Agent", tools=[tool], ...)
        """
        model_config = _ConfigDict(arbitrary_types_allowed=True)  # type: ignore[call-overload]

        name: str = "sigui_evaluate"  # type: ignore[assignment]
        description: str = DEFAULT_CREWAI_DESCRIPTION  # type: ignore[assignment]
        args_schema: type[_BaseModel] = SiguiEvaluationInput  # type: ignore[assignment]
        sigui_client: SiguiClient | SiguiClientSync = _Field(exclude=True)  # type: ignore[assignment]
        auto_escalate: bool = False  # type: ignore[assignment]
        _guard: SiguiGuard = _PrivateAttr()  # type: ignore[assignment]

        def model_post_init(self, __context: Any) -> None:
            self._guard = SiguiGuard(self.sigui_client, auto_escalate=self.auto_escalate)

        def _run(
            self,
            destination: str,
            amount_usdc: float,
            chain: str = "arc",
            action_type: str = "transfer",
            reason: str = "",
            context_json: str = "",
        ) -> str:
            if isinstance(self.sigui_client, SiguiClientSync):
                payload = self._guard.evaluate_action_sync(
                    destination=destination,
                    amount_usdc=amount_usdc,
                    chain=chain,
                    action_type=action_type,
                    reason=reason,
                    context_json=context_json,
                )
                return self._guard.render_text(payload)

            try:
                asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(
                    self._arun(
                        destination=destination,
                        amount_usdc=amount_usdc,
                        chain=chain,
                        action_type=action_type,
                        reason=reason,
                        context_json=context_json,
                    )
                )

            raise RuntimeError(
                "SiguiEvaluationTool._run() cannot execute inside an active event loop. "
                "Use the async CrewAI execution path or pass a SiguiClientSync."
            )

        async def _arun(
            self,
            destination: str,
            amount_usdc: float,
            chain: str = "arc",
            action_type: str = "transfer",
            reason: str = "",
            context_json: str = "",
        ) -> str:
            payload = await self._guard.evaluate_action(
                destination=destination,
                amount_usdc=amount_usdc,
                chain=chain,
                action_type=action_type,
                reason=reason,
                context_json=context_json,
            )
            return self._guard.render_text(payload)

else:
    # ── Safe stub — ImportError only on instantiation ─────────────────────────

    class SiguiEvaluationInput:  # type: ignore[no-redef]
        """Stub: crewai not installed."""
        pass

    class SiguiEvaluationTool:  # type: ignore[no-redef]
        """
        Stub class — crewai is not installed.
        Attempting to instantiate this will raise an ImportError with install instructions.
        """
        name = "sigui_evaluate"
        description = DEFAULT_CREWAI_DESCRIPTION

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ImportError(
                "CrewAI integration requires optional dependencies. "
                "Install with: pip install 'sigui-sdk[crewai]'"
            )
