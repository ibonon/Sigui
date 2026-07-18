"""
Sigui v3.0 — Marketplace API
API FastAPI pour le marketplace d'agents.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field, validator
from loguru import logger

from modules.marketplace.agent_discovery import AgentDiscovery, AgentProfile, AgentSkill, AgentAvailability
from modules.marketplace.service_listing import ServiceListingSystem, ServiceListing, ServiceCategory, ServiceType, ServiceStatus
from modules.marketplace.escrow_system import EscrowSystem, EscrowContract, EscrowStatus
from modules.marketplace.rating_system import RatingSystem, Rating, RatingDimension, ReviewStatus
from modules.reputation.reputation_oracle import ReputationOracle


# ────────────────────────────────────────────────────────────────────────────────
# Pydantic Models
# ────────────────────────────────────────────────────────────────────────────────

class AgentRegistrationRequest(BaseModel):
    """Requête d'enregistrement d'agent."""
    agent_did: str = Field(..., description="DID de l'agent")
    name: str = Field(..., description="Nom de l'agent", min_length=2, max_length=100)
    description: str = Field(..., description="Description de l'agent", min_length=10, max_length=1000)
    skills: List[str] = Field(..., description="Liste des compétences")
    hourly_rate: float = Field(..., description="Taux horaire en USDC", gt=0)
    metadata: Optional[Dict[str, any]] = Field(default_factory=dict, description="Métadonnées supplémentaires")
    
    @validator('skills')
    def validate_skills(cls, v):
        """Valide les compétences."""
        valid_skills = [skill.value for skill in AgentSkill]
        for skill in v:
            if skill not in valid_skills:
                raise ValueError(f"Compétence invalide: {skill}. Valides: {valid_skills}")
        return v


class ServiceCreationRequest(BaseModel):
    """Requête de création de service."""
    agent_did: str = Field(..., description="DID de l'agent fournisseur")
    title: str = Field(..., description="Titre du service", min_length=5, max_length=200)
    description: str = Field(..., description="Description du service", min_length=20, max_length=5000)
    category: str = Field(..., description="Catégorie du service")
    service_type: str = Field(..., description="Type de service")
    price: float = Field(..., description="Prix en USDC", gt=0)
    duration_hours: Optional[float] = Field(None, description="Durée en heures (pour services horaires)", gt=0)
    deliverables: Optional[List[str]] = Field(default_factory=list, description="Livrables")
    requirements: Optional[List[str]] = Field(default_factory=list, description="Prérequis")
    tags: Optional[List[str]] = Field(default_factory=list, description="Tags")
    metadata: Optional[Dict[str, any]] = Field(default_factory=dict, description="Métadonnées")
    
    @validator('category')
    def validate_category(cls, v):
        """Valide la catégorie."""
        valid_categories = [cat.value for cat in ServiceCategory]
        if v not in valid_categories:
            raise ValueError(f"Catégorie invalide: {v}. Valides: {valid_categories}")
        return v
    
    @validator('service_type')
    def validate_service_type(cls, v):
        """Valide le type de service."""
        valid_types = [stype.value for stype in ServiceType]
        if v not in valid_types:
            raise ValueError(f"Type de service invalide: {v}. Valides: {valid_types}")
        return v


class EscrowCreationRequest(BaseModel):
    """Requête de création d'escrow."""
    client_did: str = Field(..., description="DID du client")
    provider_did: str = Field(..., description="DID du fournisseur")
    service_id: str = Field(..., description="ID du service")
    amount: float = Field(..., description="Montant en USDC", gt=0)
    metadata: Optional[Dict[str, any]] = Field(default_factory=dict, description="Métadonnées")


class RatingSubmissionRequest(BaseModel):
    """Requête de soumission d'évaluation."""
    escrow_id: str = Field(..., description="ID de l'escrow")
    reviewer_did: str = Field(..., description="DID de l'évaluateur")
    reviewee_did: str = Field(..., description="DID de l'évalué")
    service_id: str = Field(..., description="ID du service")
    overall_score: float = Field(..., description="Score global (1.0-5.0)", ge=1.0, le=5.0)
    dimension_scores: Dict[str, float] = Field(..., description="Scores par dimension")
    comment: Optional[str] = Field(None, description="Commentaire", min_length=10, max_length=1000)
    metadata: Optional[Dict[str, any]] = Field(default_factory=dict, description="Métadonnées")
    
    @validator('dimension_scores')
    def validate_dimension_scores(cls, v):
        """Valide les scores par dimension."""
        valid_dimensions = [dim.value for dim in RatingDimension]
        for dim, score in v.items():
            if dim not in valid_dimensions:
                raise ValueError(f"Dimension invalide: {dim}. Valides: {valid_dimensions}")
            if not 1.0 <= score <= 5.0:
                raise ValueError(f"Score invalide pour {dim}: {score}. Doit être entre 1.0 et 5.0")
        return v


