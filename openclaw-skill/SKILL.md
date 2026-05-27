---
name: sigui-security
version: "2.0.0"
description: >
  Evaluate the security of blockchain transactions (EVM, Starknet, Aptos) using
  the Sigui Protocol AI oracle. Detects drain attacks, mixer chains, Sybil swarms,
  and flash-loan exploits before they execute. Returns a verdict (ALLOW / BLOCK /
  ESCALATE) with a risk score and on-chain proof.
author: "Warma Abdoul Ibonon Eric <ericwarma2006@gmail.com>"
homepage: "https://github.com/ibonon/Sigui"
license: MIT
tags:
  - blockchain
  - security
  - web3
  - defi
  - ai-agent
  - ethereum
  - starknet
  - aptos
  - multi-chain
requires:
  python: ">=3.10"
  packages:
    - "sigui-sdk>=0.3.1"
    - "rich>=13.0.0"
read_when:
  - The user asks to check, verify, audit, or evaluate a blockchain transaction
  - The user mentions a wallet address, tx hash, or token transfer amount
  - The user asks whether a DeFi action, NFT mint, or smart contract call is safe
  - The user mentions "drain", "rug pull", "exploit", "mixer", "Sybil", "flash loan"
  - The user wants to protect their agent's on-chain actions
  - The user mentions EVM, Ethereum, Starknet, Aptos, ARC, or any L2 chain
---

# Sigui Protocol Security Skill 🛡️

**Sigui** is a multi-chain AI security oracle that evaluates blockchain transactions before they execute. It uses a native Spatio-Temporal Transformer (Trustformer/T-GAT) to detect coordinated attacks in real time — without the 48ms graph-rendering bottleneck of VLM-based approaches.

## 🧠 Chain of Thought (for OpenClaw Agent)

When a user asks you to verify or execute a blockchain transaction, follow these steps:

1. **Extract Parameters**: Identify the `amount` (in USDC value), the `destination` address, the `chain` (default to `arc`), and the `action` type (`transfer`, `approve`, `swap`, etc.).
2. **Execute Evaluation**: Run the `evaluate.py` script provided in this skill directory using the `bash` or `python` tool.
3. **Parse Verdict**:
   - Exit code `0` (`ALLOW`): Inform the user that the transaction is safe and proceed.
   - Exit code `1` (`BLOCK`): **DO NOT EXECUTE.** Inform the user of the critical threat detected and provide the reason.
   - Exit code `2` (`ESCALATE`): Inform the user that the transaction requires a deep analysis. Run the script again with the `--escalate` flag to perform the deep analysis.
4. **Relay the Result**: Format the output nicely using emojis (✅, 🚫, 🔍) and provide the on-chain proof link if available.

---

## Supported Chains

| Chain       | Argument     | Notes                                |
|-------------|-------------|--------------------------------------|
| ARC (L2)    | `arc`       | Default; ultra-fast, fee-free        |
| Ethereum    | `ethereum`  | Mainnet + Sepolia testnet            |
| Starknet    | `starknet`  | Cairo contracts deployed on Sepolia  |
| Aptos       | `aptos`     | Move contracts on Testnet            |
| Solana      | `solana`    | Coming soon                          |

---

## 🛠️ Usage Examples

### Method 1 — Python Script (Recommended)

Run the helper script directly from the skill directory. The script uses the `rich` library to print a beautiful, easy-to-read table.

```bash
python ~/.openclaw/workspace/skills/sigui-security/evaluate.py \
  --amount 1500.0 \
  --destination "0xBadActorAddress" \
  --action "transfer" \
  --chain "ethereum"
```

To get raw JSON for programmatic parsing, add the `--json` flag:
```bash
python ~/.openclaw/workspace/skills/sigui-security/evaluate.py \
  --amount 1500.0 \
  --destination "0xBadActorAddress" \
  --json
```

### Method 2 — Deep Analysis (Escalation)

If a transaction returns `ESCALATE` (or exit code 2), you can request a deep AI analysis. This uses a heavier model (like Qwen2.5 or Claude) to perform a thorough audit of the contract or address.

```bash
python ~/.openclaw/workspace/skills/sigui-security/evaluate.py \
  --amount 1500.0 \
  --destination "0xUnknownAddress" \
  --escalate
```

### Method 3 — Inline Python (if bash is unavailable)

```python
import asyncio, sys
sys.path.insert(0, ".")

from sigui import SiguiClient
from sigui.local import start_mock_server

async def check():
    server = start_mock_server(port=8765)
    client = SiguiClient(api_url="http://127.0.0.1:8765")
    
    result = await client.evaluate(
        agent_id="openclaw_agent",
        amount=500.0,
        destination="0xRecipientAddress",
        action_type="transfer",
        chain="arc",
    )
    server.stop()
    return result

res = asyncio.run(check())
print(f"Verdict: {res.verdict.value} | Risk: {res.risk_score}")
```

---

## 📊 Interpreting the Verdict

| Verdict         | Risk Score   | Agent Action Required                                       |
|-----------------|-------------|-------------------------------------------------------------|
| `ALLOW`         | 0.0 – 0.35  | ✅ Safe to proceed. Share the safety score with the user.   |
| `ALLOW_WITH_CAP`| 0.35 – 0.55 | ⚠️ Safe but enforce the `cap_amount_usdc` spending limit.   |
| `ESCALATE`      | 0.55 – 0.80 | 🔍 Request deep analysis (`--escalate`) before proceeding.  |
| `BLOCK`         | 0.80 – 1.0  | 🚫 Abort the transaction immediately. Explain the threat.   |

**Risk score** ranges from `0.0` (completely safe) to `1.0` (critical threat).
**Safety score** = `(1 - risk_score) × 1000`. Higher is better.

---

## 🛡️ Threat Types Detected

Sigui detects the following multi-chain attack patterns in real time:

- **Drain Star** — One orchestrator wallet draining multiple victim wallets simultaneously.
- **Mixing Chain** — Funds routed through layered mixer hops to obfuscate origin.
- **Sybil Swarm** — Coordinated fake-identity cluster attacking governance or airdrops.
- **Flash Loan Exploit** — Manipulating price oracles within a single atomic block.
- **Honeypot Contract** — Buy-enabled, sell-disabled token contract trap.
- **Rug Pull** — Liquidity removal by deployer before community exit.
- **Phishing Signature** — Malicious `eth_sign` / `permit` approval requests.

---

## ⚙️ Configuration (Optional)

By default, if the Sigui SDK isn't installed or no backend is running, the script falls back to a **local mock server** for development and testing (no real funds required).

To connect to a live Sigui node, set the environment variables:
```bash
export SIGUI_API_URL="https://api.sigui.io"
export SIGUI_CHAIN="arc"
export OPENCLAW_AGENT_ID="my_agent_name"
```

## 🔒 Privacy & Cost
- Evaluations on ARC are **free** (gasless L2).
- Evaluations on Ethereum/Starknet/Aptos cost a micro-fee paid in USDC (~$0.001).
- **No transaction data is stored** beyond the on-chain proof hash.
- All sensitive fields (wallet keys, private data) stay local — only the metadata is sent for evaluation.

## 🔗 Links
- 📄 GitHub: https://github.com/ibonon/Sigui
- 📦 PyPI: https://pypi.org/project/sigui-sdk/
- 📖 Whitepaper: *Trustformer: A Native Spatio-Temporal Transaction Transformer*
