"""
ArcWarden v3.0 — Agent Loop & Policy
Autonomous 100ms asyncio loop — mode management, self-monitoring, and dynamic policy logic.
"""
import asyncio
from enum import Enum
from loguru import logger

# ────────────────────────────────────────────────────────────────────────────────
# Policy & Core Definitions
# ────────────────────────────────────────────────────────────────────────────────
class AgentMode(str, Enum):
    """ArcWarden operational modes — driven by treasury health."""
    NORMAL    = "NORMAL"      # Balance > $0.50 — all functions active, full escalation
    DEGRADED  = "DEGRADED"    # Balance $0.10–$0.50 — escalation only for R > 0.55
    EMERGENCY = "EMERGENCY"   # Balance < $0.10 — rules only, no Claude

# ── Treasury thresholds
BALANCE_NORMAL_THRESHOLD    = 0.50
BALANCE_DEGRADED_THRESHOLD  = 0.10
BALANCE_EMERGENCY_THRESHOLD = 0.01

# ── Risk thresholds
RISK_ALLOW_THRESHOLD    = 0.35
RISK_BLOCK_THRESHOLD    = 0.65

# ── Escalation policy per mode
ESCALATION_RISK_MIN = {
    AgentMode.NORMAL:    0.35,
    AgentMode.DEGRADED:  0.55,
    AgentMode.EMERGENCY: 1.00,
}

# ── Trust score & Pattern weights
TRUST_GAIN_ON_ALLOW      =  0.02
TRUST_LOSS_ON_BLOCK      = -0.15
TRUST_MAX                =  0.99
TRUST_MIN                =  0.01

PATTERN_INITIAL_WEIGHT   = 0.35
PATTERN_WEIGHT_INCREMENT = 0.05
PATTERN_WEIGHT_MAX       = 0.95
PATTERN_DECAY_PER_DAY    = 0.01
PATTERN_DECAY_FLOOR      = 0.05

def determine_mode(balance: float) -> AgentMode:
    """Determine operational mode based on treasury balance."""
    if balance >= BALANCE_NORMAL_THRESHOLD: return AgentMode.NORMAL
    if balance >= BALANCE_DEGRADED_THRESHOLD: return AgentMode.DEGRADED
    return AgentMode.EMERGENCY

def should_escalate(risk_score: float, mode: AgentMode) -> bool:
    """Check if escalation is allowed given current mode and risk score."""
    min_risk = ESCALATION_RISK_MIN.get(mode, 1.00)
    return min_risk <= risk_score < RISK_BLOCK_THRESHOLD

def is_self_protection(balance: float) -> bool:
    """Check if ArcWarden should refuse new requests (self-protection)."""
    return balance <= BALANCE_EMERGENCY_THRESHOLD


# ────────────────────────────────────────────────────────────────────────────────
# Agent Core Loop
# ────────────────────────────────────────────────────────────────────────────────
class ArcWardenAgent:
    """
    Autonomous agent loop.
    Runs at 100ms cycles, manages its own operational mode based on treasury health.
    """
    def __init__(self):
        self.cycle: int = 0
        self.running: bool = False
        self._task: asyncio.Task | None = None
        self._critique_pending: bool = False

    def request_critique(self):
        """Trigger an immediate self_critique on the next agent cycle."""
        self._critique_pending = True

    @property
    def mode(self) -> AgentMode:
        from modules.treasury import treasury
        try:
            return treasury.operating_mode
        except Exception:
            return AgentMode.EMERGENCY

    async def start(self):
        """Start the autonomous agent loop."""
        self.running = True
        self._task = asyncio.create_task(self.run(), name="arcwarden-core")
        logger.info("[AGENT] ArcWarden autonomous loop started (100ms cycles)")

    async def stop(self):
        """Gracefully stop the agent loop."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[AGENT] ArcWarden loop stopped")

    async def run(self):
        """Main autonomous loop."""
        from modules.treasury import treasury
        from modules.memory import memory
        from modules.ai_engines import policy_brain

        while self.running:
            try:
                if self.cycle % 30 == 0:
                    await treasury.sync_from_circle()

                if self.cycle % 600 == 0 and self.cycle > 0:
                    await memory.consolidate_patterns()

                # Only critique if specifically requested (avoids credit drain)
                if self._critique_pending:
                    self._critique_pending = False
                    await policy_brain.self_critique()

                # Reduced pulse frequency to 100s (1000 cycles) to minimize log noise
                if self.cycle % 1000 == 0:
                    mode = self.mode
                    bal = treasury.balance
                    profit = treasury.net_profit
                    stats = await memory.get_stats()
                    logger.info(
                        f"[AGENT] pulse cycle={self.cycle} mode={mode.value} "
                        f"balance=${bal:.4f} profit=${profit:.4f} decisions={stats['total']}"
                    )

                    if bal < 0.01:
                        logger.warning("[AGENT] 🚨 EMERGENCY — Treasury near-empty, entering self-protection")

            except Exception as e:
                logger.error(f"[AGENT] Unexpected error in cycle {self.cycle}: {e}")

            await asyncio.sleep(0.1)
            self.cycle += 1

agent = ArcWardenAgent()
