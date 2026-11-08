---
aip: 
title: On-Chain Autonomous Agent Identity and Security Reputation Standard
author: Eric Warma (@ibonon) <ericwarma2006@gmail.com>, Sigui Protocol Team
discussions-to: https://github.com/aptos-foundation/AIPs/issues
Status: Draft
type: Standard (Framework)
created: 09/13/2026
---

# AIP-XXX: On-Chain Autonomous Agent Identity & Security Reputation Standard (Using Move Objects)

## Summary

This proposal defines a native, standardized framework for Autonomous AI Agent Identity, Security Auditing, and Tiered On-Chain Reputation on Aptos. 

As autonomous AI agents (such as ElizaOS, CrewAI, AutoGPT, and trading subagents) increasingly sign transactions, interact with DeFi liquidity pools, and manage treasuries on Aptos, smart contracts require a trust-minimized, composable mechanism to verify an agent's operational integrity, track historical performance, and preemptively block known malicious topologies (e.g., Drain Stars and Honeypots).

This standard introduces:
1. **Move Object-Based Agent Identity**: A decentralized agent identifier (`did:sigui:aptos:...`) instantiated as an Aptos Object with granular capability management.
2. **Tiered Dynamic Reputation Engine**: An on-chain scoring system categorizing agents into four verifiable tiers (**Bronze, Silver, Gold, Platinum**) with mathematical bounds and formal verification via the Move Prover.
3. **Decentralized Security & Threat Registry**: An on-chain registry allowing verified AI security oracles to record malicious topologies and execute automated slashing on compromised or adversarial agents.

### Out of scope
- Off-chain LLM inference orchestration and GPU scheduling (handled off-chain by oracles such as Sigui).
- Fiat-to-crypto on-ramping for AI agent wallets.
- Cross-chain bridge custody logic.

---

## High-level Overview

Current blockchain architectures treat autonomous AI agents identically to regular human externally owned accounts (EOAs). Consequently:
- DeFi protocols cannot distinguish between a verified algorithmic market-maker and a rogue drain bot.
- Agents have no persistent, portable reputation across dApps.
- Compromised agents cannot be paused or slashed before draining user pools.

This proposal leverages Aptos's unique **Object-Oriented Move model** and **Move Prover formal verification** to create an open, protocol-agnostic agent infrastructure:

```
┌────────────────────────────────────────────────────────────┐
│                    Autonomous AI Agent                     │
│          (did:sigui:aptos:agent_genesis_001)               │
└─────────────────────────────┬──────────────────────────────┘
                              │
               1. Registers Identity Object
                              ▼
┌────────────────────────────────────────────────────────────┐
│              agent_reputation::AgentProfile                │
│   • Identity: Object<AgentProfile>                         │
│   • Tier: Bronze (0) → Silver (1) → Gold (2) → Platinum(3) │
│   • Trust Score: 0 - 1000                                  │
│   • Move Prover Invariants: Proved No-Overflow             │
└──────────────┬───────────────────────────────▲─────────────┘
               │                               │
2. Interacts with DeFi                         │ 3. Reports Attack /
   (Aries, Thala, Liquidswap)                  │    Updates Reputation
               ▼                               │
┌──────────────────────────────────────────────┴─────────────┐
│              threat_registry::ThreatRegistry               │
│   • Decentralized Multi-Oracle Consensus                   │
│   • Topological Threat Registry (DRAIN_STAR, MIXING_CHAIN) │
│   • Automated Slashing & Quarantine Capabilities           │
└────────────────────────────────────────────────────────────┘
```

Aptos protocols can inspect an agent's reputation in **1 line of Move code** (`agent_reputation::get_tier(agent_addr) >= TIER_GOLD`), granting fee discounts, higher borrowing limits, or automated guardrails.

---

## Impact

* **DeFi Protocols (Lending, DEXes, Liquid Staking)**: Can conditionally gate high-value liquidity to verified agents with proven reputations, preventing flash-loan exploit bots.
* **AI Agent Developers (ElizaOS, LangChain, CrewAI)**: Gain native on-chain identity and reputation that persists across all Aptos dApps without vendor lock-in.
* **End Users**: Treasuries delegated to autonomous agents are protected by on-chain automated slashing and pre-execution security oracles.

If this proposal is not adopted, autonomous agents on Aptos will remain indistinguishable from malicious drainers, leaving protocols vulnerable to automated multi-hop drain attacks.

---

## Alternative Solutions

### Why not port Ethereum's ERC-8259 (EVM Standard)?
An earlier exploration evaluated porting ERC-8259 (Account Abstraction Security Oracle). However, Ethereum standards suffer from severe limitations when applied to Aptos:
1. **Account-Centric Bottlenecks**: EVM standards couple state to account addresses. Aptos **Move Objects** allow agents to own modular, transferrable capability objects, sub-accounts, and segregated resources.
2. **Lack of Formal Verification**: EVM smart contracts rely on runtime reentrancy guards and defensive checks. Aptos Move enables compile-time mathematical proofs via the **Move Prover**.
3. **Sub-second Finality**: Aptos Block-STM parallel execution allows high-frequency reputation updates without network congestion.

Therefore, an Aptos-native AIP utilizing Move Objects is strictly superior.

---

## Specification and Implementation Details

### 1. Reputation Tiers & Constants

