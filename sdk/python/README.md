# Sigui SDK — Python

> **Autonomous Security for the Agentic Economy**
> Protect your AI agent's USDC payments in 2 lines of code.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built on Arc](https://img.shields.io/badge/built%20on-Arc%20L1-orange.svg)](https://arc.network)
[![Powered by AMD](https://img.shields.io/badge/inference-AMD%20MI300X-red.svg)](https://amd.com)

---

## What is Sigui?

Sigui is a **decentralized security oracle** that protects AI agent payments before they execute.
Every transaction is analyzed by a 5-layer AI security system in under 25ms:

1. **MemoClaw** — Episodic memory & behavioral profiling
2. **Sirige** — Rule-based anomaly detection  
3. **Anti-splitting** — Cross-chain flow analysis
4. **Imina Na** — Visual pattern recognition (Qwen2-VL on AMD MI300X)
5. **Kanaga** — Risk aggregation engine (ROCm/PyTorch)

Payment is handled automatically via the **x402 protocol** — your agent never touches the payment logic.

---

## Installation

```bash
pip install sigui-sdk
```

Or from source (this repo):
```bash
cd sdk/python
pip install -e .
```

---

## Quickstart

### Async (recommended)

```python
from sigui import SiguiClient

async with SiguiClient(api_url="http://localhost:8000") as client:
    result = await client.evaluate(
        amount=5.0,
        destination="0xRecipient...",
    )

    if result.is_safe:
        print(f"✅ Authorized — risk={result.risk_score:.3f}")
    elif result.is_blocked:
        print(f"🚫 Blocked — {result.reason}")
    else:
        print(f"⚠️  Escalation required")
```

### Sync (for non-async agents)

```python
from sigui import SiguiClientSync

with SiguiClientSync(api_url="http://localhost:8000") as client:
    result = client.evaluate(amount=1.0, destination="0xAbc...")
    print(result.verdict)  # ALLOW / BLOCK / ESCALATE
```

---

## x402 Payments — Fully Automatic

The Sigui API charges a micro-fee per evaluation via the [x402 protocol](https://x402.org).
The SDK handles the entire payment flow transparently:

```
Your agent calls client.evaluate()
    │
    ├─ SDK → POST /evaluate (no payment yet)
    ├─ Server → 402 + payment instructions
    ├─ SDK → Sends USDC payment (DemoWallet in dev, CircleWallet in prod)
    └─ SDK → POST /evaluate (with X-Payment header) → Result ✅
```

**Development (no real payments):**
```python
# DemoWallet is used by default — simulates payments
client = SiguiClient(api_url="http://localhost:8000")
```

**Production (Circle DCW):**
```python
from sigui import SiguiClient, CircleWallet

wallet = CircleWallet(api_key="your_circle_api_key", wallet_id="wlt_xxx")
client = SiguiClient(
    api_url="https://api.sigui.io",
    wallet=wallet,
    chain="arc",
)
```

---

## EvaluationResult

```python
result = await client.evaluate(amount=5.0, destination="0x...")

result.verdict           # Verdict.ALLOW | BLOCK | ESCALATE
result.risk_score        # float [0.0, 1.0]
result.confidence        # float [0.0, 1.0]
result.reason            # str — human-readable explanation
result.is_safe           # bool — True if ALLOW
result.is_blocked        # bool — True if BLOCK
result.needs_escalation  # bool — True if ESCALATE
result.vision_pattern    # "NORMAL" | "SMURFING" | "SPLITTING" | ...
result.onchain_proof     # Arc explorer URL (if confirmed onchain)
result.evaluation_price_usdc  # x402 fee paid
result.processing_time_ms     # backend latency
```

---

## Deep Analysis (Escalation)

When `result.needs_escalation` is `True`, call `/escalate` for deep analysis
by **Lebe** (Qwen2.5-3B on AMD MI300X) or Claude as fallback:

```python
# Manual escalation
if result.needs_escalation:
    deep = await client.escalate(amount=5.0, destination="0x...")
    print(deep.analysis)        # Detailed security analysis
    print(deep.inference_engine)  # "lebe_qwen25" | "claude_fallback"
    print(deep.inference_device)  # "AMD MI300X" | "REMOTE"

# Or auto-escalate in one call
final = await client.evaluate_and_escalate(amount=5.0, destination="0x...")
```

---

## Exception-based Flow

For cleaner agent code, use `raise_on_block=True`:

```python
from sigui import SiguiClient, SiguiBlockedError, SiguiEscalationRequiredError

client = SiguiClient(
    api_url="http://localhost:8000",
    raise_on_block=True,
    raise_on_escalate=True,
)

try:
    result = await client.evaluate(amount=100.0, destination="0x...")
    # Only reached if ALLOW
    execute_payment(result.action_hash)

except SiguiBlockedError as e:
    print(f"Payment blocked: {e.result.reason}")

except SiguiEscalationRequiredError as e:
    # Handle escalation
    pass
```

---

## Framework Integrations

### LangChain

```python
from sigui import SiguiClient
from langchain.tools import tool

_sigui = SiguiClient(api_url="http://localhost:8000")

@tool
async def safe_transfer(destination: str, amount_usdc: float) -> str:
    """Evaluate a USDC transfer with Sigui before executing it."""
    result = await _sigui.evaluate(amount=amount_usdc, destination=destination)
    return f"SIGUI: {result.verdict.value} (risk={result.risk_score:.3f})"
```

→ Full example: [`examples/langchain_agent.py`](examples/langchain_agent.py)

### CrewAI

```python
from sigui.integrations.crewai import SiguiEvaluationTool

tool = SiguiEvaluationTool(sigui_client=client)
# Add to any CrewAI Agent's tools list
```

→ Full example: [`examples/crewai_agent.py`](examples/crewai_agent.py)

---

## Supported Chains

| Chain    | Status | Payment |
|:---------|:------:|:--------|
| Arc L1   | ✅ Live | x402 native USDC |
| Ethereum | ✅ Live | ERC-20 USDC |
| Solana   | ✅ Live | SPL USDC |

---

## Run the Examples

```bash
# Start the Sigui backend first
cd ../..
uvicorn main:app --reload

# Then in another terminal
cd sdk/python
pip install -e .
python examples/simple_agent.py
python examples/langchain_agent.py
python examples/crewai_agent.py
```

---

## Architecture

```
sigui/
├── __init__.py      # Public API
├── client.py        # SiguiClient (async) + SiguiClientSync
├── models.py        # EvaluationResult, EscalationResult, etc.
├── x402.py          # x402 payment handler + wallet adapters
└── exceptions.py    # Typed exceptions
```

---

## License

MIT © Sigui Protocol

---

*Built with ❤️ on AMD MI300X · Arc L1 · Circle USDC*
