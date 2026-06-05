"""
Gestionnaire cross-chain pour coordonner tous les oracles.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict

from .ethereum_oracle import EthereumOracle
from .solana_oracle import SolanaOracle
from .cosmos_oracle import CosmosOracle
from ..database.threat_repository import ThreatRepository
from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class CrossChainAlert:
    """Alerte cross-chain."""
    id: str
    chain: str
    threat_type: str
    severity: str
    description: str
    details: Dict[str, Any]
    timestamp: datetime
    correlated_alerts: List[str] = None
    
    def __post_init__(self):
        if self.correlated_alerts is None:
            self.correlated_alerts = []


class CrossChainManager:
    """Gestionnaire pour coordonner la surveillance cross-chain."""
    
    def __init__(self):
        self.oracles = {}
        self.threat_repo = ThreatRepository()
        self.correlation_engine = CrossChainCorrelationEngine()
        self.active_monitoring = False
        
        # Initialiser les oracles
        self._initialize_oracles()
        
        logger.info("CrossChain Manager initialisé")
    
    def _initialize_oracles(self):
        """Initialise tous les oracles configurés."""
        try:
            # Ethereum
            if settings.ETHEREUM_RPC_URL:
                self.oracles["ethereum"] = EthereumOracle()
                logger.info("Oracle Ethereum initialisé")
            
            # Solana
            if settings.SOLANA_RPC_URL:
                self.oracles["solana"] = SolanaOracle()
                logger.info("Oracle Solana initialisé")
            
            # Cosmos
            if settings.COSMOS_RPC_URL:
                self.oracles["cosmos"] = CosmosOracle()
                logger.info("Oracle Cosmos initialisé")
        
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des oracles: {e}")
    
    async def start_monitoring(self):
        """Démarre la surveillance sur toutes les chaînes."""
        if self.active_monitoring:
            logger.warning("La surveillance est déjà active")
            return
        
        self.active_monitoring = True
        
        # Démarrer la surveillance sur chaque oracle
        tasks = []
        for chain_name, oracle in self.oracles.items():
            task = asyncio.create_task(
                oracle.start_monitoring(self._handle_oracle_alert)
            )
            tasks.append(task)
            logger.info(f"Surveillance démarrée pour {chain_name}")
        
        # Démarrer le moteur de corrélation
        correlation_task = asyncio.create_task(
            self.correlation_engine.start_correlation(self._handle_correlated_alert)
        )
        tasks.append(correlation_task)
        
        logger.info(f"Surveillance cross-chain démarrée sur {len(self.oracles)} chaînes")
        
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Surveillance arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans la surveillance: {e}")
    
    async def _handle_oracle_alert(self, alert_data: Dict[str, Any]):
        """Gère les alertes des oracles."""
        try:
            chain = alert_data["chain"]
            threats = alert_data["threats"]
            timestamp = alert_data["timestamp"]
            
            for threat in threats:
                # Créer une alerte
                alert_id = f"{chain}_{threat.get('tx_hash', threat.get('signature', 'unknown'))}_{timestamp.timestamp()}"
                
                alert = CrossChainAlert(
                    id=alert_id,
                    chain=chain,
                    threat_type=threat["type"],
                    severity=threat["severity"],
                    description=threat["description"],
                    details=threat,
                    timestamp=timestamp,
                )
                
                # Sauvegarder dans la base de données
                await self.threat_repo.save_cross_chain_alert(asdict(alert))
                
                # Envoyer au moteur de corrélation
                await self.correlation_engine.add_alert(alert)
                
                # Logger
                logger.warning(
                    f"Alerte {chain}: {threat['type']} - {threat['description']} "
                    f"(Sévérité: {threat['severity']})"
                )
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'alerte: {e}")
    
    async def _handle_correlated_alert(self, correlated_alert: Dict[str, Any]):
        """Gère les alertes corrélées."""
        try:
            # Sauvegarder l'alerte corrélée
            await self.threat_repo.save_correlated_alert(correlated_alert)
            
            # Logger
            logger.critical(
                f"ALERTE CORRÉLÉE: {correlated_alert['pattern_name']} - "
                f"{correlated_alert['description']} "
                f"(Chaînes: {', '.join(correlated_alert['chains_involved'])})"
            )
            
            # Notifier via WebSocket/GraphQL
            await self._notify_correlated_alert(correlated_alert)
        
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'alerte corrélée: {e}")
    
    async def _notify_correlated_alert(self, alert: Dict[str, Any]):
        """Notifie les clients via WebSocket/GraphQL."""
        # À implémenter avec GraphQL subscriptions
        pass
    
    async def get_chain_status(self) -> Dict[str, Any]:
        """Récupère le statut de chaque chaîne."""
        status = {}
        
        for chain_name, oracle in self.oracles.items():
            try:
                if isinstance(oracle, EthereumOracle):
                    latest_block = oracle.web3.eth.block_number
                    is_connected = oracle.web3.is_connected()
                
                elif isinstance(oracle, SolanaOracle):
                    latest_slot = asyncio.run(oracle.client.get_slot())
                    is_connected = True  # Simplifié
                
                elif isinstance(oracle, CosmosOracle):
                    latest_height = asyncio.run(oracle._get_latest_block_height())
                    is_connected = latest_height > 0
                
                status[chain_name] = {
                    "connected": is_connected,
                    "latest_block": latest_block if 'latest_block' in locals() else latest_slot if 'latest_slot' in locals() else latest_height,
                    "monitored_contracts": len(getattr(oracle, 'monitored_contracts', [])),
                    "active": True,
                }
            
            except Exception as e:
                status[chain_name] = {
                    "connected": False,
                    "error": str(e),
                    "active": False,
                }
        
        return status
    
    async def get_address_risk_across_chains(self, addresses: Dict[str, str]) -> Dict[str, Any]:
        """Calcule le risque d'adresses sur plusieurs chaînes."""
        results = {}
        
        for chain_name, address in addresses.items():
            if chain_name in self.oracles:
                oracle = self.oracles[chain_name]
                
                try:
                    risk_score = await oracle.get_address_risk_score(address)
                    results[chain_name] = risk_score
                
                except Exception as e:
                    results[chain_name] = {
                        "address": address,
                        "error": str(e),
                        "risk_score": 0.5,
                    }
        
        # Calculer le score global
        if results:
            total_score = sum(r.get("risk_score", 0.5) for r in results.values())
            avg_score = total_score / len(results)
            
            results["global"] = {
                "average_risk_score": avg_score,
                "highest_risk_chain": max(
                    results.items(),
                    key=lambda x: x[1].get("risk_score", 0)
                )[0] if results else None,
                "chain_count": len(results),
            }
        
        return results
    
    async def stop_monitoring(self):
        """Arrête la surveillance."""
        self.active_monitoring = False
        logger.info("Surveillance cross-chain arrêtée")


