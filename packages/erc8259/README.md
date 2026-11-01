# erc-8259

[![Ethereum ERC-8259](https://img.shields.io/badge/ERC--8259-Draft-blueviolet)](https://eips.ethereum.org/EIPS/eip-8259)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](LICENSE)

Standard Solidity interfaces and `ERC8259Guard` for **ERC-8259: AI Agent Identity & Threat Registry**.

Protect your DeFi protocols and smart contracts from rogue autonomous AI agents in **2 lines of code**.

---

## 📦 Installation

```bash
npm install erc-8259
```

Or with yarn / pnpm:
```bash
yarn add erc-8259
pnpm add erc-8259
```

With Foundry:
```bash
forge install sigui-protocol/contracts
```

---

## 🛡️ Quickstart: 2-Line Integration

Inherit `ERC8259Guard` and append `onlySafeAgent` to any function you want to protect against known rogue agents or exploit bots:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// 1. Import
import {ERC8259Guard} from "erc-8259/ERC8259Guard.sol";

// 2. Protect sensitive logic
contract Vault is ERC8259Guard {
    constructor(address _threatRegistry) 
        ERC8259Guard(_threatRegistry, address(0)) {}

    function withdrawLiquidity(uint256 amount) external onlySafeAgent {
        // Attackers flagged in the decentralized registry are reverted instantly.
    }
}
```

---

## 🔍 Available Modifiers

| Modifier | Description |
|---|---|
| `onlySafeAgent` | Reverts if the caller (`msg.sender`) is marked as an attacker in `IThreatRegistry`. |
| `onlyVerifiedAgent` | Requires the agent to be safe AND registered with a verification tier (`Tier > 0`). |
| `minTrustScore(threshold)` | Enforces a minimum trust score (0 to 1000 basis points, e.g. 700 = 70.0%). |

---

## 📍 Live Deployments

| Network | Contract | Address |
|---|---|---|
| **Ethereum Sepolia** | `AgentIdentityRegistry` | [`0x3806aeb76eDD2E22D3cF66A163113c4b24243b29`](https://sepolia.etherscan.io/address/0x3806aeb76eDD2E22D3cF66A163113c4b24243b29) |
| **Aptos Testnet** | `agent_reputation` | [`0x833279d99a693392a7245f489967c4714c7bc76589a4f1e0b1c5590c4548c828`](https://explorer.aptoslabs.com/account/0x833279d99a693392a7245f489967c4714c7bc76589a4f1e0b1c5590c4548c828?network=testnet) |

---

## 📜 Standard Specification

* **Specification**: [ERC-8259 Spec](https://eips.ethereum.org/EIPS/eip-8259)
* **Discussion Forum**: [Fellowship of Ethereum Magicians](https://ethereum-magicians.org/t/erc-8259-ai-agent-identity-reputation-threat-registry-draft-v2-request-for-feedback/28521)
* **License**: CC0-1.0
