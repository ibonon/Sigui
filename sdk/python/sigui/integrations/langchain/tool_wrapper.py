from __future__ import annotations

from ...client import SiguiClient
from .._common import SiguiGuard

DEFAULT_TOOL_NAME = "sigui_evaluate"
DEFAULT_TOOL_DESCRIPTION = (
    "Evaluate a payment or agent action with Sigui before execution. "
    "Use this tool before any transfer, swap, stake, bridge, or treasury action."
)


def create_langchain_tool(
    sigui_client: SiguiClient,
    *,
    name: str = DEFAULT_TOOL_NAME,
    description: str = DEFAULT_TOOL_DESCRIPTION,
    auto_escalate: bool = False,
):
    """
    Build a StructuredTool that can be plugged into LangChain agents.
    The returned tool also works in LangGraph ToolNode pipelines.
    """
    try:
        from langchain_core.tools import StructuredTool
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise ImportError(
            "LangChain integration requires optional dependencies. "
            "Install with: pip install 'sigui-sdk[langchain]'"
        ) from exc

    guard = SiguiGuard(sigui_client, auto_escalate=auto_escalate)

    class SiguiLangChainInput(BaseModel):
        destination: str = Field(..., description="Recipient address or service identifier")
        amount_usdc: float = Field(..., gt=0, description="Amount to evaluate in USDC")
        chain: str = Field(default="arc", description="Target chain: arc, ethereum, or solana")
        action_type: str = Field(
            default="transfer",
            description="Action type such as transfer, swap, bridge, or stake",
        )
        reason: str = Field(
            default="",
            description="Why the agent wants to perform this action",
        )
        context_json: str = Field(
            default="",
            description="Optional JSON object serialized as a string and merged into context",
        )

    async def _sigui_tool(
        destination: str,
        amount_usdc: float,
        chain: str = "arc",
        action_type: str = "transfer",
        reason: str = "",
        context_json: str = "",
    ) -> str:
        payload = await guard.evaluate_action(
            destination=destination,
            amount_usdc=amount_usdc,
            chain=chain,
            action_type=action_type,
            reason=reason,
            context_json=context_json,
        )
        return guard.render_text(payload)

    return StructuredTool.from_function(
        coroutine=_sigui_tool,
        name=name,
        description=description,
        args_schema=SiguiLangChainInput,
    )
