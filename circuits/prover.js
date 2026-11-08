#!/usr/bin/env node
/**
 * circuits/prover.js — Sigui ZK Groth16 Prover Subprocess
 *
 * Protocol (stdin/stdout JSON):
 *   stdin:  { isActive, storedTier, verificationExpiry, reputationScore,
 *             agentAddress, currentTimestamp, trustScore }
 *   stdout: { ok: true,  proof, publicSignals, verified } on success
 *           { ok: false, error_type, error_message }       on any failure
 *
 * Exit codes: 0 = success or expected constraint violation
 *             1 = artifact missing or internal error
 *
 * Never exits silently. Every failure path produces a JSON error on stdout
 * before exiting — the Python caller reads stdout, never swallows stderr only.
 */

"use strict";

const fs   = require("fs");
const path = require("path");

const CIRCUITS_DIR  = __dirname;
const WASM_PATH     = path.join(CIRCUITS_DIR, "TrustScoreProof_js", "TrustScoreProof.wasm");
const ZKEY_PATH     = path.join(CIRCUITS_DIR, "TrustScoreProof_final.zkey");
const VKEY_PATH     = path.join(CIRCUITS_DIR, "verification_key.json");

// ── Startup artifact check ────────────────────────────────────────────────────
function checkArtifacts() {
  for (const [label, p] of [["wasm", WASM_PATH], ["zkey", ZKEY_PATH], ["vkey", VKEY_PATH]]) {
    if (!fs.existsSync(p)) {
      writeError("artifact_missing", `${label} not found: ${path.basename(p)}`);
      process.exit(1);
    }
  }
}

function writeError(error_type, error_message) {
  process.stdout.write(JSON.stringify({ ok: false, error_type, error_message }) + "\n");
}

function writeSuccess(proof, publicSignals, verified) {
  process.stdout.write(JSON.stringify({ ok: true, proof, publicSignals, verified }) + "\n");
}

async function main() {
  // Artifact check before reading stdin — fast fail on missing files
  checkArtifacts();

  // Load snarkjs from local node_modules
  let snarkjs;
  try {
    snarkjs = require(path.join(CIRCUITS_DIR, "node_modules", "snarkjs"));
  } catch (e) {
    writeError("internal_error", `snarkjs load failed: ${e.message}`);
    process.exit(1);
  }

  // Read stdin (timeout handled by Python caller via asyncio.wait_for)
  let raw = "";
  process.stdin.setEncoding("utf8");
  for await (const chunk of process.stdin) {
    raw += chunk;
  }

  // Parse input
  let input;
  try {
    input = JSON.parse(raw);
  } catch (e) {
    writeError("invalid_input", `JSON parse failed: ${e.message}`);
    process.exit(1);
  }

  // Build witness input — all values must be BigInt-compatible integers
  const witness = {
    isActive:           String(input.isActive           ?? 0),
    storedTier:         String(input.storedTier         ?? 0),
    verificationExpiry: String(input.verificationExpiry ?? 0),
    reputationScore:    String(input.reputationScore    ?? 0),
    agentAddress:       String(input.agentAddress       ?? 0),
    currentTimestamp:   String(input.currentTimestamp   ?? 0),
    trustScore:         String(input.trustScore         ?? 0),
  };

  // Generate proof
  let proof, publicSignals;
  try {
    ({ proof, publicSignals } = await snarkjs.groth16.fullProve(witness, WASM_PATH, ZKEY_PATH));
  } catch (e) {
    // Distinguish constraint violation (Assert Failed) from internal errors
    const msg = e.message || String(e);
    if (msg.includes("Assert Failed") || msg.includes("assert") || msg.includes("Error in template")) {
      writeError("constraint_violation", msg);
    } else {
      writeError("prover_error", msg);
    }
    process.exit(0); // exit 0: expected domain error, not a crash
  }

  // Verify the proof
  let vKey;
  try {
    vKey = JSON.parse(fs.readFileSync(VKEY_PATH, "utf8"));
  } catch (e) {
    writeError("artifact_missing", `vkey read failed: ${e.message}`);
    process.exit(1);
  }

  let verified;
  try {
    verified = await snarkjs.groth16.verify(vKey, publicSignals, proof);
  } catch (e) {
    writeError("verifier_error", e.message || String(e));
    process.exit(1);
  }

  writeSuccess(proof, publicSignals, verified);
  process.exit(0);
}

main().catch((e) => {
  writeError("unhandled_exception", e.message || String(e));
  process.exit(1);
});
