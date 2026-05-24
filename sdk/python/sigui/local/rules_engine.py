from __future__ import annotations
from ..models import EvaluationResult, Verdict, RawSignals
from .flow_monitor import FlowMonitor

Decision = EvaluationResult

class LocalRulesEngine:
    """Evaluates transactions locally without API calls."""
    def __init__(self, config=None):
        self.config = config
        self.flow_monitor = FlowMonitor()
        
    def evaluate(self, amount: float, destination: str, context: dict) -> Decision:
        if amount > getattr(self.config, "min_amount_usdc", 10000) * 1000:
            return Decision(
                verdict=Verdict.BLOCK,
                risk_score=0.9,
                confidence=1.0,
                reason="Amount exceeds local threshold",
                action_hash="local_hash",
                layers_triggered={"rules": 0.9},
                raw_signals=RawSignals(financial={"amount_anomaly": 0.9}, provenance="local_rules_engine")
            )
            
        is_split = self.flow_monitor.check_split(amount, destination)
        if is_split:
            return Decision(
                verdict=Verdict.BLOCK,
                risk_score=0.85,
                confidence=0.9,
                reason="Transaction splitting detected",
                action_hash="local_hash",
                layers_triggered={"anti-splitting": 0.85},
                raw_signals=RawSignals(behavioral={"split_detected": 0.85}, provenance="local_rules_engine")
            )
            
        return Decision(
            verdict=Verdict.ALLOW,
            risk_score=0.1,
            confidence=1.0,
            reason="Local rules passed",
            action_hash="local_hash",
            layers_triggered={},
            raw_signals=RawSignals(provenance="local_rules_engine")
        )
