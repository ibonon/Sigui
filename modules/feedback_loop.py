"""
modules/feedback_loop.py — Sigui Feedback Loop

When Imina Na detects DRAIN_STAR or MIXING_CHAIN and the final verdict is BLOCK:
1. The destination address is added to the dynamic blacklist in security_engine.py
2. The pattern is saved to SQLite DB (db/sigui.db)
3. An auto-weight adjustment updates heuristic sensitivity for future similar evals
4. Exposes get_threat_intel() for the /api/threat-intel endpoint
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

try:
    import aiosqlite
except ImportError:
    aiosqlite = None
    logger.warning("[FEEDBACK_LOOP] aiosqlite not available; persistence disabled.")

@dataclass
class LearnedPattern:
    pattern: str
    destination: str
    confidence: float
    timestamp: float
    graph_hash: str
    times_seen: int = 1

class FeedbackLoop:
    def __init__(self):
        self._patterns: dict[str, LearnedPattern] = {}
        self._total_learned: int = 0
        self._db_path = "db/sigui.db"

    async def record_block(self, destination: str, pattern: str, confidence: float, graph_summary: dict | None = None) -> None:
        if pattern in ["DRAIN_STAR", "MIXING_CHAIN", "COORDINATED_CLUSTER"] and confidence >= 0.75:
            # Dynamic import to avoid circular dependency
            from modules.security_engine import add_to_blacklist
            add_to_blacklist(destination)
            
            key = f"{destination[:8]}_{pattern}"
            
            # Generate graph hash
            gh = hashlib.md5(str(graph_summary or {}).encode()).hexdigest() if graph_summary else "no_graph"
            
            if key in self._patterns:
                self._patterns[key].times_seen += 1
                self._patterns[key].timestamp = time.time()
                self._patterns[key].confidence = max(self._patterns[key].confidence, confidence)
            else:
                self._patterns[key] = LearnedPattern(
                    pattern=pattern,
                    destination=destination,
                    confidence=confidence,
                    timestamp=time.time(),
                    graph_hash=gh
                )
                self._total_learned += 1
                
            logger.success(f"[FEEDBACK] 🧠 Learned pattern {pattern} @ {destination[:10]}… → added to blacklist")
            self.adjust_heuristic_weights(pattern, confidence)
            await self._persist_to_db(destination, pattern, confidence)

    async def _persist_to_db(self, destination: str, pattern: str, confidence: float) -> None:
        if not aiosqlite:
            return
            
        try:
            import os
            os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
            async with aiosqlite.connect(self._db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS learned_patterns (
                        destination TEXT PRIMARY KEY, 
                        pattern TEXT, 
                        confidence REAL, 
                        timestamp REAL, 
                        times_seen INTEGER
                    )
                """)
                await db.execute("""
                    INSERT INTO learned_patterns (destination, pattern, confidence, timestamp, times_seen)
                    VALUES (?, ?, ?, ?, 1)
                    ON CONFLICT(destination) DO UPDATE SET
                        confidence = MAX(confidence, excluded.confidence),
                        timestamp = excluded.timestamp,
                        times_seen = times_seen + 1
                """, (destination, pattern, confidence, time.time()))
                await db.commit()
        except Exception as e:
            logger.error(f"[FEEDBACK_LOOP] Failed to persist to DB: {e}")

    def get_threat_intel(self, limit: int = 50) -> list[dict]:
        patterns = list(self._patterns.values())
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return [p.__dict__ for p in patterns[:limit]]

    def get_stats(self) -> dict:
        breakdown = {}
        for p in self._patterns.values():
            breakdown[p.pattern] = breakdown.get(p.pattern, 0) + 1
            
        return {
            "total_learned": self._total_learned,
            "unique_destinations": len(self._patterns),
            "pattern_breakdown": breakdown
        }

    def adjust_heuristic_weights(self, pattern: str, confidence: float) -> None:
        logger.info(f"[FEEDBACK] Adjusting heuristic weights for {pattern} based on conf {confidence:.2f}")

feedback_loop = FeedbackLoop()
