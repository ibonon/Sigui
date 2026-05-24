"""
Exemple — HuggingFace smolagents + Sigui

SiguiTool est injecté dans un CodeAgent ou ToolCallingAgent.
L'agent l'appelle avant tout paiement.

Install:
    pip install "sigui-sdk[smolagents]" smolagents transformers

Run:
    python examples/smolagents_agent.py
"""
import asyncio

from sigui import SiguiClient
from sigui.integrations.smolagents import SiguiTool

try:
    from smolagents import CodeAgent, HfApiModel, ToolCallingAgent
    _SMOLAGENTS_AVAILABLE = True
except ImportError:
    _SMOLAGENTS_AVAILABLE = False
    print("⚠️  smolagents non installé. Démo sans LLM.")


# ── Sigui client + tool ────────────────────────────────────────────────────────

_sigui = SiguiClient(
    api_url="http://localhost:8000",
    agent_id="smolagents_demo",
)

sigui_tool = SiguiTool(_sigui, auto_escalate=True)


# ── Demo directe (sans LLM) ────────────────────────────────────────────────────

async def demo_direct():
    print("╔══════════════════════════════════════════════════╗")
    print("║  Sigui SDK — smolagents Integration Demo        ║")
    print("╚══════════════════════════════════════════════════╝\n")

    test_cases = [
        ("0xRecipientABCDEF1234567890ABCDEF1234567890", 2.00, "arc",      "transfer", "API payment"),
        ("0x0000000000000000000000000000000000000001", 750.0, "solana",   "transfer", "Suspicious"),
        ("0xDeFiProtocol0000000000000000000000000001", 30.0,  "arc",      "bridge",   "Cross-chain bridge"),
    ]

    async with _sigui:
        for dest, amt, chain, action, reason in test_cases:
            print(f"📤 {action.upper()} ${amt:.2f} → {dest[:16]}… ({chain}) — {reason}")
            result = await _sigui.evaluate(
                amount=amt, destination=dest,
                action_type=action, chain=chain,
                context={"reason": reason},
            )
            icon = "✅" if result.is_safe else "🚫" if result.is_blocked else "⚠️ "
            print(f"   {icon} {result.verdict.value:8} risk={result.risk_score:.3f}  {result.reason[:65]}")
            print()

    print("✅ smolagents integration demo completed.")


# ── Demo avec vrai CodeAgent (synchrone — smolagents est sync-first) ──────────

def demo_with_agent():
    if not _SMOLAGENTS_AVAILABLE:
        asyncio.run(demo_direct())
        return

    # SiguiTool.forward() bridges sync→async internally
    tool_result = sigui_tool.forward(
        destination="0xRecipientABCDEF1234567890ABCDEF1234567890",
        amount_usdc=5.0,
        chain="arc",
        action_type="transfer",
        reason="HuggingFace agent payment",
    )
    print("Direct tool call result:", tool_result)
    print()

    # With a real CodeAgent:
    # agent = CodeAgent(
    #     tools=[sigui_tool],
    #     model=HfApiModel("meta-llama/Llama-3.1-70B-Instruct"),
    # )
    # agent.run("Transfer 5 USDC to 0xRecipient... on Arc.")


if __name__ == "__main__":
    demo_with_agent()
