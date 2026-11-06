pragma circom 2.1.6;

include "node_modules/circomlib/circuits/comparators.circom";

/**
 * @title TrustScoreProof
 * @notice Zero-Knowledge Proof for ERC-8259 Agent Trust Score calculation.
 * 
 * Normative formula from ERC-8259:
 * 1. if (!registry.isActive(agent)) return 0;
 * 2. tier = (block.timestamp > verificationExpiry) ? 0 : storedTier;
 * 3. rawScore = reputationScore + (tier * 100);
 * 4. trustScore = (rawScore > 1000) ? 1000 : rawScore;
 * 
 * Public signals:
 * - trustScore: The resulting trust score (0..1000)
 * - currentTimestamp: Timestamp at evaluation time
 * - agentAddress: Agent Ethereum address (field element)
 * 
 * Private signals (witness):
 * - isActive: Boolean flag (1 if active, 0 if inactive)
 * - storedTier: Stored registry tier (uint8)
 * - verificationExpiry: Verification expiry timestamp
 * - reputationScore: Base reputation score (0..1000)
 */
template TrustScoreProof() {
    // ── Public Inputs ──────────────────────────────────────────────
    signal input trustScore;
    signal input currentTimestamp;
    signal input agentAddress;

    // ── Private Inputs (Witness) ──────────────────────────────────
    signal input isActive;
    signal input storedTier;
    signal input verificationExpiry;
    signal input reputationScore;

    // ── Constraints ───────────────────────────────────────────────

    // 1. Constrain isActive to boolean (0 or 1)
    isActive * (1 - isActive) === 0;

    // 2. Check if currentTimestamp > verificationExpiry (64-bit comparison)
    component isExpiredComp = GreaterThan(64);
    isExpiredComp.in[0] <== currentTimestamp;
    isExpiredComp.in[1] <== verificationExpiry;
    signal isExpired;
    isExpired <== isExpiredComp.out; // 1 if expired, 0 otherwise

    // 3. Effective tier:
    // If not expired, validTier = storedTier, else 0
    signal validTier;
    validTier <== (1 - isExpired) * storedTier;

    // effectiveTier = isActive * validTier (0 if agent is inactive)
    signal effectiveTier;
    effectiveTier <== isActive * validTier;

    // 4. Compute raw score:
    // rawScore = reputationScore + (effectiveTier * 100)
    signal rawScore;
    rawScore <== reputationScore + (effectiveTier * 100);

    // 5. Clamp score to 1000 (16-bit comparison for values up to 65535)
    component isAbove1000 = GreaterThan(16);
    isAbove1000.in[0] <== rawScore;
    isAbove1000.in[1] <== 1000;
    signal exceedsCap;
    exceedsCap <== isAbove1000.out; // 1 if rawScore > 1000, 0 otherwise

    // clampedScore = exceedsCap * 1000 + (1 - exceedsCap) * rawScore
    signal clampedScore;
    clampedScore <== exceedsCap * 1000 + (1 - exceedsCap) * rawScore;

    // 6. If isActive == 0, expectedTrustScore MUST be 0
    signal expectedTrustScore;
    expectedTrustScore <== isActive * clampedScore;

    // 7. Dummy check for agentAddress to bind proof to this specific agent
    // (ensures agentAddress cannot be freely tampered with in public inputs)
    signal agentSquare;
    agentSquare <== agentAddress * agentAddress;

    // 8. Final constraint: claimed trustScore must equal expectedTrustScore
    trustScore === expectedTrustScore;
}

component main {public [trustScore, currentTimestamp, agentAddress]} = TrustScoreProof();
