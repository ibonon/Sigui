from typing import Any
from ...exceptions import SiguiBlockedError

def protect_adk_agent(agent: Any, client, interceptor, agent_id: str) -> Any:
    original_run = getattr(agent, "run", None)
    
    if original_run:
        import inspect
        is_coroutine = inspect.iscoroutinefunction(original_run)
        
        if is_coroutine:
            async def protected_run(prompt: str, **kwargs):
                if _contains_financial_intent(prompt):
                    amount = _extract_amount_from_text(prompt)
                    dest = _extract_destination_from_text(prompt)
                    decision = await client.evaluate(
                        agent_id=agent_id,
                        action_type="adk_run",
                        amount_usdc=amount,
                        destination=dest,
                        context={"prompt_preview": prompt[:100]}
                    )
                    if decision.decision == "BLOCK":
                        raise SiguiBlockedError(decision)
                return await original_run(prompt, **kwargs)
            agent.run = protected_run
        else:
            def protected_run_sync(prompt: str, **kwargs):
                if _contains_financial_intent(prompt):
                    amount = _extract_amount_from_text(prompt)
                    dest = _extract_destination_from_text(prompt)
                    
                    import asyncio
                    try:
                        loop = asyncio.get_running_loop()
                        has_loop = True
                    except RuntimeError:
                        has_loop = False
                        
                    coro = client.evaluate(
                        agent_id=agent_id,
                        action_type="adk_run",
                        amount_usdc=amount,
                        destination=dest,
                        context={"prompt_preview": prompt[:100]}
                    )
                    if has_loop:
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            decision = pool.submit(asyncio.run, coro).result()
                    else:
                        decision = asyncio.run(coro)
                        
                    if decision.decision == "BLOCK":
                        raise SiguiBlockedError(decision)
                return original_run(prompt, **kwargs)
            agent.run = protected_run_sync
            
    return agent

def _contains_financial_intent(text: str) -> bool:
    fin_keywords = {"transfer", "send", "pay", "usdc", "eth", "swap", "stake"}
    text = text.lower()
    return any(kw in text for kw in fin_keywords)

def _extract_amount_from_text(text: str) -> float:
    import re
    m = re.search(r'(?i)(?:amount|value).*?([\d.]+)', text)
    if m: return float(m.group(1))
    m2 = re.search(r'([\d.]+)\s*(?:usdc|eth|usd)', text, re.IGNORECASE)
    if m2: return float(m2.group(1))
    return 0.0

def _extract_destination_from_text(text: str) -> str:
    import re
    m = re.search(r'0x[a-fA-F0-9]{40}', text)
    if m: return m.group(0)
    return "unknown"
