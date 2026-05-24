from typing import Any
from uuid import uuid4
from .config import SiguiConfig
from .client import SiguiClient
from .interceptor import TransactionInterceptor

def _detect_framework(agent: Any) -> str:
    agent_type = type(agent).__module__
    if "langchain" in agent_type:
        return "langchain"
    if "crewai" in agent_type:
        return "crewai"
    if "autogen" in agent_type:
        return "autogen"
    if "llama_index" in agent_type:
        return "llamaindex"
    if "google.adk" in agent_type:
        return "google_adk"
    return "generic"

def protect(agent: Any, config: SiguiConfig = None, agent_id: str = None) -> Any:
    """
    Wraps any agent object with Sigui protection.
    Works with any framework.
    """
    client = SiguiClient(config=config)
    interceptor = TransactionInterceptor()
    agent_id = agent_id or f"agent_{uuid4().hex[:8]}"

    framework = _detect_framework(agent)

    if framework == "langchain":
        from .integrations.langchain.agent_wrapper import wrap_langchain
        return wrap_langchain(agent, client, interceptor, agent_id)
    elif framework == "crewai":
        from .integrations.crewai.agent_wrapper import wrap_crewai
        return wrap_crewai(agent, client, interceptor, agent_id)
    elif framework == "autogen":
        from .integrations.autogen.agent_wrapper import wrap_autogen
        return wrap_autogen(agent, client, interceptor, agent_id)
    elif framework == "llamaindex":
        from .integrations.llamaindex.query_wrapper import wrap_llamaindex
        return wrap_llamaindex(agent, client, interceptor, agent_id)
    elif framework == "google_adk":
        from .integrations.google_adk.agent_wrapper import protect_adk_agent
        return protect_adk_agent(agent, client, interceptor, agent_id)
    else:
        return _wrap_generic(agent, client, interceptor, agent_id)

def _wrap_generic(agent, client, interceptor, agent_id):
    """Generic wrapper for any Python object."""
    import functools
    class SiguiWrapper:
        def __getattr__(self, name):
            attr = getattr(agent, name)
            if callable(attr):
                # We can't check interceptor.is_financial here easily without args,
                # so we wrap it and check at call time
                @functools.wraps(attr)
                async def async_wrapper(*args, **kwargs):
                    if interceptor.is_financial(attr, args, kwargs):
                        tx = interceptor.extract_transaction(attr, args, kwargs)
                        decision = await client.evaluate(
                            agent_id=agent_id,
                            action_type=tx.function_name,
                            amount_usdc=tx.amount_usdc,
                            destination=tx.destination
                        )
                        if decision.decision == "BLOCK":
                            from .exceptions import SiguiBlockedError
                            raise SiguiBlockedError(decision)
                    return await attr(*args, **kwargs)
                
                @functools.wraps(attr)
                def sync_wrapper(*args, **kwargs):
                    if interceptor.is_financial(attr, args, kwargs):
                        tx = interceptor.extract_transaction(attr, args, kwargs)
                        import asyncio
                        try:
                            loop = asyncio.get_running_loop()
                        except RuntimeError:
                            loop = None
                        if loop and loop.is_running():
                            import concurrent.futures
                            with concurrent.futures.ThreadPoolExecutor() as pool:
                                decision = pool.submit(asyncio.run, client.evaluate(
                                    agent_id=agent_id,
                                    action_type=tx.function_name,
                                    amount_usdc=tx.amount_usdc,
                                    destination=tx.destination
                                )).result()
                        else:
                            decision = asyncio.run(client.evaluate(
                                agent_id=agent_id,
                                action_type=tx.function_name,
                                amount_usdc=tx.amount_usdc,
                                destination=tx.destination
                            ))
                        if decision.decision == "BLOCK":
                            from .exceptions import SiguiBlockedError
                            raise SiguiBlockedError(decision)
                    return attr(*args, **kwargs)
                import asyncio
                if asyncio.iscoroutinefunction(attr):
                    return async_wrapper
                return sync_wrapper
            return attr

        def __repr__(self):
            return f"SiguiProtected({repr(agent)})"

    return SiguiWrapper()
