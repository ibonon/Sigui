"""
ArcWarden v3.0 — MemoClaw (Memory Layer)
aiosqlite-based persistent memory with pattern learning
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Optional

import aiosqlite
from loguru import logger

from config import settings


class MemoClaw:
    """Persistent memory layer — tracks agents, patterns, decisions, attacks."""

    def __init__(self):
        self.db_path = settings.db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
        # LRU cache for top attack patterns (refreshed every 60s)
        self._pattern_cache: dict[str, float] = {}
        # BUG FIX #1: In-memory mirror of the persistent SQLite blacklist.
        # Populated by _load_persistent_blacklist() on startup and
        # add_to_persistent_blacklist() at runtime. Prevents getattr() guard
        # from silently masking a NameError in is_known_drain_contract().
        self._persistent_blacklist: set[str] = set()

    async def initialize(self):
        """Initialize DB + schema."""
        import os

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Increase timeout and use a single connection for the entire app life
        self._db = await aiosqlite.connect(self.db_path, timeout=60.0)
        self._db.row_factory = aiosqlite.Row
        
        # Optimize for concurrency
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute("PRAGMA synchronous=NORMAL;")
        await self._db.execute("PRAGMA busy_timeout=60000;")
        
        with open("db/schema.sql", "r") as f:
            schema = f.read()
        await self._db.executescript(schema)
        await self._db.commit()
        await self._refresh_pattern_cache()
        await self._load_persistent_blacklist()
        await self.unfreeze_expired()
        logger.info("[MEMOCLAW] Initialized — database ready (WAL mode enabled)")

    async def close(self):
        if self._db:
            await self._db.close()

    # ────────────────────────────────────────────────────────────────────────────
    # Agent Profile
    # ────────────────────────────────────────────────────────────────────────────

    async def get_agent(self, agent_id: str) -> dict:
        """Return agent profile or empty default."""
        async with self._lock:
            async with self._db.execute(
                "SELECT * FROM agents WHERE agent_id = ?", (agent_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return {
                    "agent_id": agent_id,
                    "wallet_address": "0x0000000000000000000000000000000000000000",
                    "trust_score": 0.5,
                    "tx_count": 0,
                    "avg_amount_usdc": 0.0,
                    "total_blocked": 0,
                }

    async def ensure_agent(
        self,
        agent_id: str,
        wallet_address: str = "0x0000000000000000000000000000000000000000",
    ):
        """Insert agent if not exists."""
        async with self._lock:
            await self._db.execute(
                """INSERT OR IGNORE INTO agents (agent_id, wallet_address)
                   VALUES (?, ?)""",
                (agent_id, wallet_address),
            )
            await self._db.commit()

    async def update_agent_allow(self, agent_id: str, amount_usdc: float):
        """Update trust score and stats after ALLOW — Bayesian update."""
        agent = await self.get_agent(agent_id)
        tx_count = agent["tx_count"] + 1
        avg = (agent["avg_amount_usdc"] * agent["tx_count"] + amount_usdc) / tx_count
        # Bayesian update: gain diminishes as agent accumulates history
        # stability → 0 when brand-new, → 1 when established (100+ tx)
        stability = 1.0 - (1.0 / (1.0 + tx_count * 0.10))
        trust_gain = 0.020 * (1.0 - stability) + 0.002 * stability
        new_trust = min(0.92, agent["trust_score"] + trust_gain)
        async with self._lock:
            await self._db.execute(
                """UPDATE agents
                   SET tx_count = ?, avg_amount_usdc = ?, trust_score = ?, last_seen = CURRENT_TIMESTAMP
                   WHERE agent_id = ?""",
                (tx_count, avg, new_trust, agent_id),
            )
            await self._db.commit()

    async def penalize_risky_allow(self, agent_id: str, amount_usdc: float):
        """Penalize trust when a risky action passed as ALLOW."""
        agent = await self.get_agent(agent_id)
        new_trust = max(0.01, agent["trust_score"] - 0.25)
        async with self._lock:
            await self._db.execute(
                """UPDATE agents
                   SET trust_score = ?, total_blocked = total_blocked + 1, last_seen = CURRENT_TIMESTAMP
                   WHERE agent_id = ?""",
                (new_trust, agent_id),
            )
            await self._db.commit()

    async def update_agent_block(self, agent_id: str):
        """Reduce trust score after BLOCK — adaptive penalty based on history."""
        agent = await self.get_agent(agent_id)
        tx_count = agent["tx_count"]
        # Proportional penalty: severe for new agents, light for established ones
        if tx_count < 5:
            penalty = 0.20
        elif tx_count < 20:
            penalty = 0.10
        else:
            penalty = 0.05
        new_trust = max(0.01, agent["trust_score"] - penalty)
        new_blocked = agent["total_blocked"] + 1
        async with self._lock:
            await self._db.execute(
                """UPDATE agents
                   SET trust_score = ?, total_blocked = ?, last_seen = CURRENT_TIMESTAMP
                   WHERE agent_id = ?""",
                (new_trust, new_blocked, agent_id),
            )
            await self._db.commit()

    # ────────────────────────────────────────────────────────────────────────────
    # Pattern Detection
    # ────────────────────────────────────────────────────────────────────────────

    def _make_pattern_id(
        self, action_type: str, dest_prefix: str, amount_range: str
    ) -> str:
        raw = f"{action_type}:{dest_prefix}:{amount_range}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    async def check_pattern(
        self, action_type: str, destination: str, amount_usdc: float
    ) -> float:
        """Return extra risk weight if a known attack pattern matches. Uses cache."""
        dest_prefix = destination[:8] if destination else "0x000000"
        amount_range = "high" if amount_usdc > 1.0 else "low"
        pattern_id = self._make_pattern_id(action_type, dest_prefix, amount_range)
        return self._pattern_cache.get(pattern_id, 0.0)

    def _make_fuzzy_pattern_ids(
        self, action_type: str, destination: str, amount_usdc: float
    ) -> list[str]:
        """Generate pattern IDs at 3 precision levels × 5 amount brackets.
        Resistant to address variations: attacker changing dest[:8] still matches dest[:4].
        """
        dest = destination.lower() if destination else "0x000000"
        if amount_usdc < 0.1:
            bracket = "micro"
        elif amount_usdc < 1.0:
            bracket = "low"
        elif amount_usdc < 5.0:
            bracket = "medium"
        elif amount_usdc < 20.0:
            bracket = "high"
        else:
            bracket = "whale"
        return [
            hashlib.sha256(f"{action_type}:{dest[:8]}:{bracket}".encode()).hexdigest()[
                :16
            ],  # precis
            hashlib.sha256(f"{action_type}:{dest[:4]}:{bracket}".encode()).hexdigest()[
                :16
            ],  # moyen
            hashlib.sha256(f"{action_type}:any:{bracket}".encode()).hexdigest()[
                :16
            ],  # global
        ]

    async def check_pattern_fuzzy(
        self, action_type: str, destination: str, amount_usdc: float
    ) -> float:
        """Return max risk weight across all precision levels. Drop-in replacement for check_pattern."""
        ids = self._make_fuzzy_pattern_ids(action_type, destination, amount_usdc)
        return max((self._pattern_cache.get(pid, 0.0) for pid in ids), default=0.0)

    async def record_attack_pattern(
        self, action_type: str, destination: str, amount_usdc: float
    ):
        """Register or reinforce attack patterns at all fuzzy precision levels."""
        dest = destination.lower() if destination else "0x000000"
        if amount_usdc < 0.1:
            bracket = "micro"
        elif amount_usdc < 1.0:
            bracket = "low"
        elif amount_usdc < 5.0:
            bracket = "medium"
        elif amount_usdc < 20.0:
            bracket = "high"
        else:
            bracket = "whale"

        fuzzy_ids = self._make_fuzzy_pattern_ids(action_type, destination, amount_usdc)
        # Legacy pattern for backward compat
        legacy_id = self._make_pattern_id(
            action_type, dest[:8], "high" if amount_usdc > 1.0 else "low"
        )
        legacy_sig = (
            f"{action_type}|{dest[:8]}|{'high' if amount_usdc > 1.0 else 'low'}"
        )

        to_record: dict[str, str] = {legacy_id: legacy_sig}
        levels = [(dest[:8], "high"), (dest[:4], "medium"), ("any", "global")]
        for (dest_part, level_name), pid in zip(levels, fuzzy_ids):
            to_record[pid] = f"{action_type}|{dest_part}|{bracket}|{level_name}"

        async with self._lock:
            for pid, sig in to_record.items():
                async with self._db.execute(
                    "SELECT risk_weight, occurrences FROM patterns WHERE pattern_id = ?",
                    (pid,),
                ) as cursor:
                    row = await cursor.fetchone()
                if row:
                    new_weight = min(0.95, row["risk_weight"] + 0.05)
                    await self._db.execute(
                        """UPDATE patterns
                           SET risk_weight = ?, occurrences = occurrences + 1, last_seen = CURRENT_TIMESTAMP
                           WHERE pattern_id = ?""",
                        (new_weight, pid),
                    )
                else:
                    await self._db.execute(
                        """INSERT INTO patterns (pattern_id, signature, risk_weight, occurrences)
                           VALUES (?, ?, 0.35, 1)""",
                        (pid, sig),
                    )
            await self._db.commit()

        await self._refresh_pattern_cache()

    async def _refresh_pattern_cache(self):
        """Refresh in-memory cache with top 50 patterns (fuzzy levels need more slots)."""
        async with self._lock:
            async with self._db.execute(
                "SELECT pattern_id, risk_weight FROM patterns ORDER BY risk_weight DESC LIMIT 50"
            ) as cursor:
                rows = await cursor.fetchall()
        self._pattern_cache = {row["pattern_id"]: row["risk_weight"] for row in rows}

    async def log_attack(self, pattern_id: str, agent_id: str, amount: float):
        """Record a blocked attack in the attacks table."""
        async with self._lock:
            await self._db.execute(
                """INSERT INTO attacks (pattern_id, agent_id, amount_attempted_usdc, amount_saved_usdc)
                   VALUES (?, ?, ?, ?)""",
                (pattern_id, agent_id, amount, amount),
            )
            await self._db.commit()
        logger.info(f"[MEMOCLAW] 🛡️ Attack logged: pattern={pattern_id} agent={agent_id} saved=${amount:.2f}")

    # ────────────────────────────────────────────────────────────────────────────
    # Decision Logging
    # ────────────────────────────────────────────────────────────────────────────

    async def log_decision(
        self,
        agent_id: str,
        action_type: str,
        amount_usdc: float,
        destination: str,
        action_hash: str,
        decision: str,
        risk_score: float,
        confidence: float,
        rules_triggered: list[str],
        arc_tx_hash: str,
        arcwarden_mode: str,
        processing_time_ms: int,
    ):
        async with self._lock:
            await self._db.execute(
                """INSERT INTO decisions
                   (agent_id, action_type, amount_usdc, destination, action_hash,
                    decision, risk_score, confidence, rules_triggered,
                    arc_tx_hash, arcwarden_mode, processing_time_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent_id,
                    action_type,
                    amount_usdc,
                    destination,
                    action_hash,
                    decision,
                    risk_score,
                    confidence,
                    json.dumps(rules_triggered),
                    arc_tx_hash,
                    arcwarden_mode,
                    processing_time_ms,
                ),
            )
            await self._db.commit()

    async def learn_from_onchain(self, threats: list[dict]):
        """Integrate threats synced from the blockchain into local pattern memory."""
        if not threats:
            return

        async with self._lock:
            for threat in threats:
                pattern_id = threat["pattern_hash"]
                weight = float(threat["risk_score"])
                # BUG FIX #2: The `patterns` table has a NOT NULL `signature` column
                # and no `description` column. Using `description` caused an
                # OperationalError. We now write a proper signature and also update
                # occurrences + last_seen on conflict, matching record_attack_pattern().
                tx_preview = str(threat.get("tx_hash", "unknown"))[:10]
                pattern_preview = str(threat.get("pattern_hash", ""))[:8]
                signature = f"onchain|{tx_preview}|{pattern_preview}"

                await self._db.execute(
                    """
                    INSERT INTO patterns (pattern_id, signature, risk_weight, occurrences)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(pattern_id) DO UPDATE SET
                        risk_weight = MAX(risk_weight, EXCLUDED.risk_weight),
                        occurrences = occurrences + 1,
                        last_seen   = CURRENT_TIMESTAMP
                    """,
                    (pattern_id, signature, weight),
                )
            await self._db.commit()
        await self._refresh_pattern_cache()
        logger.info(f"[MEMOCLAW] Integrated {len(threats)} global threats into local memory")

    # ────────────────────────────────────────────────────────────────────────────
    # Dashboard Queries
    # ────────────────────────────────────────────────────────────────────────────

    async def get_recent_decisions(self, limit: int = 50) -> list[dict]:
        async with self._lock:
            async with self._db.execute(
                """SELECT * FROM decisions
                WHERE arc_tx_hash NOT LIKE '0xSIM_%'
                    AND arc_tx_hash NOT LIKE '0xERROR_%'
                    AND arc_tx_hash != ''
                ORDER BY timestamp DESC LIMIT ?""",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_stats(self) -> dict:
        async with self._lock:
            async with self._db.execute(
                """SELECT decision, COUNT(*) as cnt FROM decisions
                WHERE arc_tx_hash NOT LIKE '0xSIM_%'
                    AND arc_tx_hash NOT LIKE '0xERROR_%'
                    AND arc_tx_hash != ''
                GROUP BY decision"""
            ) as cursor:
                rows = await cursor.fetchall()
            counts = {r["decision"]: r["cnt"] for r in rows}

            async with self._db.execute(
                "SELECT COALESCE(SUM(amount_saved_usdc), 0) as saved FROM attacks"
            ) as cursor:
                saved = (await cursor.fetchone())["saved"]

            async with self._db.execute("SELECT COUNT(*) as cnt FROM patterns") as cursor:
                pattern_count = (await cursor.fetchone())["cnt"]

        return {
            "allow": counts.get("ALLOW", 0),
            "block": counts.get("BLOCK", 0),
            "escalate": counts.get("ESCALATE", 0),
            "total": sum(counts.values()),
            "usdc_saved": saved,
            "patterns_learned": pattern_count,
        }

    async def get_onchain_counts(self) -> dict:
        """
        Compte les tx simulées vs confirmées onchain.
        - simulated  : hashes commençant par 0xSIM_
        - confirmed  : hashes 0x... réels (ni SIM ni ERROR, non vides)
        Utilisé par le SSE /demo/live pour ne pas charger 5000 rows.
        """
        async with self._lock:
            async with self._db.execute(
                """
                SELECT
                    COUNT(CASE WHEN arc_tx_hash LIKE '0xSIM_%'
                                THEN 1 END)                                      AS simulated,
                    COUNT(CASE WHEN arc_tx_hash != ''
                               AND arc_tx_hash NOT LIKE '0xSIM_%'
                               AND arc_tx_hash NOT LIKE '0xERROR_%'
                                THEN 1 END)                                      AS confirmed,
                    COUNT(*)                                                     AS total
                FROM decisions
                """
            ) as cursor:
                row = await cursor.fetchone()

        simulated = int(row[0]) if row and row[0] else 0
        confirmed = int(row[1]) if row and row[1] else 0
        total = int(row[2]) if row and row[2] else 0
        return {
            "simulated_tx_count": simulated,
            "confirmed_onchain_tx_count": confirmed,
            "total_tx_count": total,
            "target_50_met": confirmed >= 50,
        }

    async def get_top_patterns(self, limit: int = 5) -> list[dict]:
        async with self._lock:
            async with self._db.execute(
                "SELECT * FROM patterns ORDER BY risk_weight DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_all_agents(self) -> list[dict]:
        async with self._lock:
            async with self._db.execute(
                "SELECT * FROM agents ORDER BY tx_count DESC"
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def log_episode(
        self,
        agent_id: str,
        action_type: str,
        decision: str,
        risk_score: float,
        policy_source: str,
        outcome_label: str = "unknown",
        notes: str = "",
    ):
        async with self._lock:
            await self._db.execute(
                """INSERT INTO episodic_memory
                   (agent_id, action_type, decision, risk_score, policy_source, outcome_label, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    agent_id,
                    action_type,
                    decision,
                    risk_score,
                    policy_source,
                    outcome_label,
                    notes,
                ),
            )
            await self._db.commit()

    async def get_recent_episodes(self, limit: int = 200) -> list[dict]:
        async with self._lock:
            async with self._db.execute(
                "SELECT * FROM episodic_memory ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def record_policy_update(
        self,
        allow_threshold: float,
        block_threshold: float,
        rationale: str,
        source: str = "self_critique",
    ):
        async with self._lock:
            await self._db.execute(
                """INSERT INTO policy_updates
                   (allow_threshold, block_threshold, rationale, source)
                   VALUES (?, ?, ?, ?)""",
                (allow_threshold, block_threshold, rationale, source),
            )
            await self._db.commit()

    async def get_latest_policy_update(self) -> dict | None:
        async with self._lock:
            async with self._db.execute(
                "SELECT * FROM policy_updates ORDER BY created_at DESC LIMIT 1"
            ) as cursor:
                row = await cursor.fetchone()
        return dict(row) if row else None

    # ────────────────────────────────────────────────────────────────────────────
    # MemoClaw Security — Agent Freeze & Persistent Blacklist
    # ────────────────────────────────────────────────────────────────────────────

    async def is_agent_frozen(self, agent_id: str) -> bool:
        """Return True if agent is currently frozen (unexpired freeze in DB)."""
        async with self._lock:
            async with self._db.execute(
                "SELECT 1 FROM agent_freeze WHERE agent_id = ? AND frozen_until > CURRENT_TIMESTAMP",
                (agent_id,),
            ) as cursor:
                return await cursor.fetchone() is not None

    async def freeze_agent(
        self, agent_id: str, frozen_until: str, reason: str = "auto-freeze"
    ):
        """Freeze an agent until the given timestamp (ISO format, UTC)."""
        async with self._lock:
            await self._db.execute(
                """INSERT INTO agent_freeze (agent_id, frozen_until, reason)
                   VALUES (?, ?, ?)
                   ON CONFLICT(agent_id) DO UPDATE SET
                     frozen_until = excluded.frozen_until,
                     reason       = excluded.reason,
                     block_count  = block_count + 1""",
                (agent_id, frozen_until, reason),
            )
            await self._db.commit()
        logger.warning(
            f"[MEMOCLAW] ❄️  Agent {agent_id} frozen until {frozen_until} — {reason}"
        )

    async def unfreeze_expired(self):
        """Remove expired freeze records from DB."""
        async with self._lock:
            await self._db.execute(
                "DELETE FROM agent_freeze WHERE frozen_until <= CURRENT_TIMESTAMP"
            )
            await self._db.commit()

    async def auto_freeze_check(
        self,
        agent_id: str,
        window_minutes: int = 5,
        threshold: int = 3,
        freeze_minutes: int = 10,
    ) -> bool:
        """Auto-freeze agent if blocked >= threshold times in the window. Returns True if frozen."""
        cutoff = (datetime.utcnow() - timedelta(minutes=window_minutes)).isoformat()
        async with self._lock:
            async with self._db.execute(
                "SELECT COUNT(*) as cnt FROM decisions WHERE agent_id = ? AND decision = 'BLOCK' AND timestamp > ?",
                (agent_id, cutoff),
            ) as cursor:
                row = await cursor.fetchone()
        if row and row["cnt"] >= threshold:
            frozen_until = (
                datetime.utcnow() + timedelta(minutes=freeze_minutes)
            ).isoformat()
            await self.freeze_agent(
                agent_id,
                frozen_until,
                f"auto: {row['cnt']} blocks in {window_minutes}min",
            )
            return True
        return False

    async def _load_persistent_blacklist(self):
        """Load persisted blacklist addresses into security_engine's in-memory set on startup."""
        try:
            from modules.security_engine import add_to_blacklist

            async with self._lock:
                async with self._db.execute("SELECT address FROM blacklist") as cursor:
                    rows = await cursor.fetchall()
            for row in rows:
                addr = row["address"]
                add_to_blacklist(addr)
                # BUG FIX #1 (cont.): also populate the MemoClaw-owned set so that
                # is_known_drain_contract() can do an O(1) in-memory lookup without
                # relying on the getattr() fallback.
                self._persistent_blacklist.add(addr)
            if rows:
                logger.info(
                    f"[MEMOCLAW] Loaded {len(rows)} blacklisted address(es) from DB"
                )
        except Exception as exc:
            logger.warning(f"[MEMOCLAW] Could not load persistent blacklist: {exc}")

    async def add_to_persistent_blacklist(
        self, address: str, reason: str = "auto", added_by: str = "system"
    ):
        """Add address to both the persisted DB blacklist and the in-memory set."""
        from modules.security_engine import add_to_blacklist

        normalized = address.lower()
        add_to_blacklist(normalized)
        # BUG FIX #1 (cont.): keep the MemoClaw-owned set in sync at runtime
        # so is_known_drain_contract() always reflects the latest state.
        self._persistent_blacklist.add(normalized)
        async with self._lock:
            await self._db.execute(
                """INSERT OR IGNORE INTO blacklist (address, reason, added_by)
                   VALUES (?, ?, ?)""",
                (normalized, reason, added_by),
            )
            await self._db.commit()
        logger.warning(
            f"[MEMOCLAW] 🚫 {address} added to persistent blacklist — {reason}"
        )

    async def is_known_drain_contract(self, address: str) -> bool:
        """
        Vérifie si une adresse est un contrat drain connu.
        Cherche dans :
          1. La blacklist persistante (en mémoire + SQLite)
          2. L'historique d'attaques MemoClaw (3+ attaques vers cette adresse)

        Utilisé par le Contract Inspector (couche 4 du Risk Engine).
        """
        addr = address.lower().strip()
        if not addr:
            return False

        # 1. Blacklist persistante (en mémoire — O(1))
        # getattr guard : _persistent_blacklist peut ne pas être initialisé
        # si la sous-classe ou le test ne l'a pas défini.
        if addr in getattr(self, "_persistent_blacklist", set()):
            return True

        async with self._lock:
            try:
                # 2. Table blacklist SQLite
                async with self._db.execute(
                    "SELECT 1 FROM blacklist WHERE address = ? LIMIT 1",
                    (addr,),
                ) as cur:
                    if await cur.fetchone():
                        return True

                # 3. Historique attaques : 3+ attaques vers cette destination
                async with self._db.execute(
                    "SELECT COUNT(*) FROM attacks WHERE pattern_id LIKE ?",
                    (f"%{addr[:10]}%",),
                ) as cur:
                    row = await cur.fetchone()
                    if row and int(row[0]) >= 3:
                        return True

            except Exception as exc:
                logger.debug(f"[MEMOCLAW] is_known_drain_contract check failed: {exc}")

        return False

    # ────────────────────────────────────────────────────────────────────────────
    # Flow Windows — Anti-Splitting / Sybil Detection
    # ────────────────────────────────────────────────────────────────────────────

    async def record_flow(self, agent_id: str, destination: str, amount: float):
        """Enregistre chaque transaction dans la fenêtre glissante (10 min)."""
        async with self._lock:
            await self._db.execute(
                "INSERT INTO flow_windows (agent_id, destination, amount_usdc)"
                " VALUES (?, ?, ?)",
                (agent_id, destination, amount),
            )
            # Nettoyage automatique des entrées > 10 minutes
            await self._db.execute(
                "DELETE FROM flow_windows WHERE timestamp < datetime('now', '-10 minutes')"
            )
            await self._db.commit()

    async def get_cumulative_flow(
        self,
        agent_id: str,
        destination: str,
        window_minutes: int = 10,
    ) -> dict:
        """
        Retourne le flux cumulé de cet agent vers cette destination
        dans les N dernières minutes.
        """
        async with self._lock:
            async with self._db.execute(
                """SELECT
                    COUNT(*)         AS tx_count,
                    SUM(amount_usdc) AS total_amount,
                    MAX(amount_usdc) AS max_single,
                    MIN(amount_usdc) AS min_single
                FROM flow_windows
                WHERE agent_id = ?
                    AND destination = ?
                    AND timestamp > datetime('now', ? || ' minutes')
                """,
                (agent_id, destination, f"-{window_minutes}"),
            ) as cur:
                row = await cur.fetchone()
        return {
            "tx_count": row["tx_count"] or 0,
            "total_amount": row["total_amount"] or 0.0,
            "max_single": row["max_single"] or 0.0,
            "min_single": row["min_single"] or 0.0,
        }

    async def get_global_flow(
        self,
        agent_id: str,
        window_minutes: int = 10,
    ) -> dict:
        """
        Retourne le flux cumulé de cet agent vers TOUTES destinations
        dans les N dernières minutes — détecte le splitting multi-dest.
        """
        async with self._lock:
            async with self._db.execute(
                """SELECT
                    COUNT(*)                    AS tx_count,
                    COUNT(DISTINCT destination) AS dest_count,
                    SUM(amount_usdc)            AS total_amount
                FROM flow_windows
                WHERE agent_id = ?
                    AND timestamp > datetime('now', ? || ' minutes')
                """,
                (agent_id, f"-{window_minutes}"),
            ) as cur:
                row = await cur.fetchone()
        return {
            "tx_count": row["tx_count"] or 0,
            "dest_count": row["dest_count"] or 0,
            "total_amount": row["total_amount"] or 0.0,
        }

    # ────────────────────────────────────────────────────────────────────────────
    # Consolidation (called every 60s by Agent Core)
    # ────────────────────────────────────────────────────────────────────────────

    async def consolidate_patterns(self):
        """Decay old patterns, refresh cache, clean expired freezes."""
        cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
        async with self._lock:
            await self._db.execute(
                """UPDATE patterns
                   SET risk_weight = MAX(0.05, risk_weight - 0.01)
                   WHERE last_seen < ?""",
                (cutoff,),
            )
            await self._db.commit()
        await self._refresh_pattern_cache()
        await self.unfreeze_expired()
        logger.debug("[MEMOCLAW] Pattern consolidation + freeze cleanup complete")

    async def log_treasury(self, tx_type: str, amount_usdc: float, description: str):
        """Thread-safe logging of treasury events."""
        async with self._lock:
            await self._db.execute(
                "INSERT INTO treasury_log (type, amount_usdc, description) VALUES (?, ?, ?)",
                (tx_type, amount_usdc, description),
            )
            await self._db.commit()

    # ────────────────────────────────────────────────────────────────────────────
    # Generic DB Access (to prevent 'database is locked' by multiple connections)
    # ────────────────────────────────────────────────────────────────────────────

    async def run_query(self, sql: str, params: tuple = (), fetch: str = "none"):
        """
        Execute a query using the central connection and global lock.
        fetch: 'none' | 'one' | 'all'
        """
        if not self._db:
            return None
            
        async with self._lock:
            # aiosqlite connection already has Row factory set in initialize()
            async with self._db.execute(sql, params) as cursor:
                if fetch == "one":
                    return await cursor.fetchone()
                if fetch == "all":
                    return await cursor.fetchall()
                await self._db.commit()
                return None


memory = MemoClaw()
