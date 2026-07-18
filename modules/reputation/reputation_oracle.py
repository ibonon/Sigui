"""
Sigui v3.0 — Reputation Oracle
Oracle décentralisé pour les scores de réputation cross-chain.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from loguru import logger
from web3 import Web3

from config import settings
from modules.reputation.trust_graph import TrustGraph, TrustEdgeType
from modules.reputation.proof_of_trust import ProofOfTrust, TrustProof


class ReputationSource(Enum):
    """Sources de données de réputation."""
    ON_CHAIN = "on_chain"
    OFF_CHAIN = "off_chain"
    CROSS_CHAIN = "cross_chain"
    SOCIAL = "social"
    SERVICE = "service"


@dataclass
class ReputationData:
    """Données de réputation d'un agent."""
    agent_did: str
    source: ReputationSource
    score: float
    confidence: float  # 0.0 à 1.0
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit les données en dictionnaire."""
        return {
            "agent_did": self.agent_did,
            "source": self.source.value,
            "score": self.score,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class ReputationOracle:
    """Oracle de réputation décentralisé."""
    
    def __init__(self, trust_graph: TrustGraph, proof_of_trust: ProofOfTrust):
        self.trust_graph = trust_graph
        self.proof_of_trust = proof_of_trust
        self.reputation_data: Dict[str, List[ReputationData]] = {}
        self.cross_chain_adapters: Dict[str, any] = {}
        
        # Sources de réputation configurées
        self.enabled_sources = {
            ReputationSource.ON_CHAIN: True,
            ReputationSource.OFF_CHAIN: True,
            ReputationSource.CROSS_CHAIN: True,
            ReputationSource.SOCIAL: False,  # À activer plus tard
            ReputationSource.SERVICE: True,
        }
        
        logger.info("ReputationOracle initialisé")
    
    async def collect_reputation_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données de réputation d'un agent depuis toutes les sources."""
        all_data = []
        
        # Collecter depuis chaque source activée
        for source, enabled in self.enabled_sources.items():
            if enabled:
                source_data = await self._collect_from_source(agent_did, source)
                all_data.extend(source_data)
        
        # Stocker les données
        if agent_did not in self.reputation_data:
            self.reputation_data[agent_did] = []
        
        self.reputation_data[agent_did].extend(all_data)
        
        # Limiter l'historique
        if len(self.reputation_data[agent_did]) > 1000:
            self.reputation_data[agent_did] = self.reputation_data[agent_did][-1000:]
        
        logger.debug(f"Données de réputation collectées pour {agent_did}: {len(all_data)} points")
        return all_data
    
    async def _collect_from_source(
        self,
        agent_did: str,
        source: ReputationSource
    ) -> List[ReputationData]:
        """Collecte les données depuis une source spécifique."""
        data_points = []
        
        try:
            if source == ReputationSource.ON_CHAIN:
                data_points = await self._collect_on_chain_data(agent_did)
            elif source == ReputationSource.OFF_CHAIN:
                data_points = await self._collect_off_chain_data(agent_did)
            elif source == ReputationSource.CROSS_CHAIN:
                data_points = await self._collect_cross_chain_data(agent_did)
            elif source == ReputationSource.SERVICE:
                data_points = await self._collect_service_data(agent_did)
        
        except Exception as e:
            logger.error(f"Erreur lors de la collecte depuis {source.value}: {e}")
        
        return data_points
    
    async def _collect_on_chain_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données on-chain."""
        data_points = []
        
        try:
            # Adresse Ethereum associée au DID
            eth_address = self._extract_eth_address(agent_did)
            if not eth_address:
                return data_points
            
            # Connexion Web3
            w3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_RPC_URL))
            
            # 1. Balance ETH
            eth_balance = w3.eth.get_balance(eth_address)
            eth_balance_eth = w3.from_wei(eth_balance, 'ether')
            
            if eth_balance_eth > 0:
                data_points.append(ReputationData(
                    agent_did=agent_did,
                    source=ReputationSource.ON_CHAIN,
                    score=min(1.0, eth_balance_eth / 100),  # Normalisé
                    confidence=0.8,
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "metric": "eth_balance",
                        "value": float(eth_balance_eth),
                        "currency": "ETH",
                    },
                ))
            
            # 2. Transactions count
            # Note: En production, il faudrait utiliser un indexer
            tx_count = w3.eth.get_transaction_count(eth_address)
            
            if tx_count > 0:
                data_points.append(ReputationData(
                    agent_did=agent_did,
                    source=ReputationSource.ON_CHAIN,
                    score=min(1.0, tx_count / 1000),  # Normalisé
                    confidence=0.7,
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "metric": "transaction_count",
                        "value": tx_count,
                    },
                ))
            
            # 3. DeFi interactions (simplifié)
            # En production, il faudrait vérifier les interactions avec Aave, Compound, etc.
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte on-chain: {e}")
        
        return data_points
    
    async def _collect_off_chain_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données off-chain."""
        data_points = []
        
        try:
            # 1. Historique des paiements dans Sigui
            # En production, il faudrait interroger la base de données
            
            # 2. Score du TrustGraph
            trust_score = self.trust_graph.calculate_trust_score(agent_did)
            
            if trust_score > 0:
                data_points.append(ReputationData(
                    agent_did=agent_did,
                    source=ReputationSource.OFF_CHAIN,
                    score=trust_score,
                    confidence=0.9,
                    timestamp=datetime.now(timezone.utc),
                    metadata={
                        "metric": "trust_graph_score",
                        "value": trust_score,
                    },
                ))
            
            # 3. Historique des services rendus
            # En production, il faudrait interroger le marketplace
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte off-chain: {e}")
        
        return data_points
    
    async def _collect_cross_chain_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données cross-chain."""
        data_points = []
        
        try:
            # 1. Cosmos (ATOM)
            cosmos_data = await self._collect_cosmos_data(agent_did)
            data_points.extend(cosmos_data)
            
            # 2. Solana
            solana_data = await self._collect_solana_data(agent_did)
            data_points.extend(solana_data)
            
            # 3. Bitcoin (si intégré)
            if "bitcoin" in self.cross_chain_adapters:
                bitcoin_data = await self._collect_bitcoin_data(agent_did)
                data_points.extend(bitcoin_data)
            
            # 4. Cardano (si intégré)
            if "cardano" in self.cross_chain_adapters:
                cardano_data = await self._collect_cardano_data(agent_did)
                data_points.extend(cardano_data)
        
        except Exception as e:
            logger.error(f"Erreur lors de la collecte cross-chain: {e}")
        
        return data_points
    
    async def _collect_service_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données de service."""
        data_points = []
        
        try:
            # 1. Nombre de services fournis
            # En production, il faudrait interroger le marketplace
            
            # 2. Ratings des services
            # En production, il faudrait récupérer les avis
            
            # 3. Taux de réussite
            # En production, il faudrait calculer le succès vs échec
            pass
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte de service: {e}")
        
        return data_points
    
    async def _collect_cosmos_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données Cosmos."""
        data_points = []
        
        try:
            # En production, il faudrait utiliser le CosmosOracle existant
            # Pour l'instant, on simule
            pass
        
        except Exception as e:
            logger.error(f"Erreur lors de la collecte Cosmos: {e}")
        
        return data_points
    
    async def _collect_solana_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données Solana."""
        data_points = []
        
        try:
            # En production, il faudrait utiliser le SolanaOracle existant
            # Pour l'instant, on simule
            pass
        
        except Exception as e:
            logger.error(f"Erreur lors de la collecte Solana: {e}")
        
        return data_points
    
    async def _collect_bitcoin_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données Bitcoin."""
        data_points = []
        
        try:
            # À implémenter avec l'intégration Bitcoin
            pass
        
        except Exception as e:
            logger.error(f"Erreur lors de la collecte Bitcoin: {e}")
        
        return data_points
    
    async def _collect_cardano_data(self, agent_did: str) -> List[ReputationData]:
        """Collecte les données Cardano."""
        data_points = []
        
        try:
            # À implémenter avec l'intégration Cardano
            pass
        
        except Exception as e:
            logger.error(f"Erreur lors de la collecte Cardano: {e}")
        
        return data_points
    
    def _extract_eth_address(self, agent_did: str) -> Optional[str]:
        """Extrait l'adresse Ethereum d'un DID."""
        # Format DID: did:ethr:0x...
        if agent_did.startswith("did:ethr:"):
            return agent_did[9:]
        
        # Format DID: did:pkh:eip155:1:0x...
        if agent_did.startswith("did:pkh:eip155:"):
            parts = agent_did.split(":")
            if len(parts) >= 6:
                return parts[5]
        
        return None
    
    async def calculate_composite_score(self, agent_did: str) -> float:
        """Calcule un score composite basé sur toutes les sources."""
        # Collecter les données si nécessaire
        if agent_did not in self.reputation_data or not self.reputation_data[agent_did]:
            await self.collect_reputation_data(agent_did)
        
        if agent_did not in self.reputation_data or not self.reputation_data[agent_did]:
            return 0.0
        
        # Filtrer les données récentes (30 derniers jours)
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_data = [
            d for d in self.reputation_data[agent_did]
            if d.timestamp >= cutoff
        ]
        
        if not recent_data:
            return 0.0
        
        # Calculer le score pondéré
        total_weight = 0.0
        weighted_sum = 0.0
        
        for data in recent_data:
            # Poids = confiance * facteur_temporel
            time_factor = self._calculate_time_factor(data.timestamp)
            weight = data.confidence * time_factor
            
            weighted_sum += data.score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        composite_score = weighted_sum / total_weight
        
        # Appliquer des ajustements basés sur le comportement
        composite_score = self._apply_behavior_adjustments(agent_did, composite_score)
        
        return min(1.0, max(0.0, composite_score))
    
    def _calculate_time_factor(self, timestamp: datetime) -> float:
        """Calcule le facteur temporel pour une donnée."""
        now = datetime.now(timezone.utc)
        age_days = (now - timestamp).total_seconds() / 86400
        
        # Décroissance exponentielle sur 30 jours
        decay_factor = 0.95
        return decay_factor ** age_days
    
    def _apply_behavior_adjustments(self, agent_did: str, base_score: float) -> float:
        """Applique des ajustements basés sur le comportement."""
        adjusted_score = base_score
        
        # 1. Vérifier les attaques récentes
        # En production, il faudrait interroger le ThreatRegistry
        
        # 2. Vérifier la stabilité des paiements
        # En production, il faudrait analyser l'historique
        
        # 3. Vérifier la participation à la gouvernance
        # En production, il faudrait vérifier les votes
        
        return adjusted_score
    
    async def generate_reputation_report(self, agent_did: str) -> Dict[str, any]:
        """Génère un rapport complet de réputation."""
        composite_score = await self.calculate_composite_score(agent_did)
        
        # Collecter les données par source
        source_scores = {}
        for source in ReputationSource:
            source_data = [
                d for d in self.reputation_data.get(agent_did, [])
                if d.source == source
            ]
            
            if source_data:
                avg_score = sum(d.score for d in source_data) / len(source_data)
                avg_confidence = sum(d.confidence for d in source_data) / len(source_data)
                
                source_scores[source.value] = {
                    "score": avg_score,
                    "confidence": avg_confidence,
                    "data_points": len(source_data),
                }
        
        # Récupérer la preuve de confiance
        trust_proof = self.proof_of_trust.get_agent_proof(agent_did)
        
        return {
            "agent_did": agent_did,
            "composite_score": composite_score,
            "source_scores": source_scores,
            "trust_proof": trust_proof.to_dict() if trust_proof else None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "sources_used": [s.value for s in ReputationSource if self.enabled_sources[s]],
                "calculation_method": "weighted_average",
            },
        }
    
    def register_cross_chain_adapter(self, chain_name: str, adapter: any):
        """Enregistre un adaptateur cross-chain."""
        self.cross_chain_adapters[chain_name] = adapter
        logger.info(f"Adaptateur cross-chain enregistré: {chain_name}")
    
    def export_data(self) -> Dict[str, any]:
        """Exporte toutes les données de réputation."""
        return {
            "reputation_data": {
                agent_did: [d.to_dict() for d in data_list]
                for agent_did, data_list in self.reputation_data.items()
            },
            "cross_chain_adapters": list(self.cross_chain_adapters.keys()),
            "enabled_sources": {s.value: e for s, e in self.enabled_sources.items()},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }