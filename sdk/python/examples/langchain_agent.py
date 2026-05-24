"""
Exemple 2 — Intégration LangChain + Sigui

Un LangChain Agent Tool qui protège automatiquement tous ses paiements.
Le tool "safe_transfer" évalue via Sigui avant d'exécuter la transaction.

Run : pip install langchain langchain-openai
      python examples/langchain_agent.py
"""
import asyncio
from typing import Optional

# ── Sigui ─────────────────────────────────────────────────────────────────────
from sigui import SiguiClient, Verdict
from sigui.integrations.langchain import create_langchain_tool

# ── LangChain ─────────────────────────────────────────────────────────────────
try:
    from langchain.tools import tool
    from langchain_core.messages import HumanMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    print("⚠️  langchain non installé. Demo sans LLM.")


# ── Sigui client global ────────────────────────────────────────────────────────
_sigui = SiguiClient(
    api_url="http://localhost:8000",
    agent_id="langchain_agent_01",
    raise_on_block=False,  # On gere manuellement pour montrer le flow
)


# ── Sigui Tool pour LangChain ──────────────────────────────────────────────────

if LANGCHAIN_AVAILABLE:
    safe_transfer = create_langchain_tool(
        _sigui,
        name="safe_transfer",
        description="Evaluate a USDC transfer with Sigui before execution.",
        auto_escalate=True,
    )


# ── Demo sans LLM (pour le hackathon) ─────────────────────────────────────────

async def demo_without_llm():
    """Démontre le Sigui Tool sans nécessiter d'API OpenAI."""
    print("╔══════════════════════════════════════════════════╗")
    print("║   Sigui SDK — LangChain Integration Demo        ║")
    print("╚══════════════════════════════════════════════════╝\n")

    test_cases = [
        {
            "destination": "0xRecipientABCDEF1234567890ABCDEF1234567890",
            "amount_usdc": 0.10,
            "chain": "arc",
            "reason": "Pay for AI API service",
        },
        {
            "destination": "0x0000000000000000000000000000000000000000",
            "amount_usdc": 999.99,
            "chain": "ethereum",
            "reason": "Suspicious bulk transfer",
        },
        {
            "destination": "0xDeFiProtocol0000000000000000000000000001",
            "amount_usdc": 50.0,
            "chain": "arc",
            "reason": "Liquidity provision",
        },
    ]

    async with _sigui:
        if LANGCHAIN_AVAILABLE:
            tool_result = await safe_transfer.ainvoke(
                {
                    "destination": "0xRecipientABCDEF1234567890ABCDEF1234567890",
                    "amount_usdc": 0.10,
                    "chain": "arc",
                    "reason": "Pay for AI API service",
                }
            )
            print("Tool output:", tool_result)
            print()

        for tc in test_cases:
            print(f"📤 Transfer: ${tc['amount_usdc']} → {tc['destination'][:14]}… ({tc['chain']})")
            result = await _sigui.evaluate(
                amount=tc["amount_usdc"],
                destination=tc["destination"],
                action_type="transfer",
                chain=tc["chain"],
                context={"reason": tc["reason"]},
            )
            icon = "✅" if result.is_safe else "🚫" if result.is_blocked else "⚠️"
            print(f"   {icon} {result.verdict.value} | risk={result.risk_score:.3f} | {result.reason[:70]}")
            print()

    print("✅ LangChain integration demo completed.")


if __name__ == "__main__":
    asyncio.run(demo_without_llm())
