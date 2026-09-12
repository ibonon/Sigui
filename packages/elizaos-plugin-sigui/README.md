# @elizaos/plugin-sigui (sigui-elizaos-plugin)

> **Sigui DePIN AI Security Oracle Plugin for ElizaOS**  
> Intercepts and pre-audits autonomous agent transactions before execution using fine-tuned vision models (Qwen2-VL-7B on AMD MI300X GPUs) and Zero-Knowledge proofs.

[![NPM Version](https://img.shields.io/npm/v/sigui-elizaos-plugin.svg?color=orange)](https://www.npmjs.com/package/sigui-elizaos-plugin)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20550562-blue)](https://doi.org/10.5281/zenodo.20550562)

---

## 🛡️ Why Sigui for ElizaOS Agents?

Autonomous AI agents in Web3 execute multi-step financial actions (swaps, transfers, contract interactions) without direct human approval. Consequently, agents are prime targets for:
* **Drain Stars**: Exploitative contracts that drain agent balances via high-outdegree token transfers.
* **Mixing Chains**: Obfuscated transaction hops designed to launder stolen funds.
* **Honeypot Contracts & Rug Pulls**: Unverified or malicious bytecode trapping agent liquidity.

`plugin-sigui` acts as a **real-time pre-execution firewall** for any ElizaOS agent. In `<50ms`, transactions are visually and heuristically evaluated, returning an immutable verdict: `ALLOW`, `BLOCK`, or `ESCALATE`.

---

## 📦 Installation

```bash
npm install sigui-elizaos-plugin
# or
pnpm add sigui-elizaos-plugin
# or
bun add sigui-elizaos-plugin
```

---

## ⚡ Quickstart

Add `siguiPlugin` to your ElizaOS agent configuration:

```typescript
import { AgentRuntime } from "@elizaos/core";
import { siguiPlugin } from "sigui-elizaos-plugin";

export const agent = {
  name: "DeFi-Guardian-Agent",
  plugins: [siguiPlugin],
  // ... other agent settings
};
```

---

## ⚙️ Configuration (.env)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SIGUI_API_URL` | URL of the Sigui Security Oracle Gateway | `http://127.0.0.1:8000` |
| `SIGUI_API_KEY` | Optional bearer token for enterprise endpoints | `undefined` |
| `SIGUI_REQUIRE_ZK` | Require Groth16/STARK validity proof for ALLOW verdicts | `false` |
| `SIGUI_FAIL_CLOSED` | Halt transaction execution if oracle is unreachable | `true` |

---

## 🧩 Components

### 1. Action: `EVALUATE_TRANSACTION_SECURITY`
* **Triggered by:** Any transaction intent (transfers, swaps, approvals).
* **Similes:** `CHECK_TRANSACTION_SAFETY`, `AUDIT_TRANSACTION`, `VERIFY_SMART_CONTRACT`, `IS_THIS_SAFE`, `SIGUI_CHECK`.
* **Behavior:** Extracts target contract/wallet, estimated value, and chain. Calls the Sigui Security Engine to inspect the visual graph topology of the destination.
* **Returns:** 
  * `ALLOW` → Agent proceeds with transaction execution.
  * `BLOCK` → Agent refuses execution, logs attack pattern (e.g. `DRAIN_STAR`), and protects treasury funds.
  * `ESCALATE` → Flags transaction for multisig / human guardian confirmation.

### 2. Provider: `threatIntelProvider`
* **Behavior:** Injects the latest learned threat patterns into the agent's contextual memory.
* **Context Injected:** Recent malicious addresses, detected attack patterns, and confidence ratings from Sigui's decentralized feedback loop.

---

## 🔬 Scientific Benchmark & Research

* **Model:** Qwen2-VL-7B fine-tuned via LoRA on ROCm / AMD MI300X.
* **Dataset:** [Sigui-DePIN-1M](https://huggingface.co/datasets/Ibonon/sigui-depin-1m) (1,000,000 annotated blockchain transaction topologies).
* **Inference Latency:** Average `35.3ms` (AMD MI300X hardware).
* **Detection F1-Score:** `92.9%` against adversarial honeypots and drain patterns.
* **Research Paper:** [DOI: 10.5281/zenodo.20550562](https://doi.org/10.5281/zenodo.20550562)

---

## 📄 License

MIT © [Sigui Protocol](https://github.com/ibonon/Sigui)
