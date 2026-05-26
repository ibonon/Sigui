"""
sigui.discovery — Node discovery and routing for Sigui Network.
"""
from __future__ import annotations

import httpx
import time
from typing import Optional, Dict


class NodeDiscovery:
    """
    Discovers and caches available Sigui nodes from the NexusMind registry.
    """

    def __init__(self, api_url: str = "http://localhost:8000"):
        self.api_url = api_url.rstrip("/")
        self._cache: list = []
        self._cache_time: float = 0
        self._cache_ttl: float = 30.0

    async def _fetch_nodes(self) -> list:
        now = time.time()
        if self._cache and (now - self._cache_time) < self._cache_ttl:
            return self._cache

        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.api_url}/nexusmind/nodes")
                resp.raise_for_status()
                data = resp.json()
                self._cache = data.get("nodes", [])
                self._cache_time = now
                return self._cache
            except Exception:
                return []

    async def get_best_node(
        self,
        needs_vision: bool = False,
        max_latency_ms: float = 1000.0,
    ) -> Optional[Dict]:
        """
        Fetch nodes, filter by capabilities and latency, and rank by reputation.
        """
        nodes = await self._fetch_nodes()
        if not nodes:
            return None

        candidates = [
            n for n in nodes
            if n.get("is_online", False) and n.get("is_sigui_worker", False)
        ]

        if needs_vision:
            vision_nodes = [
                n for n in candidates 
                if n.get("capabilities", {}).get("imina_na", False)
            ]
            if vision_nodes:
                candidates = vision_nodes

        latency_filtered = [
            n for n in candidates
            if n.get("stats", {}).get("avg_latency_ms", 0) <= max_latency_ms
        ]
        if latency_filtered:
            candidates = latency_filtered

        if not candidates:
            return None

        # Sort by ERC-8259 reputation score
        candidates.sort(key=lambda n: n.get("reputation_score", 0), reverse=True)
        return candidates[0]
