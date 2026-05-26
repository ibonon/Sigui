# 🛡️ Sigui × NexusMind — The Multichain DePIN Security Oracle

> **"NexusMind is the network. Sigui is the law."**

Sigui is a decentralized security infrastructure (DePIN) for AI agents, now fully integrated with **NexusMind**, a Real P2P distributed intelligence mesh network. Utilizing the massive parallel power of AMD MI300X GPUs, Sigui detects on-chain threats via visual graph analysis, while NexusMind orchestrates real-time decentralized compute nodes.

In < 50ms, the 5-layer Risk Engine, **Imina Na V2** vision model (trained on 1,000,000 samples), and MemoClaw memory return a verdict: `ALLOW / BLOCK / ESCALATE`. Blocked attacks are permanently recorded in `ThreatRegistry.vy` on Arc L1. The loop is fully closed. Zero human intervention.

---

## 🌐 NEW: NexusMind Real P2P Mesh Network
Sigui's network layer has been completely overhauled with **NexusMind**. Instead of a mock simulation, the system now runs a **real WebSockets P2P topology**.

### Core NexusMind Features
- **Real P2P Nodes (`nexus_worker.py`)**: Individual Python processes act as compute nodes, running actual asynchronous Proof-of-Work hashing and Matrix/Prime calculations.
- **Tracker & Gossip Protocol**: The Sigui Gateway doubles as a Bootstrap Tracker. Nodes announce their ports, receive the peer list, and gossip tasks to one another.
- **Scientific Network Telemetry**: The UI visualizes real-time network health, monitoring **Spectral Radius**, **Information Entropy (nats)**, and **Variance** to predict and prevent informational collapse.
- **Cinematic CRT Dashboard**: The Next.js dashboard features a new "P2P Network" view with an Echarts Force-Directed Map, live WebSockets terminal feed, and a hacker-style CRT overlay.

---

## 🌟 Agent Identity System (ERC-8259 Native)
Sigui includes a revolutionary Agent DID (Decentralized Identity) system that solves the fundamental problem of agent identity verification: reputation is cryptographically bound to identity, not disposable wallets.

- **Portable Reputation**: Reputation follows identity across wallets/chains.
- **Multi-Tier Verification**: Bronze → Silver → Gold → Platinum verification levels.
- **6-Factor Scoring**: Identity (25%) + Transactions (30%) + Verification (20%) + Cross-chain (10%) + Threat Intel (10%) + Insurance (5%).

---

## 🧠 Imina Na — The Vision Oracle
Traditional security engines use simple thresholds. Imina Na sees the attack topology.
- **Architecture**: Fine-tuned Qwen2-VL-2B-Instruct (LoRA)
- **Hardware**: AMD MI300X (ROCm stack) for training and inference
- **Dataset**: The Dogon Dataset — 10,000+ custom transaction graph topologies
- **Patterns detected**: DRAIN_STAR, MIXING_CHAIN, COORDINATED_CLUSTER

---

## ⚡ 30-Second Architecture
```text
AI Agent ──── POST /evaluate ($0.001) ────────────────────────────────────┐
                                                                          │
         ┌───────────────────────────────────────────────────────────┐    │
         │  Sigui × NexusMind Core                                   │    │
         │                                                           │    │
         │  ① Agent DID Check    (cryptographic identity)            │    │
         │  ② Behavior Engine    (numpy, < 2ms)                      │    │
         │  ③ Anti-Splitting     (flow tracking, cumulative USDC)    │    │
         │  ④ Imina Na Vision    (AMD MI300X ROCm, < 50ms)           │    │
         │  ⑤ NexusMind P2P      (real-time compute delegation)      │    │
         │                                                           │    │
         │  PolicyBrain ←→ LangGraph ←→ CrewAI (self-critique)       │    │
         └───────────────────────────────────────────────────────────┘    │
                                                                          │
         ALLOW  ──────────────────────────────────────────────────────────┘
         BLOCK  ──── ThreatRegistry.vy (Arc L1, permanent, immutable)
         ESCALATE ── Qwen2.5 (AMD MI300X) → Claude 3.5 fallback
```

---

## 🚀 Quick Start: Run the Real P2P Network

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Launch the Sigui Gateway / Tracker
```bash
pip install -r requirements.txt
pip install websockets
uvicorn main:app --port 8000 --reload
# Gateway API: http://localhost:8000
```

### 2. Launch NexusMind P2P Workers
Open multiple terminal tabs to start real compute nodes:
```bash
# Terminal A (Port 8001)
export PORT=8001 && python nexus_worker.py

# Terminal B (Port 8002)
export PORT=8002 && python nexus_worker.py
```

### 3. Launch the Cinematic Dashboard
```bash
cd demo-ui
npm install --legacy-peer-deps
npm run dev
# Dashboard: http://localhost:3000 (or 3003)
```

---

## 🆔 SDK Integration
Integrate Sigui into any agent in 3 lines of code:

```python
pip install sigui

from sigui import SiguiClient, AgentIdentity

# Create identity and connect to NexusMind Gateway
identity = AgentIdentity.create(agent_type="trading_bot", verification_tier="silver")

async with SiguiClient(api_url="http://localhost:8000") as client:
    await client.register_identity(identity)
    
    result = await client.evaluate_with_identity(
        amount=5.0,
        destination="0xRecipient",
        agent_did=identity.did
    )
    print(f"Verdict: {result.decision} — {result.processing_time_ms}ms")
```

---

## 📁 Project Structure
```text
Sigui/
├── main.py                    # FastAPI Gateway & Tracker
├── nexus_worker.py            # 🆕 Real P2P WebSockets Compute Node
├── modules/
│   ├── gateway.py             # HTTP Routes & x402 middleware
│   ├── nexusmind_router.py    # 🆕 P2P WebSockets Tracker & Orchestrator
│   ├── security_engine.py     # 5-layer risk engine (numpy)
│   ├── imina_na_vision.py     # Imina Na vLLM client (AMD MI300X)
│   └── identity/              # ERC-8259 Agent DID system
├── contracts/
│   ├── ThreatRegistry.vy      # Arc L1 Attack Log
│   ├── Hogonat.vy             # Governance DAO
│   └── NexusMindSiguiBridge.vy # 🆕 P2P Reputation Bridge
├── sdk/python/sigui/          # Python SDK (pip install sigui)
└── demo-ui/                   # Next.js Live Dashboard (React, Echarts, Tailwind)
```

---

## 🌟 Vision: The AWS of Agent Trust
- **Phase 1 ✅ Agent Identity System** - Cryptographic identity for AI agents
- **Phase 2 ✅ NexusMind Integration** - Real P2P compute and topological metrics
- **Phase 3 🔄 Threat Intelligence Network** - Decentralized marketplace for attack patterns
- **Phase 4 🔄 Open Protocol Standard** - EIP-8259 Agent Security Standard

> **The Goal:** By 2030, every AI agent that moves value goes through Sigui. We're building the trust infrastructure for the autonomous economy.

*Built for the Agentic Economy · Arc + Circle Hackathon · 2026*