import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Optional

# Import des modules
from modules.governance.dao_manager import DAOManager, GovernanceConfig, GovernanceLevel
from modules.credit.credit_scoring import CreditScoringSystem, CreditConfig

try:
    from modules.reputation.reputation_oracle import ReputationOracle, ReputationConfig
except ImportError:
    try:
        from modules.reputation.trust_graph import ReputationOracle
    except ImportError:
        ReputationOracle = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sigui Daemon", description="Point d'entrée principal pour l'Oracle Sigui V3.0")

# Initialisation des sous-systèmes
reputation_oracle = None
if ReputationOracle:
    try:
        reputation_oracle = ReputationOracle()
    except TypeError:
        # Fallback if config is required
        reputation_oracle = ReputationOracle(None)

credit_config = CreditConfig()
credit_config.ai_scoring_enabled = False
credit_scoring = CreditScoringSystem(credit_config, reputation_oracle)

gov_config = GovernanceConfig()
dao_manager = DAOManager(gov_config, reputation_oracle, credit_scoring)

@app.on_event("startup")
async def startup_event():
    logger.info("Démarrage du démon Sigui...")
    await credit_scoring.initialize()
    logger.info("Tous les sous-systèmes sont prêts et connectés.")

@app.get("/")
async def root():
    return {"message": "Sigui Daemon is running", "status": "secure", "version": "3.0"}

@app.get("/api/v1/dao/stats")
async def get_dao_stats():
    stats = dao_manager.get_dao_stats(GovernanceLevel.PROTOCOL)
    return {"protocol_dao_stats": stats or {}}

@app.get("/api/v1/credit/{did}/score")
async def get_credit_score(did: str):
    # Simulated call for API purpose
    score = await credit_scoring.calculate_credit_score(did, 0, [])
    return {"did": did, "score": score.overall_score, "risk_level": score.risk_level.value}

@app.websocket("/ws/sentinel")
async def sentinel_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Simulate real-time stats stream from daemon to Sentinel UI
            data = {
                "active_nodes": 1024,
                "threats_deflected": 142,
                "latency_ms": 42
            }
            await websocket.send_json(data)
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("Sentinel Web UI disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
