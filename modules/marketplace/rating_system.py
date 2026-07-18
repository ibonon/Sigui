"""
Sigui v3.0 — Rating System
Système d'évaluation et de review pour les services du marketplace.
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


class RatingDimension(Enum):
    """Dimensions d'évaluation."""
    QUALITY = "quality"
    TIMELINESS = "timeliness"
    COMMUNICATION = "communication"
    PROFESSIONALISM = "professionalism"
    VALUE = "value"


class ReviewStatus(Enum):
    """Statuts d'une review."""
    PENDING = "pending"  # En attente de validation
    PUBLISHED = "published"  # Publiée
    HIDDEN = "hidden"  # Masquée (modération)
    REMOVED = "removed"  # Supprimée


@dataclass
class Rating:
    """Évaluation d'un service."""
    rating_id: str
    escrow_id: str
    reviewer_did: str  # Celui qui évalue
    reviewee_did: str  # Celui qui est évalué
    service_id: str
    overall_score: float  # 1.0 à 5.0
    dimension_scores: Dict[RatingDimension, float]  # Scores par dimension
    comment: Optional[str] = None
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    published_at: Optional[datetime] = None
    helpful_count: int = 0
    reported_count: int = 0
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit l'évaluation en dictionnaire."""
        return {
            "rating_id": self.rating_id,
            "escrow_id": self.escrow_id,
            "reviewer_did": self.reviewer_did,
            "reviewee_did": self.reviewee_did,
            "service_id": self.service_id,
            "overall_score": self.overall_score,
            "dimension_scores": {d.value: s for d, s in self.dimension_scores.items()},
            "comment": self.comment,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "helpful_count": self.helpful_count,
            "reported_count": self.reported_count,
            "metadata": self.metadata,
        }


