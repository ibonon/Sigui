"""
sigui.integrations.elizaos — ElizaOS plugin for Sigui Protocol

Intègre la sécurité Sigui directement dans les agents construits avec ElizaOS.

Installation:
    pip install sigui-sdk[elizaos] ou npm install @elizaos/plugin-sigui

Usage:
    Ce module fournit l'implémentation backend côté Python pour l'intégration
    Node.js / Python hybride.

    ELIZAOS_CONFIG_EXAMPLE = '''
    {
      "name": "eliza-agent",
      "plugins": ["@elizaos/plugin-sigui"],
      "sigui": {
        "apiUrl": "http://localhost:8000",
        "agentId": "eliza_defi_bot",
        "chain": "ethereum",
        "raiseOnBlock": true
      }
    }
    '''
"""
from typing import Any, Dict, Optional

from ..client import SiguiClient
from ..models import EvaluationResult


class SiguiElizaAction:
    """Action standard ElizaOS pour évaluer une transaction via Sigui."""

    name = "EVALUATE_TRANSACTION_SECURITY"
    description = "Evaluates the security and risk of a blockchain transaction before execution using Sigui Protocol."

    def __init__(self, client: SiguiClient):
        self.client = client

    async def run(self, context: Dict[str, Any], message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Exécute l'évaluation Sigui à partir d'un contexte ElizaOS.
        
        Args:
            context: Le state/context de l'agent ElizaOS
            message: Le message contenant les détails de la transaction (amount, destination)
            
        Returns:
            Dict formaté pour ElizaOS contenant le verdict.
        """
        amount = float(message.get("amount", 0.0))
        destination = message.get("destination", "")
        action_type = message.get("actionType", "transfer")

        if not destination:
            return {
                "success": False,
                "error": "Missing 'destination' in transaction request"
            }

        try:
            result: EvaluationResult = await self.client.evaluate(
                amount=amount,
                destination=destination,
                action_type=action_type,
                context={"eliza_context_id": context.get("id")}
            )
            
            return {
                "success": True,
                "verdict": result.verdict.value,
                "is_safe": result.is_safe,
                "risk_score": result.risk_score,
                "reason": result.reason,
                "action_hash": result.action_hash
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class SiguiElizaPlugin:
    """Plugin ElizaOS principal."""
    
    name = "sigui-security"
    description = "Sigui Protocol security oracle for transaction protection"

    def __init__(self, api_url: str = "http://localhost:8000", agent_id: str = "eliza"):
        self.client = SiguiClient(api_url=api_url, agent_id=agent_id)
        self.actions = [
            SiguiElizaAction(self.client)
        ]

    async def get_actions(self):
        return self.actions

    async def stop(self):
        await self.client.close()
