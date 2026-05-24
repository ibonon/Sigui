from typing import Any
import asyncio
try:
    from langchain.callbacks.base import BaseCallbackHandler
    from langchain.schema import AgentAction
except ImportError:
    BaseCallbackHandler = object
    AgentAction = None
from ...client import SiguiClient
from ...interceptor import TransactionInterceptor
from ...exceptions import SiguiBlockedError

class SiguiCallbackHandler(BaseCallbackHandler):
    """
    LangChain callback intercepting agent actions before execution.
    """
    def __init__(self, config=None):
        self.client = SiguiClient(config)
        self.interceptor = TransactionInterceptor()

    def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        tool_name = action.tool.lower()
        tool_input = action.tool_input

        if self._is_financial_tool(tool_name, tool_input):
            amount = self._extract_amount(tool_input)
            destination = self._extract_destination(tool_input)

            try:
                loop = asyncio.get_running_loop()
                has_loop = True
            except RuntimeError:
                has_loop = False

            coro = self.client.evaluate(
                agent_id=kwargs.get("run_id", "langchain_agent"),
                action_type=tool_name,
                amount_usdc=amount,
                destination=destination,
                context={"tool_input": str(tool_input)}
            )

            if has_loop:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    decision = pool.submit(asyncio.run, coro).result()
            else:
                decision = asyncio.run(coro)

            if decision.decision == "BLOCK":
                raise SiguiBlockedError(decision)

    def _is_financial_tool(self, tool_name: str, tool_input: Any) -> bool:
        fin_keywords = {"transfer", "send", "pay", "usdc", "eth", "swap", "stake", "deposit", "withdraw"}
        return any(kw in tool_name for kw in fin_keywords)

    def _extract_amount(self, tool_input: Any) -> float:
        if isinstance(tool_input, dict):
            for k in ["amount", "value", "amount_usdc"]:
                if k in tool_input:
                    try: return float(tool_input[k])
                    except: pass
        elif isinstance(tool_input, str):
            import re
            m = re.search(r'(?i)(?:amount|value).*?([\d.]+)', tool_input)
            if m: return float(m.group(1))
        return 0.0

    def _extract_destination(self, tool_input: Any) -> str:
        if isinstance(tool_input, dict):
            for k in ["to", "destination", "address", "recipient"]:
                if k in tool_input:
                    return str(tool_input[k])
        return "unknown"
