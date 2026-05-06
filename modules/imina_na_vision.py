"""
Sigui P1 — Imina Na Vision Layer (stub + vLLM-ready client)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from config import settings


@dataclass
class VisionOutput:
    pattern: str = "NORMAL"
    confidence: float = 0.0
    risk_delta: float = 0.0
    visual_evidence: str = "no_visual_signal"
    model: str = "Imina-Na-Stub-v1"
    inference_device: str = "CPU-MOCK"
    inference_time_ms: int = 0
    graph_summary: dict[str, Any] | None = None


class IminaNaVision:
    PATTERN_TO_DELTA = {
        "NORMAL": 0.0,
        "DRAIN_STAR": 0.45,
        "MIXING_CHAIN": 0.35,
        "COORDINATED_CLUSTER": 0.40,
    }

    def _mock_analyze(
        self,
        action: dict[str, Any],
        graph: dict[str, Any] | None = None,
    ) -> VisionOutput:
        ctx = action.get("context") or {}
        graph_summary = (graph or {}).get("summary") or {}
        cumulative = ctx.get("cumulative_flow") or {}
        global_flow = ctx.get("global_flow") or {}
        freq = float(ctx.get("frequency_last_minute", 0) or 0)
        amount = float(action.get("amount_usdc", 0.0) or 0.0)

        tx_count = int(cumulative.get("tx_count", 0) or 0)
        dest_count = int(global_flow.get("dest_count", 0) or 0)
        total_amount = float(global_flow.get("total_amount", 0.0) or 0.0)
        focus_tx_count = int(graph_summary.get("focus_tx_count", 0) or 0)
        peer_senders = int(graph_summary.get("focus_unique_peer_senders", 0) or 0)
        chain_count = int(graph_summary.get("chain_count", 0) or 0)
        unique_destinations = int(graph_summary.get("unique_destinations", 0) or 0)

        pattern = "NORMAL"
        confidence = 0.55
        evidence = "No suspicious topology inferred from behavioral proxies."

        if graph_summary:
            pattern = str(graph_summary.get("heuristic_pattern", "NORMAL")).upper()
            confidence = float(graph_summary.get("heuristic_confidence", 0.72) or 0.72)
            evidence = str(
                graph_summary.get(
                    "heuristic_evidence",
                    "Graph summary built from recent local flows.",
                )
            )[:220]

        if peer_senders >= 4 or (focus_tx_count >= 8 and freq >= 8):
            pattern = "DRAIN_STAR"
            confidence = 0.92
            evidence = (
                "Recent graph shows strong convergence toward one destination with "
                f"{peer_senders} peer senders and {focus_tx_count} focal transfers."
            )
        elif chain_count >= 2 and unique_destinations >= 3 and total_amount >= 0.3:
            pattern = "MIXING_CHAIN"
            confidence = 0.86
            evidence = (
                f"Recent activity rotates across {chain_count} chains and "
                f"{unique_destinations} destinations, suggesting a mixing route."
            )
        elif dest_count >= 5 and total_amount >= 1.0:
            pattern = "COORDINATED_CLUSTER"
            confidence = 0.87
            evidence = "Multi-destination concentration pattern suggests coordinated movement."
        elif tx_count >= 5 and amount <= 0.05 and freq >= 12:
            pattern = "MIXING_CHAIN"
            confidence = 0.84
            evidence = "Micro-transfer cascade profile suggests chain mixing behavior."

        return VisionOutput(
            pattern=pattern,
            confidence=confidence,
            risk_delta=self.PATTERN_TO_DELTA.get(pattern, 0.0),
            visual_evidence=evidence,
            model="Imina-Na-Stub-v1",
            inference_device="CPU-MOCK",
            inference_time_ms=5,
            graph_summary=graph_summary or None,
        )

    async def _vllm_analyze(
        self,
        action: dict[str, Any],
        graph: dict[str, Any] | None = None,
    ) -> VisionOutput:
        graph = graph or {}
        payload = {
            "model": settings.vision_model_name,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Imina Na. Return valid JSON only with keys: "
                        "pattern, confidence, risk_delta, visual_evidence, model. "
                        "Use the graph summary as the primary signal."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Infer blockchain graph risk signal from this action and graph payload.\n"
                        f"Action: {action}\n"
                        f"GraphSummary: {graph.get('summary', {})}\n"
                        f"GraphNodes: {graph.get('nodes', [])[:20]}\n"
                        f"GraphEdges: {graph.get('edges', [])[:30]}"
                    ),
                },
            ],
        }
        t0 = asyncio.get_running_loop().time()
        async with httpx.AsyncClient(timeout=settings.vision_timeout_s) as client:
            response = await client.post(settings.vision_endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

        content = (
            (((data.get("choices") or [{}])[0]).get("message") or {}).get("content")
            or "{}"
        )
        try:
            import json

            parsed = json.loads(content)
        except Exception:
            logger.warning("[IMINA_NA] invalid JSON from vision endpoint, using NORMAL")
            parsed = {}

        pattern = str(parsed.get("pattern", "NORMAL")).upper()
        confidence = float(parsed.get("confidence", 0.0) or 0.0)
        risk_delta = float(
            parsed.get("risk_delta", self.PATTERN_TO_DELTA.get(pattern, 0.0)) or 0.0
        )
        elapsed_ms = int((asyncio.get_running_loop().time() - t0) * 1000)
        return VisionOutput(
            pattern=pattern if pattern in self.PATTERN_TO_DELTA else "NORMAL",
            confidence=max(0.0, min(1.0, confidence)),
            risk_delta=max(0.0, min(0.7, risk_delta)),
            visual_evidence=str(parsed.get("visual_evidence", "vision_analysis_done"))[:220],
            model=str(parsed.get("model", settings.vision_model_name)),
            inference_device="AMD MI300X" if any(x in settings.vision_endpoint for x in ["localhost", "134.199.201.220"]) else "REMOTE",
            inference_time_ms=max(1, elapsed_ms),
            graph_summary=graph.get("summary") or None,
        )

    async def analyze(
        self,
        action: dict[str, Any],
        graph: dict[str, Any] | None = None,
    ) -> VisionOutput:
        if not settings.vision_enabled:
            return VisionOutput()

        if settings.vision_mock_mode:
            return self._mock_analyze(action, graph=graph)

        try:
            return await self._vllm_analyze(action, graph=graph)
        except Exception as exc:
            logger.warning(f"[IMINA_NA] vLLM analysis failed: {exc} — fallback mock")
            return self._mock_analyze(action, graph=graph)


imina_na_vision = IminaNaVision()
