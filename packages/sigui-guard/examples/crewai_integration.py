"""
Exemple d'intégration CrewAI — sigui-guard.

Expose ``check_action()`` comme un **outil CrewAI natif** (``crewai.tools.BaseTool``),
que n'importe quel agent peut appeler avant une action sensible.

Syntaxe conforme à la documentation officielle CrewAI actuelle
(« Create Custom Tools » → Subclassing ``BaseTool``) :
    https://docs.crewai.com/en/learn/create-custom-tools

Installation :
    pip install ./packages/sigui-guard
    pip install crewai

Run :
    python packages/sigui-guard/examples/crewai_integration.py

Aucun LLM ni clé API n'est requis pour lancer ce fichier : l'outil est invoqué
directement, ce qui prouve que l'intégration compile et rend un vrai verdict.

Utilisation dans un vrai crew :

    from crewai import Agent
    agent = Agent(
        role="Payment Agent",
        goal="Pay approved invoices",
        tools=[SiguiGuardTool()],   # <- le garde-fou
        backstory="...",
    )
"""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from sigui_guard import check_action

TRUSTED = "0x1111222233334444555566667777888899990000"
UNKNOWN = "0xabc12345678901234567890123456789012345678"


class SiguiGuardInput(BaseModel):
    """Schéma d'entrée de l'outil (validé par CrewAI/pydantic)."""

    action_type: str = Field(default="transfer", description="transfer, swap, contract_interaction, ...")
    amount_usd: float = Field(default=0.0, description="Montant de l'action, en USD")
    destination: str = Field(default="", description="Adresse ou identifiant de la cible")


class SiguiGuardTool(BaseTool):
    """Rend un verdict de sécurité hors ligne pour une action d'agent."""

    name: str = "sigui_guard_check"
    description: str = (
        "Vérifie la sécurité d'une action (transfert, swap, interaction de contrat) "
        "AVANT de l'exécuter. Renvoie ALLOW, BLOCK ou ESCALATE avec la raison."
    )
    args_schema: type[BaseModel] = SiguiGuardInput

    def _run(
        self,
        action_type: str = "transfer",
        amount_usd: float = 0.0,
        destination: str = "",
    ) -> str:
        verdict = check_action(action_type, amount_usd=amount_usd, destination=destination)
        return f"{verdict.decision} (blocked={verdict.blocked}) - {verdict.reason}"


def main() -> None:
    tool = SiguiGuardTool()
    print("Outil disponible pour l'agent :", tool.name)
    print("  action sûre   ->", tool._run("transfer", 5.0, TRUSTED))
    print("  action risquée ->", tool._run("transfer", 500.0, UNKNOWN))


if __name__ == "__main__":
    main()