```move
const TIER_BRONZE: u8 = 0;    // Score 0 - 249   (New / Unverified)
const TIER_SILVER: u8 = 1;    // Score 250 - 499 (Standard Agent)
const TIER_GOLD: u8 = 2;      // Score 500 - 749 (High Reliability)
const TIER_PLATINUM: u8 = 3;  // Score 750 - 1000 (Institutional Grade)

const MAX_SCORE: u64 = 1000;
const INITIAL_SCORE: u64 = 500; // Genesis Silver
```

### 2. Core Structs (Move Objects & Resources)

```move
/// Persistent on-chain identity and reputation profile for an AI agent.
struct AgentProfile has key, store {
    did: String,                  // Decentralized ID: "did:sigui:aptos:..."
    tier: u8,                     // Bronze | Silver | Gold | Platinum
    score: u64,                   // Saturating 0 - 1000
    tx_count: u64,                // Total audited transactions
    blocked_count: u64,           // Intercepted malicious actions
    slashed_stake: u64,           // Cumulative slashed amount (Octas)
    is_active: bool,              // Operational status
    last_updated: u64,            // Timestamp (seconds)
}

/// Global registry managing agent registrations and oracle authorizations.
struct ReputationRegistry has key {
    admin: address,
    oracle: address,
    total_agents: u64,
    register_events: event::EventHandle<AgentRegisteredEvent>,
    update_events: event::EventHandle<ReputationUpdatedEvent>,
    slash_events: event::EventHandle<AgentSlashedEvent>,
}
```

### 3. Core Interface & Public Functions

#### Registration
```move
public entry fun register_agent(
    account: &signer,
    did: String,
) acquires ReputationRegistry
```
Creates an agent identity profile with initial Silver standing (`score = 500`).

#### Reputation Updates & Slashing
```move
public entry fun update_reputation(
    oracle: &signer,
    agent_addr: address,
    delta: u64,
    is_positive: bool,
) acquires AgentProfile, ReputationRegistry

public entry fun slash_agent(
    oracle: &signer,
    agent_addr: address,
    slash_amount: u64,
    penalty_score: u64,
) acquires AgentProfile, ReputationRegistry
```

#### Composable View Functions for Protocols
```move
#[view]
public fun get_agent_tier(agent_addr: address): u8 acquires AgentProfile

#[view]
public fun is_agent_active(agent_addr: address): bool acquires AgentProfile

#[view]
public fun get_agent_score(agent_addr: address): u64 acquires AgentProfile
```

---

## Formal Verification (Move Prover)

The reference implementation is mathematically verified using the **Aptos Move Prover**, guaranteeing zero runtime arithmetic overflows and strict invariant preservation:

```move
spec update_reputation {
    ensures is_positive ==> (
        old(profile.score) + delta > MAX_SCORE ==> profile.score == MAX_SCORE
    );
    ensures !is_positive ==> (
        delta >= old(profile.score) ==> profile.score == 0
    );
}

spec slash_agent {
    ensures profile.score <= old(profile.score);
    ensures profile.slashed_stake == old(profile.slashed_stake) + slash_amount;
    ensures profile.is_active == (profile.score > 0);
}
```

---

## Reference Implementation

An open-source reference implementation is available in this repository (`contracts/aptos/`). The Move modules are compiled and formally specified, but **testnet deployment is planned / in progress — no verified on-chain transactions exist at this time**.

* **Repository:** [`https://github.com/ibonon/Sigui/tree/master/contracts/aptos`](https://github.com/ibonon/Sigui/tree/master/contracts/aptos)
* **Modules (source only, not yet deployed):**
  * `sigui::agent_reputation`
  * `sigui::threat_registry`
* **On-chain status:** none. When a testnet deployment occurs, this section will record the full 64-character transaction hash(es) for independent verification on the Aptos Explorer. Until then, no on-chain claims are made in this proposal.

---

## Testing Plan

* **Unit & Invariant Tests**: 100% test coverage using `aptos move test`.
* **Prover Verification**: Verified via `aptos move prove` with zero violations.
* **Integration Tests**: Tested against automated agent loops in TypeScript (ElizaOS plugin) and Python (Sigui Guard RPC proxy).

---

## Risks and Drawbacks

* **Oracle Centralization**: Mitigated by requiring multi-signature threshold consensus for registering high-severity threats in `threat_registry.move`.
* **Griefing Slashing**: Slashing requires cryptographic proof or verified oracle consensus; malicious reports result in oracle bond forfeiture.

---

## Future Potential

1. **Native Aptos AI Agent Registry Indexer**: An automated dashboard indexing all autonomous agents operating on Aptos.
2. **DeFi Protocol Composability**: Integration with Aptos lending protocols to enable under-collateralized loans for Platinum-tier AI agents.
3. **Cross-Agent Swarm Intelligence**: Collaborative reputation sharing between agent collectives on Aptos.

---

## Suggested Timeline

* **Milestone 1 (In progress)**: Reference Move modules compiled and formally specified (`contracts/aptos/`). Testnet deployment planned — full 64-character transaction hashes will be published here for verification once deployed.
* **Milestone 2 (Q4 2026)**: Formal AIP submission to `aptos-foundation/AIPs`, community review, and SDK TypeScript/Python bindings.
* **Milestone 3 (Q1 2027)**: Mainnet audit and deployment alongside leading Aptos DeFi protocols.
