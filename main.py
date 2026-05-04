"""
ArcWarden v3.0 — Main Entry Point
FastAPI lifespan: DB init → Treasury recovery → Treasury sync → Agent loop → Serve

Run with:
    uvicorn main:app --reload --port 8000
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from agent.loop import agent
from clients.integrations import arc_client
from clients.threat_registry import threat_registry
from config import settings
from ecosystem.orchestrator import ecosystem_orchestrator
from modules.ai_engines import policy_brain
from modules.memory import memory
from modules.response_validator import response_validator
from modules.service_registry import service_registry
from modules.treasury import treasury


# ── Structured logging — console + rotating file sink ────────────────────────
def _configure_logging():
    """
    Configure loguru:
    - stderr: coloured, human-readable (INFO+)
    - logs/arcwarden_YYYY-MM-DD.log: JSON-style, rotation 100 MB, 7 days retention
    """
    logger.remove()  # Drop the default handler

    # Console — coloured, concise
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
            "<level>{message}</level>"
        ),
        colorize=True,
        enqueue=True,
    )

    # File — structured, rotated, compressed
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logger.add(
        log_dir / "arcwarden_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} — {message}",
        rotation="100 MB",
        retention="7 days",
        compression="zip",
        enqueue=True,  # Thread-safe async-compatible
        serialize=False,
    )


_configure_logging()


# ── OpenAPI tag groups ────────────────────────────────────────────────────────
_OPENAPI_TAGS = [
    {
        "name": "Infrastructure",
        "description": "Health checks and agent discoverability (A2A card).",
    },
    {
        "name": "Treasury",
        "description": "Real-time P&L, USDC balance and autonomous mode state.",
    },
    {
        "name": "Security",
        "description": (
            "**Core evaluation pipeline** — gated by x402 micro-payment. "
            "POST `/evaluate` ($0.001 USDC) → ALLOW / BLOCK / ESCALATE. "
            "POST `/escalate` ($0.003 USDC) → Claude deep analysis."
        ),
    },
    {
        "name": "Statistics",
        "description": "Decision counts, MemoClaw patterns, adaptive policy thresholds.",
    },
    {
        "name": "Simulation",
        "description": "Launch and monitor the 5-agent autonomous ecosystem.",
    },
    {
        "name": "Services",
        "description": "Service registry — reputation scores, flow windows, anti-splitting.",
    },
    {
        "name": "Demo",
        "description": (
            "SSE live feed (`/demo/live`) and submission-grade compliance report (`/demo/report`). "
            "No auth required — designed for jury dashboards."
        ),
    },
]


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ordered startup sequence:
      1. MemoClaw (SQLite) initialisation
      2. Service Registry bootstrap
      3. PolicyBrain threshold reload
      4. Treasury DB injection
      5. Treasury recovery from persistent log  ← survives restarts
      6. Treasury sync from Circle API
      7. Arc L1 client initialisation
      8. Autonomous agent loop start
      9. Collective Intelligence sync from onchain
     10. Ecosystem orchestrator registration (NOT started — waits for /simulate)
     11. ThreatRegistry Vyper contract client  ← onchain attack recording
    """
    logger.info("=" * 60)
    logger.info("  🛡️  ArcWarden v3.0 — Autonomous Security Oracle")
    logger.info("  Hackathon: Agentic Economy on ARC · lablab.ai")
    logger.info(f"  DEMO_MODE={settings.demo_mode}  |  DB={settings.db_path}")
    logger.info("=" * 60)

    # 1 ── MemoClaw (SQLite)
    await memory.initialize()
    logger.info("[MAIN] ✅ MemoClaw initialized")

    # 2 ── Service Registry
    await service_registry.initialize()
    logger.info("[MAIN] ✅ Service Registry ready")

    # 2b ── Response Validator — no explicit init needed (uses aiosqlite directly)
    #        Schema tables created by memory.initialize() above via schema.sql
    logger.info(
        "[MAIN] ✅ Response Validator ready "
        "(injection · statistical · schema · historical · poisoning)"
    )

    # 3 ── PolicyBrain — reload adaptive thresholds from last self_critique
    await policy_brain.initialize()
    logger.info("[MAIN] ✅ PolicyBrain initialized")

    # 4 ── Inject DB into Treasury
    treasury.set_db(memory)

    # 5 ── Treasury recovery — reconstruct P&L from persistent treasury_log
    #       This ensures the agent "remembers" its balance across restarts.
    try:
        await treasury.recover_from_db()
    except Exception as e:
        logger.warning(
            f"[MAIN] Treasury recovery failed ({e}) — starting from initial state"
        )

    # 6 ── Treasury sync — pull live balance from Circle API (or demo simulation)
    try:
        await treasury.sync_from_circle()
        mode = treasury.operating_mode
        logger.info(
            f"[MAIN] ✅ Treasury ready — "
            f"balance=${treasury.balance:.4f}  "
            f"earned=${treasury.net_profit + treasury._state.total_spent:.4f}  "  # total_earned
            f"mode={mode.value}"
        )
    except Exception as e:
        logger.warning(
            f"[MAIN] Treasury sync failed ({e}) — using recovered/local state"
        )
        logger.info(
            f"[MAIN] Treasury ready — balance=${treasury.balance:.4f} mode=DEGRADED"
        )

    # 7 ── Arc L1 client
    try:
        await arc_client.initialize()
        logger.info(f"[MAIN] ✅ Arc client ready — demo={arc_client.demo_mode}")
    except Exception as e:
        logger.warning(f"[MAIN] Arc client init failed ({e}) — demo mode active")

    # 8 ── Autonomous agent loop (100 ms cycles)
    await agent.start()
    logger.info("[MAIN] ✅ Agent core loop started (100 ms cycles)")

    # 9 ── ThreatRegistry smart contract (Vyper on Arc L1)
    #       Connects to the deployed ThreatRegistry if THREAT_REGISTRY_ADDRESS is set.
    #       Run python scripts/deploy_contract.py to deploy and set the address.
    try:
        registry_ok = await threat_registry.initialize()
        if registry_ok:
            registry_stats = await threat_registry.get_stats()
            logger.success(
                f"[MAIN] ✅ ThreatRegistry contract connected — "
                f"onchain_attacks={registry_stats.get('total_attacks_onchain', 0)} "
                f"usdc_protected=${registry_stats.get('total_usdc_protected_usdc', 0):.4f}"
            )
        else:
            logger.info(
                "[MAIN] ⚠  ThreatRegistry not configured — "
                "run: python scripts/deploy_contract.py"
            )
    except Exception as _e:
        logger.warning(
            f"[MAIN] ThreatRegistry init failed ({_e}) — continuing without it"
        )

    # 10 ── Ecosystem orchestrator — registered but NOT started
    #       Started lazily on POST /simulate
    app.state.ecosystem_orchestrator = ecosystem_orchestrator
    logger.info("[MAIN] ✅ Ecosystem orchestrator registered (awaiting POST /simulate)")

    # ── Startup diagnostics ───────────────────────────────────────────────────
    val_stats = await response_validator.get_global_stats()
    logger.info(
        f"[MAIN] Response Validator history — "
        f"total={val_stats['total']} "
        f"poisoned={val_stats['poisoned']} "
        f"suspicious={val_stats['suspicious']}"
    )

    # ── Ready ─────────────────────────────────────────────────────────────────
    logger.success("=" * 60)
    logger.success("  🟢 ArcWarden ready")
    logger.success("  API   → http://localhost:8000")
    logger.success("  Docs  → http://localhost:8000/docs")
    logger.success("  POST /validate-response — Response poisoning detection")
    logger.success(
        f"  ThreatRegistry → {'ENABLED' if threat_registry.is_enabled else 'disabled (deploy contract first)'}"
    )
    logger.success("  Logs  → logs/arcwarden_<date>.log")
    logger.success("=" * 60)

    yield  # ── App serves requests here ──────────────────────────────────────

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    logger.info("[MAIN] Shutting down ArcWarden…")
    await agent.stop()
    await ecosystem_orchestrator.stop()
    await memory.close()
    logger.info("[MAIN] ✅ ArcWarden shutdown complete")


# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(
    title="ArcWarden Security Oracle",
    description=(
        "**ArcWarden** is an autonomous economic agent that sells security services "
        "to other agents in the Arc ecosystem.\n\n"
        "- Receives USDC payments via the **x402** protocol\n"
        "- Evaluates every request with a numpy Risk Engine → ALLOW / BLOCK / ESCALATE\n"
        "- Pays **Claude API** for deep analysis from its own treasury\n"
        "- Logs every decision immutably on **Arc L1 testnet**\n"
        "- Learns via **MemoClaw** — reducing latency on known attack patterns\n\n"
        "*The loop is entirely closed. Zero human intervention.*"
    ),
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=_OPENAPI_TAGS,
    lifespan=lifespan,
    contact={
        "name": "Eric Warma",
        "url": "https://lablab.ai",
    },
    license_info={
        "name": "MIT",
    },
)

# ── CORS — open for demo/jury dashboards ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Intentionally open — demo mode only
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all routes and middleware from gateway ───────────────────────────
from modules.gateway import register_routes  # noqa: E402

register_routes(app)
