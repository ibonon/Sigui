# Sigui Protocol — Aptos Move Contracts

This directory contains the Aptos Move smart contracts for the Sigui Protocol, targeting the Aptos Foundation grant.

## Architecture

Sigui Protocol on Aptos utilizes two core modules:
1. **`agent_reputation`**: Implements the ERC-8259 identity and reputation standard for AI agents on-chain.
2. **`threat_registry`**: A decentralized ledger of visual/semantic AI threat patterns, validated by multi-oracles.

## Formal Verification (Move Prover)

The contracts are equipped with `spec` blocks designed for the Move Prover. This provides mathematical guarantees about the contract behavior, eliminating classes of runtime errors.

- Safety properties are defined for reputation score bounds.
- Access control validation is formally verified.

## Prerequisites

- [Aptos CLI](https://aptos.dev/cli-tools/aptos-cli-tool/install-aptos-cli)

## Testing

Aptos Foundation requires robust test coverage.

```bash
cd contracts/aptos
aptos move test
```

## Proving

To run the Move Prover for formal verification:

```bash
aptos move prove
```

## Deployment on Aptos Testnet

1. Initialize your Aptos account (this creates `.aptos/config.yaml`):
```bash
aptos init --network testnet
```

2. Run the deployment script:
```bash
chmod +x deploy_testnet.sh
./deploy_testnet.sh
```

## High-Performance DePIN

By deploying on Aptos, Sigui leverages **Block-STM** (Software Transactional Memory) parallel execution. This allows the network of Oracles to process thousands of simultaneous visual inspection verdicts per second with sub-second finality.
