# Sigui SDK — Autonomous Security for AI Agents

[![PyPI version](https://img.shields.io/pypi/v/sigui-sdk.svg)](https://pypi.org/project/sigui-sdk/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Model](https://img.shields.io/badge/Model-Qwen2--VL--7B-orange)](https://huggingface.co/Ibonon/imina_na_v2_lora)
[![Dataset](https://img.shields.io/badge/Dataset-1M%20Graphs-purple)](https://huggingface.co/datasets/Ibonon/sigui-depin-1mn)

**Sigui** is an open-source security oracle that protects AI agents from sending erroneous or malicious crypto payments.

Add a security interception layer to **any** AI agent in 2 lines of code. Every transaction intent is analyzed by a **5-layer AI pipeline** (including a fine-tuned Vision Language Model) in **< 50 ms** before execution — without blocking your agent's workflow.

---

## Table of Contents

1. [The Problem & The Solution](#-the-problem--the-solution)
2. [Installation](#-installation)
3. [Backend Setup (Required)](#️-backend-setup-required)
4. [Quickstart](#-quickstart)
5. [Core API Reference](#-core-api-reference)
   - [SiguiClient (async)](#siguiclient-async)
   - [SiguiClientSync (sync)](#siguiclientsync-sync)
   - [EvaluationResult](#evaluationresult)
   - [EscalationResult](#escalationresult)
   - [Verdict & Chain enums](#verdict--chain-enums)
6. [Framework Integrations](#-framework-integrations)
7. [Framework-Agnostic Decorator](#️-framework-agnostic-decorator)
8. [Error Handling](#-error-handling)
9. [Advanced Usage](#-advanced-usage)
10. [How It Works: The 5-Layer Pipeline](#-how-it-works-the-5-layer-pipeline)
11. [Open-Source Model & Dataset](#-open-source-model--dataset)
12. [CLI Reference](#-cli-reference)
13. [License](#-license)

---

## ⚡ The Problem & The Solution

**The Problem:** Autonomous agents (LangChain, CrewAI, AutoGen, OpenAI Agents) can now execute USDC transfers and interact with DeFi protocols autonomously. But a single hallucination, prompt injection attack, or misconfigured tool means the agent can send $5,000 to the wrong address — with no way to stop it.

**The Solution:** `sigui-sdk` intercepts the payment intent **before** execution, evaluates it against a 5-layer AI security pipeline, and returns a strict, auditable verdict:

| Verdict | Meaning | Recommended action |
|---|---|---|
| `ALLOW` | Transaction is safe | Proceed |
| `BLOCK` | Transaction is flagged as malicious | Abort |
| `ESCALATE` | Ambiguous — requires deep analysis | Call `client.escalate()` |
| `ALLOW_WITH_CAP` | Safe up to a capped amount | Proceed with `cap_amount_usdc` |

---

## 📦 Installation

```bash
pip install sigui-sdk
```

Install the extras for your agent framework:

```bash
pip install "sigui-sdk[langchain]"       # LangChain & LangGraph
pip install "sigui-sdk[crewai]"          # CrewAI
pip install "sigui-sdk[autogen]"         # Microsoft AutoGen (AG2)
pip install "sigui-sdk[openai-agents]"   # OpenAI Agents SDK
pip install "sigui-sdk[smolagents]"      # HuggingFace smolagents
pip install "sigui-sdk[llamaindex]"      # LlamaIndex
pip install "sigui-sdk[google_adk]"      # Google Agent Development Kit

pip install "sigui-sdk[all]"             # All integrations at once
```

**Requirements:** Python 3.11+, and the [Sigui backend](#️-backend-setup-required) running locally.

---

## ⚙️ Backend Setup (Required)

`sigui-sdk` is a client library. It requires the **Sigui Security Engine** to be running.
We do not currently provide a public hosted API — you can run the backend locally in under 2 minutes using Docker:

```bash
# 1. Clone the main repository
git clone https://github.com/ibonon/Sigui.git
cd Sigui

# 2. Configure environment (no crypto keys required for demo)
cp .env.example .env
# Make sure DEMO_MODE=true is set in .env

# 3. Start the security oracle
docker compose up
```

Once running, the API is available at `http://localhost:8000`.
You can verify it with:

```bash
curl http://localhost:8000/health
# → {"status": "ok", "mode": "NORMAL", ...}
```

---

## 🚀 Quickstart

### Async (recommended)

```python
import asyncio
from sigui import SiguiClient

async def main():
    async with SiguiClient(api_url="http://localhost:8000") as client:
        result = await client.evaluate(
            amount=5.0,
            destination="0xRecipient..."
        )

        if result.is_safe:
            print(f"✅ Authorized   risk={result.risk_score:.3f}")
        elif result.is_blocked:
            print(f"🚫 Blocked      {result.reason}")
        else:
            print(f"⚠️  Escalation required — calling deep analysis...")
            deep = await client.escalate(amount=5.0, destination="0xRecipient...")
            print(f"   Deep verdict: {deep.verdict}  cap=${deep.cap_amount_usdc}")

asyncio.run(main())
```

### Sync (for non-async agents)

```python
from sigui import SiguiClientSync

with SiguiClientSync(api_url="http://localhost:8000") as client:
    result = client.evaluate(amount=5.0, destination="0xRecipient...")
    print(result.verdict)   # ALLOW | BLOCK | ESCALATE
```

---

## 📖 Core API Reference

### `SiguiClient` (async)

```python
SiguiClient(
    api_url: str = "http://localhost:8000",
    wallet: WalletAdapter | None = None,   # DemoWallet by default
    chain: str | Chain = Chain.ARC,
    agent_id: str = "sdk_agent",
    raise_on_block: bool = False,
    raise_on_escalate: bool = False,
    timeout: float = 15.0,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `api_url` | `str` | `"http://localhost:8000"` | URL of the Sigui backend |
| `wallet` | `WalletAdapter` | `DemoWallet()` | Wallet for x402 micropayments. Use `DemoWallet` for dev, `CircleWallet` for production |
| `chain` | `str \| Chain` | `Chain.ARC` | Default chain: `arc`, `ethereum`, or `solana` |
| `agent_id` | `str` | `"sdk_agent"` | Identifier for your agent (used in behavioral memory) |
| `raise_on_block` | `bool` | `False` | If `True`, raises `SiguiBlockedError` instead of returning a BLOCK result |
| `raise_on_escalate` | `bool` | `False` | If `True`, raises `SiguiEscalationRequiredError` on ESCALATE |
| `timeout` | `float` | `15.0` | HTTP timeout in seconds |

#### Methods

##### `await client.evaluate(...) → EvaluationResult`

Evaluates a transaction **before** execution. This is the main method you will call.

```python
result = await client.evaluate(
    amount=100.0,               # Amount in USDC
    destination="0xAbc...",     # Target wallet address
    agent_id="my_agent",        # Optional: override default agent_id
    action_type="transfer",     # "transfer" | "swap" | "stake" | "bridge" | ...
    chain="arc",                # Optional: override default chain
    context={                   # Optional: extra context for better decisions
        "memo": "payment for service X",
        "session_id": "sess_abc123",
    },
    raise_on_block=True,        # Optional: override client-level setting
    raise_on_escalate=False,
)
```

##### `await client.escalate(...) → EscalationResult`

Requests a **deep analysis** via Lebe (Qwen2.5 fine-tuned on AMD MI300X) or Claude. Costs $0.003 USDC, paid automatically via the x402 protocol.

Use this when `evaluate()` returns `verdict=ESCALATE`.

```python
eval_result = await client.evaluate(amount=500.0, destination="0x...")

if eval_result.needs_escalation:
    deep = await client.escalate(
        amount=500.0,
        destination="0x...",
        action_type="transfer",
    )
    print(f"Deep analysis: {deep.analysis}")
    print(f"Cap allowed: ${deep.cap_amount_usdc}")
```

##### `await client.evaluate_and_escalate(...) → EvaluationResult | EscalationResult`

Convenience method: evaluates the transaction and **automatically escalates** if needed. Always returns a final decision.

```python
result = await client.evaluate_and_escalate(
    amount=50.0,
    destination="0xRecipient",
)
# result.verdict is always ALLOW, BLOCK, or ALLOW_WITH_CAP — never ESCALATE
```

##### `await client.health() → dict`

Checks that the backend is online and returns its status.

```python
status = await client.health()
# {"status": "ok", "mode": "NORMAL", "version": "..."}
```

##### `await client.treasury() → TreasuryState`

Returns the current financial state of the Sigui protocol.

```python
state = await client.treasury()
print(f"Balance: ${state.balance:.4f} USDC")
print(f"Net profit: ${state.net_profit:.4f} USDC")
```

---

### `SiguiClientSync` (sync)

A synchronous wrapper around `SiguiClient`, using a dedicated event loop. Exposes the exact same methods — `evaluate()`, `escalate()`, `evaluate_and_escalate()`, `health()`, `treasury()` — but without `await`.

```python
from sigui import SiguiClientSync

# As a context manager (recommended)
with SiguiClientSync(api_url="http://localhost:8000", agent_id="crewai_bot") as client:
    result = client.evaluate(amount=10.0, destination="0x...")
    print(result.verdict)

# Or manually
client = SiguiClientSync(api_url="http://localhost:8000")
result = client.evaluate(amount=10.0, destination="0x...")
client.close()
```

---

### `EvaluationResult`

Returned by `client.evaluate()`.

| Attribute | Type | Description |
|---|---|---|
| `verdict` | `Verdict` | `ALLOW`, `BLOCK`, `ESCALATE`, or `ALLOW_WITH_CAP` |
| `risk_score` | `float` | Risk score from `0.0` (safe) to `1.0` (critical) |
| `confidence` | `float` | Model confidence in the verdict |
| `reason` | `str` | Human-readable explanation of the decision |
| `action_hash` | `str` | Unique ID for this evaluation (for audit logs) |
| `arc_tx_log` | `str` | On-chain proof transaction hash on Arc |
| `arcwarden_mode` | `str` | Current backend mode: `NORMAL`, `DEGRADED`, `EMERGENCY` |
| `escalation_available` | `bool` | Whether `/escalate` is currently available |
| `escalation_cost_usdc` | `float` | Cost to escalate (default: `0.003`) |
| `policy_source` | `str` | Which security layer made the decision |
| `processing_time_ms` | `int` | Backend evaluation time in milliseconds |
| `vision_pattern` | `str` | Visual attack pattern detected (e.g. `SMURF`, `NORMAL`) |
| `vision_confidence` | `float` | Confidence of the vision model |
| `evaluation_price_usdc` | `float` | x402 fee paid for this call |
| `chain` | `str` | Chain on which the evaluation ran |
| `layers_triggered` | `dict` | Which security layers were triggered |
| `raw` | `dict` | Full raw API response (for advanced usage) |

**Convenience properties:**

```python
result.is_safe          # True if verdict == ALLOW
result.is_blocked       # True if verdict == BLOCK
result.needs_escalation # True if verdict == ESCALATE
result.synthetic_score  # Integer score 0–1000 (higher = safer)
result.onchain_proof    # Arc explorer URL for the on-chain proof, or None
```

---

### `EscalationResult`

Returned by `client.escalate()`.

| Attribute | Type | Description |
|---|---|---|
| `verdict` | `Verdict` | `ALLOW_WITH_CAP` or `BLOCK` |
| `cap_amount_usdc` | `float` | Maximum allowed amount if `ALLOW_WITH_CAP` |
| `analysis` | `str` | Detailed explanation from the deep model |
| `confidence` | `float` | Model confidence |
| `inference_engine` | `str` | Which model was used (`qwen`, `claude`, `rule_based`) |
| `inference_device` | `str` | Hardware used (`AMD_MI300X`, `CPU`, etc.) |
| `fallback_used` | `bool` | True if the primary model fell back to a simpler engine |
| `degraded_mode` | `bool` | True if the backend is operating in degraded mode |
| `arc_tx_log` | `str` | On-chain proof for the escalation |
| `paid_by_arcwarden` | `bool` | True if Sigui subsidized the escalation cost |

```python
result.is_allowed_with_cap  # True if verdict == ALLOW_WITH_CAP
```

---

### `Verdict` & `Chain` enums

```python
from sigui import Verdict, Chain

# Verdict
Verdict.ALLOW           # → "ALLOW"
Verdict.BLOCK           # → "BLOCK"
Verdict.ESCALATE        # → "ESCALATE"
Verdict.ALLOW_WITH_CAP  # → "ALLOW_WITH_CAP"

# Chain
Chain.ARC       # → "arc"
Chain.ETHEREUM  # → "ethereum"
Chain.SOLANA    # → "solana"
```

---

## 🧩 Framework Integrations

Sigui provides **native Tools** for all major agent frameworks. Drop them into your agent's tool list with zero refactoring.

### 🦜 LangChain / LangGraph

```bash
pip install "sigui-sdk[langchain]"
```

```python
from sigui import SiguiClient
from sigui.integrations.langchain import create_langchain_tool
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI

client = SiguiClient(api_url="http://localhost:8000", agent_id="langchain_bot")
sigui_tool = create_langchain_tool(client, auto_escalate=True)

llm = ChatOpenAI(model="gpt-4o")
agent = initialize_agent(
    tools=[sigui_tool],
    llm=llm,
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=True,
)

agent.run("Send 10 USDC to 0xRecipient for API access")
```

The tool automatically formats the result as a human-readable string that the LLM can reason about. Set `auto_escalate=True` to let Sigui handle escalations transparently.

---

### 🤖 CrewAI

```bash
pip install "sigui-sdk[crewai]"
```

```python
from crewai import Agent, Task, Crew
from sigui import SiguiClientSync
from sigui.integrations.crewai import SiguiEvaluationTool

client = SiguiClientSync(api_url="http://localhost:8000", agent_id="crewai_bot")
sigui_tool = SiguiEvaluationTool(sigui_client=client, auto_escalate=True)

payment_agent = Agent(
    role="DeFi Payment Agent",
    goal="Execute only safe USDC transfers",
    tools=[sigui_tool],
    backstory="You validate every payment through Sigui before execution.",
)

task = Task(
    description="Evaluate and send 50 USDC to 0xVendor...",
    agent=payment_agent,
    expected_output="Payment status and security verdict",
)

crew = Crew(agents=[payment_agent], tasks=[task])
crew.kickoff()
```

> **Note:** CrewAI uses synchronous tools — `SiguiClientSync` is required.

---

### 🤖 Microsoft AutoGen (AG2)

```bash
pip install "sigui-sdk[autogen]"
```

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.ui import Console
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from sigui import SiguiClient
from sigui.integrations.autogen import create_autogen_tool

client = SiguiClient(api_url="http://localhost:8000")
sigui_tool = create_autogen_tool(client, auto_escalate=True)

model_client = OpenAIChatCompletionClient(model="gpt-4o")

agent = AssistantAgent(
    name="payment_agent",
    model_client=model_client,
    tools=[sigui_tool],
    system_message="Always evaluate payments through Sigui before proceeding.",
)

termination = TextMentionTermination("TERMINATE")
team = RoundRobinGroupChat([agent], termination_condition=termination)

import asyncio
asyncio.run(Console(team.run_stream(task="Evaluate sending 25 USDC to 0xTarget...")))
```

---

### 🤗 HuggingFace smolagents

```bash
pip install "sigui-sdk[smolagents]"
```

```python
from smolagents import CodeAgent, HfApiModel
from sigui import SiguiClient
from sigui.integrations.smolagents import SiguiTool

client = SiguiClient(api_url="http://localhost:8000")
sigui_tool = SiguiTool(client, auto_escalate=True)

model = HfApiModel(model_id="Qwen/Qwen2.5-72B-Instruct")
agent = CodeAgent(tools=[sigui_tool], model=model)

agent.run("Is it safe to send 200 USDC to 0xSuspiciousAddress?")
```

---

### 🔑 OpenAI Agents SDK

```bash
pip install "sigui-sdk[openai-agents]"
```

```python
from agents import Agent, Runner
from sigui import SiguiClient
from sigui.integrations.openai_agents import create_openai_agents_tool

client = SiguiClient(api_url="http://localhost:8000")
sigui_tool = create_openai_agents_tool(client, auto_escalate=True)

agent = Agent(
    name="PaymentGuard",
    instructions="Evaluate all crypto transactions through Sigui before proceeding.",
    tools=[sigui_tool],
)

import asyncio
result = asyncio.run(Runner.run(agent, "Send 15 USDC to 0xRecipient for invoice #42"))
print(result.final_output)
```

---

## 🛡️ Framework-Agnostic Decorator

If you don't use agent frameworks or want fine-grained control, gate **any async function** directly with the `@sigui_protect` decorator:

```python
from sigui import SiguiClient
from sigui.decorators import sigui_protect

client = SiguiClient(api_url="http://localhost:8000")

@sigui_protect(client, amount_arg="usdc", destination_arg="to")
async def transfer(to: str, usdc: float, memo: str = ""):
    """This code ONLY runs if Sigui returns ALLOW."""
    await wallet.send(to, usdc)
    print(f"✅ Sent ${usdc} USDC to {to}")

# Usage — raises SiguiBlockedError if flagged
try:
    await transfer(to="0xVendor...", usdc=100.0, memo="invoice #42")
except SiguiBlockedError as e:
    print(f"🚫 Blocked: {e.reason}  risk={e.risk_score:.3f}")
```

The decorator intercepts the call, runs `client.evaluate()`, and:
- **ALLOW** → executes the original function normally
- **BLOCK** → raises `SiguiBlockedError` (never calls your function)
- **ESCALATE** → raises `SiguiEscalationRequiredError` by default

---

## 🚨 Error Handling

All exceptions inherit from `SiguiError` for easy catch-all handling.

```python
from sigui.exceptions import (
    SiguiError,                  # Base class for all SDK errors
    SiguiConnectionError,        # Cannot reach the API
    SiguiBlockedError,           # Verdict is BLOCK (when raise_on_block=True)
    SiguiEscalationRequiredError,# Verdict is ESCALATE (when raise_on_escalate=True)
    SiguiPaymentError,           # x402 micropayment failed
    SiguiAuthError,              # Invalid credentials (HTTP 401)
    SiguiRateLimitError,         # Rate limit exceeded (HTTP 429)
    SiguiServiceUnavailableError,# Backend in EMERGENCY mode (HTTP 503)
)
```

### Recommended error handling pattern

```python
from sigui import SiguiClient
from sigui.exceptions import (
    SiguiBlockedError,
    SiguiEscalationRequiredError,
    SiguiConnectionError,
    SiguiRateLimitError,
)
import asyncio

async def safe_transfer(client, amount, destination):
    try:
        result = await client.evaluate(
            amount=amount,
            destination=destination,
            raise_on_block=True,
            raise_on_escalate=True,
        )
        # Only reached if verdict is ALLOW
        print(f"✅ Safe (risk={result.risk_score:.3f}) — proceeding")

    except SiguiBlockedError as e:
        print(f"🚫 BLOCKED: {e.reason}")
        print(f"   Risk score: {e.risk_score:.3f}")
        print(f"   Pattern: {e.vision_pattern}")
        # Abort the transaction

    except SiguiEscalationRequiredError as e:
        print(f"⚠️  ESCALATION needed (score={e.decision.risk_score:.2f})")
        # Optionally trigger deep analysis:
        # deep = await client.escalate(amount=amount, destination=destination)

    except SiguiConnectionError as e:
        print(f"🔌 Cannot reach Sigui backend: {e}")
        # Decide: fail-open or fail-closed

    except SiguiRateLimitError as e:
        print(f"⏳ Rate limited. Retry in {e.retry_after}s")
        await asyncio.sleep(e.retry_after)
```

### `SiguiBlockedError` attributes

```python
except SiguiBlockedError as e:
    e.reason          # str  — why it was blocked
    e.risk_score      # float — 0.0 to 1.0
    e.vision_pattern  # str  — detected attack pattern
    e.result          # EvaluationResult — full result object
```

---

## 🔬 Advanced Usage

### Setting a specific `agent_id`

The `agent_id` is used by the **MemoClaw** behavioral memory layer to track agent history across calls. Use a unique, stable ID per agent instance:

```python
client = SiguiClient(
    api_url="http://localhost:8000",
    agent_id="prod-langchain-agent-v2",  # stable identifier
)
```

### Passing context for better decisions

The `context` dict is passed to the pipeline and can improve decision accuracy:

```python
result = await client.evaluate(
    amount=500.0,
    destination="0xPartner...",
    context={
        "memo": "Monthly SLA payment",
        "invoice_id": "INV-2026-042",
        "counterparty_kyc": True,
        "session_id": "sess_abc",
    }
)
```

### Production mode with CircleWallet

In demo mode (`DemoWallet`), x402 micropayments are simulated. For production:

```python
from sigui import SiguiClient, CircleWallet

wallet = CircleWallet(
    api_key="your_circle_api_key",
    wallet_id="wlt_your_wallet_id",
)

client = SiguiClient(
    api_url="https://api.sigui.io",
    wallet=wallet,
    agent_id="prod_agent",
    chain="arc",
)
```

### Targeting specific chains

```python
from sigui import SiguiClient, Chain

client = SiguiClient(api_url="http://localhost:8000", chain=Chain.ETHEREUM)

# Override per-call
result = await client.evaluate(
    amount=1.5,
    destination="0xSolAddress...",
    chain=Chain.SOLANA,
)
```

### Checking on-chain proof

Every evaluation on Arc Protocol generates an immutable on-chain proof:

```python
result = await client.evaluate(amount=10.0, destination="0x...")

if result.onchain_proof:
    print(f"Proof: {result.onchain_proof}")
    # → https://testnet.arcscan.app/tx/0xABC...
```

### Inspecting raw pipeline signals

```python
result = await client.evaluate(amount=50.0, destination="0x...")

# Which layers triggered
print(result.layers_triggered)
# {"memoclaw": True, "sirige": False, "anti_splitting": True, ...}

# Raw behavioral signal
print(result.raw_signals.behavioral)
print(result.raw_signals.financial)
print(result.raw_signals.visual_topology)

# Full raw API response
print(result.raw)
```

---

## 🧠 How It Works: The 5-Layer Pipeline

When your agent calls `client.evaluate()`, the backend runs a multi-layer security check in **< 50 ms**:

```
┌─────────────────────────────────────────────────────────┐
│                   client.evaluate()                     │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP POST /evaluate
                       ▼
┌─────────────────────────────────────────────────────────┐
│  Layer 1 — MemoClaw (Behavioral Memory)                 │
│  Compares this action against the agent's history.      │
│  Detects unusual spikes, address changes, timing.       │
├─────────────────────────────────────────────────────────┤
│  Layer 2 — Sirige (Rule Engine)                         │
│  Fast rule-based checks: blacklists, amount thresholds, │
│  velocity limits, known malicious address patterns.     │
├─────────────────────────────────────────────────────────┤
│  Layer 3 — Anti-Splitting                               │
│  Cross-chain graph analysis to detect smurfing: large   │
│  amounts split across multiple small transactions.      │
├─────────────────────────────────────────────────────────┤
│  Layer 4 — Imina Na (Vision Model)                      │
│  Renders the transaction graph as an image and runs it  │
│  through a fine-tuned Qwen2-VL-7B classifier to detect  │
│  known attack topologies visually.                      │
├─────────────────────────────────────────────────────────┤
│  Layer 5 — Kanaga (Risk Aggregator)                     │
│  Weighted combination of all signals → final verdict.   │
│  Logs an immutable proof on Arc Protocol.               │
└──────────────────────┬──────────────────────────────────┘
                       │ EvaluationResult
                       ▼
              ALLOW / BLOCK / ESCALATE
```

If `ESCALATE` is returned, `client.escalate()` triggers a **deep analysis** by the **Lebe** model (Qwen2.5-72B fine-tuned on AMD MI300X GPUs), or falls back to Claude for maximum reliability.

---

## 🤗 Open-Source Model & Dataset

The **Imina Na** vision layer is fully open-source:

- **Model**: [Ibonon/imina_na_v2_lora](https://huggingface.co/Ibonon/imina_na_v2_lora)
  Fine-tuned Qwen2-VL-7B-Instruct using Unsloth on AMD MI300X GPUs.

- **Dataset**: [Ibonon/sigui-depin-1mn](https://huggingface.co/datasets/Ibonon/sigui-depin-1mn)
  1 million synthetic transaction graphs labeled with 12 attack categories.

Both are available under open licenses for research and community use.

---

## 💻 CLI Reference

The SDK ships with a `sigui` CLI for quick testing and diagnostics:

```bash
# Check if the backend is reachable
sigui health --url http://localhost:8000

# Evaluate a transaction from the command line
sigui evaluate \
    --url http://localhost:8000 \
    --amount 50.0 \
    --destination 0xRecipient... \
    --agent-id my_test_agent

# Check treasury state
sigui treasury --url http://localhost:8000
```

---

## 📄 License

MIT © Sigui Protocol.

*Built for the Agentic Economy.*
