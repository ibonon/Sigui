"""
Real P2P Worker Node for NexusMind.
Connects to the Tracker (Sigui Gateway) and accepts direct P2P connections.
"""
import asyncio
import hashlib
import json
import os
import random
import sys
import time

import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

app = FastAPI(title="NexusMind P2P Worker")

PORT = int(os.getenv("PORT", 8001))
NODE_ID = f"nexus_node_{PORT}"
TRACKER_URL = "http://localhost:8000"
TRACKER_WS = "ws://localhost:8000/nexusmind/ws/tracker"

# P2P State
peers = set()
active_tasks = {}

class WSManager:
    def __init__(self):
        self.active_connections = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = WSManager()

def compute_prime(target: int) -> int:
    """Inefficient prime calculation to simulate work."""
    count = 0
    num = 2
    while count < target:
        is_prime = True
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                is_prime = False
                break
        if is_prime:
            count += 1
        num += 1
    return num - 1

def compute_hash(data: str, difficulty: int) -> str:
    """Proof of work hash."""
    nonce = 0
    prefix = "0" * difficulty
    while True:
        text = f"{data}{nonce}".encode('utf-8')
        h = hashlib.sha256(text).hexdigest()
        if h.startswith(prefix):
            return h
        nonce += 1

@app.on_event("startup")
async def startup_event():
    logger.info(f"[{NODE_ID}] Starting P2P Node on port {PORT}")
    asyncio.create_task(connect_to_tracker())
    asyncio.create_task(background_task_generator())

async def connect_to_tracker():
    """Connect to Sigui Gateway tracker to discover peers and register."""
    # First, register via HTTP
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{TRACKER_URL}/nexusmind/nodes/register", json={
                "node_id": NODE_ID,
                "address": f"0x_worker_{PORT}",
                "capabilities": {"gpu": "CPU_ONLY", "imina_na": False}
            })
            logger.info(f"[{NODE_ID}] Registered with Tracker: {resp.status_code}")
    except Exception as e:
        logger.error(f"[{NODE_ID}] Failed to register: {e}")

    # Then connect via WS
    while True:
        try:
            import websockets
            async with websockets.connect(TRACKER_WS) as ws:
                logger.info(f"[{NODE_ID}] Connected to Tracker WS")
                await ws.send(json.dumps({"type": "announce", "node_id": NODE_ID, "port": PORT}))
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data["type"] == "peer_list":
                        new_peers = set(data["peers"]) - {PORT}
                        peers.update(new_peers)
                        logger.info(f"[{NODE_ID}] Updated peers: {peers}")
                    elif data["type"] == "task":
                        # Execute task requested by tracker
                        asyncio.create_task(handle_task(data["task_id"], data["task_type"], data["payload"], ws))
        except Exception as e:
            logger.error(f"[{NODE_ID}] Tracker WS disconnected: {e}. Retrying in 5s...")
            await asyncio.sleep(5)

async def handle_task(task_id: str, task_type: str, payload: dict, tracker_ws):
    logger.info(f"[{NODE_ID}] Starting task {task_id} ({task_type})")
    start = time.time()
    
    result = None
    if task_type == "prime":
        # Run in executor to not block async loop
        result = await asyncio.to_thread(compute_prime, payload.get("target", 1000))
    elif task_type == "hash":
        result = await asyncio.to_thread(compute_hash, payload.get("data", "nexus"), payload.get("difficulty", 4))
    
    elapsed = (time.time() - start) * 1000
    logger.info(f"[{NODE_ID}] Completed {task_id} in {elapsed:.2f}ms")
    
    await tracker_ws.send(json.dumps({
        "type": "task_result",
        "node_id": NODE_ID,
        "task_id": task_id,
        "result": result,
        "latency_ms": elapsed
    }))

async def background_task_generator():
    """Periodically generate and send tasks to peers to create real network traffic."""
    while True:
        await asyncio.sleep(random.uniform(5, 15))
        if not peers:
            continue
        target_port = random.choice(list(peers))
        task_id = f"task_{random.randint(1000, 9999)}"
        
        try:
            import websockets
            async with websockets.connect(f"ws://localhost:{target_port}/ws/p2p") as ws:
                payload = {
                    "type": "p2p_task",
                    "task_id": task_id,
                    "task_type": random.choice(["prime", "hash"]),
                    "payload": {"target": random.randint(100, 500)} if random.choice([True, False]) else {"data": "p2p_test", "difficulty": 3},
                    "sender": NODE_ID
                }
                await ws.send(json.dumps(payload))
                logger.info(f"[{NODE_ID}] Sent P2P task {task_id} to port {target_port}")
                res = await ws.recv()
                logger.info(f"[{NODE_ID}] Received P2P result for {task_id}: {res}")
        except Exception as e:
            logger.warning(f"[{NODE_ID}] Failed to send P2P task to {target_port}: {e}")
            peers.remove(target_port)

@app.websocket("/ws/p2p")
async def p2p_endpoint(websocket: WebSocket):
    """Endpoint for other peers to connect to."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            if msg["type"] == "p2p_task":
                task_id = msg["task_id"]
                logger.info(f"[{NODE_ID}] Received P2P task {task_id} from {msg['sender']}")
                # Mock fast computation for P2P test
                await asyncio.sleep(0.5)
                await websocket.send_text(json.dumps({
                    "task_id": task_id,
                    "status": "completed",
                    "result": "p2p_computed_ok"
                }))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
