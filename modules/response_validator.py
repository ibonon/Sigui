"""
Sigui v3.0 — Response Validator
═══════════════════════════════════
Post-service validation layer: detects data poisoning, prompt injection, and statistical
anomalies in responses that autonomous agents receive from Arc ecosystem services.

Called AFTER an agent receives a service response and BEFORE it acts on the data.
This closes the security loop in both directions:
  → Sigui validates payment BEFORE the service call  (x402 middleware)
  ← Sigui validates the response AFTER the service call (this module)

Detection layers:
  1. Prompt injection / jailbreak patterns
  2. Statistical validation (Z-score vs. history + caller-provided bounds)
  3. Schema anomaly (suspicious keys, oversized payload)
  4. Historical consistency (vs. past validated responses from same service)
  5. Known poisoning signatures (oracle zeroing, overflow, embedded addresses)
"""

import json
import math
import re
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from loguru import logger

from config import settings
from modules.memory import memory

# ────────────────────────────────────────────────────────────────────────────
# Data model
# ────────────────────────────────────────────────────────────────────────────


class ValidationVerdict(str, Enum):
    SAFE = "SAFE"  # Response looks legitimate — safe to use
    SUSPICIOUS = "SUSPICIOUS"  # Anomalies detected — cross-validate before acting
    POISONED = "POISONED"  # High confidence malicious data / injection attempt


@dataclass
class ValidationFinding:
    """A single detected anomaly or threat."""

    category: str  # "injection" | "statistical" | "schema" | "historical" | "poisoning"
    severity: str  # "low" | "medium" | "high" | "critical"
    detail: str  # Human-readable description
    risk_delta: float  # Contribution to overall risk score [0.0 – 1.0]


@dataclass
class ValidationResult:
    """Full result of a response validation run."""

    verdict: ValidationVerdict
    risk_score: float
    confidence: float
    findings: list[ValidationFinding]
    service_address: str
    request_type: str
    recommendations: list[str]
    processing_time_ms: int
    timestamp: str


# ────────────────────────────────────────────────────────────────────────────
# Response Validation Engine
# ────────────────────────────────────────────────────────────────────────────


