"""
Sigui P4 — Benchmark helpers for dashboard/API.
"""

from __future__ import annotations

from modules.memory import memory


class BenchmarkService:
    async def get_metrics(self) -> dict:
        cpu_baseline_ms = 40.0
        gpu_baseline_ms = 5.0
        vision_baseline_ms = 18.0

        recent = await memory.run_query(
            """
            SELECT processing_time_ms, decision
            FROM decisions
            ORDER BY timestamp DESC
            LIMIT 200
            """,
            fetch="all",
        )

        if not recent:
            avg_ms = gpu_baseline_ms
            block_rate = 0.0
        else:
            values = [float(r["processing_time_ms"] or 0.0) for r in recent]
            avg_ms = max(1.0, sum(values) / max(1, len(values)))
            blocks = sum(1 for r in recent if str(r["decision"]) == "BLOCK")
            block_rate = blocks / max(1, len(recent))

        speedup_vs_cpu = round(cpu_baseline_ms / max(1.0, avg_ms), 2)
        return {
            "risk_engine": {
                "cpu_baseline_ms": cpu_baseline_ms,
                "runtime_avg_ms": round(avg_ms, 2),
                "target_gpu_ms": gpu_baseline_ms,
                "speedup_vs_cpu": speedup_vs_cpu,
            },
            "vision_layer": {
                "baseline_ms": vision_baseline_ms,
                "target_ms": vision_baseline_ms,
            },
            "quality": {
                "block_rate_recent": round(block_rate, 4),
                "sample_size": len(recent or []),
            },
        }


benchmark_service = BenchmarkService()
