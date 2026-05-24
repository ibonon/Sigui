from typing import Any
from ...exceptions import SiguiBlockedError

def wrap_crewai(agent: Any, client, interceptor, agent_id: str) -> Any:
    original_execute_task = getattr(agent, "execute_task", None)

    if original_execute_task:
        def protected_execute_task(task, context=None, tools=None):
            if interceptor.task_is_financial(task):
                amount = interceptor.estimate_task_amount(task)
                dest = interceptor.extract_task_destination(task)
                
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    has_loop = True
                except RuntimeError:
                    has_loop = False
                    
                coro = client.evaluate(
                    agent_id=agent_id,
                    action_type="task_execution",
                    amount_usdc=amount,
                    destination=dest,
                    context={"task_description": getattr(task, "description", "")}
                )

                if has_loop:
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        decision = pool.submit(asyncio.run, coro).result()
                else:
                    decision = asyncio.run(coro)

                if decision.decision == "BLOCK":
                    raise SiguiBlockedError(decision)

            return original_execute_task(task, context, tools)
            
        agent.execute_task = protected_execute_task
    return agent
