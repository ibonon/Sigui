"""
Tests for sigui.integrations — vérifie que tous les modules s'importent
sans erreur même quand les dépendances optionnelles sont absentes,
et que SiguiGuard fonctionne correctement avec un client mocké.
"""
from __future__ import annotations

import json
import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from sigui.integrations._common import SiguiGuard
from sigui.models import EvaluationResult, EscalationResult, Verdict


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _make_eval_result(verdict: Verdict = Verdict.ALLOW, risk: float = 0.1) -> EvaluationResult:
    return EvaluationResult(
        verdict=verdict,
        risk_score=risk,
        confidence=0.95,
        reason="Unit test result",
        action_hash="0xTEST_HASH",
        chain="arc",
    )


def _make_escalation_result() -> EscalationResult:
    return EscalationResult(
        verdict=Verdict.ALLOW_WITH_CAP,
        cap_amount_usdc=10.0,
        analysis="Deep analysis: transaction looks OK with a cap.",
        confidence=0.80,
        inference_engine="lebe_qwen25",
        inference_device="AMD MI300X",
    )


@pytest.fixture
def mock_client_allow():
    client = MagicMock()
    client.evaluate = AsyncMock(return_value=_make_eval_result(Verdict.ALLOW))
    client.escalate = AsyncMock(return_value=_make_escalation_result())
    return client


@pytest.fixture
def mock_client_block():
    client = MagicMock()
    client.evaluate = AsyncMock(return_value=_make_eval_result(Verdict.BLOCK, risk=0.95))
    return client


@pytest.fixture
def mock_client_escalate():
    client = MagicMock()
    client.evaluate = AsyncMock(return_value=_make_eval_result(Verdict.ESCALATE, risk=0.70))
    client.escalate = AsyncMock(return_value=_make_escalation_result())
    return client


# ─── SiguiGuard tests ────────────────────────────────────────────────────────

class TestSiguiGuard:

    @pytest.mark.asyncio
    async def test_allow_verdict(self, mock_client_allow):
        guard = SiguiGuard(mock_client_allow)
        result = await guard.evaluate_action(
            destination="0xABCDEF",
            amount_usdc=1.0,
            chain="arc",
            action_type="transfer",
        )
        assert result["decision"] == "ALLOW"
        assert result["allowed"] is True
        assert result["blocked"] is False
        assert result["needs_escalation"] is False
        assert result["kind"] == "evaluation"

    @pytest.mark.asyncio
    async def test_block_verdict(self, mock_client_block):
        guard = SiguiGuard(mock_client_block)
        result = await guard.evaluate_action(
            destination="0xBAD",
            amount_usdc=999.0,
        )
        assert result["decision"] == "BLOCK"
        assert result["blocked"] is True
        assert result["allowed"] is False

    @pytest.mark.asyncio
    async def test_escalate_no_auto(self, mock_client_escalate):
        guard = SiguiGuard(mock_client_escalate, auto_escalate=False)
        result = await guard.evaluate_action(
            destination="0xESCALATE",
            amount_usdc=50.0,
        )
        assert result["decision"] == "ESCALATE"
        assert result["needs_escalation"] is True
        # escalate should NOT have been called
        mock_client_escalate.escalate.assert_not_called()

    @pytest.mark.asyncio
    async def test_escalate_auto(self, mock_client_escalate):
        guard = SiguiGuard(mock_client_escalate, auto_escalate=True)
        result = await guard.evaluate_action(
            destination="0xESCALATE",
            amount_usdc=50.0,
        )
        # Should have auto-escalated
        mock_client_escalate.escalate.assert_called_once()
        assert result["kind"] == "escalation"
        assert result["decision"] == "ALLOW_WITH_CAP"

    @pytest.mark.asyncio
    async def test_context_json_merging(self, mock_client_allow):
        guard = SiguiGuard(mock_client_allow)
        await guard.evaluate_action(
            destination="0xABC",
            amount_usdc=1.0,
            reason="test reason",
            context_json='{"source": "api"}',
        )
        call_kwargs = mock_client_allow.evaluate.call_args.kwargs
        assert call_kwargs["context"]["reason"] == "test reason"
        assert call_kwargs["context"]["source"] == "api"

    @pytest.mark.asyncio
    async def test_invalid_context_json_is_safe(self, mock_client_allow):
        guard = SiguiGuard(mock_client_allow)
        # Should not raise — just stores raw text
        await guard.evaluate_action(
            destination="0xABC",
            amount_usdc=1.0,
            context_json="not-valid-json{{",
        )
        call_kwargs = mock_client_allow.evaluate.call_args.kwargs
        assert "context_text" in call_kwargs["context"]

    def test_render_text_is_valid_json(self, mock_client_allow):
        guard = SiguiGuard(mock_client_allow)
        payload = {"decision": "ALLOW", "risk_score": 0.1}
        text = guard.render_text(payload)
        parsed = json.loads(text)
        assert parsed["decision"] == "ALLOW"


# ─── Import safety tests ─────────────────────────────────────────────────────

class TestImportSafety:
    """All integration modules must import without error, even without optional deps."""

    def test_import_langchain_module(self):
        from sigui.integrations import langchain  # noqa: F401

    def test_import_langgraph_module(self):
        from sigui.integrations import langgraph  # noqa: F401

    def test_import_crewai_module(self):
        # Must NOT raise ImportError even if crewai is absent
        from sigui.integrations import crewai  # noqa: F401

    def test_import_openai_agents_module(self):
        from sigui.integrations import openai_agents  # noqa: F401

    def test_import_autogen_module(self):
        from sigui.integrations import autogen  # noqa: F401

    def test_import_smolagents_module(self):
        from sigui.integrations import smolagents  # noqa: F401

    def test_crewai_tool_raises_on_missing_dep(self):
        """SiguiEvaluationTool.__init__ must raise ImportError if crewai absent."""
        from sigui.integrations.crewai.tool_wrapper import SiguiEvaluationTool, _CREWAI_AVAILABLE
        if not _CREWAI_AVAILABLE:
            with pytest.raises(ImportError, match="sigui-sdk\\[crewai\\]"):
                SiguiEvaluationTool(sigui_client=MagicMock())

    def test_openai_agents_raises_on_missing_dep(self):
        from sigui.integrations.openai_agents import create_openai_agents_tool
        try:
            import agents  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="sigui-sdk\\[openai-agents\\]"):
                create_openai_agents_tool(MagicMock())

    def test_autogen_raises_on_missing_dep(self):
        from sigui.integrations.autogen import create_autogen_tool
        try:
            from autogen_core.tools import FunctionTool  # noqa: F401
        except ImportError:
            with pytest.raises(ImportError, match="sigui-sdk\\[autogen\\]"):
                create_autogen_tool(MagicMock())
