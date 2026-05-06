"""
Sigui P4 — Dataset stats helper.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


class DatasetStatsService:
    def __init__(self, annotations_path: str = "datasets/dogon/annotations.json"):
        self.annotations_path = Path(annotations_path)

    def get_stats(self) -> dict:
        if not self.annotations_path.exists():
            return {
                "available": False,
                "path": str(self.annotations_path),
                "samples_total": 0,
                "patterns": {},
            }
        try:
            rows = json.loads(self.annotations_path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "available": False,
                "path": str(self.annotations_path),
                "samples_total": 0,
                "patterns": {},
                "error": "invalid_json",
            }

        patterns = Counter(str(r.get("pattern", "UNKNOWN")) for r in rows)
        return {
            "available": True,
            "path": str(self.annotations_path),
            "samples_total": len(rows),
            "patterns": dict(patterns),
        }


dataset_stats_service = DatasetStatsService()
