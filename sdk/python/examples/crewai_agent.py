"""
Exemple 3 — Intégration CrewAI + Sigui

Un Treasurer Agent qui valide les paiements de N agents via Sigui.
Le nombre d'agents est configurable via --agents (défaut: 6).
Fonctionne en mode offline si le backend Sigui n'est pas disponible.

Run :
    python examples/crewai_agent.py              # 6 agents (défaut)
    python examples/crewai_agent.py --agents 10  # 10 agents
    python examples/crewai_agent.py --offline     # démo sans backend
"""
import asyncio
import random
import sys
import time
from dataclasses import dataclass
from typing import Optional

# ── Sigui ─────────────────────────────────────────────────────────────────────
from sigui import (
    SiguiClient,
    SiguiConnectionError,
    Verdict,
    EvaluationResult,
)
from sigui.models import EvaluationResult

try:
    from sigui.integrations.crewai import SiguiEvaluationTool
    CREWAI_TOOL_AVAILABLE = True
except ImportError:
    CREWAI_TOOL_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# Générateur de transactions — s'adapte à N agents
# ─────────────────────────────────────────────────────────────────────────────

# Pool d'agents nommés (mythologie Dogon, comme dans le projet)
AGENT_POOL = [
    ("agent_payer",    "🔥", "Danseur du Feu"),
    ("agent_attacker", "🦊", "Renard Pâle"),
    ("agent_monitor",  "👁", "Oeil de la Société"),
    ("agent_learner",  "⭐", "Etoile Apprenante"),
    ("agent_grayzone", "🌫", "Gray Zone"),
    ("agent_trader",   "💹", "Marchand des Sables"),
    ("agent_oracle",   "🔮", "Oracle Silencieux"),
    ("agent_bridge",   "🌉", "Pont des Etoiles"),
    ("agent_keeper",   "🛡", "Gardien des Seuils"),
    ("agent_nomad",    "🌍", "Nomade Inter-Chain"),
]

# Scénarios de transactions avec niveau de risque réaliste
TRANSACTION_TEMPLATES = [
    # (description, amount_range, destination_pattern, action_type, risk_level)
    ("API fee",            (0.001, 0.01),  "0xService{:04X}", "transfer",  "low"),
    ("Normal transfer",    (0.05,  0.25),  "0xPartner{:04X}", "transfer",  "low"),
    ("Large transfer",     (50.0,  500.0), "0xUnknown{:04X}", "transfer",  "high"),
    ("Micro-payment",      (0.001, 0.005), "0xSame{:04X}",    "transfer",  "medium"),
    ("Splitting tx 1/3",   (0.009, 0.011), "0xZero{:04X}",    "transfer",  "high"),
    ("Splitting tx 2/3",   (0.009, 0.011), "0xZero{:04X}",    "transfer",  "high"),
    ("Splitting tx 3/3",   (0.009, 0.011), "0xZero{:04X}",    "transfer",  "high"),
    ("Stake deposit",      (0.1,   1.0),   "0xStake{:04X}",   "stake",     "low"),
    ("DeFi swap",          (1.0,   10.0),  "0xDeFi{:04X}",    "swap",      "medium"),
    ("Cross-chain bridge", (5.0,   20.0),  "0xBridge{:04X}",  "bridge",    "medium"),
]


@dataclass
class SimulatedTransaction:
    agent_id: str
    agent_icon: str
    agent_name: str
    description: str
    amount: float
    destination: str
    action_type: str
    risk_level: str
    chain: str


def generate_transactions(n_agents: int, seed: int = 42) -> list[SimulatedTransaction]:
    """
    Génère une liste de transactions réalistes pour N agents.
    Garantit un mix de transactions légitimes et suspectes.
    """
    random.seed(seed)
    agents = AGENT_POOL[:n_agents]
    chains = ["arc", "arc", "arc", "ethereum", "solana"]  # Arc majoritaire

    transactions = []
    # Chaque agent génère 1-3 transactions
    for agent_id, icon, name in agents:
        n_tx = random.randint(1, 3)
        for _ in range(n_tx):
            tmpl = random.choice(TRANSACTION_TEMPLATES)
            desc, amount_range, dest_pattern, action_type, risk = tmpl
            amount = round(random.uniform(*amount_range), 4)
            dest_id = random.randint(0, 0xFFFF)
            destination = dest_pattern.format(dest_id)
            chain = random.choice(chains)
            transactions.append(SimulatedTransaction(
                agent_id=agent_id,
                agent_icon=icon,
                agent_name=name,
                description=desc,
                amount=amount,
                destination=destination,
                action_type=action_type,
                risk_level=risk,
                chain=chain,
            ))

    # Shuffle pour mélanger les agents
    random.shuffle(transactions)
    return transactions


# ─────────────────────────────────────────────────────────────────────────────
# Mode OFFLINE — résultats simulés localement (sans backend)
# ─────────────────────────────────────────────────────────────────────────────

def simulate_offline_result(tx: SimulatedTransaction) -> tuple[str, float, str]:
    """Simule un résultat de sécurité sans appel réseau."""
    risk_map = {"low": (0.05, 0.30), "medium": (0.35, 0.60), "high": (0.65, 0.95)}
    lo, hi = risk_map[tx.risk_level]
    risk = round(random.uniform(lo, hi), 3)
    if risk < 0.35:
        verdict, reason = "ALLOW", "Comportement normal"
    elif risk < 0.65:
        verdict, reason = "ESCALATE", "Zone grise — analyse approfondie"
    else:
        verdict, reason = "BLOCK", "Activité suspecte détectée"
    return verdict, risk, reason


