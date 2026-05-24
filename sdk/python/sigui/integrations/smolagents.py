"""
sigui.integrations.smolagents — HuggingFace smolagents integration
https://github.com/huggingface/smolagents

Wraps Sigui as a native ``Tool`` subclass for any smolagents agent
(CodeAgent, ToolCallingAgent, etc.).

Install:
    pip install "sigui-sdk[smolagents]"

Usage:
    from smolagents import CodeAgent, HfApiModel
    from sigui import SiguiClient
    from sigui.integrations.smolagents import SiguiTool

    client     = SiguiClient(api_url="http://localhost:8000")
    sigui_tool = SiguiTool(client, auto_escalate=True)

    agent = CodeAgent(
        tools=[sigui_tool],
        model=HfApiModel("meta-llama/Llama-3.1-70B-Instruct"),
    )
    agent.run("Send 10 USDC to 0xRecipient...")
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from ..client import SiguiClient
from ._common import SiguiGuard


class SiguiTool:
    """
    HuggingFace smolagents ``Tool`` subclass wrapping Sigui security evaluation.

    Compatible with ``smolagents >= 1.0``.

    Args:
        sigui_client:   An initialized SiguiClient.
        auto_escalate:  If True, auto-escalates to deep analysis on ESCALATE verdict.

    Example::

        from smolagents import CodeAgent, HfApiModel
        from sigui import SiguiClient
        from sigui.integrations.smolagents import SiguiTool

        client = SiguiClient(api_url="http://localhost:8000")
        tool   = SiguiTool(client)
        agent  = CodeAgent(tools=[tool], model=HfApiModel("..."))
        agent.run("Transfer 5 USDC to 0xAbc...")
    """

    name = "sigui_evaluate"
    description = (
        "Evaluate a payment or agent action with Sigui before execution. "
        "Always call this before any transfer, swap, bridge, or treasury action. "
        "Returns a dict with 'decision' (ALLOW/BLOCK/ESCALATE), 'risk_score', and 'reason'."
    )
    inputs = {
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
            "description": "Target chain: arc, ethereum, or solana. Default: arc.",
            "nullable": True,
        },
        "action_type": {
            "type": "string",
            "description": "Action type: transfer, swap, stake, bridge, etc. Default: transfer.",
            "nullable": True,
        },
        "reason": {
            "type": "string",
            "description": "Why the agent wants to perform this action.",
            "nullable": True,
        },
    }
    output_type = "string"

    def __init__(
        self,
        sigui_client: SiguiClient,
        *,
        auto_escalate: bool = False,
    ):
        try:
            from smolagents import Tool  # noqa: F401 — validate install
        except ImportError as exc:
            raise ImportError(
                "smolagents integration requires optional dependencies. "
                "Install with: pip install 'sigui-sdk[smolagents]'"
            ) from exc

        self._guard = SiguiGuard(sigui_client, auto_escalate=auto_escalate)
        self._client = sigui_client

        # Register as a proper smolagents Tool by calling its __init__
        try:
            from smolagents import Tool
            # smolagents Tool uses __init_subclass__ machinery; we patch the class on first use
            if not isinstance(self, Tool):
                # Dynamically make SiguiTool inherit from Tool
                # This approach works without subclassing at import time
                self.__class__ = type(
                    "SiguiTool",
                    (Tool,),
                    {
                        **{k: v for k, v in SiguiTool.__dict__.items() if not k.startswith("__")},
                        "__init__": lambda s, *a, **kw: None,
                    },
                )
                Tool.__init__(self)
        except Exception:
            pass  # Graceful degradation: tool still works as a plain callable

    def forward(
        self,
        destination: str,
        amount_usdc: float,
        chain: str = "arc",
        action_type: str = "transfer",
        reason: str = "",
    ) -> str:
        """
        Synchronous entry point called by smolagents agents.
        Bridges to the async Sigui client using a dedicated event loop.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        coro = self._guard.evaluate_action(
            destination=destination,
            amount_usdc=amount_usdc,
            chain=chain,
            action_type=action_type,
            reason=reason,
        )

        if loop and loop.is_running():
            # Inside an async context — use a thread executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, coro)
                payload = future.result(timeout=30)
        else:
            payload = asyncio.run(coro)

        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    def __call__(self, *args: Any, **kwargs: Any) -> str:
        """Make the tool directly callable as a fallback for frameworks that call tools directly."""
        return self.forward(*args, **kwargs)
