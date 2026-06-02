"""
sigui.local.mock_server — Serveur FastAPI embarqué pour tester sans GPU

Permet de tester le SDK Sigui sans connexion à un serveur réel.
Simule des verdicts probabilistes basés sur des heuristiques simples.

Usage:
    from sigui.local import start_mock_server

    server = start_mock_server(port=8765)
    # → Le serveur démarre en background sur http://127.0.0.1:8765

    from sigui import SiguiClient
    async with SiguiClient(api_url="http://127.0.0.1:8765") as client:
        result = await client.evaluate(amount=1.0, destination="0xABC...")

    server.stop()  # Arrêt propre

Notes:
    - Ne nécessite aucun GPU
    - Aucun paiement réel n'est effectué
    - Idéal pour les tests d'intégration et les hackathons
"""
from __future__ import annotations

import hashlib
import random
import threading
import time
import uuid
from typing import Any, Optional
import asyncio

_uvicorn_available = False
_fastapi_available = False

try:
    import uvicorn  # type: ignore
    _uvicorn_available = True
except ImportError:
    pass

try:
    from fastapi import FastAPI  # type: ignore
    from fastapi.middleware.cors import CORSMiddleware  # type: ignore
    _fastapi_available = True
except ImportError:
    pass


# ── Known threat addresses for demo purposes ────────────────────────────────

_KNOWN_BAD = {
    "0x000000000000000000000000000000000000dead",
    "0x0000000000000000000000000000000000000001",
    "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
}

_KNOWN_GOOD = {
    "0xd8da6bf26964af9d7eed9e03e53415d37aa96045",  # vitalik.eth
    "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",  # USDC contract
}


def _compute_risk(amount: float, destination: str, action_type: str) -> tuple[float, str, str]:
    """Calcule un score de risque simulé avec des heuristiques simples."""
    dest_lower = destination.lower().strip()

    # Known bad address → BLOCK immédiatement
    if dest_lower in _KNOWN_BAD:
        return 0.97, "BLOCK", "Known malicious address in threat registry"

    # Known good address → APPROVE immédiatement
    if dest_lower in _KNOWN_GOOD:
        return 0.08, "APPROVE", "Verified contract address — low risk"

    # Heuristics
    risk = 0.15  # baseline

    # High amount → risk augmente
    if amount > 10_000:
        risk += 0.55
    elif amount > 1_000:
        risk += 0.30
    elif amount > 100:
        risk += 0.15
    elif amount > 10:
        risk += 0.05

    # Destination entropy
    if len(destination) < 10:
        risk += 0.25  # suspiciously short
    if destination.startswith("0x0000"):
        risk += 0.35  # zero-prefixed suspicious

    # Action type risks
    action_risks = {"transfer": 0.0, "swap": 0.08, "stake": 0.05, "withdraw": 0.12, "bridge": 0.18}
    risk += action_risks.get(action_type, 0.10)

    # Add small random noise
    risk += random.gauss(0, 0.04)
    risk = max(0.01, min(0.99, risk))

    # Determine verdict
    if risk >= 0.75:
        verdict = "BLOCK"
        reason = f"High-risk transaction detected (score={risk:.2f}). Pattern: elevated amount + suspicious destination."
    elif risk >= 0.45:
        verdict = "ESCALATE"
        reason = f"Ambiguous transaction (score={risk:.2f}). Manual review recommended."
    else:
        verdict = "APPROVE"
        reason = f"Transaction within acceptable risk parameters (score={risk:.2f})."

    return risk, verdict, reason


