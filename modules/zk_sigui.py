"""
modules/zk_sigui.py — ZK-Sigui: Groth16 Trust Score Prover (Z3 — Real Circuit)

Integrates the ERC-8259 TrustScoreProof Circom circuit via an async Node.js
subprocess (circuits/prover.js). The old BN128 field-arithmetic simulation
(val * 1337 % BN128_FIELD_PRIME) has been entirely removed.

Error contract (non-negotiable):
  - Any failure returns zk_proof=None and a typed zk_error string.
  - There is NO silent fallback to simulated proofs.
  - Failure modes: artifact_missing | prover_timeout | constraint_violation
                   | prover_error | invalid_input | internal_error

Usage:
    from modules.zk_sigui import zk_sigui
    result = await zk_sigui.prove_trust_score(agent_data)
    # agent_data keys: isActive, storedTier, verificationExpiry,
    #                  reputationScore, agentAddress, currentTimestamp, trustScore
"""

import asyncio
import json
import os
import time
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_REPO_ROOT   = Path(__file__).resolve().parent.parent
_PROVER_JS   = _REPO_ROOT / "circuits" / "prover.js"
_WASM_PATH   = _REPO_ROOT / "circuits" / "TrustScoreProof_js" / "TrustScoreProof.wasm"
_ZKEY_PATH   = _REPO_ROOT / "circuits" / "TrustScoreProof_final.zkey"
_VKEY_PATH   = _REPO_ROOT / "circuits" / "verification_key.json"

_PROVER_TIMEOUT_S: float = 5.0


def _artifact_check() -> str | None:
    """Return a typed error string if any required artifact is missing, else None."""
    for label, path in [
        ("prover.js", _PROVER_JS),
        ("wasm",      _WASM_PATH),
        ("zkey",      _ZKEY_PATH),
        ("vkey",      _VKEY_PATH),
    ]:
        if not path.exists():
            return f"artifact_missing: {label} not found ({path.name})"
    return None


class ZKSigui:
    """Real Groth16 prover for the ERC-8259 TrustScoreProof circuit."""

    async def prove_trust_score(self, agent_data: dict) -> dict:
        """
        Prove that trustScore was computed correctly from the given agent state.

        Parameters (all required for a real proof):
            isActive          (int) : 1 if agent is active, 0 otherwise
            storedTier        (int) : 0–3 — tier stored on-chain
            verificationExpiry(int) : Unix timestamp of tier expiry
            reputationScore   (int) : 0–1000 raw reputation
            agentAddress      (int) : agent address as integer
            currentTimestamp  (int) : Unix timestamp of evaluation
            trustScore        (int) : claimed trust score to prove

        Returns:
            {
              "zk_proof": {
                "proof":          {...},   # Groth16 pi_a / pi_b / pi_c
                "public_signals": [...],   # [trustScore, timestamp, agentAddress]
                "proof_type":     "groth16_circom_v1",
                "real_circuit":   True,
                "verified":       True | False,
                "proof_size_bytes": int,
                "prove_time_ms":    float,
              },
              "zk_error": None
            }
        or on any failure:
            {
              "zk_proof": None,
              "zk_error": "<typed_error_string>"
            }
        """
        t0 = time.perf_counter()

        # Fast artifact check before spawning a subprocess
        artifact_err = _artifact_check()
        if artifact_err:
            return {"zk_proof": None, "zk_error": artifact_err}

        # Build witness JSON
        witness = {
            "isActive":           int(agent_data.get("isActive", 0)),
            "storedTier":         int(agent_data.get("storedTier", 0)),
            "verificationExpiry": int(agent_data.get("verificationExpiry", 0)),
            "reputationScore":    int(agent_data.get("reputationScore", 0)),
            "agentAddress":       int(agent_data.get("agentAddress", 0)),
            "currentTimestamp":   int(agent_data.get("currentTimestamp", int(time.time()))),
            "trustScore":         int(agent_data.get("trustScore", 0)),
        }
        stdin_bytes = json.dumps(witness).encode()

        # Spawn prover subprocess
        try:
            proc = await asyncio.create_subprocess_exec(
                "node", str(_PROVER_JS),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(_PROVER_JS.parent),
            )
        except FileNotFoundError:
            return {"zk_proof": None, "zk_error": "internal_error: node binary not found in PATH"}
        except Exception as e:
            return {"zk_proof": None, "zk_error": f"internal_error: subprocess spawn failed — {e}"}

        # Communicate with timeout
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(input=stdin_bytes),
                timeout=_PROVER_TIMEOUT_S,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return {
                "zk_proof": None,
                "zk_error": f"prover_timeout (exceeded {_PROVER_TIMEOUT_S}s)",
            }
        except Exception as e:
            return {"zk_proof": None, "zk_error": f"internal_error: communicate failed — {e}"}

        # Parse prover output
        stdout_text = stdout_bytes.decode("utf-8", errors="replace").strip()
        if not stdout_text:
            stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
            return {
                "zk_proof": None,
                "zk_error": f"internal_error: empty prover stdout — stderr: {stderr_text[:300]}",
            }

        try:
            prover_result = json.loads(stdout_text)
        except json.JSONDecodeError:
            return {
                "zk_proof": None,
                "zk_error": f"internal_error: prover returned non-JSON — {stdout_text[:200]}",
            }

        prove_time_ms = round((time.perf_counter() - t0) * 1000, 1)

        # Prover reported a typed failure
        if not prover_result.get("ok"):
            error_type = prover_result.get("error_type", "unknown")
            error_msg  = prover_result.get("error_message", "")
            return {
                "zk_proof": None,
                "zk_error": f"{error_type}: {error_msg}",
            }

        # Success
        proof         = prover_result["proof"]
        public_signals = prover_result["publicSignals"]
        verified      = prover_result["verified"]

        proof_json_str = json.dumps({"proof": proof, "publicSignals": public_signals})

        return {
            "zk_proof": {
                "proof":           proof,
                "public_signals":  public_signals,
                "proof_type":      "groth16_circom_v1",
                "real_circuit":    True,
                "verified":        verified,
                "proof_size_bytes": len(proof_json_str.encode()),
                "prove_time_ms":    prove_time_ms,
            },
            "zk_error": None,
        }

    def get_status(self) -> dict:
        """Return circuit status and artifact availability for /api/zk-sigui/status."""
        artifact_err = _artifact_check()
        artifacts_ok = artifact_err is None

        return {
            "version":       "groth16_circom_v1",
            "proof_type":    "groth16_circom_v1",
            "real_circuit":  True,
            "circuit":       "TrustScoreProof.circom (ERC-8259 §6 — 88 non-linear constraints)",
            "curve":         "BN128",
            "protocol":      "Groth16",
            "artifacts_ok":  artifacts_ok,
            "artifact_error": artifact_err,
            "prover_timeout_s": _PROVER_TIMEOUT_S,
            "public_inputs": ["trustScore", "currentTimestamp", "agentAddress"],
            "private_inputs": ["isActive", "storedTier", "verificationExpiry", "reputationScore"],
            "note": (
                "Real Circom Groth16 circuit. Proof generated via circuits/prover.js subprocess. "
                "On any failure: zk_proof=null, zk_error=<typed>. No simulation fallback."
            ),
        }

    # ── Deprecated shim (kept for import compatibility only) ──────────────────
    def prove_and_verify(self, witness: dict) -> dict:  # noqa: D102
        """
        DEPRECATED — Synchronous shim retained to avoid ImportError during the
        transition period where old call sites in gateway.py are being replaced.
        Returns an explicit deprecation notice; never returns a simulated proof.
        Callers must be migrated to prove_trust_score() (async).
        """
        return {
            "zk_proof":   None,
            "zk_error":   "deprecated: prove_and_verify() is a sync stub; use await prove_trust_score()",
            "real_circuit": True,
            "proof_type": "groth16_circom_v1",
        }


zk_sigui = ZKSigui()
