"""
sigui.integrations.openai_agents — OpenAI Agents SDK integration
https://openai.github.io/openai-agents-python/

Enables any OpenAI Agent to use Sigui as a native security tool
before executing any payment or sensitive action.

Install:
    pip install "sigui-sdk[openai-agents]"

Usage:
    from agents import Agent, Runner
    from sigui import SiguiClient
    from sigui.integrations.openai_agents import create_openai_agents_tool

    client = SiguiClient(api_url="http://localhost:8000")
    sigui_tool = create_openai_agents_tool(client, auto_escalate=True)

    agent = Agent(
        name="PaymentAgent",
        instructions="You are a payment agent. Always use sigui_evaluate before any transfer.",
        tools=[sigui_tool],
    )
    result = await Runner.run(agent, "Send 5 USDC to 0xAbc...")
"""
from __future__ import annotations

from typing import Any

from ..client import SiguiClient
from ._common import SiguiGuard

DEFAULT_DESCRIPTION = (
    "Evaluate a payment or sensitive action with Sigui before execution. "
    "Always call this tool before any transfer, swap, stake, bridge, or treasury action. "
    "Returns a JSON object with 'decision' (ALLOW/BLOCK/ESCALATE), 'risk_score', and 'reason'."
)


def create_openai_agents_tool(
    sigui_client: SiguiClient,
    *,
    name: str = "sigui_evaluate",
    description: str = DEFAULT_DESCRIPTION,
    auto_escalate: bool = False,
):
    """
    Create an OpenAI Agents SDK FunctionTool that wraps Sigui security evaluation.

    Compatible with the ``agents`` package (openai-agents >= 0.0.5).

    Args:
        sigui_client:   An initialized SiguiClient.
        name:           Tool name visible to the LLM.
        description:    Tool description (what the LLM reads to decide when to call it).
        auto_escalate:  If True, automatically calls /escalate when verdict is ESCALATE.

    Returns:
        A ``FunctionTool`` ready to be passed in the ``tools=`` list of an ``Agent``.

    Example::

        from agents import Agent, Runner
        from sigui import SiguiClient
        from sigui.integrations.openai_agents import create_openai_agents_tool

        client = SiguiClient(api_url="http://localhost:8000")
        tool   = create_openai_agents_tool(client, auto_escalate=True)

        agent  = Agent(name="PaymentAgent", tools=[tool])
        result = await Runner.run(agent, "Transfer 5 USDC to 0xAbc...")
    """
    try:
        from agents import FunctionTool, RunContextWrapper
        from agents.tool import function_tool as _ft_marker  # noqa: F401 — version check
    except ImportError as exc:
        raise ImportError(
            "OpenAI Agents SDK integration requires optional dependencies. "
            "Install with: pip install 'sigui-sdk[openai-agents]'"
        ) from exc

    import inspect
    import json

    guard = SiguiGuard(sigui_client, auto_escalate=auto_escalate)

    async def _sigui_evaluate(
        ctx: RunContextWrapper[Any],  # noqa: ARG001
        destination: str,
        amount_usdc: float,
        chain: str = "arc",
        action_type: str = "transfer",
        reason: str = "",
        context_json: str = "",
    ) -> str:
        """Evaluate a payment action with Sigui security oracle."""
        payload = await guard.evaluate_action(
            destination=destination,
            amount_usdc=amount_usdc,
            chain=chain,
            action_type=action_type,
            reason=reason,
            context_json=context_json,
        )
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    params_schema = {
        "type": "object",
        "properties": {
            "destination": {
                "type": "string",
                "description": "Recipient address or service identifier (hex or base58).",
            },
            "amount_usdc": {
                "type": "number",
                "description": "Amount in USDC to evaluate (must be > 0).",
            },
            "chain": {
                "type": "string",
                "enum": ["arc", "ethereum", "solana"],
                "description": "Target blockchain. Default: arc.",
            },
            "action_type": {
                "type": "string",
                "description": "Action type: transfer, swap, stake, bridge, treasury, etc.",
                "default": "transfer",
            },
            "reason": {
                "type": "string",
                "description": "Why the agent wants to perform this action.",
                "default": "",
            },
            "context_json": {
                "type": "string",
                "description": "Optional JSON object with additional context, serialized as string.",
                "default": "",
            },
        },
        "required": ["destination", "amount_usdc"],
        "additionalProperties": False,
    }

    return FunctionTool(
        name=name,
        description=description,
        params_json_schema=params_schema,
        on_invoke_tool=_sigui_evaluate,
    )