class MockSiguiServer:
    """
    Serveur mock Sigui embarqué dans le processus Python.

    Attributes:
        host: Adresse d'écoute (défaut: 127.0.0.1)
        port: Port d'écoute (défaut: 8765)
        url:  URL complète du serveur
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        if not _fastapi_available:
            raise ImportError(
                "fastapi is required for the mock server. "
                "Install it with: pip install sigui-sdk[mock] or pip install fastapi uvicorn"
            )
        if not _uvicorn_available:
            raise ImportError(
                "uvicorn is required for the mock server. "
                "Install it with: pip install uvicorn"
            )

        self.host = host
        self.port = port
        self.url = f"http://{host}:{port}"
        self._server: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._started = threading.Event()
        self._request_count = 0
        self._total_earned = 0.0
        self._active_connections = []
        self._background_tasks = set()

        self._app = self._build_app()

    def _build_app(self) -> "FastAPI":  # type: ignore
        from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect  # type: ignore
        from fastapi.middleware.cors import CORSMiddleware  # type: ignore
        from fastapi.responses import JSONResponse  # type: ignore

        app = FastAPI(
            title="Sigui Mock Server",
            description="Local mock server for Sigui Protocol SDK testing",
            version="1.0.0",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*", "http://localhost:3001", "http://127.0.0.1:3001"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        server_ref = self

        @app.get("/health")
        async def health():
            return {
                "status": "ok",
                "mode": "mock",
                "version": "mock-1.0.0",
                "requests_served": server_ref._request_count,
                "node_id": "mock-node-local",
                "uptime_seconds": int(time.time()),
            }

        @app.post("/evaluate")
        async def evaluate(request: Request):
            body = await request.json()
            amount = float(body.get("amount_usdc", 0))
            destination = str(body.get("destination", ""))
            action_type = str(body.get("action_type", "transfer"))

            risk, verdict, reason = _compute_risk(amount, destination, action_type)

            # Simulate processing time
            await _async_sleep(random.uniform(0.01, 0.04))

            server_ref._request_count += 1
            evaluation_price = 0.001
            server_ref._total_earned += evaluation_price

            action_hash = "0x" + hashlib.sha256(
                f"{destination}{amount}{time.time()}".encode()
            ).hexdigest()[:40]

            return JSONResponse({
                "decision": verdict,
                "risk_score": round(risk, 4),
                "confidence": round(1.0 - abs(risk - 0.5) * 0.4, 4),
                "reason": reason,
                "action_hash": action_hash,
                "arc_tx_log": f"mock://tx/{uuid.uuid4().hex[:12]}",
                "sigui_mode": "NORMAL",
                "escalation_available": verdict == "ESCALATE",
                "escalation_cost_usdc": 0.003,
                "policy_source": "mock_local_rules",
                "processing_time_ms": random.randint(8, 45),
                "vision_pattern": "NORMAL" if risk < 0.5 else "SUSPICIOUS",
                "vision_confidence": round(random.uniform(0.75, 0.97), 4),
                "evaluation_price_usdc": evaluation_price,
                "chain": body.get("chain", "ethereum"),
                "raw_signals": {
                    "behavioral": {"amount_percentile": min(99, int(amount / 10)), "velocity": "normal"},
                    "visual_topology": {"pattern": "star" if risk < 0.5 else "hub_and_spoke", "anomaly_score": round(risk * 0.8, 3)},
                    "financial": {"amount_usd": amount, "risk_tier": "low" if risk < 0.35 else "medium" if risk < 0.65 else "high"},
                    "provenance": "mock_local",
                },
            })

        @app.post("/escalate")
        async def escalate(request: Request):
            body = await request.json()
            amount = float(body.get("amount_usdc", 0))
            destination = str(body.get("destination", ""))
            action_type = str(body.get("action_type", "transfer"))

            risk, verdict, reason = _compute_risk(amount, destination, action_type)
            await _async_sleep(random.uniform(0.05, 0.15))

            server_ref._request_count += 1
            server_ref._total_earned += 0.003

            # Escalation tends to be more permissive (human-in-loop simulation)
            if verdict == "ESCALATE":
                verdict = "APPROVE" if risk < 0.6 else "BLOCK"

            return JSONResponse({
                "escalation_result": verdict,
                "cap_amount_usdc": min(amount, 500.0),
                "analysis": f"[MOCK ESCALATION] Deep analysis completed. {reason} "
                             f"Manual override applied. Final risk assessment: {risk:.3f}",
                "confidence": round(random.uniform(0.85, 0.97), 4),
                "paid_by_sigui": False,
                "claude_cost_usdc": 0.0,
                "arc_tx_log": f"mock://escalation/{uuid.uuid4().hex[:12]}",
                "fallback_used": False,
                "degraded_mode": False,
                "reason": reason,
                "inference_engine": "mock_local",
                "inference_device": "CPU",
            })

        @app.get("/treasury")
        async def treasury():
            return {
                "balance": round(server_ref._total_earned * 0.7, 6),
                "total_earned": round(server_ref._total_earned, 6),
                "total_spent": round(server_ref._total_earned * 0.3, 6),
                "net_profit": round(server_ref._total_earned * 0.7, 6),
                "mode": "MOCK",
                "balances_by_chain": {
                    "ethereum": round(server_ref._total_earned * 0.4, 6),
                    "starknet": round(server_ref._total_earned * 0.35, 6),
                    "aptos": round(server_ref._total_earned * 0.25, 6),
                },
            }

        @app.websocket("/ws/live")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            server_ref._active_connections.append(websocket)
            try:
                while True:
                    # Keep connection alive
                    await websocket.receive_text()
            except WebSocketDisconnect:
                server_ref._active_connections.remove(websocket)

        return app

    def start(self) -> "MockSiguiServer":
        """Démarre le serveur mock en background. Retourne self pour le chaînage."""
        import uvicorn  # type: ignore

        config = uvicorn.Config(
            self._app,
            host=self.host,
            port=self.port,
            log_level="debug",
        )
        self._server = uvicorn.Server(config)

        def _run():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Start background live stream generator
            task = loop.create_task(self._live_stream_generator())
            self._background_tasks.add(task)
            
            loop.run_until_complete(self._server.serve())

        self._thread = threading.Thread(target=_run, daemon=True, name="sigui-mock-server")
        self._thread.start()

        # Wait up to 3s for the server to be ready
        deadline = time.time() + 3.0
        while time.time() < deadline:
            try:
                import urllib.request
                urllib.request.urlopen(f"{self.url}/health", timeout=0.5)
                break
            except Exception:
                time.sleep(0.05)

        return self

    def stop(self):
        """Arrête le serveur mock proprement."""
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=2.0)

    async def _live_stream_generator(self):
        """Tâche de fond qui génère des transactions simulées et les streame aux WebSockets."""
        agents = ["agent_payer", "agent_attacker", "agent_learner", "agent_grayzone", "agent_monitor"]
        chains = ["arc", "ethereum", "solana"]
        
        while not (self._server and self._server.should_exit):
            await asyncio.sleep(random.uniform(0.3, 1.2))  # Generate 1-3 tx per second
            if not self._active_connections:
                continue
                
            amount = random.uniform(10, 5000)
            destination = f"0x{uuid.uuid4().hex[:40]}"
            # Randomly trigger a known bad address to show BLOCKs
            if random.random() < 0.15:
                destination = random.choice(list(_KNOWN_BAD))
                
            risk, verdict, reason = _compute_risk(amount, destination, "transfer")
            agent = random.choice(agents)
            
            payload = {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "treasury": {
                    "balance": round(self._total_earned * 0.7, 4),
                    "total_earned": round(self._total_earned, 4),
                    "total_spent": round(self._total_earned * 0.3, 4),
                    "net_profit": round(self._total_earned * 0.7, 4),
                    "mode": "NORMAL",
                    "balances_by_chain": {"arc": round(self._total_earned * 0.5, 4), "ethereum": round(self._total_earned * 0.5, 4)}
                },
                "decisions": {
                    "allow": max(10, int(self._request_count * 0.8)),
                    "block": max(2, int(self._request_count * 0.15)),
                    "escalate": max(1, int(self._request_count * 0.05)),
                    "total": self._request_count,
                    "usdc_saved": round(self._request_count * 25.5, 2),
                    "patterns_learned": 42
                },
                "recent_logs": [
                    {
                        "agent_id": agent,
                        "action_type": "transfer",
                        "amount_usdc": round(amount, 2),
                        "decision": verdict,
                        "risk_score": round(risk, 4),
                        "arc_tx_hash": f"0x{uuid.uuid4().hex[:40]}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        "processing_time_ms": random.randint(12, 45)
                    }
                ],
                "ecosystem": {
                    "running": True,
                    "agents": {
                        "agent_payer": {"status": "active", "transactions": 100},
                        "agent_attacker": {"status": "active", "transactions": 100},
                        "agent_learner": {"status": "active", "transactions": 100},
                        "agent_grayzone": {"status": "active", "transactions": 100},
                        "agent_monitor": {"status": "active", "transactions": 100}
                    }
                }
            }
            
            self._request_count += 1
            self._total_earned += 0.001
            
            dead_connections = []
            for ws in self._active_connections:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead_connections.append(ws)
            
            for ws in dead_connections:
                if ws in self._active_connections:
                    self._active_connections.remove(ws)

    def __enter__(self) -> "MockSiguiServer":
        return self.start()

    def __exit__(self, *_):
        self.stop()

    def __repr__(self) -> str:
        return f"MockSiguiServer(url={self.url!r}, requests={self._request_count})"


async def _async_sleep(seconds: float):
    """Async sleep helper."""
    import asyncio
    await asyncio.sleep(seconds)


def start_mock_server(
    port: int = 8765,
    host: str = "127.0.0.1",
) -> MockSiguiServer:
    """
    Démarre le serveur mock Sigui sur le port spécifié.

    Args:
        port: Port TCP à utiliser (défaut: 8765)
        host: Adresse d'écoute (défaut: 127.0.0.1)

    Returns:
        MockSiguiServer — objet serveur démarré. Appeler .stop() pour l'arrêter.

    Example:
        server = start_mock_server(port=8765)

        from sigui import SiguiClient
        async with SiguiClient(api_url=server.url) as client:
            result = await client.evaluate(amount=1.0, destination="0x123...")
            print(result.verdict)

        server.stop()

    Example (context manager):
        with start_mock_server() as server:
            # ...tests...
            pass  # server auto-stopped
    """
    server = MockSiguiServer(host=host, port=port)
    return server.start()
