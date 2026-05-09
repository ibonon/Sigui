# 🛡️ Sigui — The Multichain DePIN Security Oracle

> **Powered by AMD MI300X · Trained on 1,000,000 Real-Chain Graphs · EIP-8259 Native**

[![Hardware: AMD MI300X](https://img.shields.io/badge/Hardware-AMD%20MI300X-red)](https://www.amd.com/en/products/accelerators/instinct/mi300)
[![Dataset: 1M Graphs](https://img.shields.io/badge/Dataset-1M%20Visual%20Graphs-blueviolet)](#)
[![ERC-8259](https://img.shields.io/badge/Standard-ERC--8259-blue)](https://ethereum-magicians.org/t/erc-8259-ai-agent-identity-threat-registry/28473)

**Sigui** is a decentralized security infrastructure (DePIN) for AI agents, utilizing the massive parallel power of **AMD MI300X** GPUs to detect on-chain threats via visual graph analysis.

In **< 50ms**, the 5-layer Risk Engine, Imina Na V2 vision model (trained on 1,000,000 samples), and MemoClaw memory return a verdict: **ALLOW / BLOCK / ESCALATE**.

Blocked attacks are permanently recorded in `ThreatRegistry.vy` on Arc L1.  
Risk thresholds are governed by the community via `Hogonat.vy` staking.  
**The loop is fully closed. Zero human intervention.**

---

## 🌟 NEW: Agent Identity System (Phase 1)

### 🔐 Cryptographic Identity for AI Agents

Sigui now includes a revolutionary **Agent DID (Decentralized Identity)** system that solves the fundamental problem of agent identity verification:

**The Problem:** Currently, any attacker can create a new wallet, build fake reputation for 2 weeks, then execute attacks. Agent identity is tied to wallets, not cryptographic identity.

**The Solution:** Agent DID system where reputation is cryptographically bound to identity, not wallets.

### 🆔 Agent DID Features

- **Cryptographic Identity:** Each agent has unique DID bound to Ed25519 public key
- **Portable Reputation:** Reputation follows identity across wallets/chains
- **Impossible to Usurp:** Cannot fake identity without private key
- **Reputation Laundering Prevention:** Cannot "wash" bad reputation by creating new wallets
- **Multi-Tier Verification:** Bronze → Silver → Gold → Platinum verification levels

### 📊 Identity Verification Tiers

| Tier | Requirements | Trust Multiplier | Benefits |
|------|--------------|------------------|----------|
| **Bronze** | DID registration + email | 1.2x | Basic reputation |
| **Silver** | Organization verification | 1.5x | Enhanced scoring |
| **Gold** | Enterprise audit + KYC | 1.8x | Premium features |
| **Platinum** | Insurance backing | 2.0x | Maximum trust |

### 🧠 AI-Powered Reputation Engine

- **AMD MI300X Optimized:** 10-100x performance improvement over CPU
- **6-Factor Scoring:** Identity (25%) + Transactions (30%) + Verification (20%) + Cross-chain (10%) + Threat Intel (10%) + Insurance (5%)
- **Real-time Updates:** Reputation updates in <50ms
- **Anomaly Detection:** Isolation Forest for detecting suspicious behavior
- **Predictive Scoring:** ML model trained on 10,000+ agent behaviors

### 🔗 DID Format

```
did:sigui:arc:individual:0x7a3f2e1b9c8d4e5f
```

**Components:**
- `did`: Standard DID prefix
- `sigui`: Sigui method identifier
- `arc`: Blockchain network (Arc L1)
- `individual`: Agent type (individual/organization/enterprise)
- `0x7a3f...`: Public key hash (16 characters)

---

## ⚡ 30-Second Architecture

```
AI Agent ──── POST /evaluate ($0.001 x402) ────────────────────────────┐
                                                                         │
         ┌───────────────────────────────────────────────────────────┐  │
         │  Sigui Security Pipeline                                  │  │
         │                                                           │  │
         │  ① Agent DID Check    (cryptographic identity)          │  │
         │  ② Behavior Engine    (numpy,   < 2ms)                   │  │
         │  ③ Anti-Splitting     (flow tracking, cumulative USDC)   │  │
         │  ④ Service Registry   (reputation scores, on-chain)        │  │
         │  ⑤ Contract Inspector (bytecode analysis, approvals)     │  │
         │  ⑥ Imina Na Vision    (AMD MI300X ROCm, < 50ms)          │  │
         │                                                           │  │
         │  PolicyBrain ←→ LangGraph ←→ CrewAI (self-critique)     │  │
         └───────────────────────────────────────────────────────────┘  │
                                                                         │
         ALLOW  ──────────────────────────────────────────────────────-─┘
         BLOCK  ──── ThreatRegistry.vy (Arc L1, permanent, immutable)
         ESCALATE ── Qwen2.5 (AMD MI300X) → Claude 3.5 fallback
```

---

## ♻️ Economic Flywheel

```
Agent pays $0.001 ──→ Sigui Oracle receives revenue
                            │
                    ┌───────┴────────┐
                  80%              20%
                    │                │
              Treasury           Hogonat.vy
           (pays Claude &         Fee Pool
            Arc fees)                │
                                 Stakers claim
                                 proportional rewards
                                     │
                                 Stakers vote
                                 risk_weights &
                                 thresholds
                                     │
                                 PolicyBrain
                                 reloads live thresholds
                                     │
                         ←── Better protection → more agents
```

**Every evaluation strengthens the protocol. Every staker earns from every attack blocked.**

---

## 🧠 Imina Na — The Vision Oracle

Traditional security engines use simple thresholds. Imina Na *sees* the attack topology.

- **Architecture**: Fine-tuned Qwen2-VL-2B-Instruct (LoRA)
- **Hardware**: AMD MI300X (ROCm stack) for training and inference
- **Dataset**: The Dogon Dataset — 10,000+ custom transaction graph topologies
- **Patterns detected**: `DRAIN_STAR`, `MIXING_CHAIN`, `COORDINATED_CLUSTER`
- **Integration**: Provides a `risk_delta` injected into the Kanaga risk aggregator

→ [View model on HuggingFace](https://huggingface.co/Ibonon/imina_na_lora)

---

## 🏗️ Full Stack

| Component | Technology | Role |
|:---|:---|:---|
| **API** | FastAPI + uvicorn | Security oracle endpoint |
| **Payment** | x402 protocol + Circle DCW | $0.001/call micropayments |
| **Risk Engine** | numpy, 5-layer pipeline | Real-time threat scoring |
| **Vision Oracle** | Imina Na (Qwen2-VL, LoRA) | Graph topology detection |
| **AI Hardware** | **AMD MI300X (ROCm)** | Training + inference |
| **Memory** | MemoClaw (SQLite async) | Episodic memory, pattern recall |
| **Self-Critique** | PolicyBrain + LangGraph + CrewAI | Autonomous threshold tuning |
| **Smart Contracts** | Vyper 0.4.3 (2 contracts) | ThreatRegistry + Hogonat DAO |
| **Blockchain** | Arc L1 Testnet | Immutable attack log |
| **Governance** | Hogonat.vy staking | Community votes on risk thresholds |
| **Dashboard** | Next.js 14 | Cinematic live monitoring UI |
| **SDK** | Python (pip install sigui) | 2-line integration for agents |

---

## 🚀 Quick Start

### Prerequisites
```bash
# Python 3.11+ required
pip install -r requirements.txt

# For AMD GPU inference (ROCm):
pip install -r requirements_amd.txt
```

### 1. Configure environment
```bash
cp .env.example .env
# Edit .env with your Circle API key and Arc testnet credentials
# DEMO_MODE=true works out of the box with no credentials
```

### 2. Launch the Security Oracle
```bash
uvicorn main:app --port 8000 --reload
# API: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

### 3. Launch the Dashboard
```bash
cd demo-ui
npm install && npm run dev
# Dashboard: http://localhost:3001
```

### 4. Deploy the Autonomous Ecosystem
Click **⚡ Lancer le rituel** in the dashboard to launch the 5-agent simulation:
- 🔥 **Danseur du Feu** (PayerAgent) — legitimate payments, varied amounts
- 🦊 **Renard Pâle** (AttackerAgent) — adversarial, 4 rotating strategies
- ⭐ **Étoile Apprenante** (LearnerAgent) — warmup → probe → attack cycles
- 🌫 **Gray Zone** (GrayZoneAgent) — ambiguous transactions challenging the AI
- 👁 **Œil de la Société** (MonitorAgent) — ROI tracking, anomaly detection

---

## 🆔 Agent Identity SDK — 3-Line Integration

```bash
pip install sigui
```

```python
from sigui import SiguiClient, AgentIdentity

# Create agent identity
identity = AgentIdentity.create(
    agent_type="trading_bot",
    verification_tier="silver"
)

async with SiguiClient(api_url="http://localhost:8000") as client:
    # Register identity
    await client.register_identity(identity)
    
    # Evaluate transaction with identity
    result = await client.evaluate_with_identity(
        amount=5.0,
        destination="0xRecipient",
        agent_did=identity.did
    )
    
    print(f"✅ ALLOW — reputation={result.reputation_score:.3f} — {result.processing_time_ms}ms")
```

---

## 🐍 Basic SDK — 2-Line Integration

```bash
pip install sigui
```

```python
from sigui import SiguiClient

async with SiguiClient(api_url="http://localhost:8000") as client:
    result = await client.evaluate(amount=5.0, destination="0xRecipient")
    if result.is_safe:
        print(f"✅ ALLOW — risk={result.risk_score:.3f} — {result.processing_time_ms}ms")
    else:
        print(f"🚫 BLOCK — {result.reason}")
```

---

## 📊 On-Chain Proof

| Metric | Value |
|:---|:---|
| **ThreatRegistry** | `0x17430A67e11535466cC5f17e736D5e4643B86ba1` |
| **Hogonat DAO** | [`0x1e497ed89fc4f6ae2Da826a18B4a7728919684a1`](https://testnet.arcscan.app/address/0x1e497ed89fc4f6ae2Da826a18B4a7728919684a1) |
| **Explorer** | [testnet.arcscan.app](https://testnet.arcscan.app) |
| **Attacks recorded** | 380+ blocked and permanently logged |
| **Model** | [Ibonon/imina_na_lora](https://huggingface.co/Ibonon/imina_na_lora) |

---

## 🔑 Key Differentiators

| Feature | Traditional Security | Sigui |
|:---|:---|:---|
| **Response** | Passive filter | Autonomous economic agent |
| **Identity** | Wallet-based | Cryptographic DID |
| **Reputation** | Per-wallet | Portable across chains |
| **Learning** | Static rules | MemoClaw episodic memory + self-critique |
| **Governance** | Centralized | On-chain staking DAO (Hogonat.vy) |
| **Payments** | Subscription | x402 pay-per-call ($0.001) |
| **Proof** | Logs | Immutable on-chain (ThreatRegistry.vy) |
| **Vision** | None | Imina Na graph topology (AMD MI300X) |
| **Audit trail** | Centralized DB | Arc L1 blockchain |

---

## 🐳 Docker

```bash
docker-compose up
# Backend: http://localhost:8000
# Dashboard: http://localhost:3001
```

---

## 📁 Project Structure

```
Sigui/
├── main.py                    # FastAPI app — 10-step startup sequence
├── modules/
│   ├── gateway.py             # All routes, x402 middleware (50KB)
│   ├── security_engine.py     # 5-layer risk engine (numpy)
│   ├── memory.py              # MemoClaw episodic memory (SQLite async)
│   ├── ai_engines.py          # PolicyBrain + CrewAI + LangGraph + Claude
│   ├── imina_na_vision.py     # Imina Na vLLM client (AMD MI300X)
│   ├── response_validator.py  # LLM response poisoning detection
│   ├── treasury.py            # Autonomous treasury management
│   └── identity/              # 🆕 Agent DID system
│       ├── agent_did.py       # DID generation & management
│       ├── reputation_engine.py # AI-powered reputation scoring
│       └── identity_integration.py # Identity + security pipeline
├── contracts/
│   ├── ThreatRegistry.vy      # Onchain attack log (Vyper 0.4.3)
│   ├── Hogonat.vy             # Governance DAO — staking + threshold votes
│   └── AgentIdentityRegistry.vy # 🆕 Agent identity registry
├── ecosystem/
│   └── agents.py              # 5 autonomous agents (Payer, Attacker, Learner...)
├── governance/
│   └── hogonat_client.py      # Dual-mode governance client (mock/on-chain)
├── sdk/python/sigui/          # Python SDK (pip install sigui)
└── demo-ui/                   # Next.js 14 live dashboard
```

---

## 🌟 Vision: The AWS of Agent Trust

**Phase 1** ✅ **Agent Identity System** - Cryptographic identity for AI agents  
**Phase 2** 🔄 **Threat Intelligence Network** - Decentralized marketplace for attack patterns  
**Phase 3** 🔄 **Insurance Layer** - Risk coverage for autonomous transactions  
**Phase 4** 🔄 **Open Protocol Standard** - EIP-XXXX Agent Security Standard

**The Goal:** By 2030, every AI agent that moves value goes through Sigui. We're building the trust infrastructure for the autonomous economy.

---

*Sigui · Built for the Agentic Economy · Arc + Circle Hackathon · 2026*  
*"The firewall doesn't wait for humans. It learns, adapts, and protects — autonomously."*

**Next Steps:**
- [ ] Deploy AgentIdentityRegistry.vy to Arc mainnet
- [ ] Onboard 1,000 agents with cryptographic identities
- [ ] Launch Threat Intelligence Network (Phase 2)
- [ ] Submit EIP-XXXX Agent Security Standard (Phase 4)