"""
Intégration Aave pour la surveillance des flash loans et positions.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from web3 import Web3
from web3.middleware import geth_poa_middleware

from ..config import settings

logger = logging.getLogger(__name__)


class AaveIntegration:
    """Intégration avec le protocole Aave."""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.ETHEREUM_RPC_URL
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Contrats Aave V3
        self.pool_address = "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2"
        self.oracle_address = "0x54586bE62E3c3580375aE3723C145253060Ca0C2"
        
        # ABI simplifié pour les fonctions principales
        self.pool_abi = [
            {
                "name": "flashLoan",
                "type": "function",
                "inputs": [
                    {"name": "receiver", "type": "address"},
                    {"name": "assets", "type": "address[]"},
                    {"name": "amounts", "type": "uint256[]"},
                    {"name": "modes", "type": "uint256[]"},
                    {"name": "onBehalfOf", "type": "address"},
                    {"name": "params", "type": "bytes"},
                    {"name": "referralCode", "type": "uint16"}
                ],
                "outputs": [],
                "stateMutability": "nonpayable"
            },
            {
                "name": "getUserAccountData",
                "type": "function",
                "inputs": [{"name": "user", "type": "address"}],
                "outputs": [
                    {"name": "totalCollateralBase", "type": "uint256"},
                    {"name": "totalDebtBase", "type": "uint256"},
                    {"name": "availableBorrowsBase", "type": "uint256"},
                    {"name": "currentLiquidationThreshold", "type": "uint256"},
                    {"name": "ltv", "type": "uint256"},
                    {"name": "healthFactor", "type": "uint256"}
                ],
                "stateMutability": "view"
            }
        ]
        
        self.pool_contract = self.web3.eth.contract(
            address=self.pool_address,
            abi=self.pool_abi
        )
        
        logger.info("Intégration Aave initialisée")
    
    async def monitor_flash_loans(self, callback) -> None:
        """Surveille les flash loans Aave en temps réel."""
        logger.info("Démarrage de la surveillance des flash loans Aave")
        
        last_block = self.web3.eth.block_number
        
        while True:
            try:
                current_block = self.web3.eth.block_number
                
                if current_block > last_block:
                    for block_num in range(last_block + 1, current_block + 1):
                        await self._check_block_for_flash_loans(block_num, callback)
                    
                    last_block = current_block
                
                await asyncio.sleep(2)
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance Aave: {e}")
                await asyncio.sleep(10)
    
    async def _check_block_for_flash_loans(self, block_number: int, callback) -> None:
        """Vérifie un bloc pour les flash loans."""
        try:
            block = self.web3.eth.get_block(block_number, full_transactions=True)
            
            for tx in block.transactions:
                # Vérifier les appels à flashLoan
                if tx.get("to") == self.pool_address and tx.get("input"):
                    input_data = tx["input"]
                    
                    if input_data.startswith("0x5cffe9de"):  # Signature de flashLoan
                        await self._analyze_flash_loan(tx, block, callback)
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du bloc {block_number}: {e}")
    
    async def _analyze_flash_loan(self, tx: Dict, block: Dict, callback) -> None:
        """Analyse un flash loan Aave."""
        try:
            # Décoder les paramètres du flash loan
            # (simplifié pour l'exemple)
            assets = ["0x..."]  # Adresses des tokens
            amounts = [self.web3.from_wei(tx.get("value", 0), "ether")]
            
            # Calculer le risque
            risk_score = self._calculate_flash_loan_risk(tx, amounts)
            
            alert = {
                "type": "AAVE_FLASH_LOAN",
                "severity": "HIGH" if risk_score > 0.7 else "MEDIUM",
                "description": f"Flash loan Aave de {amounts[0]} ETH détecté",
                "tx_hash": tx["hash"].hex(),
                "from": tx["from"],
                "to": tx.get("to"),
                "amount_eth": float(amounts[0]),
                "block_number": block["number"],
                "timestamp": datetime.fromtimestamp(block["timestamp"]),
                "risk_score": risk_score,
                "recommendations": [
                    "Surveiller les interactions suivantes avec les DEX",
                    "Vérifier les patterns d'arbitrage",
                    "Analyser les liquidations potentielles"
                ]
            }
            
            await callback(alert)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du flash loan: {e}")
    
    def _calculate_flash_loan_risk(self, tx: Dict, amounts: List[float]) -> float:
        """Calcule le score de risque d'un flash loan."""
        risk_score = 0.0
        
        # Montant élevé
        if amounts[0] > 1000:  # Plus de 1000 ETH
            risk_score += 0.4
        
        # Nouvelle adresse
        tx_count = self.web3.eth.get_transaction_count(tx["from"])
        if tx_count < 10:
            risk_score += 0.3
        
        # Heure de la journée (nuit = plus risqué)
        hour = datetime.now().hour
        if 0 <= hour < 6:  # Entre minuit et 6h
            risk_score += 0.2
        
        return min(risk_score, 1.0)
    
    async def get_user_position(self, address: str) -> Dict[str, Any]:
        """Récupère la position d'un utilisateur sur Aave."""
        try:
            checksum_address = self.web3.to_checksum_address(address)
            
            # Récupérer les données du compte
            account_data = self.pool_contract.functions.getUserAccountData(
                checksum_address
            ).call()
            
            # Convertir les valeurs
            total_collateral = self.web3.from_wei(account_data[0], "ether")
            total_debt = self.web3.from_wei(account_data[1], "ether")
            available_borrows = self.web3.from_wei(account_data[2], "ether")
            liquidation_threshold = account_data[3] / 100  # Pourcentage
            ltv = account_data[4] / 100  # Pourcentage
            health_factor = account_data[5] / 1e18
            
            return {
                "address": checksum_address,
                "total_collateral_eth": float(total_collateral),
                "total_debt_eth": float(total_debt),
                "available_borrows_eth": float(available_borrows),
                "liquidation_threshold_percent": float(liquidation_threshold),
                "loan_to_value_percent": float(ltv),
                "health_factor": float(health_factor),
                "at_risk": health_factor < 1.5,
                "last_updated": datetime.now(),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la position: {e}")
            return {
                "address": address,
                "error": str(e),
                "last_updated": datetime.now(),
            }
    
    async def get_protocol_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du protocole Aave."""
        try:
            # Récupérer le prix ETH via l'oracle
            # (simplifié pour l'exemple)
            eth_price = 3500.0  # Prix simulé en USD
            
            # Calculer les métriques
            total_value_locked = 15_000_000.0  # 15M ETH TVL simulé
            total_borrowed = 3_000_000.0  # 3M ETH empruntés
            
            utilization_rate = total_borrowed / total_value_locked if total_value_locked > 0 else 0
            
            return {
                "total_value_locked_usd": total_value_locked * eth_price,
                "total_borrowed_usd": total_borrowed * eth_price,
                "utilization_rate_percent": float(utilization_rate * 100),
                "eth_price_usd": eth_price,
                "average_apy_percent": 4.2,
                "flash_loan_fee_percent": 0.09,
                "last_updated": datetime.now(),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des métriques: {e}")
            return {
                "error": str(e),
                "last_updated": datetime.now(),
            }
    
    async def check_liquidation_risk(self, address: str) -> Dict[str, Any]:
        """Vérifie le risque de liquidation pour une adresse."""
        try:
            position = await self.get_user_position(address)
            
            if "error" in position:
                return position
            
            risk_level = "LOW"
            if position["health_factor"] < 1.0:
                risk_level = "CRITICAL"
            elif position["health_factor"] < 1.2:
                risk_level = "HIGH"
            elif position["health_factor"] < 1.5:
                risk_level = "MEDIUM"
            
            liquidation_price = 0.0
            if position["total_collateral_eth"] > 0:
                liquidation_price = (
                    position["total_debt_eth"] * position["liquidation_threshold_percent"] / 100
                ) / position["total_collateral_eth"]
            
            return {
                "address": address,
                "risk_level": risk_level,
                "health_factor": position["health_factor"],
                "liquidation_price_eth": float(liquidation_price),
                "current_eth_price": 3500.0,  # Simulé
                "margin_of_safety_percent": float(
                    (position["health_factor"] - 1.0) * 100
                    if position["health_factor"] > 1.0 else 0
                ),
                "recommendations": self._generate_liquidation_recommendations(risk_level),
                "last_updated": datetime.now(),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du risque: {e}")
            return {
                "address": address,
                "error": str(e),
                "last_updated": datetime.now(),
            }
    
    def _generate_liquidation_recommendations(self, risk_level: str) -> List[str]:
        """Génère des recommandations basées sur le niveau de risque."""
        recommendations = {
            "CRITICAL": [
                "Ajouter du collatéral immédiatement",
                "Rembourser une partie de la dette",
                "Considérer la liquidation comme imminente"
            ],
            "HIGH": [
                "Surveiller le prix du collatéral",
                "Préparer des fonds pour ajouter du collatéral",
                "Éviter de prendre plus de dette"
            ],
            "MEDIUM": [
                "Maintenir une marge de sécurité",
                "Surveiller les ratios de santé",
                "Planifier des actions en cas de baisse de prix"
            ],
            "LOW": [
                "Continuer la surveillance régulière",
                "Maintenir des pratiques de gestion de risque"
            ]
        }
        
        return recommendations.get(risk_level, ["Surveillance continue"])