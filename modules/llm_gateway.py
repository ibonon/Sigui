"""
Sigui v2.0 — Dual LLM Gateway
Lebe (Qwen2.5-3B on AMD MI300X via vLLM) → primary escalation engine.
OpenShell (Claude via Anthropic SDK) → fallback / self-critique.

Architecture:
  call_json_model (lebe)   →  Qwen2.5 vLLM ROCm (local, ~15ms)
                           ↘  on failure → Claude (Anthropic API)
                                         ↘  on failure → rule-based in ai_engines.py

Shared guardrails (pre-flight sanitization + post-flight JSON validation)
are implemented once in _GatewayBase and reused by both gateways.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Optional

import httpx
from loguru import logger

from config import settings

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Shared Guardrail Base
# ─────────────────────────────────────────────────────────────────────────────

class _GatewayBase:
    """Shared pre-flight / post-flight guardrail logic reused by all gateways."""

    def _sanitize_input(self, payload: dict | str) -> str:
        """
        Pre-flight Guardrail: Prevent common injection patterns.
        - Strip known LLM control tokens like <|system|>.
        - Enforce max context length to avoid DoS/Context-flood.
        """
        raw_text = json.dumps(payload) if isinstance(payload, dict) else str(payload)

        # Guardrail 1: Block control token injections
        sanitized = re.sub(
            r"<(?:/?|\|)(?:system|assistant|user|role).*?>",
            "[REDACTED]",
            raw_text,
            flags=re.IGNORECASE,
        )
        sanitized = re.sub(
            r"\[(?:/?)\(?INST|SYS\).*?\]",
            "[REDACTED]",
            sanitized,
            flags=re.IGNORECASE,
        )

        # Guardrail 2: Enforce max context length
        if len(sanitized) > 15_000:
            logger.warning("[GATEWAY] Payload truncated due to excessive length (>15000 chars).")
            sanitized = sanitized[:15_000] + "...[TRUNCATED]"

        return sanitized

    def _validate_output(self, raw_output: str, required_keys: set) -> dict[str, Any]:
        """
        Post-flight Guardrail: Strict JSON schema enforcement.
        LLMs sometimes wrap JSON in ```json ... ``` — handled here.
        """
        text = raw_output.strip()
        for prefix in ("```json", "```"):
            if text.startswith(prefix):
                text = text[len(prefix):]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        start_idx = text.find("{")
        end_idx = text.rfind("}")
        if start_idx == -1 or end_idx == -1:
            raise ValueError("No JSON object found in output.")

        data = json.loads(text[start_idx : end_idx + 1])

        if required_keys:
            missing = required_keys - set(data.keys())
            if missing:
                raise ValueError(f"Missing required keys: {missing}")

        return data


# ─────────────────────────────────────────────────────────────────────────────
# Lebe Gateway — Qwen2.5-3B on AMD MI300X (vLLM ROCm, OpenAI-compat)
# ─────────────────────────────────────────────────────────────────────────────

class LebeGateway(_GatewayBase):
    """
    Primary escalation engine: Qwen2.5-3B served via vLLM on AMD MI300X.
    Uses the OpenAI-compatible /v1/chat/completions endpoint exposed by vLLM.

    Launch command on AMD MI300X (from PRD):
      VLLM_USE_TRITON_FLASH_ATTN=0 vllm serve \\
        Qwen/Qwen2.5-3B-Instruct --served-model-name lebe \\
        --api-key sigui-key --port 8001 \\
        --max-model-len 8192 --gpu-memory-utilization 0.30 &
    """

    def __init__(self):
        self._enabled = settings.lebe_enabled
        self._endpoint = settings.lebe_endpoint
        self._model = settings.lebe_model_name
        self._api_key = settings.lebe_api_key
        self._timeout = settings.lebe_timeout_s
        self._mock_mode = settings.lebe_mock_mode
        self._consecutive_failures: int = 0
        self._MAX_FAILURES = 5  # Circuit-breaker threshold

    def is_available(self) -> bool:
        """Lebe is available if enabled, not in mock mode, and circuit-breaker is open."""
        return (
            self._enabled
            and not self._mock_mode
            and self._consecutive_failures < self._MAX_FAILURES
        )

    def reset_circuit(self):
        """Reset the circuit-breaker (called after a successful call)."""
        if self._consecutive_failures > 0:
            self._consecutive_failures = 0
            logger.info("[LEBE] ✅ Circuit breaker reset — Qwen2.5 back online.")

    async def call_json_model(
        self,
        system_prompt: str,
        user_payload: dict | str,
        max_tokens: int = 256,
        required_keys: Optional[set] = None,
        timeout: float | None = None,
        context_id: str = "lebe_generic",
    ) -> tuple[Optional[dict[str, Any]], str]:
        """
        Call Qwen2.5-3B via vLLM OpenAI-compat endpoint.
        Returns (parsed_dict, status_string).
        """
        if not self.is_available():
            return None, "lebe_unavailable"

        required_keys = required_keys or set()
        sanitized = self._sanitize_input(user_payload)
        call_timeout = timeout or self._timeout

        payload = {
            "model": self._model,
            "temperature": 0.0,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": sanitized},
            ],
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with asyncio.timeout(call_timeout):
                async with httpx.AsyncClient(timeout=call_timeout + 1.0) as client:
                    resp = await client.post(
                        self._endpoint, json=payload, headers=headers
                    )
                    resp.raise_for_status()

            data = resp.json()
            raw_text = (
                ((data.get("choices") or [{}])[0])
                .get("message", {})
                .get("content", "")
            )
            if not raw_text:
                raise ValueError("Empty content from Lebe endpoint.")

            validated = self._validate_output(raw_text, required_keys)
            self.reset_circuit()
            logger.info(
                f"[LEBE] ✅ Qwen2.5 inference OK — context={context_id} "
                f"device=AMD_MI300X tokens={data.get('usage', {}).get('completion_tokens', '?')}"
            )
            return validated, "lebe_success"

        except asyncio.TimeoutError:
            self._consecutive_failures += 1
            logger.warning(
                f"[LEBE] ⏱ Timeout ({call_timeout}s) — context={context_id} "
                f"failures={self._consecutive_failures}/{self._MAX_FAILURES}"
            )
            return None, "lebe_timeout"
        except httpx.HTTPStatusError as e:
            self._consecutive_failures += 1
            logger.warning(f"[LEBE] HTTP {e.response.status_code} — context={context_id}")
            return None, f"lebe_http_{e.response.status_code}"
        except ValueError as ve:
            self._consecutive_failures += 1
            logger.warning(f"[LEBE] Validation failed — context={context_id}: {ve}")
            return None, "lebe_validation_failed"
        except Exception as exc:
            self._consecutive_failures += 1
            logger.warning(
                f"[LEBE] ❌ Unexpected error — context={context_id}: {exc} "
                f"failures={self._consecutive_failures}/{self._MAX_FAILURES}"
            )
            return None, "lebe_error"


# ─────────────────────────────────────────────────────────────────────────────
# OpenShell Gateway — Claude via Anthropic SDK (fallback / self-critique)
# ─────────────────────────────────────────────────────────────────────────────

class OpenShellGateway(_GatewayBase):
    """
    Fallback LLM gateway: Claude via Anthropic SDK.
    Used for:
      - Escalation fallback when Lebe is unreachable
      - PolicyBrain self-critique (not time-critical)
    """

    def __init__(self):
        self._client: Optional[anthropic.AsyncAnthropic] = None
        self._credits_exhausted = False
        self._setup_client()

    def _setup_client(self):
        if (
            ANTHROPIC_AVAILABLE
            and settings.anthropic_api_key
            and settings.anthropic_api_key != "demo_key"
        ):
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    def is_available(self) -> bool:
        return self._client is not None and not self._credits_exhausted

    def mark_credits_exhausted(self):
        """Mark that the API key has no credits left."""
        if not self._credits_exhausted:
            self._credits_exhausted = True
            logger.error(
                "[OPENSHELL] 🚨 ANTHROPIC CREDITS EXHAUSTED — "
                "Escalation & Self-Critique now use rule-based fallback."
            )

    async def call_json_model(
        self,
        system_prompt: str,
        user_payload: dict | str,
        max_tokens: int = 256,
        required_keys: Optional[set] = None,
        timeout: float = 5.0,
        context_id: str = "generic",
    ) -> tuple[Optional[dict[str, Any]], str]:
        """
        Execute a secure Claude invocation expecting JSON output.
        Returns (parsed_dict, status_string).
        """
        if not self.is_available():
            return None, "llm_gateway_unavailable"

        required_keys = required_keys or set()
        sanitized_payload = self._sanitize_input(user_payload)

        try:
            async with asyncio.timeout(timeout):
                message = await self._client.messages.create(
                    model=settings.decision_ai_model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": sanitized_payload}],
                )

            raw_text = message.content[0].text
            logger.debug(f"[OPENSHELL] ✅ Claude invocation OK — context={context_id}")
            validated_json = self._validate_output(raw_text, required_keys)
            return validated_json, "success"

        except asyncio.TimeoutError:
            logger.warning(f"[OPENSHELL] Timeout ({timeout}s) — context={context_id}")
            return None, "timeout"
        except ValueError as ve:
            logger.warning(f"[OPENSHELL] Validation failed — context={context_id}: {ve}")
            return None, "guardrail_validation_failed"
        except Exception as e:
            err_msg = str(e).lower()
            if "credit balance" in err_msg or "billing" in err_msg or "insufficient funds" in err_msg:
                self.mark_credits_exhausted()
                return None, "credits_exhausted"
            logger.error(f"[OPENSHELL] Unexpected error — context={context_id}: {e}")
            return None, "unexpected_error"


# ─────────────────────────────────────────────────────────────────────────────
# Singletons
# ─────────────────────────────────────────────────────────────────────────────

lebe_gateway = LebeGateway()
llm_gateway = OpenShellGateway()  # kept as-is — used by PolicyBrain / agent graph
