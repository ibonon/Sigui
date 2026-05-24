from typing import Any
from ...exceptions import SiguiBlockedError

def wrap_autogen(agent: Any, client, interceptor, agent_id: str) -> Any:
    original_generate_reply = getattr(agent, "generate_reply", None)
    original_a_generate_reply = getattr(agent, "a_generate_reply", None)

    async def protected_a_generate_reply(messages=None, sender=None, **kwargs):
        if messages and isinstance(messages, list) and len(messages) > 0:
            last_msg = messages[-1]
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
            if _contains_financial_intent(content):
                amount = _extract_amount_from_text(content)
                dest = _extract_destination_from_text(content)

                decision = await client.evaluate(
                    agent_id=agent_id,
                    action_type="message_reply",
                    amount_usdc=amount,
                    destination=dest,
                    context={"message": content[:200]}
                )

                if decision.decision == "BLOCK":
                    return True, f"I cannot proceed with this transaction. Security oracle blocked it: {decision.reason}"

        if original_a_generate_reply:
            return await original_a_generate_reply(messages, sender, **kwargs)
        return False, None

    def protected_generate_reply(messages=None, sender=None, **kwargs):
        if messages and isinstance(messages, list) and len(messages) > 0:
            last_msg = messages[-1]
            content = last_msg.get("content", "") if isinstance(last_msg, dict) else str(last_msg)
            if _contains_financial_intent(content):
                amount = _extract_amount_from_text(content)
                dest = _extract_destination_from_text(content)

                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    has_loop = True
                except RuntimeError:
                    has_loop = False
                    
                coro = client.evaluate(
                    agent_id=agent_id,
                    action_type="message_reply",
                    amount_usdc=amount,
                    destination=dest,
                    context={"message": content[:200]}
                )

                if has_loop:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        decision = pool.submit(asyncio.run, coro).result()
                else:
                    decision = asyncio.run(coro)

                if decision.decision == "BLOCK":
                    return True, f"I cannot proceed with this transaction. Security oracle blocked it: {decision.reason}"

        if original_generate_reply:
            return original_generate_reply(messages, sender, **kwargs)
        return False, None

    if original_a_generate_reply:
        agent.a_generate_reply = protected_a_generate_reply
    if original_generate_reply:
        agent.generate_reply = protected_generate_reply
        
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
