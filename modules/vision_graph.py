"""
Sigui P4 — Reuse the main graph builder for the vision dashboard.
"""

from __future__ import annotations

from modules.graph_builder import graph_builder_service


class VisionGraphService:
    async def get_agent_graph(self, agent_id: str, limit: int = 30) -> dict:
        graph = await graph_builder_service.build_for_agent(agent_id=agent_id)
        if limit <= 0:
            return graph
        graph["edges"] = graph.get("edges", [])[:limit]
        return graph


vision_graph_service = VisionGraphService()