class SearchQuery(BaseModel):
    """Requête de recherche."""
    query: Optional[str] = Field(None, description="Recherche textuelle")
    category: Optional[str] = Field(None, description="Catégorie")
    min_price: Optional[float] = Field(None, description="Prix minimum", ge=0)
    max_price: Optional[float] = Field(None, description="Prix maximum", ge=0)
    tags: Optional[List[str]] = Field(None, description="Tags")
    agent_did: Optional[str] = Field(None, description="DID de l'agent")
    service_type: Optional[str] = Field(None, description="Type de service")
    min_rating: float = Field(0.0, description="Rating minimum", ge=0.0, le=5.0)
    limit: int = Field(20, description="Limite de résultats", ge=1, le=100)
    offset: int = Field(0, description="Offset de pagination", ge=0)


# ────────────────────────────────────────────────────────────────────────────────
# FastAPI Router
# ────────────────────────────────────────────────────────────────────────────────

class MarketplaceAPI:
    """API FastAPI pour le marketplace."""
    
    def __init__(
        self,
        agent_discovery: AgentDiscovery,
        service_listing: ServiceListingSystem,
        escrow_system: EscrowSystem,
        rating_system: RatingSystem,
        reputation_oracle: ReputationOracle
    ):
        self.agent_discovery = agent_discovery
        self.service_listing = service_listing
        self.escrow_system = escrow_system
        self.rating_system = rating_system
        self.reputation_oracle = reputation_oracle
        
        self.router = APIRouter(prefix="/marketplace", tags=["marketplace"])
        self._setup_routes()
        
        logger.info("MarketplaceAPI initialisé")
    
    def _setup_routes(self):
        """Configure les routes de l'API."""
        
        @self.router.post("/agents/register", response_model=Dict[str, any])
        async def register_agent(request: AgentRegistrationRequest):
            """Enregistre un agent dans le marketplace."""
            try:
                # Convertir les compétences
                skills = [AgentSkill(skill) for skill in request.skills]
                
                # Enregistrer l'agent
                profile = await self.agent_discovery.register_agent(
                    agent_did=request.agent_did,
                    name=request.name,
                    description=request.description,
                    skills=skills,
                    hourly_rate=request.hourly_rate,
                    metadata=request.metadata,
                )
                
                return {
                    "success": True,
                    "agent_profile": profile.to_dict(),
                    "message": "Agent enregistré avec succès",
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de l'enregistrement de l'agent: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/agents/{agent_did}", response_model=Dict[str, any])
        async def get_agent_profile(agent_did: str):
            """Récupère le profil d'un agent."""
            profile = self.agent_discovery.get_agent_profile(agent_did)
            
            if not profile:
                raise HTTPException(status_code=404, detail="Agent non trouvé")
            
            # Récupérer les services de l'agent
            services = self.service_listing.get_agent_services(agent_did)
            
            # Récupérer les évaluations de l'agent
            ratings = await self.rating_system.get_agent_ratings(agent_did)
            
            # Récupérer le résumé des évaluations
            rating_summary = await self.rating_system.get_rating_summary(agent_did, "agent")
            
            return {
                "agent_profile": profile.to_dict(),
                "services": [s.to_dict() for s in services],
                "ratings": [r.to_dict() for r in ratings],
                "rating_summary": rating_summary.to_dict() if rating_summary else None,
            }
        
        @self.router.post("/services/create", response_model=Dict[str, any])
        async def create_service(request: ServiceCreationRequest):
            """Crée un nouveau service."""
            try:
                # Convertir les enums
                category = ServiceCategory(request.category)
                service_type = ServiceType(request.service_type)
                
                # Créer le service
                service = await self.service_listing.create_service(
                    agent_did=request.agent_did,
                    title=request.title,
                    description=request.description,
                    category=category,
                    service_type=service_type,
                    price=request.price,
                    duration_hours=request.duration_hours,
                    deliverables=request.deliverables,
                    requirements=request.requirements,
                    tags=request.tags,
                    metadata=request.metadata,
                )
                
                return {
                    "success": True,
                    "service": service.to_dict(),
                    "message": "Service créé avec succès",
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de la création du service: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/services/{service_id}/publish", response_model=Dict[str, any])
        async def publish_service(service_id: str):
            """Publie un service."""
            service = await self.service_listing.publish_service(service_id)
            
            if not service:
                raise HTTPException(status_code=404, detail="Service non trouvé ou non publiable")
            
            return {
                "success": True,
                "service": service.to_dict(),
                "message": "Service publié avec succès",
            }
        
        @self.router.get("/services/{service_id}", response_model=Dict[str, any])
        async def get_service(service_id: str):
            """Récupère les détails d'un service."""
            service = self.service_listing.get_service(service_id)
            
            if not service:
                raise HTTPException(status_code=404, detail="Service non trouvé")
            
            # Récupérer le profil de l'agent
            agent_profile = self.agent_discovery.get_agent_profile(service.agent_did)
            
            # Récupérer les évaluations du service
            ratings = await self.rating_system.get_service_ratings(service_id)
            
            # Récupérer le résumé des évaluations
            rating_summary = await self.rating_system.get_rating_summary(service_id, "service")
            
            return {
                "service": service.to_dict(),
                "agent_profile": agent_profile.to_dict() if agent_profile else None,
                "ratings": [r.to_dict() for r in ratings],
                "rating_summary": rating_summary.to_dict() if rating_summary else None,
            }
        
        @self.router.post("/search/services", response_model=Dict[str, any])
        async def search_services(query: SearchQuery):
            """Recherche des services."""
            try:
                # Convertir la catégorie
                category = None
                if query.category:
                    category = ServiceCategory(query.category)
                
                # Convertir le type de service
                service_type = None
                if query.service_type:
                    service_type = ServiceType(query.service_type)
                
                # Effectuer la recherche
                services = await self.service_listing.search_services(
                    query=query.query,
                    category=category,
                    min_price=query.min_price,
                    max_price=query.max_price,
                    tags=query.tags,
                    agent_did=query.agent_did,
                    service_type=service_type,
                    min_rating=query.min_rating,
                    limit=query.limit,
                    offset=query.offset,
                )
                
                return {
                    "success": True,
                    "services": [s.to_dict() for s in services],
                    "total_results": len(services),
                    "query": query.dict(),
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de la recherche de services: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/search/agents", response_model=Dict[str, any])
        async def search_agents(query: SearchQuery):
            """Recherche des agents."""
            try:
                # Convertir les compétences
                skills = None
                if query.tags:
                    skills = [AgentSkill(tag) for tag in query.tags]
                
                # Effectuer la recherche
                agents = await self.agent_discovery.search_agents(
                    skills=skills,
                    min_reputation=query.min_rating,
                    max_hourly_rate=query.max_price,
                    availability=AgentAvailability.AVAILABLE,
                    limit=query.limit,
                    offset=query.offset,
                )
                
                return {
                    "success": True,
                    "agents": [a.to_dict() for a in agents],
                    "total_results": len(agents),
                    "query": query.dict(),
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de la recherche d'agents: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/escrows/create", response_model=Dict[str, any])
        async def create_escrow(request: EscrowCreationRequest):
            """Crée un nouvel escrow."""
            try:
                # Créer l'escrow
                escrow = await self.escrow_system.create_escrow(
                    client_did=request.client_did,
                    provider_did=request.provider_did,
                    service_id=request.service_id,
                    amount=request.amount,
                    metadata=request.metadata,
                )
                
                return {
                    "success": True,
                    "escrow": escrow.to_dict(),
                    "message": "Escrow créé avec succès",
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de la création de l'escrow: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/escrows/{escrow_id}/fund", response_model=Dict[str, any])
        async def fund_escrow(
            escrow_id: str,
            transaction_hash: str = Body(..., embed=True),
            contract_address: Optional[str] = Body(None, embed=True)
        ):
            """Fonde un escrow."""
            escrow = await self.escrow_system.fund_escrow(
                escrow_id=escrow_id,
                transaction_hash=transaction_hash,
                contract_address=contract_address,
            )
            
            if not escrow:
                raise HTTPException(status_code=404, detail="Escrow non trouvé ou non fondable")
            
            return {
                "success": True,
                "escrow": escrow.to_dict(),
                "message": "Escrow fondé avec succès",
            }
        
        @self.router.post("/escrows/{escrow_id}/complete", response_model=Dict[str, any])
        async def complete_escrow(
            escrow_id: str,
            release_transaction_hash: Optional[str] = Body(None, embed=True)
        ):
            """Termine un service et libère les fonds."""
            escrow = await self.escrow_system.complete_service(
                escrow_id=escrow_id,
                release_transaction_hash=release_transaction_hash,
            )
            
            if not escrow:
                raise HTTPException(status_code=404, detail="Escrow non trouvé ou non terminable")
            
            return {
                "success": True,
                "escrow": escrow.to_dict(),
                "message": "Service terminé avec succès",
            }
        
        @self.router.post("/ratings/submit", response_model=Dict[str, any])
        async def submit_rating(request: RatingSubmissionRequest):
            """Soumet une nouvelle évaluation."""
            try:
                # Convertir les scores par dimension
                dimension_scores = {
                    RatingDimension(dim): score
                    for dim, score in request.dimension_scores.items()
                }
                
                # Soumettre l'évaluation
                rating = await self.rating_system.submit_rating(
                    escrow_id=request.escrow_id,
                    reviewer_did=request.reviewer_did,
                    reviewee_did=request.reviewee_did,
                    service_id=request.service_id,
                    overall_score=request.overall_score,
                    dimension_scores=dimension_scores,
                    comment=request.comment,
                    metadata=request.metadata,
                )
                
                if not rating:
                    raise HTTPException(status_code=400, detail="Évaluation invalide")
                
                return {
                    "success": True,
                    "rating": rating.to_dict(),
                    "message": "Évaluation soumise avec succès",
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de la soumission de l'évaluation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/stats", response_model=Dict[str, any])
        async def get_marketplace_stats():
            """Récupère les statistiques du marketplace."""
            try:
                # Statistiques des agents
                total_agents = len(self.agent_discovery.agent_profiles)
                available_agents = len(self.agent_discovery.availability_index[AgentAvailability.AVAILABLE])
                
                # Statistiques des services
                total_services = len(self.service_listing.services)
                published_services = len([
                    s for s in self.service_listing.services.values()
                    if s.status == ServiceStatus.PUBLISHED
                ])
                
                # Statistiques des escrows
                total_escrows = len(self.escrow_system.escrows)
                completed_escrows = len([
                    e for e in self.escrow_system.escrows.values()
                    if e.status == EscrowStatus.COMPLETED
                ])
                
                # Statistiques des évaluations
                total_ratings = len(self.rating_system.ratings)
                published_ratings = len([
                    r for r in self.rating_system.ratings.values()
                    if r.status == ReviewStatus.PUBLISHED
                ])
                
                # Top catégories
                category_counts = {}
                for service in self.service_listing.services.values():
                    if service.status == ServiceStatus.PUBLISHED:
                        category = service.category.value
                        category_counts[category] = category_counts.get(category, 0) + 1
                
                top_categories = sorted(
                    category_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
                
                return {
                    "success": True,
                    "stats": {
                        "agents": {
                            "total": total_agents,
                            "available": available_agents,
                            "unavailable": total_agents - available_agents,
                        },
                        "services": {
                            "total": total_services,
                            "published": published_services,
                            "draft": total_services - published_services,
                        },
                        "escrows": {
                            "total": total_escrows,
                            "completed": completed_escrows,
                            "in_progress": total_escrows - completed_escrows,
                        },
                        "ratings": {
                            "total": total_ratings,
                            "published": published_ratings,
                            "pending": total_ratings - published_ratings,
                        },
                        "top_categories": top_categories,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                }
            
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des statistiques: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/health", response_model=Dict[str, any])
        async def health_check():
            """Vérifie la santé du marketplace."""
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "agent_discovery": "operational",
                    "service_listing": "operational",
                    "escrow_system": "operational",
                    "rating_system": "operational",
                },
            }