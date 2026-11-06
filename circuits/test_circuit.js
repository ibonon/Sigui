const fs = require("fs");
const path = require("path");
const snarkjs = require("snarkjs");

async function main() {
    console.log("================================================================");
    console.log("   ERC-8259 TrustScoreProof — Circom / Groth16 Test Suite");
    console.log("================================================================\n");

    const wasmPath = path.join(__dirname, "TrustScoreProof_js", "TrustScoreProof.wasm");
    const zkeyPath = path.join(__dirname, "TrustScoreProof_final.zkey");
    const vKeyPath = path.join(__dirname, "verification_key.json");
    const vKey = JSON.parse(fs.readFileSync(vKeyPath, "utf8"));

    const AGENT_ADDR = "1351174987293847291847192847192847192847"; // uint160 field representation

    // ─────────────────────────────────────────────────────────────
    // TEST 1: Positive Case — Active Agent, Unexpired Tier
    // rep = 450, tier = 2, unexpired => raw = 450 + 200 = 650 => score = 650
    // ─────────────────────────────────────────────────────────────
    console.log("─── TEST 1: Active Agent, Unexpired Tier (Valid Calculation) ───");
    const input1 = {
        trustScore: "650",
        currentTimestamp: "1750000000",
        agentAddress: AGENT_ADDR,
        isActive: "1",
        storedTier: "2",
        verificationExpiry: "1800000000",
        reputationScore: "450"
    };

    const t0_prove = performance.now();
    const { proof: proof1, publicSignals: publicSignals1 } = await snarkjs.groth16.fullProve(
        input1,
        wasmPath,
        zkeyPath
    );
    const proveTimeMs = (performance.now() - t0_prove).toFixed(2);

    fs.writeFileSync(path.join(__dirname, "proof.json"), JSON.stringify(proof1, null, 2));
    fs.writeFileSync(path.join(__dirname, "public.json"), JSON.stringify(publicSignals1, null, 2));

    const proofSizeBytes = Buffer.byteLength(JSON.stringify(proof1));

    const t0_verify = performance.now();
    const verifyResult1 = await snarkjs.groth16.verify(vKey, publicSignals1, proof1);
    const verifyTimeMs = (performance.now() - t0_verify).toFixed(2);

    console.log(`Input: isActive=1, tier=2, exp=1800000000, now=1750000000, rep=450 => claimed=650`);
    console.log(`Public signals: [trustScore=${publicSignals1[0]}, now=${publicSignals1[1]}, agent=${publicSignals1[2]}]`);
    console.log(`Proof generated in: ${proveTimeMs} ms`);
    console.log(`Proof verified in:  ${verifyTimeMs} ms`);
    console.log(`Proof size (JSON):  ${proofSizeBytes} bytes`);
    console.log(`Verification result: ${verifyResult1 ? "CONFIRMED VALID (OK)" : "FAILED (INVALID)"}`);
    if (!verifyResult1) throw new Error("Test 1 failed verification");

    // ─────────────────────────────────────────────────────────────
    // TEST 2: Positive Case — Active Agent, Expired Tier
    // rep = 450, tier = 2, expired (now > exp) => effectiveTier = 0 => score = 450
    // ─────────────────────────────────────────────────────────────
    console.log("\n─── TEST 2: Active Agent, Expired Tier (Effective Tier = 0) ───");
    const input2 = {
        trustScore: "450",
        currentTimestamp: "1850000000",
        agentAddress: AGENT_ADDR,
        isActive: "1",
        storedTier: "2",
        verificationExpiry: "1800000000",
        reputationScore: "450"
    };

    const { proof: proof2, publicSignals: publicSignals2 } = await snarkjs.groth16.fullProve(
        input2,
        wasmPath,
        zkeyPath
    );
    const verifyResult2 = await snarkjs.groth16.verify(vKey, publicSignals2, proof2);
    console.log(`Input: isActive=1, tier=2, exp=1800000000, now=1850000000 (EXPIRED), rep=450 => claimed=450`);
    console.log(`Verification result: ${verifyResult2 ? "CONFIRMED VALID (OK)" : "FAILED (INVALID)"}`);
    if (!verifyResult2) throw new Error("Test 2 failed verification");

    // ─────────────────────────────────────────────────────────────
    // TEST 3: Positive Case — Inactive Agent with Honest Score 0
    // isActive = 0 => score MUST be 0 regardless of reputation or tier
    // ─────────────────────────────────────────────────────────────
    console.log("\n─── TEST 3: Inactive Agent, Honest Score = 0 ───");
    const input3 = {
        trustScore: "0",
        currentTimestamp: "1750000000",
        agentAddress: AGENT_ADDR,
        isActive: "0",
        storedTier: "3",
        verificationExpiry: "1800000000",
        reputationScore: "850"
    };

    const { proof: proof3, publicSignals: publicSignals3 } = await snarkjs.groth16.fullProve(
        input3,
        wasmPath,
        zkeyPath
    );
    const verifyResult3 = await snarkjs.groth16.verify(vKey, publicSignals3, proof3);
    console.log(`Input: isActive=0 (INACTIVE), tier=3, rep=850 => claimed=0`);
    console.log(`Verification result: ${verifyResult3 ? "CONFIRMED VALID (OK)" : "FAILED (INVALID)"}`);
    if (!verifyResult3) throw new Error("Test 3 failed verification");

    // ─────────────────────────────────────────────────────────────
    // TEST 4: Negative Case — Inactive Agent Attempting Non-Zero Score
    // isActive = 0, claimed trustScore = 850 (Fraud attempt)
    // ─────────────────────────────────────────────────────────────
    console.log("\n─── TEST 4: Negative — Inactive Agent Claiming Non-Zero Score ───");
    const input4 = {
        trustScore: "850",
        currentTimestamp: "1750000000",
        agentAddress: AGENT_ADDR,
        isActive: "0",
        storedTier: "3",
        verificationExpiry: "1800000000",
        reputationScore: "850"
    };

    let witnessFailed4 = false;
    try {
        await snarkjs.groth16.fullProve(input4, wasmPath, zkeyPath);
    } catch (err) {
        witnessFailed4 = true;
        console.log(`Witness/Constraint Check: REJECTED AS EXPECTED (${err.message.split("\n")[0]})`);
    }
    if (!witnessFailed4) throw new Error("Test 4 should have failed constraint check!");

    // ─────────────────────────────────────────────────────────────
    // TEST 5: Negative Case — Active Agent, Forged Public TrustScore
    // Valid proof for 650, but verifier is presented with claimed score 999
    // ─────────────────────────────────────────────────────────────
    console.log("\n─── TEST 5: Negative — Forged Public Output (Score Tampering) ───");
    const forgedPublicSignals = ["999", publicSignals1[1], publicSignals1[2]];
    const verifyResult5 = await snarkjs.groth16.verify(vKey, forgedPublicSignals, proof1);
    console.log(`Verifier presented with authentic proof but forged trustScore=999`);
    console.log(`Verification result: ${verifyResult5 ? "FAILED (ACCEPTED FORGERY)" : "CONFIRMED REJECTED (INVALID)"}`);
    if (verifyResult5) throw new Error("Test 5 accepted a forged public score!");

    // ─────────────────────────────────────────────────────────────
    // TEST 6: Negative Case — Tampered Proof Coordinates
    // ─────────────────────────────────────────────────────────────
    console.log("\n─── TEST 6: Negative — Tampered Proof Coordinates ───");
    const tamperedProof = JSON.parse(JSON.stringify(proof1));
    // Tamper with pi_a[0]
    tamperedProof.pi_a[0] = "12345678901234567890";
    const verifyResult6 = await snarkjs.groth16.verify(vKey, publicSignals1, tamperedProof);
    console.log(`Verifier presented with corrupted pi_a coordinate`);
    console.log(`Verification result: ${verifyResult6 ? "FAILED (ACCEPTED CORRUPTED PROOF)" : "CONFIRMED REJECTED (INVALID)"}`);
    if (verifyResult6) throw new Error("Test 6 accepted corrupted proof!");

    console.log("\n================================================================");
    console.log("   ALL 6 CIRCUIT TEST CASES CONFIRMED: INTEGRITY GUARANTEED");
    console.log("================================================================");
    process.exit(0);
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
