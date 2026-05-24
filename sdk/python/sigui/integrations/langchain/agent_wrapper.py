from typing import Any
from .callback import SiguiCallbackHandler

def wrap_langchain(agent: Any, client, interceptor, agent_id: str) -> Any:
    """Wraps a LangChain agent/executor by injecting the Sigui callback."""
    if hasattr(agent, "callbacks"):
        cb = SiguiCallbackHandler(client.config)
        if agent.callbacks is None:
            agent.callbacks = [cb]
        elif isinstance(agent.callbacks, list):
            agent.callbacks.append(cb)
    return agent
