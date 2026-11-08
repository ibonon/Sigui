# KNOWN LIMITATIONS & PENDING TASKS

## ⏳ Z3 — Real snarkjs integration into gateway (PENDING EXECUTION)

**Status:** Architecture confirmed, code written, **not yet executed**.

**What exists:**
- [`circuits/prover.js`](circuits/prover.js) — Node.js subprocess prover,
  tested in isolation (artifact_missing, constraint_violation, success cases all verified)
- [`modules/zk_sigui.py`](modules/zk_sigui.py) — Rewritten with real
  `prove_trust_score()` async method (old `val * 1337 % BN128_FIELD_PRIME`
  simulation removed)
- [`brain/.../scratch/z3_patch_gateway.py`](../../../.gemini/antigravity/brain/14f02cd7-0b64-4563-99b1-f608fb5edc5d/scratch/z3_patch_gateway.py)
  — Patch script for `modules/gateway.py` (all 4 call sites), **written but
  not yet applied**

**What remains:**
1. Run `python brain/.../scratch/z3_patch_gateway.py` to patch gateway.py
2. Start the FastAPI server and hit all 4 endpoints with proof of execution:
   - `GET /api/zk-sigui/status` → `real_circuit: true`, `artifacts_ok: true`
   - `POST /api/zk-sigui/prove` → real Groth16 proof + `verified: true`
   - `POST /api/simulate-attack` → `zk_proof: {..., real_circuit: true}`
   - `POST /v2/evaluate?zk=true` → real proof or `zk_error` (never simulated)
3. Run the 3 required failure tests (artifact_missing, prover_timeout, constraint_violation)
4. Update `sentinel.html`, `ZKVerifierPanel.tsx`, `architecture.html`
   to remove "Simulated PoC" banners (replaced by real circuit status)
5. Commit as `feat(zk): integrate real Circom Groth16 prover into gateway (Z3)`

**Error contract (confirmed, non-negotiable):**
- Any failure → `zk_proof: null` + `zk_error: "<typed>"`. Never silent fallback to simulation.
- Replacement is **atomic**: old simulate logic is already deleted in `zk_sigui.py`.
- Timeout: 5.0 seconds via `asyncio.wait_for`.

**Do NOT mark Z3 as done until all 4 endpoints return real proofs and all 3 failure
tests pass with proof of execution (literal command + raw terminal output).**

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
