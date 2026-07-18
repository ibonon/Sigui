"""
Oracle Plutus pour Sigui - Surveillance des smart contracts Cardano
"""

import asyncio
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import json
import logging

from .cardano_adapter import CardanoAdapter, CardanoTransaction
from ...reputation.reputation_oracle import ReputationOracle


logger = logging.getLogger(__name__)


@dataclass
class PlutusContractEvent:
    """Événement de contrat Plutus"""
    contract_id: str
    tx_hash: str
    action: str
    timestamp: int
    caller_did: Optional[str] = None
    parameters: Optional[Dict] = None
    result: Optional[Dict] = None
    metadata: Optional[Dict] = None


class PlutusOracle:
    """Oracle pour surveiller et exécuter les contrats Plutus"""
    
    def __init__(self, cardano_adapter: CardanoAdapter, reputation_oracle: ReputationOracle):
        self.cardano_adapter = cardano_adapter
        self.reputation_oracle = reputation_oracle
        self._active_contracts: Dict[str, Dict] = {}
        self._contract_events: Dict[str, List[PlutusContractEvent]] = {}
        self._monitoring_tasks: List[asyncio.Task] = []
        self._callbacks: List[callable] = []
        
    async def initialize(self) -> bool:
        """Initialise l'oracle Plutus"""
        try:
            # Vérifie que Plutus est activé
            if not self.cardano_adapter.config.plutus_enabled:
                logger.warning("Plutus désactivé dans la configuration")
                return False
            
            # Charge les contrats par défaut
            await self._load_default_contracts()
            
            # Démarre la surveillance
            await self._start_contract_monitoring()
            
            logger.info("Oracle Plutus initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation oracle Plutus: {e}")
            return False
    
    async def _load_default_contracts(self):
        """Charge les contrats Plutus par défaut"""
        try:
            # Contrat d'escrow décentralisé
            escrow_contract = {
                "name": "decentralized_escrow",
                "description": "Contrat d'escrow pour services Sigui",
                "validator_hash": self.cardano_adapter.config.plutus_validator_hash,
                "parameters": {
                    "client_did": "string",
                    "provider_did": "string",
                    "service_id": "string",
                    "amount_lovelace": "integer",
                    "timeout_slots": "integer"
                },
                "functions": [
                    "deposit",
                    "release",
                    "refund",
                    "dispute"
                ]
            }
            
            self._active_contracts["escrow"] = escrow_contract
            
            # Contrat de réputation
            reputation_contract = {
                "name": "reputation_tracker",
                "description": "Suivi de réputation sur-chain",
                "validator_hash": None,  # À définir
                "parameters": {
                    "agent_did": "string",
                    "trust_score": "float",
                    "evidence_hash": "string"
                },
                "functions": [
                    "update_score",
                    "get_score",
                    "add_evidence"
                ]
            }
            
            self._active_contracts["reputation"] = reputation_contract
            
            logger.info(f"{len(self._active_contracts)} contrats Plutus chargés")
            
        except Exception as e:
            logger.error(f"Erreur chargement contrats: {e}")
    
    async def deploy_contract(self, contract_name: str, contract_code: str,
                             parameters: Dict[str, str]) -> Optional[str]:
        """Déploie un nouveau contrat Plutus"""
        try:
            # Génère un ID de contrat unique
            contract_id = f"contract_{contract_name}_{int(time.time())}"
            
            # Compile et déploie le contrat (implémentation simplifiée)
            deployed_contract = {
                "id": contract_id,
                "name": contract_name,
                "code_hash": f"hash_{contract_code[:32]}",
                "parameters": parameters,
                "deployed_at": time.time(),
                "deployer_did": None,  # À remplir par l'appelant
                "status": "active"
            }
            
            self._active_contracts[contract_id] = deployed_contract
            
            # Enregistre l'événement
            event = PlutusContractEvent(
                contract_id=contract_id,
                tx_hash=f"deploy_{int(time.time())}",
                action="deploy",
                timestamp=int(time.time()),
                parameters=parameters,
                metadata={
                    "code_size": len(contract_code),
                    "network": self.cardano_adapter.network.value
                }
            )
            
            self._add_contract_event(contract_id, event)
            
            logger.info(f"Contrat déployé: {contract_id}")
            return contract_id
            
        except Exception as e:
            logger.error(f"Erreur déploiement contrat: {e}")
            return None
    
    async def execute_contract(self, contract_id: str, function_name: str,
                              caller_did: str, parameters: Dict[str, any],
                              amount_lovelace: int = 0,
                              assets: Optional[Dict[str, int]] = None) -> Optional[PlutusContractEvent]:
        """Exécute une fonction d'un contrat Plutus"""
        try:
            if contract_id not in self._active_contracts:
                raise ValueError(f"Contrat {contract_id} non trouvé")
            
            contract = self._active_contracts[contract_id]
            
            # Vérifie que la fonction existe
            if "functions" in contract and function_name not in contract["functions"]:
                raise ValueError(f"Fonction {function_name} non supportée")
            
            # Vérifie la réputation de l'appelant
            caller_trust = self.reputation_oracle.get_trust_score(caller_did)
            if caller_trust < 0.4:  # Seuil pour l'exécution de contrats
                logger.warning(f"Appelant {caller_did} a une réputation trop faible: {caller_trust}")
                return None
            
            # Exécute le contrat via l'adaptateur Cardano
            redeemer = {
                "function": function_name,
                "parameters": parameters,
                "caller": caller_did,
                "timestamp": int(time.time())
            }
            
            tx = await self.cardano_adapter.execute_plutus_contract(
                script_name=contract["name"],
                redeemer=redeemer,
                amount_lovelace=amount_lovelace,
                assets=assets
            )
            
            if not tx:
                raise ValueError("Échec de l'exécution du contrat")
            
            # Traite le résultat selon la fonction
            result = await self._process_contract_result(
                contract_id, function_name, parameters, caller_did
            )
            
            # Crée l'événement
            event = PlutusContractEvent(
                contract_id=contract_id,
                tx_hash=tx.tx_hash,
                action=function_name,
                timestamp=int(time.time()),
                caller_did=caller_did,
                parameters=parameters,
                result=result,
                metadata={
                    "amount_lovelace": amount_lovelace,
                    "assets": assets,
                    "tx_status": tx.status.value
                }
            )
            
            self._add_contract_event(contract_id, event)
            
            # Met à jour la réputation
            await self._update_reputation_from_contract(caller_did, function_name, result)
            
            # Déclenche les callbacks
            await self._trigger_callbacks(event)
            
            logger.info(f"Contrat exécuté: {contract_id}.{function_name}")
            return event
            
        except Exception as e:
            logger.error(f"Erreur exécution contrat: {e}")
            return None
    
    async def _process_contract_result(self, contract_id: str, function_name: str,
                                      parameters: Dict[str, any], caller_did: str) -> Dict:
        """Traite le résultat d'une exécution de contrat"""
        try:
            # Logique de traitement selon le type de contrat
            if "escrow" in contract_id:
                return await self._process_escrow_contract(function_name, parameters, caller_did)
            elif "reputation" in contract_id:
                return await self._process_reputation_contract(function_name, parameters, caller_did)
            else:
                return {"status": "executed", "message": "Function completed"}
                
        except Exception as e:
            logger.error(f"Erreur traitement résultat contrat: {e}")
            return {"status": "error", "message": str(e)}
    
    async def _process_escrow_contract(self, function_name: str, parameters: Dict[str, any], caller_did: str) -> Dict:
        """Traite les contrats d'escrow"""
        if function_name == "deposit":
            return {
                "status": "deposited",
                "amount": parameters.get("amount_lovelace", 0),
                "escrow_id": f"escrow_{int(time.time())}"
            }
        elif function_name == "release":
            return {
                "status": "released",
                "recipient": parameters.get("provider_did"),
                "released_by": caller_did
            }
        elif function_name == "refund":
            return {
                "status": "refunded",
                "refund_to": parameters.get("client_did"),
                "refunded_by": caller_did
            }
        else:
            return {"status": "processed", "action": function_name}
    
    async def _process_reputation_contract(self, function_name: str, parameters: Dict[str, any], caller_did: str) -> Dict:
        """Traite les contrats de réputation"""
        if function_name == "update_score":
            agent_did = parameters.get("agent_did")
            trust_score = parameters.get("trust_score", 0.0)
            
            # Met à jour la réputation off-chain aussi
            await self.reputation_oracle.update_trust_score(
                target_did=agent_did,
                increment=trust_score - self.reputation_oracle.get_trust_score(agent_did),
                reason="plutus_contract_update",
                metadata={"caller": caller_did}
            )
            
            return {
                "status": "updated",
                "agent": agent_did,
                "new_score": trust_score,
                "updated_by": caller_did
            }
        else:
            return {"status": "processed", "action": function_name}
    
    async def _update_reputation_from_contract(self, caller_did: str, function_name: str, result: Dict):
        """Met à jour la réputation basée sur l'exécution de contrat"""
        try:
            if result.get("status") == "error":
                # Pénalité pour échec
                penalty = -0.05
                await self.reputation_oracle.update_trust_score(
                    target_did=caller_did,
                    increment=penalty,
                    reason="contract_execution_failed",
                    metadata={"function": function_name, "error": result.get("message")}
                )
            else:
                # Récompense pour succès
                reward = 0.02
                await self.reputation_oracle.update_trust_score(
                    target_did=caller_did,
                    increment=reward,
                    reason="contract_execution_success",
                    metadata={"function": function_name, "result": result}
                )
                
        except Exception as e:
            logger.error(f"Erreur mise à jour réputation contrat: {e}")
    
    async def get_contract_events(self, contract_id: str, limit: int = 50) -> List[PlutusContractEvent]:
        """Récupère les événements d'un contrat"""
        try:
            if contract_id not in self._contract_events:
                return []
            
            events = self._contract_events[contract_id]
            return events[-limit:]  # Les plus récents en premier
            
        except Exception as e:
            logger.error(f"Erreur récupération événements contrat: {e}")
            return []
    
    async def get_contract_state(self, contract_id: str) -> Optional[Dict]:
        """Récupère l'état actuel d'un contrat"""
        try:
            if contract_id not in self._active_contracts:
                return None
            
            contract = self._active_contracts[contract_id].copy()
            
            # Ajoute les statistiques
            event_count = len(self._contract_events.get(contract_id, []))
            contract["event_count"] = event_count
            contract["last_event"] = None
            
            if event_count > 0:
                last_event = self._contract_events[contract_id][-1]
                contract["last_event"] = {
                    "action": last_event.action,
                    "timestamp": last_event.timestamp,
                    "caller": last_event.caller_did
                }
            
            return contract
            
        except Exception as e:
            logger.error(f"Erreur récupération état contrat: {e}")
            return None
    
    def register_callback(self, callback: callable):
        """Enregistre un callback pour les événements de contrat"""
        self._callbacks.append(callback)
    
    def _add_contract_event(self, contract_id: str, event: PlutusContractEvent):
        """Ajoute un événement à l'historique du contrat"""
        if contract_id not in self._contract_events:
            self._contract_events[contract_id] = []
        
        self._contract_events[contract_id].append(event)
        
        # Limite la taille de l'historique
        if len(self._contract_events[contract_id]) > 1000:
            self._contract_events[contract_id] = self._contract_events[contract_id][-500:]
    
    async def _trigger_callbacks(self, event: PlutusContractEvent):
        """Déclenche les callbacks enregistrés"""
        for callback in self._callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Erreur callback contrat: {e}")
    
    async def _start_contract_monitoring(self):
        """Démarre la surveillance des contrats"""
        async def monitor_contracts():
            while True:
                try:
                    # Vérifie l'état des contrats actifs
                    for contract_id in list(self._active_contracts.keys()):
                        await self._check_contract_health(contract_id)
                    
                    await asyncio.sleep(300)  # Vérifie toutes les 5 minutes
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance contrats: {e}")
                    await asyncio.sleep(30)
        
        task = asyncio.create_task(monitor_contracts())
        self._monitoring_tasks.append(task)
    
    async def _check_contract_health(self, contract_id: str):
        """Vérifie la santé d'un contrat"""
        try:
            contract = self._active_contracts[contract_id]
            
            # Vérifie la dernière activité
            event_count = len(self._contract_events.get(contract_id, []))
            if event_count == 0:
                # Pas d'activité récente
                contract["health"] = "inactive"
            else:
                last_event = self._contract_events[contract_id][-1]
                time_since_last = time.time() - last_event.timestamp
                
                if time_since_last > 86400:  # 24 heures
                    contract["health"] = "dormant"
                elif time_since_last > 3600:  # 1 heure
                    contract["health"] = "idle"
                else:
                    contract["health"] = "active"
            
            self._active_contracts[contract_id] = contract
            
        except Exception as e:
            logger.error(f"Erreur vérification santé contrat: {e}")
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._active_contracts.clear()
        self._contract_events.clear()
        self._callbacks.clear()