class ResponseValidationEngine:
    """
    Multi-layer post-service response validation.

    Usage:
        result = await response_validator.validate(
            agent_id="agent_payer",
            service_address="0xARCDATA...",
            request_type="price_feed",
            response_data={"price": 67000.0, "asset": "BTC"},
            context={
                "asset": "BTC",
                "expected_range": [40_000, 100_000],
                "previous_prices": [67100, 66900, 67050],
            },
        )
        # result.verdict: SAFE | SUSPICIOUS | POISONED
    """

    # ── Prompt injection & jailbreak patterns ─────────────────────────────
    # Each entry: (regex_pattern, severity)
    INJECTION_PATTERNS: list[tuple[str, str]] = [
        # Instruction override
        (
            r"ignore\s+(previous|prior|all)\s+(instructions?|rules?|constraints?)",
            "critical",
        ),
        (r"new\s+(instructions?|rules?|directives?)\s*:", "high"),
        (r"override\s+(your|the|all)\s*(rules?|instructions?|constraints?)", "high"),
        (r"disregard\s+(your|the|all)\s*(previous|prior|safety)", "high"),
        (r"forget\s+(everything|all)\s*(you\s+know|previous)", "high"),
        # Persona hijack
        (r"you\s+are\s+now\s+(a\s+)?(different|new|another)", "critical"),
        (r"act\s+as\s+(if|though)\s+(you\s+are|you\'?re)", "high"),
        # LLM control tokens
        (r"<\|?(system|assistant|user|role)\|?>", "critical"),
        (r"\[/?(?:INST|SYS|SYSTEM)\]", "critical"),
        # Financial override — highest priority
        (r"approve\s+all\s+(transactions?|payments?|requests?)", "critical"),
        (r"transfer\s+all\s+(funds?|balance|usdc)", "critical"),
        (
            r"send\s+\$?\d+(\.\d+)?\s*(usdc|usd|eth|btc)\s+to\s+0x[a-f0-9]{6,}",
            "critical",
        ),
        (r"(drain|empty)\s+(the\s+)?(wallet|treasury|balance)", "critical"),
        # Code injection
        (r"eval\s*\(|exec\s*\(|__import__\s*\(|subprocess\.", "critical"),
        # Known jailbreak keywords
        (r"jailbreak|prompt[\s_]?injection|DAN\s+mode|do\s+anything\s+now", "high"),
    ]

    # ── Asset-specific sanity bounds for price feeds ──────────────────────
    # Very wide bounds — just to catch extreme oracle manipulation
    PRICE_BOUNDS: dict[str, tuple[float, float]] = {
        "BTC": (100, 10_000_000),
        "ETH": (1, 1_000_000),
        "USDC": (0.90, 1.10),
        "USDT": (0.90, 1.10),
        "DAI": (0.85, 1.15),
        "SOL": (0.01, 100_000),
        "ARB": (0.001, 10_000),
        "default": (0.0, 1_000_000_000_000),
    }

    # Keys that should never appear in a legitimate service response
    SUSPICIOUS_KEYS: frozenset[str] = frozenset(
        {
            "instruction",
            "override",
            "system_prompt",
            "jailbreak",
            "new_rules",
            "admin_key",
            "private_key",
            "secret",
            "seed_phrase",
            "transfer_to",
            "send_funds_to",
            "drain",
            "execute",
            "eval",
        }
    )

    # ── Core validation entry point ───────────────────────────────────────

    async def validate(
        self,
        agent_id: str,
        service_address: str,
        request_type: str,
        response_data: Any,
        context: dict,
    ) -> ValidationResult:
        """
        Run all five detection layers and return a ValidationResult.

        Args:
            agent_id:        ID of the calling agent (for logging & history)
            service_address: Arc address of the service that produced the response
            request_type:    Semantic type: "price_feed" | "oracle_data" | "api_response"
                             | "inference_result" | "generic"
            response_data:   The raw response body (dict, list, str, or numeric)
            context:         Optional caller hints:
                               expected_range: [min, max] — numeric bounds
                               previous_prices / previous_values: list[float] — history
                               asset: str — for price-feed bound checks
        """
        t_start = time.perf_counter()
        findings: list[ValidationFinding] = []

        # Serialize once for text-level analysis
        response_text = (
            json.dumps(response_data, ensure_ascii=False)
            if not isinstance(response_data, str)
            else response_data
        )

        # Layer 1 — Prompt injection / jailbreak
        findings += self._detect_injection(response_text)

        # Layer 2 — Statistical validation
        findings += self._validate_statistical(response_data, request_type, context)

        # Layer 3 — Schema anomaly
        findings += self._detect_schema_anomaly(
            response_data, request_type, response_text
        )

        # Layer 4 — Historical consistency (async DB query)
        findings += await self._check_historical(
            service_address, request_type, response_data
        )

        # Layer 5 — Known poisoning signatures
        findings += self._detect_poisoning(response_data, request_type, response_text)

        # Aggregate
        risk_score = self._compute_risk(findings)
        confidence = self._compute_confidence(findings, context)
        verdict = self._determine_verdict(risk_score, findings)
        recs = self._recommendations(verdict, findings, request_type)

        ms = int((time.perf_counter() - t_start) * 1000)
        timestamp = datetime.now(timezone.utc).isoformat()

        result = ValidationResult(
            verdict=verdict,
            risk_score=round(risk_score, 4),
            confidence=round(confidence, 4),
            findings=findings,
            service_address=service_address,
            request_type=request_type,
            recommendations=recs,
            processing_time_ms=ms,
            timestamp=timestamp,
        )

        # Persist to DB (non-blocking on failure)
        primary_numeric = self._extract_primary_numeric(response_data, request_type)
        await self._persist(
            agent_id, service_address, request_type, result, primary_numeric
        )

        logger.info(
            f"[RESP_VALIDATOR] {verdict.value} | agent={agent_id} | "
            f"service={service_address[:16]}… | type={request_type} | "
            f"R={risk_score:.3f} conf={confidence:.2f} | "
            f"findings={len(findings)} | {ms}ms"
        )

        return result

    # ── Layer 1 — Injection detection ─────────────────────────────────────

    def _detect_injection(self, text: str) -> list[ValidationFinding]:
        findings = []
        for pattern, severity in self.INJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                risk_delta = {
                    "critical": 0.80,
                    "high": 0.50,
                    "medium": 0.30,
                    "low": 0.10,
                }[severity]
                findings.append(
                    ValidationFinding(
                        category="injection",
                        severity=severity,
                        detail=f"Injection pattern matched: `{pattern[:60]}`",
                        risk_delta=risk_delta,
                    )
                )
        return findings

    # ── Layer 2 — Statistical validation ─────────────────────────────────

    def _validate_statistical(
        self, response_data: Any, request_type: str, context: dict
    ) -> list[ValidationFinding]:
        findings = []
        value = self._extract_primary_numeric(response_data, request_type)
        if value is None:
            return findings

        # 2a — Caller-provided expected range
        expected_range = context.get("expected_range")
        if expected_range and len(expected_range) == 2:
            lo, hi = float(expected_range[0]), float(expected_range[1])
            if not (lo <= value <= hi):
                span = max(abs(hi - lo), 1e-9)
                deviation = min(abs(value - lo), abs(value - hi)) / span
                severity = (
                    "critical"
                    if deviation > 10
                    else "high"
                    if deviation > 2
                    else "medium"
                )
                findings.append(
                    ValidationFinding(
                        category="statistical",
                        severity=severity,
                        detail=(
                            f"Value {value} outside caller-specified range [{lo}, {hi}] "
                            f"(deviation ≈ {deviation:.1f}×)"
                        ),
                        risk_delta=min(0.70, 0.15 + deviation * 0.04),
                    )
                )

        # 2b — Z-score vs. caller-provided history
        history = context.get("previous_prices") or context.get("previous_values") or []
        if len(history) >= 3:
            try:
                mean = statistics.mean(history)
                std = statistics.stdev(history)
                if std > 0:
                    z = abs(value - mean) / std
                    if z > 5:
                        findings.append(
                            ValidationFinding(
                                category="statistical",
                                severity="critical",
                                detail=(
                                    f"Z-score {z:.1f}σ — extreme outlier vs. {len(history)} historical values "
                                    f"(μ={mean:.4f}, σ={std:.4f})"
                                ),
                                risk_delta=min(0.65, 0.15 + z * 0.05),
                            )
                        )
                    elif z > 3:
                        findings.append(
                            ValidationFinding(
                                category="statistical",
                                severity="high",
                                detail=f"Z-score {z:.1f}σ — significant outlier (μ={mean:.4f})",
                                risk_delta=0.30,
                            )
                        )
            except (statistics.StatisticsError, ZeroDivisionError):
                pass

        # 2c — Asset-specific sanity bounds (price feeds)
        if request_type in ("price_feed", "oracle_data"):
            asset = str(context.get("asset", "default")).upper()
            lo, hi = self.PRICE_BOUNDS.get(asset, self.PRICE_BOUNDS["default"])
            if not (lo <= value <= hi):
                findings.append(
                    ValidationFinding(
                        category="statistical",
                        severity="critical",
                        detail=(
                            f"Price {value} for {asset} violates sanity bounds "
                            f"[{lo:,}, {hi:,}]"
                        ),
                        risk_delta=0.75,
                    )
                )

        return findings

    # ── Layer 3 — Schema anomaly ───────────────────────────────────────────

    def _detect_schema_anomaly(
        self, response_data: Any, request_type: str, response_text: str
    ) -> list[ValidationFinding]:
        findings = []

        if isinstance(response_data, dict):
            # Suspicious keys
            suspicious = self.SUSPICIOUS_KEYS & set(response_data.keys())
            if suspicious:
                findings.append(
                    ValidationFinding(
                        category="schema",
                        severity="high",
                        detail=f"Response contains suspicious keys: {sorted(suspicious)}",
                        risk_delta=0.40,
                    )
                )

        # Oversized payload (potential context flooding)
        if len(response_text) > 50_000:
            findings.append(
                ValidationFinding(
                    category="schema",
                    severity="medium",
                    detail=f"Payload size {len(response_text):,} bytes exceeds 50 KB — potential context flood",
                    risk_delta=0.15,
                )
            )

        # Deeply nested structure (evasion technique)
        depth = self._measure_depth(response_data)
        if depth > 8:
            findings.append(
                ValidationFinding(
                    category="schema",
                    severity="low",
                    detail=f"Response nesting depth {depth} — unusually deep for {request_type}",
                    risk_delta=0.10,
                )
            )

        return findings

    def _measure_depth(self, obj: Any, current: int = 0) -> int:
        if current > 15:
            return current  # cap recursion
        if isinstance(obj, dict):
            return max(
                (self._measure_depth(v, current + 1) for v in obj.values()),
                default=current,
            )
        if isinstance(obj, list):
            return max(
                (self._measure_depth(v, current + 1) for v in obj), default=current
            )
        return current

    # ── Layer 4 — Historical consistency ─────────────────────────────────

    async def _check_historical(
        self, service_address: str, request_type: str, response_data: Any
    ) -> list[ValidationFinding]:
        """Compare this response against validated historical responses from the same service."""
        findings = []
        value = self._extract_primary_numeric(response_data, request_type)
        if value is None:
            return findings

        try:
            rows = await memory.run_query(
                """
                SELECT primary_numeric_value
                FROM   response_validations
                WHERE  service_address = ?
                  AND  request_type    = ?
                  AND  verdict        != 'POISONED'
                  AND  primary_numeric_value IS NOT NULL
                ORDER  BY timestamp DESC
                LIMIT  30
                """,
                (service_address, request_type),
                fetch="all"
            )

            history = [float(r[0]) for r in rows if r[0] is not None]
            if len(history) >= 5:
                mean = statistics.mean(history)
                std = statistics.stdev(history) if len(history) > 1 else 0.0
                if std > 0:
                    z = abs(value - mean) / std
                    if z > 4:
                        findings.append(
                            ValidationFinding(
                                category="historical",
                                severity="high",
                                detail=(
                                    f"Value {value:.4f} deviates {z:.1f}σ from service history "
                                    f"(μ={mean:.4f}, n={len(history)})"
                                ),
                                risk_delta=min(0.50, 0.10 + z * 0.04),
                            )
                        )
        except Exception as exc:
            logger.debug(f"[RESP_VALIDATOR] Historical check failed: {exc}")

        return findings

    # ── Layer 5 — Poisoning signatures ────────────────────────────────────

    def _detect_poisoning(
        self, response_data: Any, request_type: str, response_text: str
    ) -> list[ValidationFinding]:
        findings = []
        value = self._extract_primary_numeric(response_data, request_type)

        # Signature 1 — Oracle zeroing
        if (
            value is not None
            and value == 0.0
            and request_type in ("price_feed", "oracle_data")
        ):
            findings.append(
                ValidationFinding(
                    category="poisoning",
                    severity="high",
                    detail="Primary value is exactly 0 — classic oracle zeroing attack pattern",
                    risk_delta=0.45,
                )
            )

        # Signature 2 — Astronomical overflow
        if value is not None and value >= 1e15:
            findings.append(
                ValidationFinding(
                    category="poisoning",
                    severity="critical",
                    detail=f"Astronomical value {value:.2e} — likely integer overflow or oracle manipulation",
                    risk_delta=0.80,
                )
            )

        # Signature 3 — NaN / Infinity in payload
        if any(
            tok in response_text
            for tok in ('"Infinity"', '"NaN"', '"inf"', '"nan"', "Infinity", "NaN")
        ):
            findings.append(
                ValidationFinding(
                    category="poisoning",
                    severity="high",
                    detail="Response contains Infinity/NaN — unsafe for financial calculations",
                    risk_delta=0.45,
                )
            )

        # Signature 4 — Embedded Ethereum addresses in non-address responses
        ETH_ADDR_PATTERN = r"\b0x[a-fA-F0-9]{40}\b"
        embedded = re.findall(ETH_ADDR_PATTERN, response_text)
        if embedded and request_type not in (
            "contract_lookup",
            "address_info",
            "wallet_info",
        ):
            findings.append(
                ValidationFinding(
                    category="poisoning",
                    severity="medium",
                    detail=(
                        f"Response contains {len(embedded)} Ethereum address(es) "
                        f"— unexpected for request_type='{request_type}'"
                    ),
                    risk_delta=0.20,
                )
            )

        # Signature 5 — Negative prices / rates
        if (
            value is not None
            and value < 0
            and request_type in ("price_feed", "oracle_data", "rate")
        ):
            findings.append(
                ValidationFinding(
                    category="poisoning",
                    severity="high",
                    detail=f"Negative value {value} for {request_type} — impossible in a real market",
                    risk_delta=0.55,
                )
            )

        return findings

    # ── Aggregation ───────────────────────────────────────────────────────

    def _compute_risk(self, findings: list[ValidationFinding]) -> float:
        if not findings:
            return 0.0
        # Sort descending; first finding contributes 100%, subsequent 60%
        deltas = sorted((f.risk_delta for f in findings), reverse=True)
        total = deltas[0] + sum(d * 0.60 for d in deltas[1:])
        return min(1.0, total)

    def _compute_confidence(
        self, findings: list[ValidationFinding], context: dict
    ) -> float:
        base = 0.55
        base += min(0.25, len(findings) * 0.08)
        if context.get("expected_range"):
            base += 0.08
        if context.get("previous_prices") or context.get("previous_values"):
            base += 0.07
        if context.get("asset"):
            base += 0.03
        return min(0.98, base)

    def _determine_verdict(
        self, risk_score: float, findings: list[ValidationFinding]
    ) -> ValidationVerdict:
        # Any critical finding → immediate POISONED regardless of score
        if any(f.severity == "critical" for f in findings):
            return ValidationVerdict.POISONED
        if risk_score >= 0.60:
            return ValidationVerdict.POISONED
        if risk_score >= 0.25:
            return ValidationVerdict.SUSPICIOUS
        return ValidationVerdict.SAFE

    def _recommendations(
        self,
        verdict: ValidationVerdict,
        findings: list[ValidationFinding],
        request_type: str,
    ) -> list[str]:
        recs: list[str] = []

        if verdict == ValidationVerdict.POISONED:
            recs.append("🚨 DO NOT use this response — discard immediately")
            recs.append(
                "This service has been auto-reported via POST /services/complain"
            )
            recs.append("Request the same data from a different, verified service")
        elif verdict == ValidationVerdict.SUSPICIOUS:
            recs.append("⚠️ Cross-validate with another verified service before acting")
            recs.append(
                "Consider escalating to Claude via POST /escalate for deeper analysis"
            )

        for f in findings:
            if f.category == "injection":
                recs.append(
                    "🔒 Injection attempt in response — NEVER pass this text to an LLM unparsed"
                )
            if (
                f.category == "statistical"
                and "outside caller-specified range" in f.detail
            ):
                recs.append(
                    "📊 Provide tighter expected_range in context for more precise bounds checking"
                )

        if not recs:
            recs.append("✅ Response passed all 5 validation layers — safe to use")

        # Deduplicate while preserving order
        seen: set[str] = set()
        return [r for r in recs if not (r in seen or seen.add(r))]  # type: ignore[func-returns-value]

    # ── Helpers ───────────────────────────────────────────────────────────

    def _extract_primary_numeric(self, data: Any, request_type: str) -> Optional[float]:
        """Extract the most semantically relevant numeric value from a response."""
        if isinstance(data, (int, float)) and not isinstance(data, bool):
            return float(data)
        if isinstance(data, dict):
            # Try request-type-specific keys first
            priority_keys = {
                "price_feed": ("price", "value", "rate", "amount", "result"),
                "oracle_data": ("value", "price", "data", "result", "answer"),
                "api_response": ("result", "value", "data", "amount"),
                "inference_result": ("confidence", "score", "probability"),
            }.get(request_type, ("value", "price", "result", "amount", "data"))
            for key in priority_keys:
                v = data.get(key)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    return float(v)
        if isinstance(data, list) and len(data) == 1:
            return self._extract_primary_numeric(data[0], request_type)
        return None

    # ── Persistence ───────────────────────────────────────────────────────

    async def _persist(
        self,
        agent_id: str,
        service_address: str,
        request_type: str,
        result: ValidationResult,
        primary_numeric: Optional[float],
    ) -> None:
        try:
            await memory.run_query(
                """
                INSERT INTO response_validations
                    (agent_id, service_address, request_type, verdict, risk_score,
                     findings_count, primary_numeric_value, processing_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_id,
                    service_address,
                    request_type,
                    result.verdict.value,
                    result.risk_score,
                    len(result.findings),
                    primary_numeric,
                    result.processing_time_ms,
                ),
                fetch="none"
            )
        except Exception as exc:
            logger.debug(f"[RESP_VALIDATOR] Persist failed: {exc}")

    # ── Public analytics ──────────────────────────────────────────────────

    async def get_service_validation_stats(self, service_address: str) -> dict:
        """
        Aggregated validation history for a service address.
        Called by the /services/{address} endpoint to enrich the service profile.
        """
        try:
            row = await memory.run_query(
                """
                SELECT
                    COUNT(*)                                               AS total,
                    SUM(CASE WHEN verdict = 'POISONED'   THEN 1 ELSE 0 END) AS poisoned,
                    SUM(CASE WHEN verdict = 'SUSPICIOUS' THEN 1 ELSE 0 END) AS suspicious,
                    AVG(risk_score)                                        AS avg_risk,
                    MAX(timestamp)                                         AS last_seen
                FROM response_validations
                WHERE service_address = ?
                """,
                (service_address,),
                fetch="one"
            )

            if not row or not row[0]:
                return {
                    "total_validations": 0,
                    "poisoned_count": 0,
                    "suspicious_count": 0,
                }

            total = int(row[0])
            poisoned = int(row[1] or 0)
            susp = int(row[2] or 0)
            return {
                "total_validations": total,
                "poisoned_count": poisoned,
                "suspicious_count": susp,
                "avg_risk_score": round(float(row[3] or 0.0), 4),
                "last_validation": row[4],
                "poison_rate": round(poisoned / total, 4) if total else 0.0,
            }
        except Exception as exc:
            logger.debug(f"[RESP_VALIDATOR] Stats query failed: {exc}")
            return {"total_validations": 0, "poisoned_count": 0, "suspicious_count": 0}

    async def get_global_stats(self) -> dict:
        """Global validation statistics — used by /stats endpoint."""
        try:
            row = await memory.run_query(
                """
                SELECT
                    COUNT(*)                                                 AS total,
                    SUM(CASE WHEN verdict = 'SAFE'       THEN 1 ELSE 0 END) AS safe,
                    SUM(CASE WHEN verdict = 'SUSPICIOUS' THEN 1 ELSE 0 END) AS suspicious,
                    SUM(CASE WHEN verdict = 'POISONED'   THEN 1 ELSE 0 END) AS poisoned,
                    COUNT(DISTINCT service_address)                          AS services_evaluated,
                    AVG(risk_score)                                          AS avg_risk
                FROM response_validations
                """,
                fetch="one"
            )
            if not row or not row[0]:
                return {"total": 0, "safe": 0, "suspicious": 0, "poisoned": 0}
            return {
                "total": int(row[0]),
                "safe": int(row[1] or 0),
                "suspicious": int(row[2] or 0),
                "poisoned": int(row[3] or 0),
                "services_evaluated": int(row[4] or 0),
                "avg_risk_score": round(float(row[5] or 0.0), 4),
            }
        except Exception:
            return {"total": 0, "safe": 0, "suspicious": 0, "poisoned": 0}


# ── Singleton ─────────────────────────────────────────────────────────────────
response_validator = ResponseValidationEngine()
