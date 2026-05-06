"""
Sigui P1 — Kanaga Risk Aggregator (PyTorch ROCm with CPU fallback)
"""

from __future__ import annotations

from dataclasses import dataclass

from config import settings

try:
    import torch

    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False


@dataclass
class KanagaOutput:
    risk_score: float
    device: str
    components: dict[str, float]
    deltas: dict[str, float]


class KanagaEngine:
    def __init__(self):
        self._weights = [0.55, 0.30, 0.15]

    def _select_device(self) -> str:
        if not TORCH_AVAILABLE:
            return "CPU-NUMPY"
        if settings.kanaga_prefer_gpu and torch.cuda.is_available():
            return "AMD MI300X"
        return "CPU-TORCH"

    def compute(
        self,
        components: dict[str, float],
        deltas: dict[str, float] | None = None,
    ) -> KanagaOutput:
        deltas = deltas or {}
        a = float(components.get("action", 0.0))
        c = float(components.get("context", 0.0))
        h = float(components.get("history", 0.0))
        flow = float(deltas.get("flow", 0.0))
        service = float(deltas.get("service", 0.0))
        contract = float(deltas.get("contract", 0.0))
        vision = float(deltas.get("vision", 0.0))

        device = self._select_device()
        if TORCH_AVAILABLE:
            target = "cuda" if device == "AMD MI300X" else "cpu"
            w = torch.tensor(self._weights, dtype=torch.float32, device=target)
            base = torch.tensor([a, c, h], dtype=torch.float32, device=target)
            score = float(torch.clamp(torch.dot(w, base), 0.0, 1.0).item())
        else:
            score = max(0.0, min(1.0, self._weights[0] * a + self._weights[1] * c + self._weights[2] * h))

        final = max(0.0, min(1.0, score + flow + service + contract + vision))
        return KanagaOutput(
            risk_score=round(final, 4),
            device=device,
            components={"action": a, "context": c, "history": h},
            deltas={
                "flow": flow,
                "service": service,
                "contract": contract,
                "vision": vision,
            },
        )


kanaga_engine = KanagaEngine()
