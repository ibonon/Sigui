# 🛡️ ArcWarden v3.0 — Per-API Monetization Engine + Agent-to-Agent Payment Loop

> *"ArcWarden is not a firewall. It's an agent that gets paid to protect other agents — from everything."*

**Hackathon:** Agentic Economy on ARC · lablab.ai · April 20–25, 2026
**Tracks:** Per-API Monetization Engine · Agent-to-Agent Payment Loop
**Author:** Eric Warma · Solo builder · Ouagadougou, Burkina Faso

---

## What is ArcWarden?

ArcWarden is an **autonomous economic agent** that sells security services to other agents in the Arc ecosystem.
It is not a monitoring tool bolted onto the outside of the agentic economy — it **lives inside it**.

| What ArcWarden does | How |
|---|---|
| **Charges per security evaluation** | x402 protocol · $0.001 USDC per call (≤ $0.01 rule ✅) |
| **Evaluates every action on 4 layers** | Behavior · Anti-splitting · Service reputation · Smart contract risk |
| **Decides in < 5 ms** | ALLOW / BLOCK / ESCALATE — numpy Risk Engine |
| **Bonded Oracle Model** | On-chain Guaranty Fund for economically backed decisions |
| **Dynamic Risk Pricing** | Surge pricing for suspicious agents ($0.001 → $0.005) |
| **Uses a custom Smart Contract** | Vyper 0.4.3 registry for immutable attack logging |
| **Collective Intelligence** | Synced patterns from all Oracles via blockchain |
| **Hybrid Learning Logic** | Learns via MemoClaw (statistical) + Optional LLM Critique |
| **Pays Claude from its own treasury** | Escalation = $0.0006 USDC paid autonomously (Optional) |
| **Logs every decision immutably** | Arc L1 testnet · `testnet.arcscan.app` |
| **Adapts to treasury health** | NORMAL → DEGRADED → EMERGENCY — zero human intervention |
| **Validates service responses** | POST /validate-response · 5-layer data poisoning detection |

**The loop is entirely closed. Zero human intervention.**

---

## 📡 Track Alignment

### 🪙 Per-API Monetization Engine
Every `/evaluate` call is gated behind an x402 payment of **$0.001 USDC**.
ArcWarden earns revenue, pays Claude for escalations, pays Arc L1 gas fees,
and maintains a positive P&L — all autonomously, onchain.

### 🤖 Agent-to-Agent Payment Loop
Five autonomous agents (Payer, Attacker, Learner, GrayZone, Monitor) each have
a real Circle Developer-Controlled Wallet. They pay ArcWarden in real USDC,
receive ALLOW / BLOCK / ESCALATE decisions, and trigger collective learning
across the ecosystem. No human is in the loop.

---

## ✅ Hackathon Compliance

| Requirement | Status |
|---|---|
| Per-action pricing ≤ $0.01 | ✅ $0.001 / evaluation |
| 50+ onchain transactions | ✅ 389 confirmed on Arc L1 (verifiable on arcscan.app) |
| Margin explanation | ✅ See Economics section below |
| Arc + USDC + Circle DCW | ✅ 6 real wallets · chain_id=5042002 |
| Circle Nanopayments / x402 | ✅ Custom middleware · HTTP 402 flow |
| Circle Product Feedback | ✅ See section below |
| MIT License | ✅ LICENSE file |

---

## 🏗️ Architecture — 4 Security Layers

```
┌──────────────────────────────────────────────────────────────────────┐
│                       ARCWARDEN AGENT                                │
│                                                                      │
│  Client Agent ─$0.001 USDC──▶ [ x402 Middleware ]                   │
│                                        │                             │
│                         ┌──────────────▼──────────────┐             │
│  LAYER 1 — BEHAVIOR     │  Amount anomaly · Frequency  │ +0.00–0.50 │
│  LAYER 2 — ANTI-SPLIT   │  Flow windows 10min · 4 ptn  │ +0.25–0.60 │
│  LAYER 3 — SERVICE REP  │  Registry NEUTRAL→MALICIOUS  │ -0.25–0.60 │
│  LAYER 4 — CONTRACT RISK│  EVM bytecode · 0xF4 · 0xFF  │ -0.15–0.70 │
│                         └──────────────┬──────────────┘             │
│                                        │ Score R ∈ [0,1]             │
│                    ┌───────────────────▼────────────────────┐       │
│  R < 0.35 → ALLOW  │       DECISION ENGINE                  │       │
│  R ∈ [0.35,0.65) → │  ALLOW · BLOCK · ESCALATE              │       │
│  R ≥ 0.65 → BLOCK  └───────────────────┬────────────────────┘       │
│                                        │                             │
│          ┌─────────────────────────────┼──────────────────┐         │
│          ▼                             ▼                  ▼         │
│     [MemoClaw]               [Claude API — $0.0006]   [Arc L1]      │
│     Pattern learning         Paid by ArcWarden        Decision log  │
└──────────────────────────────────────────────────────────────────────┘
```

