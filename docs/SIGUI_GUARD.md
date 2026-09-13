# 🛡️ Sigui Guard — Zero-Code AI Agent RPC Security Proxy

> **Protect autonomous AI agents from wallet drains, honeypots, and rug pulls with 0 lines of code changed in your agent.**

Sigui Guard acts as an ultra-fast local RPC firewall proxy (`http://127.0.0.1:8545`). Whenever an autonomous agent (ElizaOS, AutoGPT, CrewAI, LangChain, or custom trading bot) attempts to execute a blockchain transaction, Sigui Guard intercepts and pre-audits the call in `<30ms`.

If the destination address or token beneficiary exhibits a `DRAIN_STAR` or malicious pattern, **Sigui Guard aborts the transaction immediately**, returning a standard JSON-RPC error `-32003` to the agent. The transaction **never reaches the blockchain**, keeping the treasury completely safe.

---

## ⚡ How It Works

```
[ Autonomous AI Agent ] 
       │ (Calls standard eth_sendRawTransaction / Aptos REST)
       ▼
[ Sigui Guard RPC Proxy ] (http://127.0.0.1:8545)
       │
       ├── Non-transaction queries (eth_blockNumber, eth_getBalance, etc.)
       │     └──► Fast-path forward to Upstream Node (Alchemy, Ankr, Fullnode)
       │
       └── Transaction Calls (eth_sendRawTransaction, Aptos /v1/transactions)
             │
             ├── 1. RLP & Calldata Decoder (<2ms): extracts destination & ERC-20 recipient
             ├── 2. Sigui Security Oracle (<30ms): queries Imina-Na V2 multimodal vision
             │
             ├── ✅ Verdict = ALLOW: Forward to blockchain mempool
             └── 🚨 Verdict = BLOCK: Halt with JSON-RPC error -32003 (Agent treasury protected!)
```

---

## 🚀 Quickstart (1 Command)

### 1. Start Sigui Guard for EVM (Ethereum / Arbitrum / Base / Polygon)
```bash
python -m modules.sigui_guard --port 8545 --upstream https://rpc.ankr.com/eth --network ethereum
```

### 2. Start Sigui Guard for Aptos
```bash
python -m modules.sigui_guard --port 8080 --upstream https://fullnode.testnet.aptoslabs.com --network aptos
```

---

## 💻 Zero-Code Integration Examples

### Web3.py (Python)
Change only your RPC provider URL:
```python
from web3 import Web3

# Simply point to Sigui Guard instead of raw node:
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

# All agent transactions are now automatically protected!
```

### Ethers.js / Viem (TypeScript / Node.js)
```typescript
import { JsonRpcProvider } from "ethers";

// Point to local Sigui Guard firewall:
const provider = new JsonRpcProvider("http://127.0.0.1:8545");
const wallet = new Wallet(privateKey, provider);
```

### ElizaOS Agent (.env)
```env
EVM_PROVIDER_URL=http://127.0.0.1:8545
```

---

## 🛡️ What Happens on an Attack?

When an agent is tricked into sending funds to a Drain Star contract, Sigui Guard intercepts the request and responds:

```json
{
  "jsonrpc": "2.0",
  "id": 42,
  "error": {
    "code": -32003,
    "message": "Transaction rejected by Sigui Guard: DRAIN_STAR threat detected at destination 0xdeadbeef...",
    "data": {
      "sigui_verdict": "BLOCK",
      "target": "0xdeadbeef...",
      "pattern": "DRAIN_STAR",
      "risk_score": 0.99,
      "reason": "High-outdegree drain contract detected by Imina-Na V2 Vision Model"
    }
  }
}
```

The transaction never leaves the agent's machine, saving 100% of the funds.

---

## 🧪 Testing

Run the automated test suite:
```bash
python -m pytest tests/test_sigui_guard.py -v
```
All 7 unit and integration tests verify RLP decoding, ERC-20 calldata extraction, dynamic blacklist interception, and Aptos REST protection.
