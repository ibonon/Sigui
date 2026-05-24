from typing import Any
from ...exceptions import SiguiBlockedError

def wrap_llamaindex(agent: Any, client, interceptor, agent_id: str) -> Any:
    original_query = getattr(agent, "query", None)
    original_aquery = getattr(agent, "aquery", None)
    
    async def protected_aquery(str_or_query_bundle, **kwargs):
        query_str = str(str_or_query_bundle)
        if _contains_financial_intent(query_str):
            amount = _extract_amount_from_text(query_str)
            dest = _extract_destination_from_text(query_str)
            
            decision = await client.evaluate(
                agent_id=agent_id,
                action_type="query",
                amount_usdc=amount,
                destination=dest,
                context={"query": query_str[:200]}
            )
            if decision.decision == "BLOCK":
                raise SiguiBlockedError(decision)
                
        if original_aquery:
            return await original_aquery(str_or_query_bundle, **kwargs)
            
    def protected_query(str_or_query_bundle, **kwargs):
        query_str = str(str_or_query_bundle)
        if _contains_financial_intent(query_str):
            amount = _extract_amount_from_text(query_str)
            dest = _extract_destination_from_text(query_str)
            
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                has_loop = True
            except RuntimeError:
                has_loop = False
                
            coro = client.evaluate(
                agent_id=agent_id,
                action_type="query",
                amount_usdc=amount,
                destination=dest,
                context={"query": query_str[:200]}
            )
            if has_loop:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    decision = pool.submit(asyncio.run, coro).result()
            else:
                decision = asyncio.run(coro)
                
            if decision.decision == "BLOCK":
                raise SiguiBlockedError(decision)
                
        if original_query:
            return original_query(str_or_query_bundle, **kwargs)

    if original_aquery:
        agent.aquery = protected_aquery
    if original_query:
        agent.query = protected_query
        
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
