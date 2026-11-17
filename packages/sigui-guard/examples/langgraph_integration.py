"""
Exemple d'intégration LangGraph — sigui-guard.

Deux usages conformes à la documentation officielle LangGraph actuelle
(« Call tools ») : https://docs.langchain.com/oss/python/langgraph/use-tools

  1. Un **noeud de graphe** (``StateGraph``) qui rend un verdict pour l'action
     courante — le garde-fou s'insère directement dans le workflow.
  2. Un **outil LangChain** (``@tool``) consommable par ``ToolNode`` ou
     ``create_react_agent``.

Installation :
    pip install ./packages/sigui-guard
    pip install langgraph langchain-core

Run :
    python packages/sigui-guard/examples/langgraph_integration.py

Aucun LLM n'est requis : le graphe et l'outil sont invoqués directement, ce qui
prouve que l'intégration compile et rend un vrai verdict.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph

from sigui_guard import check_action

TRUSTED = "0x1111222233334444555566667777888899990000"
UNKNOWN = "0xabc12345678901234567890123456789012345678"


class ActionState(TypedDict):
    """État du graphe : l'action soumise, puis le verdict rendu."""

    action_type: str
    amount_usd: float
    destination: str
    decision: str
    blocked: bool


def sigui_guard_node(state: ActionState) -> dict:
    """Noeud de graphe : rend le verdict sigui-guard pour l'action courante."""
    verdict = check_action(
        state["action_type"],
        amount_usd=state["amount_usd"],
        destination=state["destination"],
    )
    return {"decision": verdict.decision, "blocked": verdict.blocked}


def build_graph():
    builder = StateGraph(ActionState)
    builder.add_node("sigui_guard", sigui_guard_node)
    builder.add_edge(START, "sigui_guard")
    builder.add_edge("sigui_guard", END)
    return builder.compile()


@tool
def sigui_guard_check(
    action_type: str = "transfer",
    amount_usd: float = 0.0,
    destination: str = "",
) -> str:
    """Vérifie la sécurité d'une action d'agent avant exécution (ALLOW/BLOCK/ESCALATE)."""
    verdict = check_action(action_type, amount_usd=amount_usd, destination=destination)
    return f"{verdict.decision} (blocked={verdict.blocked})"


def main() -> None:
    graph = build_graph()

    safe = graph.invoke(
        {"action_type": "transfer", "amount_usd": 5.0, "destination": TRUSTED,
         "decision": "", "blocked": False}
    )
    risky = graph.invoke(
        {"action_type": "transfer", "amount_usd": 500.0, "destination": UNKNOWN,
         "decision": "", "blocked": False}
    )

    print("Noeud LangGraph (action sûre)    ->", safe["decision"], "blocked =", safe["blocked"])
    print("Noeud LangGraph (action risquée) ->", risky["decision"], "blocked =", risky["blocked"])
    print("Outil LangChain  (appel direct)  ->",
          sigui_guard_check.invoke({"action_type": "transfer", "amount_usd": 500.0, "destination": UNKNOWN}))


if __name__ == "__main__":
    main()