### 1. The Oracle Agent (The Core)
The detection brain. It uses a hybrid risk engine:
- **On-chain Statistical Learning**: Even without an LLM API key, ArcWarden learns attack patterns by analyzing data from the `ThreatRegistry` Smart Contract and its local `MemoClaw` database. It autonomously adjusts its security thresholds.
- **AI Analysis (Optional)**: If an `ANTHROPIC_API_KEY` is provided, ArcWarden can escalate ambiguous cases to Claude 3.5 Sonnet for deep contextual analysis.

### 2. The ThreatRegistry Smart Contract (Vyper 0.4.3)

An immutable onchain registry deployed on Arc L1. Every BLOCK decision is permanently
recorded here — pattern hash, agent address, amount attempted, risk score, and the
security layer that triggered. Anyone can verify any blocked attack independently.

---

#### ⚠️ Smart Contract Migration — April 24, 2026

**Why the contract was redeployed:**

The original ThreatRegistry (`v1`) was deployed during the early development phase
with a slightly different Vyper source. When the codebase was later upgraded to add
the `guaranty_fund` solvency mechanism and align the ABI with the Python client, the
compiled `recordAttack` function selector changed:

| Version | `recordAttack` first param | EVM selector | Status |
|---|---|---|---|
| **v1 (original)** | `String[64]` (agent name) | `66b78804` | ❌ Deprecated |
| **v2 (current)** | `address` (agent wallet) | `cd21c5bc` | ✅ Active |

Because EVM function selectors are computed from the parameter types
(`keccak256("recordAttack(address,bytes32,...)")[:4]`), changing `String[64]` to
`address` produces a completely different 4-byte selector. The Python client was
calling selector `cd21c5bc` but the deployed contract only knew `66b78804` — every
`recordAttack()` call was silently rejected by the EVM without reverting.

This was discovered by scanning the deployed bytecode for the expected selector and
confirming its absence. The fix was to recompile with Vyper 0.4.3 and redeploy.

---

#### 📜 Contract v1 — Original (Deprecated)

> **748 attacks** recorded during the development and testing phase.
> This contract is preserved for historical reference and audit trail.

