"""
Exemple — OpenAI Agents SDK + Sigui

Le tool sigui_evaluate est injecté dans un Agent OpenAI.
L'agent l'appelle automatiquement avant tout paiement.

Install:
    pip install "sigui-sdk[openai-agents]" openai

Run:
    python examples/openai_agents_agent.py
"""
import asyncio

from sigui import SiguiClient
from sigui.integrations.openai_agents import create_openai_agents_tool

try:
    from agents import Agent, Runner
    _AGENTS_AVAILABLE = True
except ImportError:
    _AGENTS_AVAILABLE = False
    print("⚠️  openai-agents non installé. Démo sans LLM.")


# ── Sigui client ───────────────────────────────────────────────────────────────

_sigui = SiguiClient(
    api_url="http://localhost:8000",
    agent_id="openai_agents_demo",
)

sigui_tool = create_openai_agents_tool(_sigui, auto_escalate=True)


# ── Demo directe (sans LLM) ────────────────────────────────────────────────────

async def demo_direct():
    """Invoque le Sigui tool directement, sans passer par un LLM."""
    print("╔══════════════════════════════════════════════════╗")
    print("║  Sigui SDK — OpenAI Agents Integration Demo     ║")
    print("╚══════════════════════════════════════════════════╝\n")

    test_cases = [
        ("0xRecipientABCDEF1234567890ABCDEF1234567890", 1.50,  "arc",      "transfer", "Pay for data API"),
        ("0x0000000000000000000000000000000000000000", 999.0, "ethereum", "transfer", "Suspicious bulk"),
        ("0xDeFiProtocol0000000000000000000000000001", 25.0,  "arc",      "swap",     "Liquidity swap"),
    ]

    async with _sigui:
        for dest, amt, chain, action, reason in test_cases:
            print(f"📤 {action.upper()} ${amt:.2f} → {dest[:16]}… ({chain})")
            result = await _sigui.evaluate(
                amount=amt,
                destination=dest,
                action_type=action,
                chain=chain,
                context={"reason": reason},
            )
            icon = "✅" if result.is_safe else "🚫" if result.is_blocked else "⚠️ "
            print(f"   {icon} {result.verdict.value:8} risk={result.risk_score:.3f}  {result.reason[:60]}")
            print()

    print("✅ OpenAI Agents integration demo completed.")


# ── Demo avec vrai Agent (si openai-agents installé) ──────────────────────────

async def demo_with_agent():
    """Run a real OpenAI Agent with the Sigui tool."""
    if not _AGENTS_AVAILABLE:
        return await demo_direct()

    agent = Agent(
        name="PaymentAgent",
        instructions=(
            "You are a payment agent for an agentic economy platform. "
            "ALWAYS call sigui_evaluate before executing any transfer, swap, or payment. "
            "If the result shows BLOCK, refuse the transaction and explain why. "
            "If ALLOW, confirm the transaction is safe."
        ),
        tools=[sigui_tool],
    )

    async with _sigui:
        result = await Runner.run(
            agent,
            "I need to transfer 5 USDC to address 0xRecipientABCDEF1234567890ABCDEF1234567890 on Arc.",
        )
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(demo_with_agent())
