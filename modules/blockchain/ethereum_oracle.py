"""
Oracle Ethereum pour la surveillance cross-chain.
Surveille les transactions, smart contracts et activités suspectes sur Ethereum.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_abi import abi
from eth_utils import to_checksum_address

from ..config import settings

logger = logging.getLogger(__name__)


class EthereumOracle:
    """Oracle pour la surveillance Ethereum."""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.ETHEREUM_RPC_URL
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Ajouter le middleware pour les réseaux PoA
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Adresses des contrats à surveiller
        self.monitored_contracts = {
            "tornado_cash": "0x12D66f87A04A9E220743712cE6d9bB1B5616B8Fc",
            "uniswap_v2": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "aave_v2": "0x7d2768dE32b0b80b7a3454c06BdAc94A69DDc7A9",
            "compound_v2": "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B",
        }
        
        # Patterns de transactions suspectes
        self.suspicious_patterns = [
            {"name": "tornado_cash_mix", "signature": "0x21a0adb6"},
            {"name": "flash_loan_attack", "signature": "0x5cffe9de"},
            {"name": "reentrancy", "signature": "0xf340fa01"},
            {"name": "front_running", "signature": "0x1cff79cd"},
        ]
        
        logger.info(f"Ethereum Oracle initialisé sur {self.rpc_url}")
    
    async def monitor_block(self, block_number: int) -> List[Dict[str, Any]]:
        """Surveille un bloc spécifique pour détecter des activités suspectes."""
        threats = []
        
        try:
            block = self.web3.eth.get_block(block_number, full_transactions=True)
            
            for tx in block.transactions:
                # Analyser chaque transaction
                tx_threats = await self._analyze_transaction(tx, block)
                threats.extend(tx_threats)
                
                # Surveiller les interactions avec les contrats
                if tx.get("to") and tx["to"] in self.monitored_contracts.values():
                    contract_threats = await self._analyze_contract_interaction(tx)
                    threats.extend(contract_threats)
        
        except Exception as e:
            logger.error(f"Erreur lors de la surveillance du bloc {block_number}: {e}")
        
        return threats
    
    async def _analyze_transaction(self, tx: Dict, block: Dict) -> List[Dict[str, Any]]:
        """Analyse une transaction pour détecter des patterns suspects."""
        threats = []
        
        # Vérifier les montants élevés
        value_eth = self.web3.from_wei(tx.get("value", 0), "ether")
        if value_eth > 100:  # Plus de 100 ETH
            threats.append({
                "type": "HIGH_VALUE_TRANSACTION",
                "severity": "MEDIUM",
                "description": f"Transaction de {value_eth} ETH détectée",
                "tx_hash": tx["hash"].hex(),
                "from": tx["from"],
                "to": tx.get("to"),
                "value_eth": float(value_eth),
                "block_number": block["number"],
                "timestamp": datetime.fromtimestamp(block["timestamp"]),
            })
        
        # Vérifier les patterns de signature
        if tx.get("input") and tx["input"] != "0x":
            for pattern in self.suspicious_patterns:
                if pattern["signature"] in tx["input"][:10]:
                    threats.append({
                        "type": "SUSPICIOUS_PATTERN",
                        "severity": "HIGH",
                        "description": f"Pattern {pattern['name']} détecté",
                        "tx_hash": tx["hash"].hex(),
                        "from": tx["from"],
                        "to": tx.get("to"),
                        "pattern": pattern["name"],
                        "block_number": block["number"],
                        "timestamp": datetime.fromtimestamp(block["timestamp"]),
                    })
        
        # Vérifier les adresses nouvellement créées
        if not tx.get("to") and tx.get("contractAddress"):
            threats.append({
                "type": "CONTRACT_CREATION",
                "severity": "LOW",
                "description": "Nouveau contrat créé",
                "tx_hash": tx["hash"].hex(),
                "from": tx["from"],
                "contract_address": tx["contractAddress"],
                "block_number": block["number"],
                "timestamp": datetime.fromtimestamp(block["timestamp"]),
            })
        
        return threats
    
    async def _analyze_contract_interaction(self, tx: Dict) -> List[Dict[str, Any]]:
        """Analyse les interactions avec les contrats surveillés."""
        threats = []
        
        # Décoder l'input de la transaction
        if not tx.get("input") or tx["input"] == "0x":
            return threats
        
        try:
            # Pour Tornado Cash, vérifier les mix
            if tx["to"] == self.monitored_contracts["tornado_cash"]:
                if "deposit" in tx["input"] or "withdraw" in tx["input"]:
                    threats.append({
                        "type": "PRIVACY_PROTOCOL_INTERACTION",
                        "severity": "HIGH",
                        "description": "Interaction avec Tornado Cash détectée",
                        "tx_hash": tx["hash"].hex(),
                        "from": tx["from"],
                        "protocol": "Tornado Cash",
                        "action": "deposit/withdraw",
                    })
            
            # Pour Uniswap, vérifier les flash swaps
            elif tx["to"] == self.monitored_contracts["uniswap_v2"]:
                if "swap" in tx["input"]:
                    # Vérifier les montants importants
                    threats.append({
                        "type": "DEX_INTERACTION",
                        "severity": "MEDIUM",
                        "description": "Swap important sur Uniswap",
                        "tx_hash": tx["hash"].hex(),
                        "from": tx["from"],
                        "protocol": "Uniswap V2",
                        "action": "swap",
                    })
            
            # Pour Aave, vérifier les flash loans
            elif tx["to"] == self.monitored_contracts["aave_v2"]:
                if "flashLoan" in tx["input"]:
                    threats.append({
                        "type": "FLASH_LOAN",
                        "severity": "HIGH",
                        "description": "Flash loan sur Aave détecté",
                        "tx_hash": tx["hash"].hex(),
                        "from": tx["from"],
                        "protocol": "Aave V2",
                        "action": "flashLoan",
                    })
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de l'interaction: {e}")
        
        return threats
    
    async def get_address_risk_score(self, address: str) -> Dict[str, Any]:
        """Calcule un score de risque pour une adresse Ethereum."""
        try:
            checksum_address = to_checksum_address(address)
            
            # Récupérer les transactions
            tx_count = self.web3.eth.get_transaction_count(checksum_address)
            balance = self.web3.eth.get_balance(checksum_address)
            balance_eth = self.web3.from_wei(balance, "ether")
            
            # Calculer le score de risque
            risk_score = 0.0
            
            # Facteurs de risque
            if tx_count < 10:
                risk_score += 0.3  # Nouvelle adresse
            
            if balance_eth > 1000:
                risk_score += 0.2  # Gros portefeuille
            
            # Vérifier les interactions avec des contrats à risque
            # (simplifié pour l'exemple)
            
            return {
                "address": checksum_address,
                "risk_score": min(risk_score, 1.0),
                "transaction_count": tx_count,
                "balance_eth": float(balance_eth),
                "is_contract": await self._is_contract(checksum_address),
                "last_active": await self._get_last_active(checksum_address),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul du score de risque: {e}")
            return {
                "address": address,
                "risk_score": 0.5,
                "error": str(e),
            }
    
    async def _is_contract(self, address: str) -> bool:
        """Vérifie si une adresse est un contrat."""
        try:
            code = self.web3.eth.get_code(address)
            return len(code) > 2
        except:
            return False
    
    async def _get_last_active(self, address: str) -> Optional[datetime]:
        """Récupère la dernière activité d'une adresse."""
        try:
            # Récupérer le dernier bloc avec une transaction
            # (simplifié pour l'exemple)
            return datetime.now() - timedelta(days=1)
        except:
            return None
    
    async def start_monitoring(self, callback):
        """Démarre la surveillance en temps réel."""
        logger.info("Démarrage de la surveillance Ethereum en temps réel")
        
        last_block = self.web3.eth.block_number
        
        while True:
            try:
                current_block = self.web3.eth.block_number
                
                if current_block > last_block:
                    for block_num in range(last_block + 1, current_block + 1):
                        threats = await self.monitor_block(block_num)
                        
                        if threats:
                            await callback({
                                "chain": "ethereum",
                                "block_number": block_num,
                                "threats": threats,
                                "timestamp": datetime.now(),
                            })
                    
                    last_block = current_block
                
                await asyncio.sleep(1)  # Vérifier toutes les secondes
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance: {e}")
                await asyncio.sleep(5)