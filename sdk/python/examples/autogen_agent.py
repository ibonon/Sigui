"""
Exemple — AutoGen + Sigui

Un AssistantAgent AutoGen avec sigui_evaluate comme tool natif.
L'agent protège tous ses paiements automatiquement.

Install:
    pip install "sigui-sdk[autogen]" autogen-agentchat autogen-ext[openai]

Run:
    python examples/autogen_agent.py
"""
import asyncio

from sigui import SiguiClient
from sigui.integrations.autogen import create_autogen_tool

try:
    from autogen_agentchat.agents import AssistantAgent
    from autogen_agentchat.ui import Console
    _AUTOGEN_AVAILABLE = True
except ImportError:
    _AUTOGEN_AVAILABLE = False
    print("⚠️  autogen-agentchat non installé. Démo sans LLM.")


# ── Sigui client ───────────────────────────────────────────────────────────────

_sigui = SiguiClient(
    api_url="http://localhost:8000",
    agent_id="autogen_demo_agent",
)

sigui_tool = create_autogen_tool(_sigui, auto_escalate=True)


# ── Demo directe (sans LLM) ────────────────────────────────────────────────────

async def demo_direct():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Sigui SDK — AutoGen Integration Demo           ║")
    print("╚══════════════════════════════════════════════════╝\n")

    test_cases = [
        ("0xRecipientABCDEF1234567890ABCDEF1234567890", 0.50, "arc",      "transfer"),
        ("0x0000000000000000000000000000000000000001", 500.0, "ethereum", "transfer"),
        ("0xDeFiProtocol0000000000000000000000000001", 15.0,  "arc",      "stake"),
    ]

    async with _sigui:
        for dest, amt, chain, action in test_cases:
            print(f"📤 {action.upper()} ${amt:.2f} → {dest[:16]}… ({chain})")
            result = await _sigui.evaluate(
                amount=amt, destination=dest,
                action_type=action, chain=chain,
            )
            icon = "✅" if result.is_safe else "🚫" if result.is_blocked else "⚠️ "
            print(f"   {icon} {result.verdict.value:8} risk={result.risk_score:.3f}")
            print()

    print("✅ AutoGen integration demo completed.")


# ── Demo avec vrai AssistantAgent (si autogen installé) ───────────────────────

async def demo_with_agent():
    if not _AUTOGEN_AVAILABLE:
        return await demo_direct()

    try:
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    except ImportError:
        print("⚠️  autogen-ext[openai] non installé. Fallback demo direct.")
        return await demo_direct()

    agent = AssistantAgent(
        name="payment_agent",
        model_client=model_client,
        tools=[sigui_tool],
        system_message=(
            "You are a DeFi payment agent. "
            "ALWAYS call sigui_evaluate before any transfer, swap, stake, or bridge. "
            "If Sigui returns BLOCK, abort and explain. If ALLOW, proceed."
        ),
    )

    async with _sigui:
        await Console(
            agent.run_stream(task="Transfer 10 USDC to 0xRecipient123 on Arc network.")
        )


if __name__ == "__main__":
    asyncio.run(demo_with_agent())
