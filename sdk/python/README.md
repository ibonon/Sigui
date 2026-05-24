# Sigui SDK — Python

> **Autonomous Security for the Agentic Economy**  
> Add Sigui to any AI agent in **2 lines of code**. Protect every USDC payment before it executes.

[![PyPI version](https://img.shields.io/pypi/v/sigui-sdk.svg)](https://pypi.org/project/sigui-sdk/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built on Arc](https://img.shields.io/badge/built%20on-Arc%20L1-orange.svg)](https://arc.network)
[![Powered by AMD](https://img.shields.io/badge/inference-AMD%20MI300X-red.svg)](https://amd.com)

---

## What is Sigui?

Sigui is a **decentralized security oracle** that protects AI agent payments before they execute.  
Every transaction is analyzed by a 5-layer AI security pipeline in **< 25 ms**:

| Layer | Module | Role |
|:------|:-------|:-----|
| 1 | **MemoClaw** | Episodic memory & behavioral profiling |
| 2 | **Sirige** | Rule-based anomaly detection |
| 3 | **Anti-splitting** | Cross-chain flow analysis |
| 4 | **Imina Na** | Visual pattern recognition (Qwen2-VL / AMD MI300X) |
| 5 | **Kanaga** | Risk aggregation (ROCm / PyTorch) |

Payment is handled automatically via the **x402 protocol** — your agent never touches payment logic.

---

## Installation

```bash
pip install sigui-sdk
```

**Framework extras** — install only what you need:

```bash
pip install "sigui-sdk[langchain]"       # LangChain
pip install "sigui-sdk[langgraph]"       # LangGraph
pip install "sigui-sdk[crewai]"          # CrewAI
pip install "sigui-sdk[openai-agents]"   # OpenAI Agents SDK
pip install "sigui-sdk[autogen]"         # Microsoft AutoGen ≥ 0.4
pip install "sigui-sdk[smolagents]"      # HuggingFace smolagents

pip install "sigui-sdk[all]"             # Every integration at once
```

---

## Quickstart (2 lines)

```python
from sigui import SiguiClient

async with SiguiClient(api_url="http://localhost:8000") as client:
    result = await client.evaluate(amount=5.0, destination="0xRecipient...")

    if result.is_safe:
        print(f"✅ Authorized   risk={result.risk_score:.3f}")
    elif result.is_blocked:
        print(f"🚫 Blocked      {result.reason}")
    else:
        print(f"⚠️  Escalation required")
```

**Sync version** (for non-async agents):

```python
from sigui import SiguiClientSync

with SiguiClientSync(api_url="http://localhost:8000") as client:
    result = client.evaluate(amount=1.0, destination="0xAbc...")
    print(result.verdict)  # ALLOW / BLOCK / ESCALATE
```

---

## Framework Integrations

### 🦜 LangChain

```python
from sigui import SiguiClient
from sigui.integrations.langchain import create_langchain_tool

client     = SiguiClient(api_url="http://localhost:8000")
sigui_tool = create_langchain_tool(client, auto_escalate=True)

# Drop into any LangChain agent's tools list
agent = initialize_agent(tools=[sigui_tool, ...], llm=llm, ...)
```

### 🕸️ LangGraph

```python
from sigui import SiguiClient
from sigui.integrations.langgraph import create_langgraph_tool
from langgraph.prebuilt import ToolNode

client     = SiguiClient(api_url="http://localhost:8000")
sigui_tool = create_langgraph_tool(client, auto_escalate=True)
tool_node  = ToolNode([sigui_tool])
```

### 🤖 CrewAI

```python
from sigui import SiguiClientSync
from sigui.integrations.crewai import SiguiEvaluationTool

client = SiguiClientSync(api_url="http://localhost:8000", agent_id="crewai_agent")
tool   = SiguiEvaluationTool(sigui_client=client, auto_escalate=True)

agent = Agent(role="Payment Agent", tools=[tool], ...)
```

### 🔮 OpenAI Agents SDK

```python
from agents import Agent, Runner
from sigui import SiguiClient
from sigui.integrations.openai_agents import create_openai_agents_tool

client     = SiguiClient(api_url="http://localhost:8000")
sigui_tool = create_openai_agents_tool(client, auto_escalate=True)

agent  = Agent(name="PaymentAgent", tools=[sigui_tool])
result = await Runner.run(agent, "Send 5 USDC to 0xAbc...")
```

### 🧩 AutoGen (Microsoft)

```python
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from sigui import SiguiClient
from sigui.integrations.autogen import create_autogen_tool

client     = SiguiClient(api_url="http://localhost:8000")
sigui_tool = create_autogen_tool(client, auto_escalate=True)

agent = AssistantAgent(
    name="payment_agent",
    model_client=OpenAIChatCompletionClient(model="gpt-4o"),
    tools=[sigui_tool],
    system_message="Always use sigui_evaluate before any transfer.",
)
```

### 🤗 smolagents (HuggingFace)

```python
from smolagents import CodeAgent, HfApiModel
from sigui import SiguiClient
from sigui.integrations.smolagents import SiguiTool

client = SiguiClient(api_url="http://localhost:8000")
tool   = SiguiTool(client, auto_escalate=True)

agent = CodeAgent(tools=[tool], model=HfApiModel("meta-llama/Llama-3.1-70B-Instruct"))
agent.run("Transfer 5 USDC to 0xRecipient on Arc network.")
```

---

## `@sigui_protect` Decorator

Gate **any async function** behind Sigui — framework-agnostic:

```python
from sigui import SiguiClient
from sigui.decorators import sigui_protect

client = SiguiClient(api_url="http://localhost:8000")

@sigui_protect(client, amount_arg="usdc", destination_arg="to")
async def transfer(to: str, usdc: float, memo: str = ""):
    # Only executes if Sigui returns ALLOW
    await wallet.send(to, usdc)

# Usage:
await transfer(to="0xAbc...", usdc=5.0)  # raises SiguiBlockedError if blocked
```

---

## x402 Payments — Fully Automatic

```
Your agent calls client.evaluate()
    │
    ├─ SDK → POST /evaluate   (no payment)
    ├─ Server → 402 + payment instructions
    ├─ SDK → Sends USDC via wallet adapter
    └─ SDK → POST /evaluate   (X-Payment: <tx_hash>) → ✅ Result
```

**Development** (no real money):
```python
client = SiguiClient(api_url="http://localhost:8000")   # DemoWallet by default
```

**Production** (Circle DCW):
```python
from sigui import SiguiClient, CircleWallet

wallet = CircleWallet(api_key="circle_key", wallet_id="wlt_xxx")
client = SiguiClient(api_url="https://api.sigui.io", wallet=wallet)
```

---

## EvaluationResult Reference

```python
result = await client.evaluate(amount=5.0, destination="0x...")

result.verdict              # Verdict.ALLOW | BLOCK | ESCALATE | ALLOW_WITH_CAP
result.risk_score           # float [0.0 – 1.0]
result.confidence           # float [0.0 – 1.0]
result.reason               # str — human-readable explanation
result.is_safe              # bool — True if ALLOW
result.is_blocked           # bool — True if BLOCK
result.needs_escalation     # bool — True if ESCALATE
result.vision_pattern       # "NORMAL" | "SMURFING" | "SPLITTING" | ...
result.onchain_proof        # Arc explorer URL (real on-chain proof, or None)
result.evaluation_price_usdc  # x402 fee paid (in USDC)
result.processing_time_ms   # backend latency
```

---

## Deep Analysis (Escalation)

```python
# Manual escalation
if result.needs_escalation:
    deep = await client.escalate(amount=5.0, destination="0x...")
    print(deep.analysis)           # Full security analysis text
    print(deep.inference_engine)   # "lebe_qwen25" | "claude_fallback"
    print(deep.inference_device)   # "AMD MI300X" | "REMOTE"

# Auto-escalate in one call
final = await client.evaluate_and_escalate(amount=5.0, destination="0x...")
```

---

## Exception-based Flow

```python
from sigui import SiguiClient, SiguiBlockedError

client = SiguiClient(api_url="http://localhost:8000", raise_on_block=True)

try:
    result = await client.evaluate(amount=100.0, destination="0x...")
    execute_payment(result.action_hash)          # Only reached if ALLOW
except SiguiBlockedError as e:
    log.warning(f"Blocked: {e.result.reason}")
```

---

## Supported Chains

| Chain | Status | Payment |
|:------|:------:|:--------|
| Arc L1 | ✅ Live | x402 native USDC |
| Ethereum | ✅ Live | ERC-20 USDC |
| Solana | ✅ Live | SPL USDC |

---

## Run the Examples

```bash
# 1. Start the Sigui backend
cd ../..
uvicorn main:app --reload

# 2. Run examples (separate terminal)
cd sdk/python
pip install -e ".[all]"

python examples/simple_agent.py          # Basic async
python examples/langchain_agent.py       # LangChain
python examples/crewai_agent.py          # CrewAI
python examples/openai_agents_agent.py   # OpenAI Agents SDK
python examples/autogen_agent.py         # AutoGen
python examples/smolagents_agent.py      # smolagents
```

---

## Package Architecture

```
sigui/
├── __init__.py           # Public API surface
├── client.py             # SiguiClient (async) + SiguiClientSync
├── models.py             # EvaluationResult, EscalationResult, Verdict, Chain, …
├── x402.py               # x402 protocol handler + DemoWallet / CircleWallet
├── decorators.py         # @sigui_protect — framework-agnostic decorator
├── exceptions.py         # Typed exception hierarchy
└── integrations/
    ├── _common.py        # SiguiGuard — shared evaluation logic
    ├── langchain.py      # create_langchain_tool()
    ├── langgraph.py      # create_langgraph_tool()
    ├── crewai.py         # SiguiEvaluationTool
    ├── openai_agents.py  # create_openai_agents_tool()
    ├── autogen.py        # create_autogen_tool()
    └── smolagents.py     # SiguiTool
```

---

## License

MIT © Sigui Protocol

---

*Built with ❤️ on AMD MI300X · Arc L1 · Circle USDC*
