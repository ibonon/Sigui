// ============================================================
//  Sigui Protocol — Starknet Smart Contracts
//  Module Declarations
//
//  Architecture:
//    ┌─────────────────────────────────┐
//    │         Sigui Protocol          │
//    ├─────────────┬───────────────────┤
//    │ agent_rep.. │  threat_registry  │
//    └─────────────┴───────────────────┘
//
//  SPDX-License-Identifier: MIT
// ============================================================

/// Agent reputation tracking module.
/// Implements ERC-8259 compatible agent identity and scoring.
pub mod agent_reputation;

/// Threat pattern registry module.
/// Multi-oracle validated threat intelligence ledger.
pub mod threat_registry;
