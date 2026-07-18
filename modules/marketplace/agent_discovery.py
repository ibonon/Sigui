"""
Sigui v3.0 — Agent Discovery Service
Service de découverte d'agents basé sur la réputation et les compétences.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from loguru import logger

from config import settings
from modules.reputation.reputation_oracle import ReputationOracle


class AgentSkill(Enum):
    """Compétences des agents."""
    DATA_ANALYSIS = "data_analysis"
    SMART_CONTRACT_DEV = "smart_contract_dev"
    SECURITY_AUDIT = "security_audit"
    TRADING = "trading"
    CONTENT_CREATION = "content_creation"
    CUSTOMER_SUPPORT = "customer_support"
    RESEARCH = "research"
    AUTOMATION = "automation"


class AgentAvailability(Enum):
    """Disponibilité des agents."""
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"


@dataclass
class AgentProfile:
    """Profil d'un agent dans le marketplace."""
    agent_did: str
    name: str
    description: str
    skills: List[AgentSkill]
    hourly_rate: float  # USDC par heure
    availability: AgentAvailability
    reputation_score: float
    total_completed_jobs: int
    success_rate: float  # 0.0 à 1.0
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit le profil en dictionnaire."""
        return {
            "agent_did": self.agent_did,
            "name": self.name,
            "description": self.description,
            "skills": [s.value for s in self.skills],
            "hourly_rate": self.hourly_rate,
            "availability": self.availability.value,
            "reputation_score": self.reputation_score,
            "total_completed_jobs": self.total_completed_jobs,
            "success_rate": self.success_rate,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class AgentDiscovery:
    """Service de découverte d'agents."""
    
    def __init__(self, reputation_oracle: ReputationOracle):
        self.reputation_oracle = reputation_oracle
        self.agent_profiles: Dict[str, AgentProfile] = {}
        self.skill_index: Dict[AgentSkill, Set[str]] = {
            skill: set() for skill in AgentSkill
        }
        self.availability_index: Dict[AgentAvailability, Set[str]] = {
            status: set() for status in AgentAvailability
        }
        
        logger.info("AgentDiscovery initialisé")
    
    async def register_agent(
        self,
        agent_did: str,
        name: str,
        description: str,
        skills: List[AgentSkill],
        hourly_rate: float,
        metadata: Optional[Dict[str, any]] = None
    ) -> AgentProfile:
        """Enregistre un agent dans le marketplace."""
        # Calculer le score de réputation
        reputation_score = await self.reputation_oracle.calculate_composite_score(agent_did)
        
        now = datetime.now(timezone.utc)
        
        profile = AgentProfile(
            agent_did=agent_did,
            name=name,
            description=description,
            skills=skills,
            hourly_rate=hourly_rate,
            availability=AgentAvailability.AVAILABLE,
            reputation_score=reputation_score,
            total_completed_jobs=0,
            success_rate=1.0,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        
        # Stocker le profil
        self.agent_profiles[agent_did] = profile
        
        # Mettre à jour les index
        for skill in skills:
            self.skill_index[skill].add(agent_did)
        
        self.availability_index[AgentAvailability.AVAILABLE].add(agent_did)
        
        logger.info(f"Agent enregistré: {agent_did} ({name})")
        return profile
    
    async def update_agent_profile(
        self,
        agent_did: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        skills: Optional[List[AgentSkill]] = None,
        hourly_rate: Optional[float] = None,
        availability: Optional[AgentAvailability] = None,
        metadata: Optional[Dict[str, any]] = None
    ) -> Optional[AgentProfile]:
        """Met à jour le profil d'un agent."""
        if agent_did not in self.agent_profiles:
            logger.warning(f"Agent non trouvé: {agent_did}")
            return None
        
        profile = self.agent_profiles[agent_did]
        
        # Mettre à jour les champs
        if name is not None:
            profile.name = name
        
        if description is not None:
            profile.description = description
        
        if skills is not None:
            # Mettre à jour l'index des compétences
            old_skills = set(profile.skills)
            new_skills = set(skills)
            
            # Retirer des anciennes compétences
            for skill in old_skills - new_skills:
                self.skill_index[skill].discard(agent_did)
            
            # Ajouter aux nouvelles compétences
            for skill in new_skills - old_skills:
                self.skill_index[skill].add(agent_did)
            
            profile.skills = skills
        
        if hourly_rate is not None:
            profile.hourly_rate = hourly_rate
        
        if availability is not None:
            # Mettre à jour l'index de disponibilité
            old_status = profile.availability
            self.availability_index[old_status].discard(agent_did)
            
            profile.availability = availability
            self.availability_index[availability].add(agent_did)
        
        if metadata is not None:
            profile.metadata.update(metadata)
        
        # Mettre à jour le score de réputation
        profile.reputation_score = await self.reputation_oracle.calculate_composite_score(agent_did)
        profile.updated_at = datetime.now(timezone.utc)
        
        logger.debug(f"Profil mis à jour pour {agent_did}")
        return profile
    
    async def search_agents(
        self,
        skills: Optional[List[AgentSkill]] = None,
        min_reputation: float = 0.0,
        max_hourly_rate: Optional[float] = None,
        availability: Optional[AgentAvailability] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[AgentProfile]:
        """Recherche des agents selon des critères."""
        candidates = set(self.agent_profiles.keys())
        
        # Filtrer par compétences
        if skills:
            skill_sets = [self.skill_index[skill] for skill in skills]
            if skill_sets:
                candidates &= set.union(*skill_sets)
        
        # Filtrer par disponibilité
        if availability:
            candidates &= self.availability_index[availability]
        
        # Filtrer par réputation et taux horaire
        filtered_profiles = []
        for agent_did in candidates:
            profile = self.agent_profiles[agent_did]
            
            if profile.reputation_score < min_reputation:
                continue
            
            if max_hourly_rate is not None and profile.hourly_rate > max_hourly_rate:
                continue
            
            filtered_profiles.append(profile)
        
        # Trier par score de réputation (descendant)
        filtered_profiles.sort(key=lambda p: p.reputation_score, reverse=True)
        
        # Appliquer la pagination
        start = offset
        end = offset + limit
        
        return filtered_profiles[start:end]
    
    async def get_agent_recommendations(
        self,
        requester_did: str,
        context: Optional[Dict[str, any]] = None,
        limit: int = 10
    ) -> List[AgentProfile]:
        """Recommandation d'agents basée sur le contexte et l'historique."""
        recommendations = []
        
        try:
            # 1. Agents avec des compétences complémentaires
            requester_profile = self.agent_profiles.get(requester_did)
            if requester_profile:
                # Chercher des agents avec des compétences différentes
                for agent_did, profile in self.agent_profiles.items():
                    if agent_did == requester_did:
                        continue
                    
                    # Vérifier la complémentarité des compétences
                    common_skills = set(profile.skills) & set(requester_profile.skills)
                    if len(common_skills) < 2:  # Pas trop similaires
                        recommendations.append(profile)
            
            # 2. Agents avec une bonne réputation
            if not recommendations:
                all_profiles = list(self.agent_profiles.values())
                all_profiles.sort(key=lambda p: p.reputation_score, reverse=True)
                
                # Exclure le demandeur
                recommendations = [
                    p for p in all_profiles 
                    if p.agent_did != requester_did
                ]
            
            # 3. Filtrer par disponibilité
            recommendations = [
                p for p in recommendations
                if p.availability == AgentAvailability.AVAILABLE
            ]
            
            # Limiter les résultats
            return recommendations[:limit]
        
        except Exception as e:
            logger.error(f"Erreur lors de la génération de recommandations: {e}")
            return []
    
    async def update_job_statistics(
        self,
        agent_did: str,
        success: bool
    ) -> Optional[AgentProfile]:
        """Met à jour les statistiques d'emploi d'un agent."""
        if agent_did not in self.agent_profiles:
            return None
        
        profile = self.agent_profiles[agent_did]
        
        # Mettre à jour les statistiques
        profile.total_completed_jobs += 1
        
        # Calculer le nouveau taux de réussite
        # (simplifié - en production, il faudrait un historique plus détaillé)
        if success:
            # Augmenter légèrement le taux de réussite
            profile.success_rate = min(1.0, profile.success_rate + 0.01)
        else:
            # Diminuer le taux de réussite
            profile.success_rate = max(0.0, profile.success_rate - 0.05)
        
        profile.updated_at = datetime.now(timezone.utc)
        
        logger.debug(f"Statistiques mises à jour pour {agent_did}: succès={success}")
        return profile
    
    def get_agent_profile(self, agent_did: str) -> Optional[AgentProfile]:
        """Récupère le profil d'un agent."""
        return self.agent_profiles.get(agent_did)
    
    def get_top_agents(
        self,
        skill: Optional[AgentSkill] = None,
        limit: int = 10
    ) -> List[AgentProfile]:
        """Récupère les meilleurs agents selon un critère."""
        candidates = set(self.agent_profiles.keys())
        
        if skill:
            candidates &= self.skill_index[skill]
        
        profiles = [self.agent_profiles[did] for did in candidates]
        profiles.sort(key=lambda p: p.reputation_score, reverse=True)
        
        return profiles[:limit]
    
    def export_marketplace_data(self) -> Dict[str, any]:
        """Exporte toutes les données du marketplace."""
        return {
            "agent_profiles": {
                did: profile.to_dict()
                for did, profile in self.agent_profiles.items()
            },
            "skill_index": {
                skill.value: list(agent_dids)
                for skill, agent_dids in self.skill_index.items()
            },
            "availability_index": {
                status.value: list(agent_dids)
                for status, agent_dids in self.availability_index.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }