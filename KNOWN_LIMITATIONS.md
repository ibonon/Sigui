# KNOWN LIMITATIONS & PENDING TASKS

## ✅ Z3 — Real snarkjs Groth16 circuit integration into gateway (COMPLETED & VERIFIED)

**Status:** Completed and verified via end-to-end integration tests.

**Implementation details:**
- [`circuits/TrustScoreProof.circom`](circuits/TrustScoreProof.circom) — Circom 2.2.3 Groth16 circuit implementing ERC-8259 trust score verification (88 non-linear constraints).
- [`circuits/prover.js`](circuits/prover.js) — Node.js subprocess prover using `snarkjs.groth16.fullProve` and `snarkjs.groth16.verify`.
- [`modules/zk_sigui.py`](modules/zk_sigui.py) — Async prover interface with zero silent fallback to simulated proofs. Returns typed `zk_error` on failure.
- [`modules/gateway.py`](modules/gateway.py) — 4 active endpoints updated to use real Groth16 circuit:
  - `GET /api/zk-sigui/status`
  - `POST /api/zk-sigui/prove`
  - `POST /api/simulate-attack`
  - `POST /v2/evaluate?zk=true`

All 4 nominal cases and 3 controlled failure modes (missing zkey, missing wasm, constraint violation) pass with verified proof of execution.

---

## ⚠️ Sepolia Redeployment (tracked separately)

The ERC-8259 contract at `0x3806aeb76eDD2E22D3cF66A163113c4b24243b29` is deprecated
(pre-PR #2137, privilege escalation risk). A corrected deployment is tracked at
[Issue #2](https://github.com/ibonon/Sigui/issues/2). Until redeployed, all
documentation correctly marks this address as DEPRECATED.

---

## ℹ️ Starknet Grant (no action needed)

Starknet Foundation Seed Grant: **rejected** (generic rejection, no actionable
feedback). No next steps identified.

## ℹ️ Aptos Grant (action required, separate track)

Aptos Foundation: constructive feedback from Corey (July 3). Re-candidature
actionable in 3–4 weeks after:
1. Real testnet deployment with full 64-char tx hash archived
2. Public benchmark report (accuracy / FP / FN on sigui-depin-1m)
3. SDK Aptos TypeScript client (minimal — 50 lines)
4. At least 1 confirmed Aptos ecosystem partner (email evidence)

See full assessment: `.gemini/antigravity/brain/14f02cd7-0b64-4563-99b1-f608fb5edc5d/aptos_grant_assessment.md`
