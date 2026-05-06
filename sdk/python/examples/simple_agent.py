"""
Exemple 1 — Agent simple autonome protégé par Sigui

Démontre le flux complet :
  - Évaluation avec paiement x402 automatique (mode démo)
  - Gestion du résultat ALLOW / BLOCK / ESCALATE
  - Escalade automatique si nécessaire

Run : python examples/simple_agent.py
"""
import asyncio
from sigui import SiguiClient, SiguiBlockedError, Chain


async def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║   Sigui SDK — Simple Agent Demo                 ║")
    print("╚══════════════════════════════════════════════════╝\n")

    # Initialisation du client en mode démo (aucun vrai paiement)
    async with SiguiClient(
        api_url="http://localhost:8000",
        agent_id="demo_simple_agent",
        chain=Chain.ARC,
    ) as client:

        # ── Vérification de la santé du serveur ─────────────────────────
        health = await client.health()
        print(f"🌐 Sigui status: {health.get('status')} | mode: {health.get('mode')}")

        # ── Transaction normale (devrait être ALLOW) ─────────────────────
        print("\n📤 Évaluation d'un paiement normal ($0.05 USDC)...")
        result = await client.evaluate(
            amount=0.05,
            destination="0xABCDEF1234567890ABCDEF1234567890ABCDEF12",
            action_type="transfer",
        )
        print(f"   Verdict     : {result.verdict.value}")
        print(f"   Risk score  : {result.risk_score:.3f}")
        print(f"   Raison      : {result.reason[:80]}")
        print(f"   Temps       : {result.processing_time_ms}ms")
        print(f"   Prix payé   : ${result.evaluation_price_usdc:.6f} USDC (x402)")
        if result.onchain_proof:
            print(f"   Preuve Arc  : {result.onchain_proof}")

        # ── Transaction suspecte (gros montant, nouveau destinataire) ────
        print("\n🚨 Évaluation d'un paiement suspect ($500 USDC)...")
        result2 = await client.evaluate_and_escalate(
            amount=500.0,
            destination="0x0000000000000000000000000000000000000001",
            action_type="transfer",
            context={"suspicious": True, "first_transaction": True},
        )
        print(f"   Verdict     : {result2.verdict.value}")

        if hasattr(result2, "analysis"):
            # EscalationResult
            print(f"   Analyse     : {result2.analysis[:100]}")
            print(f"   Moteur IA   : {result2.inference_engine} ({result2.inference_device})")
        else:
            # EvaluationResult
            print(f"   Risk score  : {result2.risk_score:.3f}")
            print(f"   Raison      : {result2.reason[:100]}")

        # ── Treasury state ───────────────────────────────────────────────
        print("\n💰 État de la trésorerie Sigui :")
        treasury = await client.treasury()
        print(f"   Solde   : ${treasury.balance:.4f} USDC")
        print(f"   Gagné   : ${treasury.total_earned:.4f} USDC")
        print(f"   Mode    : {treasury.mode}")

    print("\n✅ Demo terminée.")


if __name__ == "__main__":
    asyncio.run(main())