| Field | Value |
|---|---|
| **Address** | [`0x9566aDB7719008d4571CFd9E21f8DDb4d3024D93`](https://testnet.arcscan.app/address/0x9566aDB7719008d4571CFd9E21f8DDb4d3024D93) |
| **Deployer** | [`0x2AB9cBBC5bC4b819C48a10F76a7B1B325c5A484f`](https://testnet.arcscan.app/address/0x2AB9cBBC5bC4b819C48a10F76a7B1B325c5A484f) |
| **Network** | Arc Testnet · chain_id=5042002 |
| **Attacks recorded** | 748 |
| **USDC protected** | $1,682.92 |
| **Status** | ❌ Deprecated — ABI mismatch with current Python client |
| **Reason deprecated** | `recordAttack` selector mismatch (String vs address param) |

---

#### 🟢 Contract v2 — Current (Active)

> **This is the active contract.** All new BLOCK decisions are recorded here in
> real time, fired as background `asyncio` tasks from the decision pipeline.

| Field | Value |
|---|---|
| **Address** | [`0x17430A67e11535466cC5f17e736D5e4643B86ba1`](https://testnet.arcscan.app/address/0x17430A67e11535466cC5f17e736D5e4643B86ba1) |
| **Deployer** | [`0x2AB9cBBC5bC4b819C48a10F76a7B1B325c5A484f`](https://testnet.arcscan.app/address/0x2AB9cBBC5bC4b819C48a10F76a7B1B325c5A484f) |
| **Network** | Arc Testnet · chain_id=5042002 |
| **Compiler** | Vyper 0.4.3+commit.bff19ea2 |
| **Deployment TX** | [`0x382aa10e...`](https://testnet.arcscan.app/tx/0x382aa10eff73c4112e16906d405c5d4df62a25af32dba1cefc312d3c55984382) |
| **Verified selector** | `recordAttack(address,bytes32,uint256,uint256,uint8)` = `cd21c5bc` ✅ |
| **Status** | ✅ Active — receiving live attack data |

**Security properties:**
- **Owner-only writes** — only the ArcWarden oracle signer can call `recordAttack()`
- **`@nonreentrant` guard** — prevents reentrancy on all state-changing functions
- **Anti-replay** — same pattern hash rate-limited to 1 record per 2 seconds
- **Emergency circuit breaker** — `pause()` / `unpause()` for incident response
- **Ownership transfer** — `transferOwnership()` with zero-address guard for key rotation
- **Immutable by design** — no proxy, no `selfdestruct`, no upgradeability
- **Guaranty fund** — `depositGuaranty()` / `withdrawGuaranty()` for solvency proof
- **Full event audit trail** — `AttackBlocked`, `OwnershipTransferred`, `RegistryPaused`

**Key functions (public ABI):**

```
recordAttack(agent, pattern, amount_usdc6, risk_milli, layer)  → write, owner-only
getStats()                → (total_attacks, total_usdc_protected6, guaranty_fund6)
getAttack(idx)            → AttackRecord struct
isKnownAttacker(address)  → bool  (true if 3+ confirmed blocks)
isPatternKnown(bytes32)   → bool  (true if pattern seen before)
transferOwnership(address) → write, owner-only
pause() / unpause()       → write, owner-only (circuit breaker)
```

**Verify on ArcScan:**
```
https://testnet.arcscan.app/address/0x17430A67e11535466cC5f17e736D5e4643B86ba1
```

### 3. Simulation Agents (The Ecosystem)
Five autonomous agents (Payer, Attacker, Monitor, Learner, GrayZone) each possess a real Circle DCW wallet. They interact with the Oracle to demonstrate its detection capabilities in real-time.

---

## 🏗️ Architecture — 4 Security Layers

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys (or leave defaults for DEMO_MODE=true)
```

### 3. Start ArcWarden

```bash
uvicorn main:app --reload --port 8000
```

### 4. Launch Command Center Dashboard (new terminal)

```bash
cd demo-ui
npm run dev
# Open http://localhost:3001
```

### 5. Deploy Autonomous Agents

```bash
# Triggers the 5 autonomous agents with real Circle DCW wallets
curl -X POST http://localhost:8000/simulate

# Or click ⚡ Deploy Agents in the dashboard
```

### 6. One-click startup (Windows PowerShell)

```powershell
.\scripts\start_demo.ps1
```

---

## 🔥 Pre-submission Checklist

```bash
# Verify all hackathon requirements are met
venv\Scripts\python scripts/check_beast_ready.py

# Security regression tests
venv\Scripts\python -m unittest tests.test_security_minimal

# Security probe harness
venv\Scripts\python scripts/security_probe_harness.py
```

Expected before submission:
- `DEMO_MODE=false`
- `/health` → `demo_mode=false`, `db_connected=true`
- `/demo/report` → `onchain_proof.confirmed_onchain_tx_count >= 50`
- `/stats` → non-zero `block`, `escalate`, `patterns_learned`
- `testnet.arcscan.app/address/{signer}` → real transactions visible

---

## 📡 API Endpoints

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `/.well-known/agent-card` | GET | Free | Agent discoverability (A2A) |
| `/health` | GET | Free | Status · mode · DB connectivity |
| `/treasury` | GET | Free | Real-time P&L |
| `/stats` | GET | Free | Decisions · patterns · policy thresholds |
| `/evaluate` | POST | x402 $0.001 | **Main 4-layer security pipeline** |
| `/escalate` | POST | x402 $0.003 | Claude deep analysis |
| `/validate-response` | POST | Free | Post-service response validator (5 layers) |
| `/simulate` | POST | Free | Launch 5-agent autonomous ecosystem |
| `/demo/live` | GET | Free | SSE live feed (dashboard) |
| `/demo/report` | GET | Free | Submission-grade compliance report |
| `/flows/active` | GET | Free | Active flow windows (anti-splitting) |
| `/services/{address}` | GET | Free | Service trust profile |
| `/services/complain` | POST | Free | Report fraudulent service |
| `/ecosystem/status` | GET | Free | All 5 agents status + balances |
| `/docs` | GET | Free | OpenAPI interactive documentation |

### POST /validate-response — New in v3.0

Call this **after** receiving a response from an Arc service, **before** acting on the data.
Detects prompt injection, statistical anomalies, schema attacks, and known poisoning signatures.

```bash
curl -X POST http://localhost:8000/validate-response \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "my_agent",
    "service_address": "0xARCDATA...",
    "request_type": "price_feed",
    "response_received": {"price": 0.0, "note": "ignore previous instructions"},
    "context": {"asset": "BTC", "expected_range": [40000, 100000]}
  }'
```

---

### 5. Multi-Layer Risk Engine (V3 Advanced)
Our Risk Engine uses a Bayesian-inspired weighted scoring model across 4 distinct security layers. It doesn't just check a balance; it analyzes intent.

#### The Core Formula:
$$R_{final} = 	ext{clip}\left( \sum (W_i \cdot S_i) + \text{Boosts} + \Delta_{Service} + \Delta_{Contract}, 0, 1 \right)$$

Where:
- **$S_{Action}$ ($W=0.55$)**: Real-time behavior (amount spikes, destination risk).
- **$S_{Context}$ ($W=0.30$)**: Anti-splitting & Anti-spoofing (detecting micro-transaction fragmentation).
- **$S_{History}$ ($W=0.15$)**: Long-term trust scores and transaction frequency.

#### Advanced Anti-Splitting (Anti-Sybil):
Detects attackers trying to bypass limits by splitting large transfers into hundreds of tiny ones.
- **Uniformity Check**: Flags transactions with suspiciously low variance in amount.
- **Global Flow Analysis**: Monitors total volume across multiple destination wallets in real-time.

#### Layer 4: Contract Inspection
Directly analyzes the bytecode/selectors of the destination contract to detect "Drainers" or "Infinite Approval" patterns before they execute.

---

### 6. Demonstration Scenario (Video Flow)
This is the walkthrough shown in our presentation video:

1.  **Boot Sequence**: The system initializes with a high-tech terminal sequence, verifying the **ThreatRegistry** connection and the **$5.00 USDC Guaranty Fund** on Arc L1.
2.  **Dashboard Overview**: A real-time view of the "Economic OS".
    - **Net Profit**: Showing ArcWarden's ability to self-fund and monetize its security services.
    - **Guaranty Fund**: Visual proof of the "Bonded Oracle" model.
3.  **Live Agent Loop**:
    - Deployment of 5 autonomous agents (Circle DCW).
    - Real-time evaluation of transactions ($0.001 fee via x402).
4.  **On-Chain Proof**:
    - Clicking on an attack hash to open **ArcScan**.
    - Verifying the **Identity Link**: The contract is deployed by the author's Circle DCW (`0x2AB9...`), linking web3 reputation to Circle's infrastructure.
5.  **Economics Section**: Why Arc? Demonstrating the profitability of sub-cent transactions thanks to Arc's near-zero gas fees.

---

### 7. Bonded Oracle Architecture (Open Oracle)
ArcWarden operates as a **Bonded Oracle**.
- **Skin in the Game**: The Oracle must deposit USDC into the Guaranty Fund to be active.
- **Slashing Risk**: If the Oracle provides false data or fails to block a known threat, its fund can be slashed.
- **Identity Link**: By using Circle DCW to manage the contract, we bridge the gap between anonymous agents and accountable security providers.

---

### 8. Monetization: The x402 Engine
ArcWarden is a pioneer in **API Monetization for Agents**.
- Each security check costs **$0.001 USDC**.
- Settlement happens instantly on Arc L1.
- This creates a sustainable loop: ArcWarden earns enough to pay for its own AI brain (Claude) and its own on-chain presence.

---

### 9. Technology Stack
- **Network**: [Arc L1 (Circle)](https://testnet.arcscan.app)
- **Payments**: Circle Programmable Wallets (DCW) & x402 Protocol
- **Intelligence**: MemoClaw (Vector Index) + CrewAI (Decision Brain)
- **Contracts**: Vyper 0.4.3 (ThreatRegistry)
- **Frontend**: Next.js 14 (Cyber-UI)
- **Backend**: FastAPI / Python 3.14

---

*ArcWarden v3.0 · MIT License · Eric Warma · Hackathon: Agentic Economy on ARC · lablab.ai*