class CrossChainCorrelationEngine:
    """Moteur de corrélation pour détecter les attaques cross-chain."""
    
    def __init__(self):
        self.alerts_buffer = []
        self.correlation_patterns = [
            {
                "name": "BRIDGE_ATTACK",
                "description": "Attaque sur un bridge cross-chain",
                "chains_required": ["ethereum", "solana"],
                "time_window_seconds": 300,
                "pattern": lambda alerts: len(alerts) >= 2 and any(
                    "BRIDGE" in a.threat_type for a in alerts
                ),
            },
            {
                "name": "ARBITRAGE_ATTACK",
                "description": "Attaque d'arbitrage cross-chain",
                "chains_required": ["ethereum", "cosmos"],
                "time_window_seconds": 60,
                "pattern": lambda alerts: len(alerts) >= 3 and all(
                    "LARGE_TRANSFER" in a.threat_type for a in alerts
                ),
            },
            {
                "name": "FLASH_LOAN_ATTACK",
                "description": "Attaque par flash loan sur multiple chaînes",
                "chains_required": ["ethereum", "solana"],
                "time_window_seconds": 120,
                "pattern": lambda alerts: len(alerts) >= 2 and any(
                    "FLASH_LOAN" in a.threat_type for a in alerts
                ),
            },
        ]
        
        self.correlation_callback = None
    
    async def add_alert(self, alert: CrossChainAlert):
        """Ajoute une alerte au buffer pour corrélation."""
        self.alerts_buffer.append(alert)
        
        # Nettoyer les alertes anciennes
        current_time = datetime.now()
        self.alerts_buffer = [
            a for a in self.alerts_buffer
            if (current_time - a.timestamp).total_seconds() < 600  # 10 minutes
        ]
        
        # Vérifier les corrélations
        await self._check_correlations()
    
    async def _check_correlations(self):
        """Vérifie les corrélations entre alertes."""
        for pattern in self.correlation_patterns:
            # Filtrer les alertes dans la fenêtre de temps
            time_window = pattern["time_window_seconds"]
            current_time = datetime.now()
            
            recent_alerts = [
                a for a in self.alerts_buffer
                if (current_time - a.timestamp).total_seconds() <= time_window
            ]
            
            # Vérifier si on a des alertes des chaînes requises
            chains_present = set(a.chain for a in recent_alerts)
            required_chains = set(pattern["chains_required"])
            
            if required_chains.issubset(chains_present):
                # Filtrer les alertes des chaînes requises
                relevant_alerts = [
                    a for a in recent_alerts
                    if a.chain in required_chains
                ]
                
                # Appliquer le pattern
                if pattern["pattern"](relevant_alerts):
                    # Créer une alerte corrélée
                    correlated_alert = {
                        "pattern_name": pattern["name"],
                        "description": pattern["description"],
                        "chains_involved": list(chains_present),
                        "alerts": [asdict(a) for a in relevant_alerts],
                        "timestamp": current_time,
                        "severity": "CRITICAL",
                        "confidence": 0.85,
                    }
                    
                    # Appeler le callback
                    if self.correlation_callback:
                        await self.correlation_callback(correlated_alert)
    
    async def start_correlation(self, callback):
        """Démarre le moteur de corrélation."""
        self.correlation_callback = callback
        logger.info("Moteur de corrélation cross-chain démarré")