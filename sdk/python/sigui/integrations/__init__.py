"""
sigui.integrations — Native adapters for popular AI agent frameworks.

Each sub-module is imported lazily so that the package never raises ImportError
at import time when an optional dependency is absent.

Available integrations
----------------------
- langchain      : ``create_langchain_tool``    (pip install sigui-sdk[langchain])
- langgraph      : ``create_langgraph_tool``    (pip install sigui-sdk[langgraph])
- crewai         : ``SiguiEvaluationTool``      (pip install sigui-sdk[crewai])
- openai_agents  : ``create_openai_agents_tool`` (pip install sigui-sdk[openai-agents])
- autogen        : ``create_autogen_tool``      (pip install sigui-sdk[autogen])
- smolagents     : ``SiguiTool``               (pip install sigui-sdk[smolagents])
"""

from ._common import SiguiGuard

def __getattr__(name):
    if name == "create_langchain_tool":
        from .langchain import create_langchain_tool
        return create_langchain_tool
    if name == "create_langgraph_tool":
        from .langgraph import create_langgraph_tool
        return create_langgraph_tool
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # Core guard (framework-agnostic)
    "SiguiGuard",
    # LangChain / LangGraph
    "create_langchain_tool",
    "create_langgraph_tool",
    # CrewAI — imported on demand to avoid bare crewai dep
    # from sigui.integrations.crewai import SiguiEvaluationTool
    # OpenAI Agents SDK
    # from sigui.integrations.openai_agents import create_openai_agents_tool
    # AutoGen
    # from sigui.integrations.autogen import create_autogen_tool
    # smolagents
    # from sigui.integrations.smolagents import SiguiTool
]
