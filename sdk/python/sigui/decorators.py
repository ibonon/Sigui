"""
sigui.decorators — Universal @sigui_protect decorator.

Works with any async agent function regardless of framework.
Intercepts the call, evaluates security via Sigui, then either
proceeds or raises SiguiBlockedError before executing the action.

Usage:
    from sigui import SiguiClient
    from sigui.decorators import sigui_protect

    client = SiguiClient(api_url="http://localhost:8000")

    @sigui_protect(client, amount_arg="usdc_amount", destination_arg="to_address")
    async def transfer_funds(to_address: str, usdc_amount: float, memo: str = ""):
        # This only runs if Sigui says ALLOW
        await wallet.send(to_address, usdc_amount)

    # Or with extractor functions for complex signatures:
    @sigui_protect(
        client,
        amount_getter=lambda args, kwargs: kwargs["payload"]["value"],
        destination_getter=lambda args, kwargs: kwargs["payload"]["to"],
    )
    async def execute_trade(payload: dict):
        ...
"""
from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, Optional

from .client import SiguiClient
from .exceptions import SiguiBlockedError
from .models import EvaluationResult, Verdict


def sigui_protect(
    client: SiguiClient,
    *,
    amount_arg: str = "amount",
    destination_arg: str = "destination",
    action_type: str = "transfer",
    agent_id: Optional[str] = None,
    raise_on_block: bool = True,
    raise_on_escalate: bool = False,
    amount_getter: Optional[Callable[[tuple, dict], float]] = None,
    destination_getter: Optional[Callable[[tuple, dict], str]] = None,
    on_block: Optional[Callable[[EvaluationResult], Any]] = None,
    on_escalate: Optional[Callable[[EvaluationResult], Any]] = None,
):
    """
    Decorator that gates any async function behind a Sigui security evaluation.

    Args:
        client:             A configured SiguiClient instance.
        amount_arg:         Name of the amount kwarg in the decorated function.
        destination_arg:    Name of the destination kwarg in the decorated function.
        action_type:        Action type label sent to Sigui ('transfer', 'swap', etc.).
        agent_id:           Override agent_id. Defaults to client's agent_id.
        raise_on_block:     Raise SiguiBlockedError if verdict is BLOCK (default: True).
        raise_on_escalate:  Raise SiguiEscalationRequiredError if ESCALATE.
        amount_getter:      Custom extractor: fn(args, kwargs) -> float.
        destination_getter: Custom extractor: fn(args, kwargs) -> str.
        on_block:           Callback called with EvaluationResult when blocked.
        on_escalate:        Callback called with EvaluationResult when escalated.

    Returns:
        Decorated async function.

    Example:
        @sigui_protect(client, amount_arg="usdc", destination_arg="to")
        async def pay(to: str, usdc: float):
            ...
    """
    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract amount
            if amount_getter is not None:
                amount = float(amount_getter(args, kwargs))
            elif amount_arg in kwargs:
                amount = float(kwargs[amount_arg])
            else:
                # Try positional
                params = list(sig.parameters.keys())
                if amount_arg in params:
                    idx = params.index(amount_arg)
                    amount = float(args[idx]) if idx < len(args) else 0.0
                else:
                    amount = 0.0

            # Extract destination
            if destination_getter is not None:
                destination = str(destination_getter(args, kwargs))
            elif destination_arg in kwargs:
                destination = str(kwargs[destination_arg])
            else:
                params = list(sig.parameters.keys())
                if destination_arg in params:
                    idx = params.index(destination_arg)
                    destination = str(args[idx]) if idx < len(args) else "0x0"
                else:
                    destination = "0x0"

            # Evaluate
            result = await client.evaluate(
                amount=amount,
                destination=destination,
                agent_id=agent_id or client._default_agent_id,
                action_type=action_type,
                raise_on_block=False,
                raise_on_escalate=False,
            )

            if result.verdict == Verdict.BLOCK:
                if on_block is not None:
                    cb = on_block(result)
                    if inspect.isawaitable(cb):
                        await cb
                if raise_on_block:
                    raise SiguiBlockedError(result)
                return result  # caller can check .is_blocked

            if result.verdict == Verdict.ESCALATE:
                if on_escalate is not None:
                    cb = on_escalate(result)
                    if inspect.isawaitable(cb):
                        await cb
                if raise_on_escalate:
                    from .exceptions import SiguiEscalationRequiredError
                    raise SiguiEscalationRequiredError(result)

            # ALLOW — proceed with the original function
            return await func(*args, **kwargs)

        wrapper.__sigui_protected__ = True  # type: ignore[attr-defined]
        return wrapper

    return decorator