# ─────────────────────────────────────────────────────────────────────────────
# Demo principale — N agents, mode online ou offline
# ─────────────────────────────────────────────────────────────────────────────

async def run_demo(n_agents: int = 6, offline: bool = False):
    print(f"\n{'='*65}")
    print(f"  Sigui SDK v0.1.0 — Multi-Agent Security Demo")
    print(f"  Agents: {n_agents} | Mode: {'OFFLINE (simule)' if offline else 'ONLINE (live API)'}")
    print(f"{'='*65}\n")

    transactions = generate_transactions(n_agents)
    total = len(transactions)
    print(f"  {total} transactions generees pour {n_agents} agents\n")

    # En-tête du tableau
    col = {"agent": 20, "desc": 22, "amount": 9, "chain": 7, "verdict": 11, "risk": 7}
    header = (
        f"{'Agent':<{col['agent']}} "
        f"{'Transaction':<{col['desc']}} "
        f"{'Amount':>{col['amount']}} "
        f"{'Chain':<{col['chain']}} "
        f"{'Verdict':<{col['verdict']}} "
        f"{'Risk':>{col['risk']}}"
    )
    print(header)
    print("─" * (sum(col.values()) + len(col)))

    # Compteurs
    allowed = blocked = escalated = 0
    total_protected_usdc = 0.0
    total_fees_usdc = 0.0
    latencies_ms = []

    async with SiguiClient(
        api_url="http://localhost:8000",
        agent_id="sigui_sdk_treasurer",
    ) as client:
        if CREWAI_TOOL_AVAILABLE:
            native_tool = SiguiEvaluationTool(
                sigui_client=client,
                auto_escalate=True,
            )
            preview = await native_tool._arun(
                destination="0xServiceBEEF",
                amount_usdc=0.01,
                chain="arc",
                action_type="transfer",
                reason="CrewAI native tool preview",
            )
            print(f"  CrewAI native tool preview: {preview}\n")

        for tx in transactions:
            agent_label = f"{tx.agent_icon} {tx.agent_name}"[:col['agent']]
            desc_label = tx.description[:col['desc']]
            chain_label = tx.chain[:col['chain']]
            amount_label = f"${tx.amount:.4f}"

            if offline:
                # Simulation locale — pas d'appel réseau
                t0 = time.perf_counter()
                verdict_str, risk, reason = simulate_offline_result(tx)
                latency = int((time.perf_counter() - t0) * 1000)
                fee = 0.001
            else:
                # Appel réel à l'API Sigui
                t0 = time.perf_counter()
                try:
                    result = await client.evaluate(
                        amount=tx.amount,
                        destination=tx.destination,
                        agent_id=tx.agent_id,
                        action_type=tx.action_type,
                        chain=tx.chain,
                    )
                    verdict_str = result.verdict.value
                    risk = result.risk_score
                    reason = result.reason
                    fee = result.evaluation_price_usdc
                    latency = result.processing_time_ms
                except SiguiConnectionError:
                    # Backend joignable mais occupé — fallback offline
                    verdict_str, risk, reason = simulate_offline_result(tx)
                    fee = 0.0
                    latency = int((time.perf_counter() - t0) * 1000)
                    print(f"  [WARN] Backend unreachable — offline fallback for {tx.agent_id}")

            icon = {"ALLOW": "OK ", "BLOCK": "KO ", "ESCALATE": "?? "}.get(verdict_str, "?  ")
            verdict_label = f"[{icon}] {verdict_str}"[:col['verdict']]

            print(
                f"{agent_label:<{col['agent']}} "
                f"{desc_label:<{col['desc']}} "
                f"{amount_label:>{col['amount']}} "
                f"{chain_label:<{col['chain']}} "
                f"{verdict_label:<{col['verdict']}} "
                f"{risk:>{col['risk']}.3f}"
            )

            if verdict_str == "ALLOW":
                allowed += 1
            elif verdict_str == "BLOCK":
                blocked += 1
                total_protected_usdc += tx.amount
            else:
                escalated += 1

            total_fees_usdc += fee
            latencies_ms.append(latency)

    # ── Résumé ────────────────────────────────────────────────────────────────
    print("─" * (sum(col.values()) + len(col)))
    avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0
    p99_latency = sorted(latencies_ms)[int(len(latencies_ms) * 0.99)] if latencies_ms else 0

    print(f"\n  Resultats pour {n_agents} agents — {total} transactions")
    print(f"  [OK]  Autorisees : {allowed:>4}  ({allowed/total*100:.1f}%)")
    print(f"  [KO]  Bloquees   : {blocked:>4}  ({blocked/total*100:.1f}%)  "
          f"— ${total_protected_usdc:.4f} USDC proteges")
    print(f"  [??]  Escaladees : {escalated:>4}  ({escalated/total*100:.1f}%)")
    print(f"\n  Latence avg    : {avg_latency:.1f}ms  |  p99: {p99_latency}ms")
    print(f"  Frais x402     : ${total_fees_usdc:.6f} USDC")
    print(f"\n  Demo terminee — SDK Sigui v0.1.0")
    print(f"{'='*65}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Entrée principale — parsing args minimal
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]
    offline = "--offline" in args
    n_agents = 6  # défaut

    for i, arg in enumerate(args):
        if arg == "--agents" and i + 1 < len(args):
            try:
                n_agents = max(1, min(len(AGENT_POOL), int(args[i + 1])))
            except ValueError:
                pass

    if n_agents > len(AGENT_POOL):
        print(f"[WARN] Max {len(AGENT_POOL)} agents disponibles. Utilisation de {len(AGENT_POOL)}.")
        n_agents = len(AGENT_POOL)

    asyncio.run(run_demo(n_agents=n_agents, offline=offline))
