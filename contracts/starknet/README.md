# Sigui Protocol — Starknet Smart Contracts

This directory contains the Cairo 2.x smart contracts for the Sigui Protocol, targeting the Starknet Foundation grant.

## Architecture

Sigui Protocol on Starknet utilizes two core contracts:
1. **AgentReputation (`agent_reputation.cairo`)**: Implements Sigui's native Starknet agent identity and reputation scoring.
2. **ThreatRegistry (`threat_registry.cairo`)**: A decentralized ledger of visual/semantic AI threat patterns, validated by multi-oracles.

## Prerequisites

- [Scarb](https://docs.swmansion.com/scarb/) >= 2.8.0
- [Starkli](https://github.com/xJonathanLEI/starkli)

## Building the Contracts

```bash
cd contracts/starknet
scarb build
```

## Deployment on Sepolia Testnet

1. Ensure your Braavos or Argent X testnet wallet is configured in starkli.
2. Export your keystore and account JSONs to `~/.starkli-wallets/deployer/`.
3. Run the deployment script:

```bash
chmod +x deploy_sepolia.sh
./deploy_sepolia.sh
```

## Wallet Integrations

### Argent X
Argent X accounts natively support the multi-call functionality. The Sigui Python SDK generates multi-call calldata to register an agent and immediately report threats in a single transaction.

### Braavos
Braavos wallets can interact with the reputation contracts using the hardware signer (Signer inside Secure Enclave) for maximum security when updating the `AgentProfile` or reporting critical threats.

## ERC-8259 Relationship & Non-Normative Status

> [!NOTE]
> **Proprietary Cairo Architecture**: These Cairo contracts implement Sigui's native multi-oracle reputation and threat pattern architecture on Starknet. They do **not** implement the normative EVM ERC-8259 standard interfaces (they use an unbounded `u64` reputation score, score-derived tiers, multi-oracle threshold validation, and omit `verificationExpiry` / incident lifecycle).
>
> The canonical, normative reference implementation for ERC-8259 is in Solidity:
> - `assets/erc-8259/` (ethereum/ERCs upstream repository)
> - `packages/erc8259/contracts/` (NPM package `erc-8259 >= 1.2.0`)
