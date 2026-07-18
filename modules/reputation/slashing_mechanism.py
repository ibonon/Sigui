"""
Sigui v3.0 — Slashing Mechanism
Mécanisme de pénalisation pour les mauvais acteurs dans le système de réputation.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from loguru import logger

from config import settings
from modules.reputation.trust_graph import TrustGraph, TrustEdgeType
from modules.reputation.proof_of_trust import ProofOfTrust


class SlashingReason(Enum):
    """Raisons de slashing."""
    MALICIOUS_BEHAVIOR = "malicious_behavior"
    DOUBLE_SPEND = "double_spend"
    FALSE_REPORTING = "false_reporting"
    SYBIL_ATTACK = "sybil_attack"
    GOVERNANCE_ABUSE = "governance_abuse"
    SERVICE_FAILURE = "service_failure"
    COLLUSION = "collusion"


class SlashingSeverity(Enum):
    """Sévérité du slashing."""
    MINOR = "minor"  # 10% de slash
    MODERATE = "moderate"  # 30% de slash
    MAJOR = "major"  # 60% de slash
    SEVERE = "severe"  # 100% de slash


@dataclass
class SlashingEvent:
    """Événement de slashing."""
    agent_did: str
    reason: SlashingReason
    severity: SlashingSeverity
    amount_slashed: float
    timestamp: datetime
    evidence: Dict[str, any] = field(default_factory=dict)
    reporter_did: Optional[str] = None
    transaction_hash: Optional[str] = None
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit l'événement en dictionnaire."""
        return {
            "agent_did": self.agent_did,
            "reason": self.reason.value,
            "severity": self.severity.value,
            "amount_slashed": self.amount_slashed,
            "timestamp": self.timestamp.isoformat(),
            "evidence": self.evidence,
            "reporter_did": self.reporter_did,
            "transaction_hash": self.transaction_hash,
        }


