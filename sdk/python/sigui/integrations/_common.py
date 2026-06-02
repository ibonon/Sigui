from __future__ import annotations

import inspect
import json
from typing import Any, Mapping

from ..client import SiguiClient, SiguiClientSync
from ..models import EscalationResult, EvaluationResult


class SiguiGuard:
    """Shared guardrail helper used by framework integrations."""

    def __init__(
        self,
        client: SiguiClient | SiguiClientSync,
        *,
        auto_escalate: bool = False,
    ):
        self._client = client
        self._auto_escalate = auto_escalate

    async def evaluate_action(
        self,
        *,
        destination: str,
        amount_usdc: float,
        chain: str = "arc",
        action_type: str = "transfer",
        reason: str = "",
        context: Mapping[str, Any] | None = None,
        context_json: str = "",
    ) -> dict[str, Any]:
        merged_context = self._merge_context(
            reason=reason,
            context=context,
            context_json=context_json,
        )

        result = self._client.evaluate(
            amount=amount_usdc,
            destination=destination,
            action_type=action_type,
            chain=chain,
            context=merged_context,
        )
        if inspect.isawaitable(result):
            result = await result

        if self._auto_escalate and result.needs_escalation:
            escalation = self._client.escalate(
                amount=amount_usdc,
                destination=destination,
                action_type=action_type,
                chain=chain,
                context=merged_context,
            )
            if inspect.isawaitable(escalation):
                escalation = await escalation
            return self.serialize_escalation(escalation)

        return self.serialize_evaluation(result)

    def evaluate_action_sync(
        self,
        *,
        destination: str,
        amount_usdc: float,
        chain: str = "arc",
        action_type: str = "transfer",
        reason: str = "",
        context: Mapping[str, Any] | None = None,
        context_json: str = "",
    ) -> dict[str, Any]:
        merged_context = self._merge_context(
            reason=reason,
            context=context,
            context_json=context_json,
        )

        result = self._client.evaluate(
            amount=amount_usdc,
            destination=destination,
            action_type=action_type,
            chain=chain,
            context=merged_context,
        )
        if inspect.isawaitable(result):
            raise RuntimeError(
                "evaluate_action_sync() requires a synchronous Sigui client."
            )

        if self._auto_escalate and result.needs_escalation:
            escalation = self._client.escalate(
                amount=amount_usdc,
                destination=destination,
                action_type=action_type,
                chain=chain,
                context=merged_context,
            )
            if inspect.isawaitable(escalation):
                raise RuntimeError(
                    "evaluate_action_sync() requires a synchronous Sigui client."
                )
            return self.serialize_escalation(escalation)

        return self.serialize_evaluation(result)

    @staticmethod
    def render_text(payload: Mapping[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    @staticmethod
    def serialize_evaluation(result: EvaluationResult) -> dict[str, Any]:
        return {
            "kind": "evaluation",
            "decision": result.verdict.value,
            "allowed": result.is_safe,
            "blocked": result.is_blocked,
            "needs_escalation": result.needs_escalation,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "reason": result.reason,
            "action_hash": result.action_hash,
            "policy_source": result.policy_source,
            "evaluation_price_usdc": result.evaluation_price_usdc,
            "processing_time_ms": result.processing_time_ms,
            "chain": result.chain,
            "vision_pattern": result.vision_pattern,
            "onchain_proof": result.onchain_proof,
        }

    @staticmethod
    def serialize_escalation(result: EscalationResult) -> dict[str, Any]:
        return {
            "kind": "escalation",
            "decision": result.verdict.value,
            "analysis": result.analysis,
            "confidence": result.confidence,
            "reason": result.reason,
            "cap_amount_usdc": result.cap_amount_usdc,
            "paid_by_sigui": result.paid_by_sigui,
            "fallback_used": result.fallback_used,
            "degraded_mode": result.degraded_mode,
            "inference_engine": result.inference_engine,
            "inference_device": result.inference_device,
            "arc_tx_log": result.arc_tx_log,
        }

    @staticmethod
    def _merge_context(
        *,
        reason: str,
        context: Mapping[str, Any] | None,
        context_json: str,
    ) -> dict[str, Any]:
        merged = dict(context or {})
        if reason and "reason" not in merged:
            merged["reason"] = reason

        raw_json = context_json.strip()
        if not raw_json:
            return merged

        try:
            parsed = json.loads(raw_json)
        except json.JSONDecodeError:
            merged["context_text"] = raw_json
            return merged

        if isinstance(parsed, dict):
            merged.update(parsed)
        else:
            merged["context_data"] = parsed
        return merged
