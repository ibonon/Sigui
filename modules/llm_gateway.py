"""
ArcWarden v3.0 — OpenShell LLM Gateway
Inspired by NemoClaw architecture, this module acts as a strict proxy for all LLM inferences.
Includes pre-flight (input sanitization) and post-flight (output validation) guardrails.
"""
import asyncio
import json
import re
from typing import Any, Optional
from loguru import logger

from config import settings

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class OpenShellGateway:
    """
    Centralized Gateway for LLM invocations.
    Enforces security layers (Guardrails) before allowing direct LLM calls.
    """

    def __init__(self):
        self._client: Optional[anthropic.AsyncAnthropic] = None
        self._credits_exhausted = False
        self._setup_client()

    def _setup_client(self):
        if ANTHROPIC_AVAILABLE and settings.anthropic_api_key and settings.anthropic_api_key != "demo_key":
            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    def is_available(self) -> bool:
        return self._client is not None and not self._credits_exhausted

    def mark_credits_exhausted(self):
        """Mark that the API key has no credits left."""
        if not self._credits_exhausted:
            self._credits_exhausted = True
            logger.error("[OPENSHELL] 🚨 ANTHROPIC CREDITS EXHAUSTED — LLM features (Escalation, Self-Critique) are now disabled.")

    def _sanitize_input(self, payload: dict | str) -> str:
        """
        Pre-flight Guardrail: Prevent common injection patterns.
        - Strip known LLM control tokens context markers like <|system|>.
        - Limit excessive lengths.
        """
        raw_text = json.dumps(payload) if isinstance(payload, dict) else str(payload)
        
        # Guardrail 1: Block control token injections
        sanitized = re.sub(r'<(?:/?|\|)(?:system|assistant|user|role).*?>', '[REDACTED]', raw_text, flags=re.IGNORECASE)
        sanitized = re.sub(r'\[(?:/?)(?:INST|SYS).*?\]', '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        # Guardrail 2: Enforce max context length to avoid DoS/Context-flood
        if len(sanitized) > 15000:
            logger.warning("[OPENSHELL] Payload truncated due to excessive length (>15000 chars).")
            sanitized = sanitized[:15000] + "...[TRUNCATED]"
            
        return sanitized

    def _validate_output(self, raw_output: str, required_keys: set) -> dict[str, Any]:
        """
        Post-flight Guardrail: Strict JSON schema enforcement.
        """
        try:
            # Sometime LLMs wrap JSON in ```json ... ``` blocks
            text = raw_output.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            start_idx = text.find('{')
            end_idx = text.rfind('}')
            if start_idx == -1 or end_idx == -1:
                raise ValueError("No JSON object found in output.")
                
            json_str = text[start_idx:end_idx+1]
            data = json.loads(json_str)

            if required_keys:
                missing = required_keys - set(data.keys())
                if missing:
                    raise ValueError(f"Missing required keys: {missing}")
            
            return data
        except json.JSONDecodeError as e:
            logger.error(f"[OPENSHELL] JSON Decode Error: {e} - Raw: {raw_output[:100]}...")
            raise ValueError("Output is not valid JSON.") from e

    async def call_json_model(
        self,
        system_prompt: str,
        user_payload: dict | str,
        max_tokens: int = 256,
        required_keys: Optional[set] = None,
        timeout: float = 5.0,
        context_id: str = "generic"
    ) -> tuple[Optional[dict[str, Any]], str]:
        """
        Executes a secure LLM invocation expecting JSON output.
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
                    messages=[{"role": "user", "content": sanitized_payload}]
                )
            
            raw_text = message.content[0].text
            logger.debug(f"[OPENSHELL] successful invocation for context: {context_id}")
            validated_json = self._validate_output(raw_text, required_keys)
            return validated_json, "success"

        except asyncio.TimeoutError:
            logger.warning(f"[OPENSHELL] Timeout ({timeout}s) evaluating {context_id}")
            return None, "timeout"
        except ValueError as ve:
            logger.warning(f"[OPENSHELL] Validation failed for {context_id}: {ve}")
            return None, "guardrail_validation_failed"
        except Exception as e:
            err_msg = str(e).lower()
            if "credit balance" in err_msg or "billing" in err_msg or "insufficient funds" in err_msg:
                self.mark_credits_exhausted()
                return None, "credits_exhausted"
            
            logger.error(f"[OPENSHELL] Unexpected error during model call {context_id}: {e}")
            return None, "unexpected_error"


# Global singleton Gateway instance
llm_gateway = OpenShellGateway()
