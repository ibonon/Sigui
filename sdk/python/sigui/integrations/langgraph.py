from __future__ import annotations

from ..client import SiguiClient
from .langchain import create_langchain_tool


def create_langgraph_tool(
    sigui_client: SiguiClient,
    *,
    name: str = "sigui_evaluate",
    description: str = (
        "LangGraph-compatible Sigui security tool. "
        "Call this before any payment or sensitive agent action."
    ),
    auto_escalate: bool = False,
):
    """
    LangGraph commonly consumes LangChain-compatible tools via ToolNode,
    so this helper intentionally returns the same StructuredTool shape.
    """
    return create_langchain_tool(
        sigui_client,
        name=name,
        description=description,
        auto_escalate=auto_escalate,
    )
