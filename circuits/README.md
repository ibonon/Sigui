# ERC-8259 Trust Score Groth16 Zero-Knowledge Circuit

This directory implements the first honest Zero-Knowledge proof circuit for the normative ERC-8259 `calculateTrustScore()` function.

## 1. Specification & Normative Formula

The circuit models the exact formula merged in `ethereum/ERCs:master` (PR #2142 & PR #2143):

```solidity
function calculateTrustScore(address agent) external view returns (uint256) {
    if (!registry.isActive(agent)) {
        return 0;
    }
    uint8 tier = this.getEffectiveTier(agent);
    uint256 base = registry.getReputationScore(agent);
    uint256 score = base + (uint256(tier) * 100);
    return score > 1000 ? 1000 : score;
}
```

```solidity
function getEffectiveTier(address agent) external view returns (uint8) {
    if (!registry.isActive(agent)) {
        return 0;
    }
    if (block.timestamp > registry.getVerificationExpiry(agent)) {
        return 0;
    }
    return registry.getTier(agent);
}
```

## 2. Public vs. Private Signals (Product Trade-Off)

- **Public Signals** (Known to verifier / on-chain caller):
  - `trustScore`: The calculated trust score (0..1000).
  - `currentTimestamp`: Timestamp at evaluation time (UNIX seconds).
  - `agentAddress`: Agent identifier (field element representation).

- **Private Signals** (Witness kept confidential):
  - `isActive`: Boolean flag (0 = inactive, 1 = active).
  - `storedTier`: Base tier from registry (uint8).
  - `verificationExpiry`: Verification expiration timestamp.
  - `reputationScore`: Base reputation score (0..1000).

**Justification**: Preserves agent privacy. An agent can cryptographically prove to counter-parties or verifiers that its published `trustScore` was correctly computed from valid registry state without exposing its raw internal reputation metrics, tier, or expiration boundaries.

## 3. Circuit Metrics & Constraints

Compiled with `circom 2.2.3`:
- Non-linear constraints: **88**
- Linear constraints: **7**
- Total wires: **99**
- Public inputs: **3**
- Private inputs: **4**

## 4. Benchmark Measurements (Local Hardware)

- **Proof Size**:
  - JSON format: **725 bytes**
  - EVM calldata / raw curve coordinates: **3 group elements** (2 in $G_1$, 1 in $G_2$) = **128 bytes** (compressed) / **256 bytes** (uncompressed)
- **Proof Generation Time**: **~850 ms**
- **Verification Time**: **~43 ms** (Node.js snarkjs) / **sub-millisecond** (Solidity pairing check)

## 5. Reproduction & Testing

```bash
# 1. Compile circuit
npm run compile

# 2. Run automated test suite (6 cases: positive, expired, inactive, fraud attempt, score tampering, corrupted proof)
npm test

# 3. Direct CLI verification
npx snarkjs groth16 verify verification_key.json public.json proof.json
```