class SlashingMechanism:
    """Mécanisme de slashing décentralisé."""
    
    def __init__(self, trust_graph: TrustGraph, proof_of_trust: ProofOfTrust):
        self.trust_graph = trust_graph
        self.proof_of_trust = proof_of_trust
        self.slashing_events: Dict[str, List[SlashingEvent]] = {}
        self.pending_slashes: Dict[str, List[SlashingEvent]] = {}
        self.blacklist: Set[str] = set()
        
        # Paramètres de slashing
        self.slashing_parameters = {
            SlashingSeverity.MINOR: {
                "percentage": 0.10,
                "cooldown_days": 7,
                "trust_score_penalty": 0.20,
            },
            SlashingSeverity.MODERATE: {
                "percentage": 0.30,
                "cooldown_days": 30,
                "trust_score_penalty": 0.50,
            },
            SlashingSeverity.MAJOR: {
                "percentage": 0.60,
                "cooldown_days": 90,
                "trust_score_penalty": 0.80,
            },
            SlashingSeverity.SEVERE: {
                "percentage": 1.00,
                "cooldown_days": 365,
                "trust_score_penalty": 1.00,
            },
        }
        
        # Seuils de détection
        self.detection_thresholds = {
            "double_spend_amount": 100.0,  # USDC
            "false_reporting_count": 3,
            "sybil_cluster_size": 5,
            "service_failure_rate": 0.3,  # 30% d'échec
        }
        
        logger.info("SlashingMechanism initialisé")
    
    async def detect_and_slash(self, agent_did: str) -> List[SlashingEvent]:
        """Détecte les comportements malveillants et applique le slashing."""
        slashing_events = []
        
        # 1. Vérifier les doubles dépenses
        double_spend_events = await self._detect_double_spends(agent_did)
        slashing_events.extend(double_spend_events)
        
        # 2. Vérifier les faux signalements
        false_reporting_events = await self._detect_false_reporting(agent_did)
        slashing_events.extend(false_reporting_events)
        
        # 3. Vérifier les attaques Sybil
        sybil_events = await self._detect_sybil_attacks(agent_did)
        slashing_events.extend(sybil_events)
        
        # 4. Vérifier les échecs de service
        service_failure_events = await self._detect_service_failures(agent_did)
        slashing_events.extend(service_failure_events)
        
        # 5. Vérifier la collusion
        collusion_events = await self._detect_collusion(agent_did)
        slashing_events.extend(collusion_events)
        
        # Appliquer les slashing events
        for event in slashing_events:
            await self._apply_slashing(event)
        
        return slashing_events
    
    async def _detect_double_spends(self, agent_did: str) -> List[SlashingEvent]:
        """Détecte les doubles dépenses."""
        events = []
        
        try:
            # En production, il faudrait analyser l'historique des transactions
            # Pour l'instant, on simule
            
            # Vérifier si l'agent est un validateur
            if agent_did in self.proof_of_trust.validators:
                stake = self.proof_of_trust.stake_pool.get(agent_did, 0.0)
                
                # Simuler une détection de double dépense
                # (À remplacer par une vraie logique)
                if stake > 10000.0:  # Exemple: validateur avec gros stake
                    # Vérifier les transactions récentes
                    pass
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection des doubles dépenses: {e}")
        
        return events
    
    async def _detect_false_reporting(self, agent_did: str) -> List[SlashingEvent]:
        """Détecte les faux signalements."""
        events = []
        
        try:
            # Analyser l'historique des signalements de l'agent
            # En production, il faudrait interroger le ThreatRegistry
            
            # Vérifier le taux de signalements invalides
            false_report_count = 0  # À calculer
            
            if false_report_count >= self.detection_thresholds["false_reporting_count"]:
                event = SlashingEvent(
                    agent_did=agent_did,
                    reason=SlashingReason.FALSE_REPORTING,
                    severity=SlashingSeverity.MODERATE,
                    amount_slashed=0.0,  # À calculer
                    timestamp=datetime.now(timezone.utc),
                    evidence={
                        "false_report_count": false_report_count,
                        "threshold": self.detection_thresholds["false_reporting_count"],
                    },
                )
                events.append(event)
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection des faux signalements: {e}")
        
        return events
    
    async def _detect_sybil_attacks(self, agent_did: str) -> List[SlashingEvent]:
        """Détecte les attaques Sybil."""
        events = []
        
        try:
            # Analyser le graphe de confiance pour détecter les clusters Sybil
            neighborhood = self.trust_graph.get_trust_neighborhood(agent_did, radius=3)
            
            # Vérifier les patterns de création de comptes
            # (À implémenter avec une analyse de graphe plus avancée)
            
            # Détecter les clusters suspects
            suspected_sybil_cluster = []
            
            if len(suspected_sybil_cluster) >= self.detection_thresholds["sybil_cluster_size"]:
                event = SlashingEvent(
                    agent_did=agent_did,
                    reason=SlashingReason.SYBIL_ATTACK,
                    severity=SlashingSeverity.MAJOR,
                    amount_slashed=0.0,  # À calculer
                    timestamp=datetime.now(timezone.utc),
                    evidence={
                        "cluster_size": len(suspected_sybil_cluster),
                        "cluster_members": suspected_sybil_cluster,
                    },
                )
                events.append(event)
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection des attaques Sybil: {e}")
        
        return events
    
    async def _detect_service_failures(self, agent_did: str) -> List[SlashingEvent]:
        """Détecte les échecs de service répétés."""
        events = []
        
        try:
            # Analyser l'historique des services de l'agent
            # En production, il faudrait interroger le marketplace
            
            # Calculer le taux d'échec
            total_services = 0
            failed_services = 0
            
            failure_rate = failed_services / total_services if total_services > 0 else 0.0
            
            if failure_rate >= self.detection_thresholds["service_failure_rate"]:
                event = SlashingEvent(
                    agent_did=agent_did,
                    reason=SlashingReason.SERVICE_FAILURE,
                    severity=SlashingSeverity.MODERATE,
                    amount_slashed=0.0,  # À calculer
                    timestamp=datetime.now(timezone.utc),
                    evidence={
                        "failure_rate": failure_rate,
                        "total_services": total_services,
                        "failed_services": failed_services,
                    },
                )
                events.append(event)
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection des échecs de service: {e}")
        
        return events
    
    async def _detect_collusion(self, agent_did: str) -> List[SlashingEvent]:
        """Détecte la collusion entre agents."""
        events = []
        
        try:
            # Analyser les patterns de vote et de délégation
            # Détecter les groupes qui votent toujours ensemble
            
            # Utiliser l'analyse de communauté sur le graphe de confiance
            # (À implémenter avec networkx ou un algorithme de clustering)
            
            suspected_collusion_group = []
            
            if len(suspected_collusion_group) >= 3:  # Seuil arbitraire
                event = SlashingEvent(
                    agent_did=agent_did,
                    reason=SlashingReason.COLLUSION,
                    severity=SlashingSeverity.SEVERE,
                    amount_slashed=0.0,  # À calculer
                    timestamp=datetime.now(timezone.utc),
                    evidence={
                        "group_size": len(suspected_collusion_group),
                        "group_members": suspected_collusion_group,
                    },
                )
                events.append(event)
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection de la collusion: {e}")
        
        return events
    
    async def _apply_slashing(self, event: SlashingEvent):
        """Applique un événement de slashing."""
        try:
            # Calculer le montant à slasher
            if event.agent_did in self.proof_of_trust.validators:
                stake = self.proof_of_trust.stake_pool.get(event.agent_did, 0.0)
                params = self.slashing_parameters[event.severity]
                
                amount_slashed = stake * params["percentage"]
                event.amount_slashed = amount_slashed
                
                # Mettre à jour le stake
                new_stake = stake - amount_slashed
                self.proof_of_trust.stake_pool[event.agent_did] = new_stake
                
                # Appliquer la pénalité de score de confiance
                self._apply_trust_score_penalty(event.agent_did, params["trust_score_penalty"])
                
                # Ajouter à la liste noire si nécessaire
                if event.severity == SlashingSeverity.SEVERE:
                    self.blacklist.add(event.agent_did)
                
                # Historiser l'événement
                if event.agent_did not in self.slashing_events:
                    self.slashing_events[event.agent_did] = []
                
                self.slashing_events[event.agent_did].append(event)
                
                logger.warning(
                    f"Slashing appliqué à {event.agent_did}: "
                    f"{event.reason.value} ({event.severity.value}), "
                    f"montant: {amount_slashed}"
                )
            
            else:
                # Pour les non-validateurs, appliquer seulement la pénalité de score
                params = self.slashing_parameters[event.severity]
                self._apply_trust_score_penalty(event.agent_did, params["trust_score_penalty"])
                
                # Historiser l'événement
                if event.agent_did not in self.slashing_events:
                    self.slashing_events[event.agent_did] = []
                
                self.slashing_events[event.agent_did].append(event)
                
                logger.warning(
                    f"Pénalité de réputation appliquée à {event.agent_did}: "
                    f"{event.reason.value} ({event.severity.value})"
                )
        
        except Exception as e:
            logger.error(f"Erreur lors de l'application du slashing: {e}")
    
    def _apply_trust_score_penalty(self, agent_did: str, penalty_percentage: float):
        """Applique une pénalité au score de confiance."""
        try:
            # Ajouter une arête négative au graphe
            self.trust_graph.add_trust_edge(
                source_did="system:slashing",
                target_did=agent_did,
                edge_type=TrustEdgeType.VERIFICATION,
                weight=1.0 - penalty_percentage,  # Inversé: poids bas = mauvaise réputation
                metadata={
                    "penalty_percentage": penalty_percentage,
                    "action": "trust_score_penalty",
                },
            )
        
        except Exception as e:
            logger.error(f"Erreur lors de l'application de la pénalité de score: {e}")
    
    async def report_malicious_behavior(
        self,
        reporter_did: str,
        target_did: str,
        reason: SlashingReason,
        evidence: Dict[str, any],
        severity: SlashingSeverity = SlashingSeverity.MODERATE
    ) -> Optional[SlashingEvent]:
        """Permet à un agent de signaler un comportement malveillant."""
        try:
            # Vérifier que le reporter a une bonne réputation
            reporter_score = self.trust_graph.calculate_trust_score(reporter_did)
            if reporter_score < 0.5:
                logger.warning(f"Reporter {reporter_did} a un score trop bas: {reporter_score}")
                return None
            
            # Vérifier que la cible n'est pas déjà blacklistée
            if target_did in self.blacklist:
                logger.warning(f"Cible {target_did} déjà blacklistée")
                return None
            
            # Créer l'événement de slashing
            event = SlashingEvent(
                agent_did=target_did,
                reason=reason,
                severity=severity,
                amount_slashed=0.0,  # À calculer lors de l'application
                timestamp=datetime.now(timezone.utc),
                evidence=evidence,
                reporter_did=reporter_did,
            )
            
            # Ajouter aux pending slashes
            if target_did not in self.pending_slashes:
                self.pending_slashes[target_did] = []
            
            self.pending_slashes[target_did].append(event)
            
            logger.info(
                f"Comportement malveillant signalé par {reporter_did} contre {target_did}: "
                f"{reason.value}"
            )
            
            return event
        
        except Exception as e:
            logger.error(f"Erreur lors du signalement de comportement malveillant: {e}")
            return None
    
    async def process_pending_slashes(self, target_did: str) -> List[SlashingEvent]:
        """Traite les slashing en attente pour un agent."""
        events = []
        
        if target_did not in self.pending_slashes:
            return events
        
        pending = self.pending_slashes[target_did]
        
        # Vérifier le consensus (nombre de signalements similaires)
        similar_reports = {}
        for event in pending:
            key = (event.reason, event.severity)
            if key not in similar_reports:
                similar_reports[key] = []
            similar_reports[key].append(event)
        
        # Appliquer le slashing si consensus atteint
        for (reason, severity), report_list in similar_reports.items():
            if len(report_list) >= 3:  # Seuil de consensus
                # Prendre le premier rapport comme représentatif
                representative = report_list[0]
                
                # Appliquer le slashing
                await self._apply_slashing(representative)
                events.append(representative)
        
        # Nettoyer les pending slashes traités
        if events:
            self.pending_slashes[target_did] = [
                e for e in pending if e not in events
            ]
        
        return events
    
    def is_blacklisted(self, agent_did: str) -> bool:
        """Vérifie si un agent est blacklisté."""
        return agent_did in self.blacklist
    
    def get_slashing_history(self, agent_did: str) -> List[SlashingEvent]:
        """Récupère l'historique de slashing d'un agent."""
        return self.slashing_events.get(agent_did, [])
    
    def export_state(self) -> Dict[str, any]:
        """Exporte l'état du mécanisme de slashing."""
        return {
            "slashing_events": {
                agent_did: [e.to_dict() for e in events]
                for agent_did, events in self.slashing_events.items()
            },
            "pending_slashes": {
                agent_did: [e.to_dict() for e in events]
                for agent_did, events in self.pending_slashes.items()
            },
            "blacklist": list(self.blacklist),
            "slashing_parameters": {
                s.value: p for s, p in self.slashing_parameters.items()
            },
            "detection_thresholds": self.detection_thresholds,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }