# Sigui SDK — Autonomous Security for AI Agents (v0.3.1)

[![PyPI version](https://img.shields.io/pypi/v/sigui-sdk.svg)](https://pypi.org/project/sigui-sdk/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Starknet](https://img.shields.io/badge/Starknet-Cairo_2.x-red.svg)](https://starknet.io)
[![Aptos](https://img.shields.io/badge/Aptos-Move-green.svg)](https://aptosfoundation.org)

**Sigui** is an open-source security oracle that protects AI agents from sending erroneous or malicious crypto payments. 

In version **0.3.1**, we introduce massive upgrades: **ElizaOS Native Integration**, a built-in **Local Mock Server** for hackathons, **Hugging Face `from_pretrained`** support for DePIN nodes, and **Multi-Chain Smart Contracts** (EVM, Starknet Cairo, Aptos Move).

## Table of Contents

1. [Installation](#-installation)
2. [What's New in 0.3.1](#-whats-new-in-031)
3. [Local Development (Mock Server)](#-local-development-mock-server-new)
4. [Framework Integrations (ElizaOS, LangChain, etc.)](#-framework-integrations)
5. [DePIN Node: from_pretrained](#-depin-node-from_pretrained-new)
6. [Multi-Chain Smart Contracts](#-multi-chain-smart-contracts-new)
7. [Core API Reference](#-core-api-reference)

---

## 📦 Installation

```bash
pip install sigui-sdk==0.3.1
```

Install the extras for your preferred agent framework:

```bash
pip install "sigui-sdk[elizaos]"         # ElizaOS (Node.js/Python hybrid)
pip install "sigui-sdk[langchain]"       # LangChain & LangGraph
pip install "sigui-sdk[crewai]"          # CrewAI
pip install "sigui-sdk[autogen]"         # Microsoft AutoGen (AG2)
pip install "sigui-sdk[openai-agents]"   # OpenAI Agents SDK
pip install "sigui-sdk[smolagents]"      # HuggingFace smolagents
```

---

## 🔥 What's New in 0.3.1

- **ElizaOS Plugin**: Natively integrate Sigui into the Eliza ecosystem.
- **Local Mock Server**: Test your integration without spinning up Docker or needing a GPU.
- **Pretrained Weights**: Run the `sigui/imina-na-v2` LoRA model locally via `huggingface_hub`.
- **Multichain Reputation**: Support for ERC-8259 across Ethereum (Vyper), Starknet (Cairo), and Aptos (Move).

---

## 🛠️ Local Development (Mock Server) [NEW]

You no longer need to run the full Docker stack to build with Sigui. The SDK now ships with an embedded FastAPI mock server that simulates probabilistic risk heuristics.

```python
import asyncio
from sigui import SiguiClient, start_mock_server

async def main():
    # 1. Start the mock server in a background thread
    server = start_mock_server(port=8765)
    
    # 2. Connect the client to the mock URL
    async with SiguiClient(api_url=server.url) as client:
        result = await client.evaluate(
            amount=5000.0, 
            destination="0x000000000000000000000000000000000000dead" # Known bad
        )
        print(f"Verdict: {result.verdict} | Risk: {result.risk_score}")
        # -> Verdict: Verdict.BLOCK | Risk: 0.97
        
    # 3. Shutdown cleanly
    server.stop()

asyncio.run(main())
```

---

## 🤖 Framework Integrations

### 🔴 ElizaOS (New in 0.3.1)
Use Sigui as a security plugin in your ElizaOS character config.

```python
# The python backend for the Eliza plugin
from sigui.integrations.elizaos import SiguiElizaPlugin

plugin = SiguiElizaPlugin(api_url="http://localhost:8000", agent_id="eliza_defi")
```
*Note: This pairs with the `@elizaos/plugin-sigui` npm package in your TypeScript agent.*

### 🦜 LangChain / LangGraph
```python
from sigui import SiguiClient
from sigui.integrations.langchain import create_langchain_tool

client = SiguiClient(api_url="http://localhost:8000")
sigui_tool = create_langchain_tool(client, auto_escalate=True)

# Add sigui_tool to your LangChain agent's tool list
```

---

## 🖥️ DePIN Node: `from_pretrained` [NEW]

If you are a Sigui DePIN node operator (e.g., running AMD MI300X), you can download the model weights directly and run local inference via the SDK.

```python
import asyncio
from sigui import from_pretrained

async def run_node():
    # Automatically downloads Imina-Na V2 weights from HuggingFace
    # and spins up a local inference engine.
    client = await from_pretrained("sigui/imina-na-v2")
    
    result = await client.evaluate(amount=100, destination="0xAbc...")
    print(result.verdict)
    
    await client.close()

asyncio.run(run_node())
```

---

## ⛓️ Multi-Chain Smart Contracts [NEW]

Sigui enforces reputation using the ERC-8259 standard. In version 0.3.1, we have expanded our smart contract footprint beyond Ethereum:

- **Ethereum (Vyper)**: Native EVM support (`contracts/ethereum`).
- **Starknet (Cairo 2.x)**: Full ZK-Rollup support (`contracts/starknet`). High-throughput oracle validation.
- **Aptos (Move)**: Highly parallelized Block-STM execution with Move Prover formal verification (`contracts/aptos`).

---

## 📄 License
MIT © Sigui Protocol.
*Built for the Agentic Economy.*
