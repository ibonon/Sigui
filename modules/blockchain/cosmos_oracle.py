"""
Oracle Cosmos pour la surveillance cross-chain.
Surveille les transactions, IBC transfers et activités suspectes sur Cosmos SDK chains.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import base64
import hashlib

import aiohttp
from cosmpy.aerial.client import LedgerClient
from cosmpy.aerial.config import NetworkConfig
from cosmpy.crypto.address import Address
from cosmpy.protos.cosmos.base.v1beta1.coin_pb2 import Coin

from ..config import settings

logger = logging.getLogger(__name__)


class CosmosOracle:
    """Oracle pour la surveillance Cosmos."""
    
    def __init__(self, rpc_url: Optional[str] = None, chain_id: str = "cosmoshub-4"):
        self.rpc_url = rpc_url or settings.COSMOS_RPC_URL
        self.chain_id = chain_id
        
        # Configuration du réseau
        self.network_config = NetworkConfig(
            chain_id=chain_id,
            url="grpc+http://localhost:9090",  # URL gRPC
            fee_minimum_gas_price=0.025,
            fee_denomination="uatom",
            staking_denomination="uatom",
        )
        
        self.client = LedgerClient(self.network_config)
        
        # Chaînes IBC à surveiller
        self.ibc_channels = {
            "osmosis": "channel-0",
            "juno": "channel-1",
            "axelar": "channel-2",
            "stargaze": "channel-3",
        }
        
        # Patterns de transactions suspectes
        self.suspicious_patterns = [
            {"name": "large_ibc_transfer", "threshold": 1000},  # 1000 ATOM
            {"name": "governance_spam", "threshold": 10},  # 10 propositions
            {"name": "validator_slashing", "description": "Slashing de validateur"},
            {"name": "dust_attack", "threshold": 0.001},  # 0.001 ATOM
        ]
        
        logger.info(f"Cosmos Oracle initialisé pour {chain_id} sur {self.rpc_url}")
    
    async def monitor_block(self, height: int) -> List[Dict[str, Any]]:
        """Surveille un bloc spécifique pour détecter des activités suspectes."""
        threats = []
        
        try:
            # Récupérer le bloc via l'API REST
            async with aiohttp.ClientSession() as session:
                url = f"{self.rpc_url}/block?height={height}"
                async with session.get(url) as response:
                    if response.status == 200:
                        block_data = await response.json()
                        
                        # Analyser les transactions du bloc
                        if "block" in block_data and "data" in block_data["block"]:
                            txs = block_data["block"]["data"]["txs"]
                            
                            for tx_base64 in txs:
                                if tx_base64:
                                    tx_threats = await self._analyze_transaction(
                                        tx_base64, height
                                    )
                                    threats.extend(tx_threats)
        
        except Exception as e:
            logger.error(f"Erreur lors de la surveillance du bloc {height}: {e}")
        
        return threats
    
    async def _analyze_transaction(self, tx_base64: str, height: int) -> List[Dict[str, Any]]:
        """Analyse une transaction Cosmos pour détecter des patterns suspects."""
        threats = []
        
        try:
            # Décoder la transaction
            tx_bytes = base64.b64decode(tx_base64)
            
            # Pour l'exemple, on simule l'analyse
            # En réalité, il faudrait parser le protobuf
            
            # Vérifier la taille de la transaction
            tx_size = len(tx_bytes)
            if tx_size > 10000:  # Transaction très grande
                threats.append({
                    "type": "LARGE_TRANSACTION",
                    "severity": "LOW",
                    "description": f"Transaction de {tx_size} bytes détectée",
                    "height": height,
                    "tx_size": tx_size,
                    "timestamp": datetime.now(),
                })
            
            # Calculer le hash de la transaction
            tx_hash = hashlib.sha256(tx_bytes).hexdigest()
            
            # Vérifier les patterns via l'API REST
            async with aiohttp.ClientSession() as session:
                # Récupérer les détails de la transaction
                tx_url = f"{self.rpc_url}/tx?hash=0x{tx_hash}"
                async with session.get(tx_url) as response:
                    if response.status == 200:
                        tx_details = await response.json()
                        
                        # Analyser les messages
                        if "tx" in tx_details and "body" in tx_details["tx"]:
                            messages = tx_details["tx"]["body"]["messages"]
                            
                            for msg in messages:
                                msg_threats = await self._analyze_message(msg, tx_hash, height)
                                threats.extend(msg_threats)
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la transaction: {e}")
        
        return threats
    
    async def _analyze_message(self, msg: Dict, tx_hash: str, height: int) -> List[Dict[str, Any]]:
        """Analyse un message Cosmos SDK."""
        threats = []
        
        msg_type = msg.get("@type", "")
        
        # Transfert bancaire
        if "/cosmos.bank.v1beta1.MsgSend" in msg_type:
            amount = msg.get("amount", [])
            
            for coin in amount:
                denom = coin.get("denom", "")
                amount_str = coin.get("amount", "0")
                
                try:
                    amount_val = float(amount_str) / 1_000_000  # Convertir uatom en ATOM
                    
                    if denom == "uatom" and amount_val > 1000:
                        threats.append({
                            "type": "LARGE_TRANSFER",
                            "severity": "MEDIUM",
                            "description": f"Transfert de {amount_val} ATOM détecté",
                            "tx_hash": tx_hash,
                            "from": msg.get("from_address", ""),
                            "to": msg.get("to_address", ""),
                            "amount_atom": amount_val,
                            "height": height,
                            "timestamp": datetime.now(),
                        })
                
                except ValueError:
                    pass
        
        # Transfert IBC
        elif "/ibc.applications.transfer.v1.MsgTransfer" in msg_type:
            token = msg.get("token", {})
            amount_str = token.get("amount", "0")
            
            try:
                amount_val = float(amount_str) / 1_000_000
                
                if amount_val > 500:  # 500 ATOM via IBC
                    threats.append({
                        "type": "LARGE_IBC_TRANSFER",
                        "severity": "HIGH",
                        "description": f"Transfert IBC de {amount_val} ATOM détecté",
                        "tx_hash": tx_hash,
                        "source_channel": msg.get("source_channel", ""),
                        "receiver": msg.get("receiver", ""),
                        "amount_atom": amount_val,
                        "height": height,
                        "timestamp": datetime.now(),
                    })
            
            except ValueError:
                pass
        
        # Vote de gouvernance
        elif "/cosmos.gov.v1beta1.MsgVote" in msg_type:
            # Vérifier les votes multiples
            threats.append({
                "type": "GOVERNANCE_VOTE",
                "severity": "LOW",
                "description": "Vote de gouvernance détecté",
                "tx_hash": tx_hash,
                "voter": msg.get("voter", ""),
                "proposal_id": msg.get("proposal_id", ""),
                "option": msg.get("option", ""),
                "height": height,
                "timestamp": datetime.now(),
            })
        
        # Délégation
        elif "/cosmos.staking.v1beta1.MsgDelegate" in msg_type:
            amount = msg.get("amount", {})
            amount_str = amount.get("amount", "0")
            
            try:
                amount_val = float(amount_str) / 1_000_000
                
                if amount_val > 10000:  # 10,000 ATOM de délégation
                    threats.append({
                        "type": "LARGE_DELEGATION",
                        "severity": "MEDIUM",
                        "description": f"Délégation de {amount_val} ATOM détectée",
                        "tx_hash": tx_hash,
                        "delegator_address": msg.get("delegator_address", ""),
                        "validator_address": msg.get("validator_address", ""),
                        "amount_atom": amount_val,
                        "height": height,
                        "timestamp": datetime.now(),
                    })
            
            except ValueError:
                pass
        
        return threats
    
    async def get_address_risk_score(self, address: str) -> Dict[str, Any]:
        """Calcule un score de risque pour une adresse Cosmos."""
        try:
            cosmos_address = Address(address)
            
            # Récupérer le solde
            balance = await self.client.query_bank_all_balances(cosmos_address)
            
            # Convertir en ATOM
            atom_balance = 0.0
            for coin in balance:
                if coin.denom == "uatom":
                    atom_balance = float(coin.amount) / 1_000_000
                    break
            
            # Récupérer les délégations
            delegations = await self.client.query_staking_delegations(cosmos_address)
            total_delegated = sum(
                float(del.balance.amount) / 1_000_000 
                for del in delegations
                if del.balance.denom == "uatom"
            )
            
            # Récupérer les transactions récentes
            # (simplifié pour l'exemple)
            
            # Calculer le score de risque
            risk_score = 0.0
            
            # Facteurs de risque
            if atom_balance < 1.0 and total_delegated < 1.0:
                risk_score += 0.4  # Adresse avec peu de fonds
            
            if atom_balance > 10000:
                risk_score += 0.2  # Gros portefeuille
            
            # Vérifier si c'est un validateur
            is_validator = False
            try:
                validator = await self.client.query_staking_validator(cosmos_address)
                is_validator = True
            except:
                pass
            
            if is_validator:
                risk_score -= 0.1  # Les validateurs sont généralement plus fiables
            
            return {
                "address": address,
                "risk_score": max(0.0, min(risk_score, 1.0)),
                "balance_atom": atom_balance,
                "delegated_atom": total_delegated,
                "is_validator": is_validator,
                "total_balance_atom": atom_balance + total_delegated,
                "last_active": await self._get_last_active(address),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul du score de risque: {e}")
            return {
                "address": address,
                "risk_score": 0.5,
                "error": str(e),
            }
    
    async def _get_last_active(self, address: str) -> Optional[datetime]:
        """Récupère la dernière activité d'une adresse."""
        try:
            # Via l'API REST
            async with aiohttp.ClientSession() as session:
                url = f"{self.rpc_url}/cosmos/tx/v1beta1/txs?events=message.sender='{address}'&limit=1&order_by=ORDER_BY_DESC"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("txs") and len(data["txs"]) > 0:
                            tx = data["txs"][0]
                            timestamp = tx.get("timestamp", "")
                            if timestamp:
                                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            return None
        except:
            return None
    
    async def start_monitoring(self, callback):
        """Démarre la surveillance en temps réel."""
        logger.info(f"Démarrage de la surveillance Cosmos ({self.chain_id}) en temps réel")
        
        last_height = await self._get_latest_block_height()
        
        while True:
            try:
                current_height = await self._get_latest_block_height()
                
                if current_height > last_height:
                    # Surveiller les nouveaux blocs
                    for height in range(last_height + 1, current_height + 1):
                        threats = await self.monitor_block(height)
                        
                        if threats:
                            await callback({
                                "chain": self.chain_id,
                                "height": height,
                                "threats": threats,
                                "timestamp": datetime.now(),
                            })
                    
                    last_height = current_height
                
                await asyncio.sleep(3)  # Vérifier toutes les 3 secondes
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance: {e}")
                await asyncio.sleep(10)
    
    async def _get_latest_block_height(self) -> int:
        """Récupère la hauteur du dernier bloc."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.rpc_url}/blocks/latest"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return int(data["block"]["header"]["height"])
            return 0
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la hauteur: {e}")
            return 0
