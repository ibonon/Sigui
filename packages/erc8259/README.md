# erc-8259

[![Ethereum ERC-8259](https://img.shields.io/badge/ERC--8259-Draft-blueviolet)](https://eips.ethereum.org/EIPS/eip-8259)
[![PR #2142 Merged](https://img.shields.io/badge/ethereum%2FERCs-PR%20%232142%20merged-brightgreen)](https://github.com/ethereum/ERCs/pull/2142)
[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-lightgrey.svg)](LICENSE)
[![NPM Version](https://img.shields.io/npm/v/erc-8259)](https://www.npmjs.com/package/erc-8259)

Standard Solidity interfaces and `ERC8259Guard` for **ERC-8259: AI Agent Identity & Threat Registry**.

Protect your DeFi protocols and smart contracts from rogue autonomous AI agents in **2 lines of code**.

---

> [!CAUTION]
> **CRITICAL SECURITY FIX - v1.3.0 - UPGRADE IMMEDIATELY**
> Versions prior to 1.3.0 contained a logic flaw where **deactivated agents retained verified status**:
> - `getEffectiveTier(agent)` returned non-zero for deactivated agents with unexpired tiers.
> - `isVerified(agent)` returned `true` for deactivated agents.
> - `calculateTrustScore(agent)` awarded full trust score to deactivated agents.
> This allowed banned/compromised agents to bypass `ERC8259Guard` checks.
> Found by internal audit (2026-11-04) - present since v1.0.0.
> **Upgrade to v1.3.0 immediately.** See [CHANGELOG.md](./CHANGELOG.md) for details.

> [!IMPORTANT]
> **UPGRADE NOTICE FOR USERS OF v1.0.x / v1.1.0**:
> Versions prior to 1.2.0 contained a desynchronized version of `IAgentIdentityRegistry.sol`:
> - Missing `uint256 verificationExpiry` in `AgentIdentity`.
> - Missing `getEffectiveTier(address)`.
> - Incorrectly accepted `verificationTier` in `registerAgent()`, which allowed self-assigned verification tiers.
>
> **Upgrade to v1.2.1 immediately.** In v1.2.0+, newly registered agents strictly initialize at Tier 0 (unverified), and verification status expires dynamically via `getEffectiveTier()`. See [CHANGELOG.md](./CHANGELOG.md) for details.

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
import {ERC8259Guard} from "erc-8259/contracts/ERC8259Guard.sol";

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

> [!WARNING]
> ⚠️ **DEPRECATED CONTRACT NOTICE (Sepolia)**: The Vyper contract deployed at `0x3806aeb76eDD2E22D3cF66A163113c4b24243b29` predates ERC-8259 PR #2137 and does NOT include `verification_expiry`, `get_effective_tier`, or incident lifecycle (`retract_attack`/`resolve_attack`). It accepts `verification_tier` directly at registration (privilege escalation risk). **DO NOT use this address in production or as a reference implementation.** A corrected deployment is tracked at [Redeployment Issue #2](https://github.com/ibonon/Sigui/issues/2).

| Network | Contract | Status | Address |
|---|---|---|---|
| **Ethereum Sepolia** | `AgentIdentityRegistry` | ⚠️ **DEPRECATED (Pre-PR #2137)** | [`0x3806aeb76eDD2E22D3cF66A163113c4b24243b29`](https://sepolia.etherscan.io/address/0x3806aeb76eDD2E22D3cF66A163113c4b24243b29) |
| **Aptos Testnet** | `agent_reputation` | Active Testnet | [`0x833279d99a693392a7245f489967c4714c7bc76589a4f1e0b1c5590c4548c828`](https://explorer.aptoslabs.com/account/0x833279d99a693392a7245f489967c4714c7bc76589a4f1e0b1c5590c4548c828?network=testnet) |

---

## 📜 Standard Specification

* **Specification**: [ERC-8259 Spec](https://eips.ethereum.org/EIPS/eip-8259)
* **Discussion Forum**: [Fellowship of Ethereum Magicians](https://ethereum-magicians.org/t/erc-8259-ai-agent-identity-reputation-threat-registry-draft-v2-request-for-feedback/28521)
* **Changelog**: Full history in [CHANGELOG.md](./CHANGELOG.md)
* **License**: CC0-1.0
