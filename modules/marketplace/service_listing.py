"""
Sigui v3.0 — Service Listing System
Système de publication et de gestion de services pour agents IA.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from loguru import logger

from config import settings


class ServiceCategory(Enum):
    """Catégories de services."""
    DATA_ANALYSIS = "data_analysis"
    SMART_CONTRACT = "smart_contract"
    SECURITY = "security"
    TRADING = "trading"
    CONTENT = "content"
    AUTOMATION = "automation"
    RESEARCH = "research"
    CONSULTING = "consulting"


class ServiceStatus(Enum):
    """Statuts d'un service."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"


class ServiceType(Enum):
    """Types de services."""
    HOURLY = "hourly"
    FIXED_PRICE = "fixed_price"
    MILESTONE = "milestone"
    SUBSCRIPTION = "subscription"


@dataclass
class ServiceListing:
    """Listing d'un service dans le marketplace."""
    service_id: str
    agent_did: str
    title: str
    description: str
    category: ServiceCategory
    service_type: ServiceType
    price: float  # USDC
    duration_hours: Optional[float] = None  # Pour les services horaires
    deliverables: List[str] = field(default_factory=list)
    requirements: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    status: ServiceStatus = ServiceStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None
    total_orders: int = 0
    success_rate: float = 1.0
    avg_rating: float = 5.0
    review_count: int = 0
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit le listing en dictionnaire."""
        return {
            "service_id": self.service_id,
            "agent_did": self.agent_did,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "service_type": self.service_type.value,
            "price": self.price,
            "duration_hours": self.duration_hours,
            "deliverables": self.deliverables,
            "requirements": self.requirements,
            "tags": self.tags,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "total_orders": self.total_orders,
            "success_rate": self.success_rate,
            "avg_rating": self.avg_rating,
            "review_count": self.review_count,
            "metadata": self.metadata,
        }


class ServiceListingSystem:
    """Système de gestion des listings de services."""
    
    def __init__(self):
        self.services: Dict[str, ServiceListing] = {}
        self.category_index: Dict[ServiceCategory, Set[str]] = {
            category: set() for category in ServiceCategory
        }
        self.agent_index: Dict[str, Set[str]] = {}
        self.tag_index: Dict[str, Set[str]] = {}
        
        logger.info("ServiceListingSystem initialisé")
    
    async def create_service(
        self,
        agent_did: str,
        title: str,
        description: str,
        category: ServiceCategory,
        service_type: ServiceType,
        price: float,
        duration_hours: Optional[float] = None,
        deliverables: Optional[List[str]] = None,
        requirements: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, any]] = None
    ) -> ServiceListing:
        """Crée un nouveau service."""
        service_id = self._generate_service_id(agent_did)
        
        service = ServiceListing(
            service_id=service_id,
            agent_did=agent_did,
            title=title,
            description=description,
            category=category,
            service_type=service_type,
            price=price,
            duration_hours=duration_hours,
            deliverables=deliverables or [],
            requirements=requirements or [],
            tags=tags or [],
            metadata=metadata or {},
        )
        
        # Stocker le service
        self.services[service_id] = service
        
        # Mettre à jour les index
        self.category_index[category].add(service_id)
        
        if agent_did not in self.agent_index:
            self.agent_index[agent_did] = set()
        self.agent_index[agent_did].add(service_id)
        
        for tag in service.tags:
            if tag not in self.tag_index:
                self.tag_index[tag] = set()
            self.tag_index[tag].add(service_id)
        
        logger.info(f"Service créé: {service_id} par {agent_did}")
        return service
    
    async def publish_service(self, service_id: str) -> Optional[ServiceListing]:
        """Publie un service (le rend visible dans le marketplace)."""
        if service_id not in self.services:
            return None
        
        service = self.services[service_id]
        
        if service.status == ServiceStatus.PUBLISHED:
            return service
        
        # Vérifier les prérequis pour la publication
        if not self._validate_service_for_publication(service):
            logger.warning(f"Service {service_id} ne peut pas être publié")
            return None
        
        # Mettre à jour le statut
        service.status = ServiceStatus.PUBLISHED
        service.published_at = datetime.now(timezone.utc)
        service.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Service publié: {service_id}")
        return service
    
    async def update_service(
        self,
        service_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        category: Optional[ServiceCategory] = None,
        service_type: Optional[ServiceType] = None,
        price: Optional[float] = None,
        duration_hours: Optional[float] = None,
        deliverables: Optional[List[str]] = None,
        requirements: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, any]] = None
    ) -> Optional[ServiceListing]:
        """Met à jour un service."""
        if service_id not in self.services:
            return None
        
        service = self.services[service_id]
        
        # Mettre à jour les champs
        if title is not None:
            service.title = title
        
        if description is not None:
            service.description = description
        
        if category is not None and category != service.category:
            # Mettre à jour l'index des catégories
            self.category_index[service.category].discard(service_id)
            self.category_index[category].add(service_id)
            service.category = category
        
        if service_type is not None:
            service.service_type = service_type
        
        if price is not None:
            service.price = price
        
        if duration_hours is not None:
            service.duration_hours = duration_hours
        
        if deliverables is not None:
            service.deliverables = deliverables
        
        if requirements is not None:
            service.requirements = requirements
        
        if tags is not None:
            # Mettre à jour l'index des tags
            old_tags = set(service.tags)
            new_tags = set(tags)
            
            # Retirer des anciens tags
            for tag in old_tags - new_tags:
                if tag in self.tag_index:
                    self.tag_index[tag].discard(service_id)
            
            # Ajouter aux nouveaux tags
            for tag in new_tags - old_tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = set()
                self.tag_index[tag].add(service_id)
            
            service.tags = tags
        
        if metadata is not None:
            service.metadata.update(metadata)
        
        service.updated_at = datetime.now(timezone.utc)
        
        logger.debug(f"Service mis à jour: {service_id}")
        return service
    
    async def archive_service(self, service_id: str) -> Optional[ServiceListing]:
        """Archive un service (le retire du marketplace)."""
        if service_id not in self.services:
            return None
        
        service = self.services[service_id]
        service.status = ServiceStatus.ARCHIVED
        service.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Service archivé: {service_id}")
        return service
    
    async def search_services(
        self,
        query: Optional[str] = None,
        category: Optional[ServiceCategory] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        tags: Optional[List[str]] = None,
        agent_did: Optional[str] = None,
        service_type: Optional[ServiceType] = None,
        min_rating: float = 0.0,
        limit: int = 20,
        offset: int = 0
    ) -> List[ServiceListing]:
        """Recherche des services selon des critères."""
        candidates = set(self.services.keys())
        
        # Filtrer par statut (seulement publiés)
        candidates = {
            sid for sid in candidates
            if self.services[sid].status == ServiceStatus.PUBLISHED
        }
        
        # Filtrer par catégorie
        if category:
            candidates &= self.category_index[category]
        
        # Filtrer par agent
        if agent_did and agent_did in self.agent_index:
            candidates &= self.agent_index[agent_did]
        
        # Filtrer par tags
        if tags:
            for tag in tags:
                if tag in self.tag_index:
                    candidates &= self.tag_index[tag]
        
        # Filtrer par type de service
        if service_type:
            candidates = {
                sid for sid in candidates
                if self.services[sid].service_type == service_type
            }
        
        # Filtrer par prix
        if min_price is not None:
            candidates = {
                sid for sid in candidates
                if self.services[sid].price >= min_price
            }
        
        if max_price is not None:
            candidates = {
                sid for sid in candidates
                if self.services[sid].price <= max_price
            }
        
        # Filtrer par rating
        if min_rating > 0:
            candidates = {
                sid for sid in candidates
                if self.services[sid].avg_rating >= min_rating
            }
        
        # Recherche textuelle
        if query:
            query_lower = query.lower()
            text_candidates = set()
            
            for sid in candidates:
                service = self.services[sid]
                
                # Rechercher dans le titre et la description
                if (query_lower in service.title.lower() or
                    query_lower in service.description.lower() or
                    any(query_lower in tag.lower() for tag in service.tags)):
                    text_candidates.add(sid)
            
            candidates = text_candidates
        
        # Convertir en profils et trier
        service_list = [self.services[sid] for sid in candidates]
        
        # Trier par pertinence (rating * succès_rate)
        service_list.sort(
            key=lambda s: s.avg_rating * s.success_rate,
            reverse=True
        )
        
        # Appliquer la pagination
        start = offset
        end = offset + limit
        
        return service_list[start:end]
    
    async def update_service_statistics(
        self,
        service_id: str,
        success: bool,
        rating: Optional[float] = None
    ) -> Optional[ServiceListing]:
        """Met à jour les statistiques d'un service après une commande."""
        if service_id not in self.services:
            return None
        
        service = self.services[service_id]
        
        # Mettre à jour les statistiques
        service.total_orders += 1
        
        if success:
            service.success_rate = min(1.0, service.success_rate + 0.01)
        else:
            service.success_rate = max(0.0, service.success_rate - 0.05)
        
        if rating is not None:
            # Mettre à jour la moyenne des ratings
            total_rating = service.avg_rating * service.review_count
            service.review_count += 1
            service.avg_rating = (total_rating + rating) / service.review_count
        
        service.updated_at = datetime.now(timezone.utc)
        
        logger.debug(f"Statistiques mises à jour pour le service {service_id}")
        return service
    
    def get_service(self, service_id: str) -> Optional[ServiceListing]:
        """Récupère un service par son ID."""
        return self.services.get(service_id)
    
    def get_agent_services(self, agent_did: str) -> List[ServiceListing]:
        """Récupère tous les services d'un agent."""
        if agent_did not in self.agent_index:
            return []
        
        return [
            self.services[sid]
            for sid in self.agent_index[agent_did]
        ]
    
    def get_popular_services(
        self,
        category: Optional[ServiceCategory] = None,
        limit: int = 10
    ) -> List[ServiceListing]:
        """Récupère les services les plus populaires."""
        candidates = set(self.services.keys())
        
        # Filtrer par catégorie
        if category:
            candidates &= self.category_index[category]
        
        # Filtrer par statut (seulement publiés)
        candidates = {
            sid for sid in candidates
            if self.services[sid].status == ServiceStatus.PUBLISHED
        }
        
        # Trier par popularité (orders * rating)
        service_list = [self.services[sid] for sid in candidates]
        service_list.sort(
            key=lambda s: s.total_orders * s.avg_rating,
            reverse=True
        )
        
        return service_list[:limit]
    
    def _generate_service_id(self, agent_did: str) -> str:
        """Génère un ID unique pour un service."""
        import hashlib
        import time
        
        timestamp = str(time.time_ns())
        data = f"{agent_did}:{timestamp}"
        
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _validate_service_for_publication(self, service: ServiceListing) -> bool:
        """Valide un service pour la publication."""
        # Vérifier les champs requis
        if not service.title or not service.description:
            return False
        
        # Vérifier le prix
        if service.price <= 0:
            return False
        
        # Vérifier la durée pour les services horaires
        if (service.service_type == ServiceType.HOURLY and 
            (service.duration_hours is None or service.duration_hours <= 0)):
            return False
        
        # Vérifier les livrables pour les services à prix fixe
        if (service.service_type == ServiceType.FIXED_PRICE and
            not service.deliverables):
            return False
        
        return True
    
    def export_service_data(self) -> Dict[str, any]:
        """Exporte toutes les données des services."""
        return {
            "services": {
                sid: service.to_dict()
                for sid, service in self.services.items()
            },
            "category_index": {
                category.value: list(service_ids)
                for category, service_ids in self.category_index.items()
            },
            "agent_index": {
                agent_did: list(service_ids)
                for agent_did, service_ids in self.agent_index.items()
            },
            "tag_index": {
                tag: list(service_ids)
                for tag, service_ids in self.tag_index.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }