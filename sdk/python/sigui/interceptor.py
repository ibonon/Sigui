import inspect
from typing import Callable
from dataclasses import dataclass

@dataclass
class TransactionInfo:
    amount_usdc: float
    destination: str
    function_name: str

class TransactionInterceptor:
    """
    Detects financial function calls automatically.
    """
    AMOUNT_PARAMS = {
        "amount", "value", "amount_usdc", "usdc_amount",
        "transfer_amount", "payment", "price", "cost",
        "quantity", "qty", "sum", "total"
    }

    DESTINATION_PARAMS = {
        "to", "destination", "recipient", "address",
        "wallet", "receiver", "target", "dest"
    }

    FINANCIAL_METHODS = {
        "transfer", "send", "pay", "purchase", "buy",
        "swap", "stake", "deposit", "withdraw",
        "execute_payment", "send_usdc", "transfer_usdc",
        "make_payment", "process_payment"
    }

    def is_financial(self, func: Callable, args: tuple, kwargs: dict) -> bool:
        if not hasattr(func, "__name__"):
            return False
        name = func.__name__.lower()
        
        if any(fin in name for fin in self.FINANCIAL_METHODS):
            return True
            
        try:
            sig = inspect.signature(func)
            params = {p.lower() for p in sig.parameters}
        except (ValueError, TypeError):
            return False

        if (params & self.AMOUNT_PARAMS) and (params & self.DESTINATION_PARAMS):
            return True

        return False

    def extract_transaction(self, func: Callable, args: tuple, kwargs: dict) -> TransactionInfo:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        params = bound.arguments

        amount = 0.0
        destination = "unknown"

        for key, value in params.items():
            if key.lower() in self.AMOUNT_PARAMS and isinstance(value, (int, float, str)):
                try:
                    amount = float(value)
                except ValueError:
                    pass
            if key.lower() in self.DESTINATION_PARAMS and isinstance(value, str):
                destination = value

        return TransactionInfo(
            amount_usdc=amount,
            destination=destination,
            function_name=func.__name__
        )

    def task_is_financial(self, task) -> bool:
        """Heuristic for CrewAI tasks"""
        desc = getattr(task, "description", "").lower()
        return any(fin in desc for fin in self.FINANCIAL_METHODS)

    def estimate_task_amount(self, task) -> float:
        # Placeholder heuristic
        return 0.0

    def extract_task_destination(self, task) -> str:
        # Placeholder heuristic
        return "unknown"
