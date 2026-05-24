"""
sigui.integrations.autogen — Microsoft AutoGen integration
https://microsoft.github.io/autogen/

Compatible with AutoGen >= 0.4 (autogen-agentchat package).
Wraps Sigui as a callable tool that any AssistantAgent can invoke
before executing a payment or sensitive action.

Install:
    pip install "sigui-sdk[autogen]"

Usage:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_ext.models.openai import OpenAIChatCompletionClient
    from sigui import SiguiClient
    from sigui.integrations.autogen import create_autogen_tool

    client     = SiguiClient(api_url="http://localhost:8000")
    sigui_tool = create_autogen_tool(client, auto_escalate=True)

    agent = AssistantAgent(
        name="payment_agent",
        model_client=OpenAIChatCompletionClient(model="gpt-4o"),
        tools=[sigui_tool],
        system_message="Always use sigui_evaluate before any transfer.",
    )
"""
from __future__ import annotations

import json
from typing import Annotated, Any

from ...client import SiguiClient
from .._common import SiguiGuard

DEFAULT_DESCRIPTION = (
    "Evaluate a payment or sensitive action with Sigui before execution. "
    "Call this before any transfer, swap, bridge, or treasury operation."
)


def create_autogen_tool(
    sigui_client: SiguiClient,
    *,
    auto_escalate: bool = False,
):
    """
    Create an AutoGen-compatible async callable tool for Sigui.

    Compatible with ``autogen-agentchat >= 0.4``.

    Args:
        sigui_client:   An initialized SiguiClient.
        auto_escalate:  If True, auto-escalates to deep analysis on ESCALATE verdict.

    Returns:
        An async function decorated with AutoGen's ``@FunctionTool`` metadata,
        ready to be passed in the ``tools=`` list of an ``AssistantAgent``.

    Example::

        from autogen_agentchat.agents import AssistantAgent
        from sigui import SiguiClient
        from sigui.integrations.autogen import create_autogen_tool

        client = SiguiClient(api_url="http://localhost:8000")
        tool   = create_autogen_tool(client)

        agent  = AssistantAgent("agent", tools=[tool], ...)
    """
    try:
        from autogen_core.tools import FunctionTool
    except ImportError as exc:
        raise ImportError(
            "AutoGen integration requires optional dependencies. "
            "Install with: pip install 'sigui-sdk[autogen]'"
        ) from exc

    guard = SiguiGuard(sigui_client, auto_escalate=auto_escalate)

    async def sigui_evaluate(
        destination: Annotated[str, "Recipient address or service identifier"],
        amount_usdc: Annotated[float, "Amount in USDC to evaluate (must be > 0)"],
        chain: Annotated[str, "Target chain: arc, ethereum, or solana"] = "arc",
        action_type: Annotated[str, "Action type: transfer, swap, stake, bridge, etc."] = "transfer",
        reason: Annotated[str, "Why the agent wants to perform this action"] = "",
        context_json: Annotated[str, "Optional JSON context object serialized as a string"] = "",
    ) -> str:
        """
        Evaluate a payment or agent action with Sigui before execution.
        Always call this before any transfer, swap, bridge, or payout action.
        Returns a JSON string with decision (ALLOW/BLOCK/ESCALATE), risk_score, and reason.
        """
        payload = await guard.evaluate_action(
            destination=destination,
            amount_usdc=amount_usdc,
            chain=chain,
            action_type=action_type,
            reason=reason,
            context_json=context_json,
        )
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    return FunctionTool(sigui_evaluate, description=DEFAULT_DESCRIPTION)
