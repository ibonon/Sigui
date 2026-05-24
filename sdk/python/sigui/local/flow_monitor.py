from collections import defaultdict
import time

class FlowMonitor:
    """Local anti-splitting heuristic"""
    def __init__(self):
        self._history = defaultdict(list)
        
    def check_split(self, amount: float, destination: str, window_seconds: int = 300) -> bool:
        now = time.time()
        self._history[destination] = [
            t for t in self._history[destination] if now - t[0] < window_seconds
        ]
        
        self._history[destination].append((now, amount))
        
        # Simple heuristic: more than 3 transactions to same dest in 5 min
        if len(self._history[destination]) > 3:
            return True
            
        return False