@dataclass
class RatingSummary:
    """Résumé des évaluations pour un agent ou un service."""
    entity_id: str  # agent_did ou service_id
    entity_type: str  # "agent" ou "service"
    total_ratings: int
    avg_overall_score: float
    dimension_avgs: Dict[RatingDimension, float]
    score_distribution: Dict[int, int]  # 1-5 étoiles
    recent_trend: float  # Variation sur 30 jours
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit le résumé en dictionnaire."""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "total_ratings": self.total_ratings,
            "avg_overall_score": self.avg_overall_score,
            "dimension_avgs": {d.value: s for d, s in self.dimension_avgs.items()},
            "score_distribution": self.score_distribution,
            "recent_trend": self.recent_trend,
            "created_at": self.created_at.isoformat(),
        }


class RatingSystem:
    """Système d'évaluation décentralisé."""
    
    def __init__(self):
        self.ratings: Dict[str, Rating] = {}
        self.rating_summaries: Dict[str, RatingSummary] = {}
        
        # Indexes
        self.reviewee_index: Dict[str, Set[str]] = {}  # reviewee_did -> rating_ids
        self.service_index: Dict[str, Set[str]] = {}  # service_id -> rating_ids
        
        # Paramètres
        self.min_comment_length = 10
        self.max_comment_length = 1000
        self.auto_publish_delay_hours = 24  # Auto-publication après 24h
        
        logger.info("RatingSystem initialisé")
    
    async def submit_rating(
        self,
        escrow_id: str,
        reviewer_did: str,
        reviewee_did: str,
        service_id: str,
        overall_score: float,
        dimension_scores: Dict[RatingDimension, float],
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, any]] = None
    ) -> Optional[Rating]:
        """Soumet une nouvelle évaluation."""
        # Valider les scores
        if not self._validate_scores(overall_score, dimension_scores):
            logger.warning(f"Scores invalides: overall={overall_score}, dimensions={dimension_scores}")
            return None
        
        # Valider le commentaire
        if comment and not self._validate_comment(comment):
            logger.warning(f"Commentaire invalide: longueur={len(comment)}")
            return None
        
        # Générer un ID unique
        rating_id = self._generate_rating_id(escrow_id, reviewer_did)
        
        # Créer l'évaluation
        rating = Rating(
            rating_id=rating_id,
            escrow_id=escrow_id,
            reviewer_did=reviewer_did,
            reviewee_did=reviewee_did,
            service_id=service_id,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            comment=comment,
            status=ReviewStatus.PENDING,
            metadata=metadata or {},
        )
        
        # Stocker l'évaluation
        self.ratings[rating_id] = rating
        
        # Mettre à jour les index
        if reviewee_did not in self.reviewee_index:
            self.reviewee_index[reviewee_did] = set()
        self.reviewee_index[reviewee_did].add(rating_id)
        
        if service_id not in self.service_index:
            self.service_index[service_id] = set()
        self.service_index[service_id].add(rating_id)
        
        # Mettre à jour les résumés
        await self._update_rating_summaries(reviewee_did, "agent")
        await self._update_rating_summaries(service_id, "service")
        
        logger.info(f"Évaluation soumise: {rating_id} par {reviewer_did}")
        return rating
    
    async def publish_rating(self, rating_id: str) -> Optional[Rating]:
        """Publie une évaluation (la rend visible)."""
        if rating_id not in self.ratings:
            return None
        
        rating = self.ratings[rating_id]
        
        if rating.status != ReviewStatus.PENDING:
            logger.warning(f"Évaluation {rating_id} n'est pas en attente: {rating.status}")
            return None
        
        # Vérifier la modération automatique
        if not await self._auto_moderate(rating):
            rating.status = ReviewStatus.HIDDEN
            logger.warning(f"Évaluation {rating_id} masquée par la modération automatique")
        else:
            rating.status = ReviewStatus.PUBLISHED
            rating.published_at = datetime.now(timezone.utc)
        
        rating.metadata["moderated_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Évaluation publiée: {rating_id}")
        return rating
    
    async def report_rating(
        self,
        rating_id: str,
        reporter_did: str,
        reason: str,
        details: Optional[str] = None
    ) -> bool:
        """Signale une évaluation inappropriée."""
        if rating_id not in self.ratings:
            return False
        
        rating = self.ratings[rating_id]
        
        # Incrémenter le compteur de signalements
        rating.reported_count += 1
        
        # Ajouter aux métadonnées
        if "reports" not in rating.metadata:
            rating.metadata["reports"] = []
        
        rating.metadata["reports"].append({
            "reporter_did": reporter_did,
            "reason": reason,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Vérifier si l'évaluation doit être masquée
        if rating.reported_count >= 3:
            rating.status = ReviewStatus.HIDDEN
            rating.metadata["auto_hidden_at"] = datetime.now(timezone.utc).isoformat()
            logger.warning(f"Évaluation {rating_id} masquée après {rating.reported_count} signalements")
        
        logger.info(f"Évaluation signalée: {rating_id} par {reporter_did}")
        return True
    
    async def mark_helpful(
        self,
        rating_id: str,
        voter_did: str
    ) -> Optional[Rating]:
        """Marque une évaluation comme utile."""
        if rating_id not in self.ratings:
            return None
        
        rating = self.ratings[rating_id]
        
        # Vérifier que l'évaluation est publiée
        if rating.status != ReviewStatus.PUBLISHED:
            return None
        
        # Incrémenter le compteur
        rating.helpful_count += 1
        
        # Ajouter aux métadonnées
        if "helpful_votes" not in rating.metadata:
            rating.metadata["helpful_votes"] = []
        
        rating.metadata["helpful_votes"].append({
            "voter_did": voter_did,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.debug(f"Évaluation marquée comme utile: {rating_id} par {voter_did}")
        return rating
    
    async def get_agent_ratings(
        self,
        agent_did: str,
        only_published: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> List[Rating]:
        """Récupère les évaluations d'un agent."""
        if agent_did not in self.reviewee_index:
            return []
        
        rating_ids = self.reviewee_index[agent_did]
        ratings = [self.ratings[rid] for rid in rating_ids]
        
        # Filtrer par statut
        if only_published:
            ratings = [r for r in ratings if r.status == ReviewStatus.PUBLISHED]
        
        # Trier par date (plus récent d'abord)
        ratings.sort(key=lambda r: r.created_at, reverse=True)
        
        # Appliquer la pagination
        start = offset
        end = offset + limit
        
        return ratings[start:end]
    
    async def get_service_ratings(
        self,
        service_id: str,
        only_published: bool = True,
        limit: int = 20,
        offset: int = 0
    ) -> List[Rating]:
        """Récupère les évaluations d'un service."""
        if service_id not in self.service_index:
            return []
        
        rating_ids = self.service_index[service_id]
        ratings = [self.ratings[rid] for rid in rating_ids]
        
        # Filtrer par statut
        if only_published:
            ratings = [r for r in ratings if r.status == ReviewStatus.PUBLISHED]
        
        # Trier par date (plus récent d'abord)
        ratings.sort(key=lambda r: r.created_at, reverse=True)
        
        # Appliquer la pagination
        start = offset
        end = offset + limit
        
        return ratings[start:end]
    
    async def get_rating_summary(
        self,
        entity_id: str,
        entity_type: str
    ) -> Optional[RatingSummary]:
        """Récupère le résumé des évaluations pour une entité."""
        key = f"{entity_type}:{entity_id}"
        
        if key in self.rating_summaries:
            return self.rating_summaries[key]
        
        # Générer un nouveau résumé
        await self._update_rating_summaries(entity_id, entity_type)
        
        return self.rating_summaries.get(key)
    
    async def _update_rating_summaries(
        self,
        entity_id: str,
        entity_type: str
    ):
        """Met à jour les résumés d'évaluations pour une entité."""
        key = f"{entity_type}:{entity_id}"
        
        # Récupérer les évaluations pertinentes
        if entity_type == "agent":
            ratings = await self.get_agent_ratings(entity_id, only_published=True)
        elif entity_type == "service":
            ratings = await self.get_service_ratings(entity_id, only_published=True)
        else:
            return
        
        if not ratings:
            return
        
        # Calculer les statistiques
        total_ratings = len(ratings)
        
        # Score global moyen
        avg_overall_score = sum(r.overall_score for r in ratings) / total_ratings
        
        # Moyennes par dimension
        dimension_avgs = {}
        for dimension in RatingDimension:
            dimension_scores = [r.dimension_scores.get(dimension, 0.0) for r in ratings]
            dimension_avgs[dimension] = sum(dimension_scores) / total_ratings
        
        # Distribution des scores
        score_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in ratings:
            score = int(round(r.overall_score))
            if 1 <= score <= 5:
                score_distribution[score] += 1
        
        # Tendance récente (variation sur 30 jours)
        now = datetime.now(timezone.utc)
        month_ago = now - timedelta(days=30)
        
        recent_ratings = [r for r in ratings if r.created_at >= month_ago]
        older_ratings = [r for r in ratings if r.created_at < month_ago]
        
        if recent_ratings and older_ratings:
            recent_avg = sum(r.overall_score for r in recent_ratings) / len(recent_ratings)
            older_avg = sum(r.overall_score for r in older_ratings) / len(older_ratings)
            
            if older_avg > 0:
                recent_trend = (recent_avg - older_avg) / older_avg
            else:
                recent_trend = 0.0
        else:
            recent_trend = 0.0
        
        # Créer ou mettre à jour le résumé
        summary = RatingSummary(
            entity_id=entity_id,
            entity_type=entity_type,
            total_ratings=total_ratings,
            avg_overall_score=avg_overall_score,
            dimension_avgs=dimension_avgs,
            score_distribution=score_distribution,
            recent_trend=recent_trend,
        )
        
        self.rating_summaries[key] = summary
    
    async def _auto_moderate(self, rating: Rating) -> bool:
        """Modération automatique d'une évaluation."""
        # Vérifier le langage inapproprié (simplifié)
        inappropriate_keywords = ["spam", "scam", "fraud", "hate", "abuse"]
        
        if rating.comment:
            comment_lower = rating.comment.lower()
            for keyword in inappropriate_keywords:
                if keyword in comment_lower:
                    logger.warning(f"Évaluation {rating.rating_id} contient un mot-clé inapproprié: {keyword}")
                    return False
        
        # Vérifier les scores extrêmes
        if rating.overall_score < 1.0 or rating.overall_score > 5.0:
            logger.warning(f"Évaluation {rating.rating_id} a un score extrême: {rating.overall_score}")
            return False
        
        # Vérifier la longueur du commentaire
        if rating.comment and len(rating.comment) < self.min_comment_length:
            logger.warning(f"Évaluation {rating.rating_id} a un commentaire trop court")
            return False
        
        return True
    
    def _validate_scores(
        self,
        overall_score: float,
        dimension_scores: Dict[RatingDimension, float]
    ) -> bool:
        """Valide les scores d'une évaluation."""
        # Vérifier le score global
        if not 1.0 <= overall_score <= 5.0:
            return False
        
        # Vérifier les scores par dimension
        for score in dimension_scores.values():
            if not 1.0 <= score <= 5.0:
                return False
        
        return True
    
    def _validate_comment(self, comment: str) -> bool:
        """Valide un commentaire."""
        if len(comment) < self.min_comment_length:
            return False
        
        if len(comment) > self.max_comment_length:
            return False
        
        return True
    
    def _generate_rating_id(self, escrow_id: str, reviewer_did: str) -> str:
        """Génère un ID unique pour une évaluation."""
        import time
        
        timestamp = str(time.time_ns())
        data = f"{escrow_id}:{reviewer_did}:{timestamp}"
        
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def process_pending_ratings(self):
        """Traite les évaluations en attente (auto-publication)."""
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self.auto_publish_delay_hours)
        
        pending_ratings = [
            r for r in self.ratings.values()
            if r.status == ReviewStatus.PENDING and r.created_at <= cutoff
        ]
        
        for rating in pending_ratings:
            await self.publish_rating(rating.rating_id)
        
        if pending_ratings:
            logger.info(f"{len(pending_ratings)} évaluations auto-publiées")
    
    def export_rating_data(self) -> Dict[str, any]:
        """Exporte toutes les données d'évaluation."""
        return {
            "ratings": {
                rid: rating.to_dict()
                for rid, rating in self.ratings.items()
            },
            "rating_summaries": {
                key: summary.to_dict()
                for key, summary in self.rating_summaries.items()
            },
            "indexes": {
                "reviewee_index": {
                    did: list(rating_ids)
                    for did, rating_ids in self.reviewee_index.items()
                },
                "service_index": {
                    sid: list(rating_ids)
                    for sid, rating_ids in self.service_index.items()
                },
            },
            "parameters": {
                "min_comment_length": self.min_comment_length,
                "max_comment_length": self.max_comment_length,
                "auto_publish_delay_hours": self.auto_publish_delay_hours,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }