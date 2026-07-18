"""
API FastAPI pour le système d'assurance décentralisée Sigui
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
import time
import uuid
import logging

from .insurance_config import InsuranceConfig, InsuranceType, RiskCategory, ClaimStatus
from .insurance_pool import InsurancePoolManager, InsurancePool, InsurancePolicy, InsuranceClaim, PoolParticipant
from .risk_assessment import RiskAssessmentSystem, RiskAssessment
from .claim_processor import ClaimProcessor, ClaimAnalysis
from ..reputation.reputation_oracle import ReputationOracle
from ..credit.credit_scoring import CreditScoringSystem


logger = logging.getLogger(__name__)


class InsuranceAPI:
    """API FastAPI pour le système d'assurance"""
    
    def __init__(self, config: InsuranceConfig,
                 pool_manager: InsurancePoolManager,
                 risk_assessment: RiskAssessmentSystem,
                 claim_processor: ClaimProcessor,
                 reputation_oracle: ReputationOracle):
        self.config = config
        self.pool_manager = pool_manager
        self.risk_assessment = risk_assessment
        self.claim_processor = claim_processor
        self.reputation_oracle = reputation_oracle
        
        self.router = APIRouter(prefix="/insurance", tags=["insurance"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Configure les routes de l'API"""
        
        @self.router.get("/health")
        async def health_check():
            """Vérifie la santé du système d'assurance"""
            return {
                "status": "healthy" if self.config.enabled else "disabled",
                "timestamp": int(time.time()),
                "version": "1.0.0"
            }
        
        @self.router.get("/config")
        async def get_insurance_config():
            """Récupère la configuration du système d'assurance"""
            return {
                "enabled": self.config.enabled,
                "min_premium_usd": self.config.min_premium_usd,
                "max_coverage_usd": self.config.max_coverage_usd,
                "min_coverage_usd": self.config.min_coverage_usd,
                "pool_creation_min_stake_usd": self.config.pool_creation_min_stake_usd,
                "pool_management_fee_percent": self.config.pool_management_fee_percent,
                "pool_reserve_ratio": self.config.pool_reserve_ratio,
                "base_premium_rates": {k.value: v for k, v in self.config.base_premium_rates.items()},
                "risk_multipliers": {k.value: v for k, v in self.config.risk_multipliers.items()},
                "deductible_rates": {k.value: v for k, v in self.config.deductible_rates.items()},
                "max_coverage_per_pool_usd": self.config.max_coverage_per_pool_usd,
                "min_pool_participants": self.config.min_pool_participants,
                "max_claim_ratio": self.config.max_claim_ratio,
                "ai_risk_assessment_enabled": self.config.ai_risk_assessment_enabled,
                "ai_claim_assessment_enabled": self.config.ai_claim_assessment_enabled,
                "supported_blockchains": self.config.supported_blockchains
            }
        
        @self.router.post("/pool/create")
        async def create_insurance_pool(
            creator_did: str = Body(..., description="DID du créateur du pool"),
            insurance_type: str = Body(..., description="Type d'assurance"),
            initial_stake_usd: float = Body(..., description="Stake initial en USD"),
            metadata: Optional[Dict[str, Any]] = Body(None, description="Métadonnées additionnelles")
        ) -> Dict[str, Any]:
            """Crée un nouveau pool d'assurance"""
            try:
                # Valide le type d'assurance
                try:
                    type_enum = InsuranceType(insurance_type)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Type d'assurance invalide. Options: {[t.value for t in InsuranceType]}"
                    )
                
                # Crée le pool
                pool = await self.pool_manager.create_pool(
                    creator_did, type_enum, initial_stake_usd, metadata
                )
                
                if not pool:
                    raise HTTPException(status_code=500, detail="Échec de création du pool")
                
                return {
                    "pool_id": pool.pool_id,
                    "creator_did": pool.creator_did,
                    "insurance_type": pool.insurance_type.value,
                    "total_capital_usd": pool.total_capital_usd,
                    "coverage_provided_usd": pool.coverage_provided_usd,
                    "reserve_ratio": pool.reserve_ratio,
                    "status": pool.status.value,
                    "participants_count": len(pool.participants),
                    "created_date": pool.created_date,
                    "metadata": pool.metadata
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur création pool: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/pool/{pool_id}")
        async def get_pool_details(pool_id: str) -> Optional[Dict[str, Any]]:
            """Récupère les détails d'un pool d'assurance"""
            try:
                pool = await self.pool_manager.get_pool(pool_id)
                
                if not pool:
                    return None
                
                return {
                    "pool_id": pool.pool_id,
                    "creator_did": pool.creator_did,
                    "insurance_type": pool.insurance_type.value,
                    "total_capital_usd": pool.total_capital_usd,
                    "coverage_provided_usd": pool.coverage_provided_usd,
                    "reserve_ratio": pool.reserve_ratio,
                    "status": pool.status.value,
                    "participants": [
                        {
                            "participant_did": p.participant_did,
                            "stake_amount_usd": p.stake_amount_usd,
                            "share_percentage": p.share_percentage,
                            "rewards_earned_usd": p.rewards_earned_usd
                        }
                        for p in pool.participants
                    ],
                    "policies_count": len(pool.policies),
                    "claims_count": len(pool.claims),
                    "created_date": pool.created_date,
                    "metadata": pool.metadata
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération détails pool: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/pools")
        async def get_pools_by_type(
            insurance_type: Optional[str] = Query(None, description="Filtrer par type d'assurance")
        ) -> List[Dict[str, Any]]:
            """Récupère les pools d'assurance"""
            try:
                if insurance_type:
                    # Valide le type
                    try:
                        type_enum = InsuranceType(insurance_type)
                    except ValueError:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Type d'assurance invalide. Options: {[t.value for t in InsuranceType]}"
                        )
                    
                    pools = await self.pool_manager.get_pools_by_type(type_enum)
                else:
                    # Tous les pools
                    pools = list(self.pool_manager._pools.values())
                
                return [
                    {
                        "pool_id": pool.pool_id,
                        "insurance_type": pool.insurance_type.value,
                        "total_capital_usd": pool.total_capital_usd,
                        "coverage_provided_usd": pool.coverage_provided_usd,
                        "status": pool.status.value,
                        "participants_count": len(pool.participants),
                        "policies_count": len(pool.policies),
                        "created_date": pool.created_date
                    }
                    for pool in pools
                ]
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur récupération pools: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/pool/{pool_id}/join")
        async def join_pool(
            pool_id: str,
            participant_did: str = Body(..., description="DID du participant"),
            stake_amount_usd: float = Body(..., description="Montant du stake en USD")
        ) -> Dict[str, Any]:
            """Rejoint un pool d'assurance"""
            try:
                participant = await self.pool_manager.join_pool(
                    pool_id, participant_did, stake_amount_usd
                )
                
                if not participant:
                    raise HTTPException(status_code=400, detail="Échec de rejoindre le pool")
                
                return {
                    "participant_did": participant.participant_did,
                    "pool_id": participant.pool_id,
                    "stake_amount_usd": participant.stake_amount_usd,
                    "share_percentage": participant.share_percentage,
                    "joined_date": participant.joined_date
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur rejoindre pool: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/policy/purchase")
        async def purchase_policy(
            pool_id: str = Body(..., description="ID du pool"),
            insured_did: str = Body(..., description="DID de l'assuré"),
            insurance_type: str = Body(..., description="Type d'assurance"),
            coverage_amount_usd: float = Body(..., description="Montant de couverture en USD"),
            duration_days: int = Body(365, description="Durée en jours"),
            metadata: Optional[Dict[str, Any]] = Body(None, description="Métadonnées additionnelles")
        ) -> Dict[str, Any]:
            """Achète une police d'assurance"""
            try:
                # Valide le type d'assurance
                try:
                    type_enum = InsuranceType(insurance_type)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Type d'assurance invalide. Options: {[t.value for t in InsuranceType]}"
                    )
                
                # Achète la police
                policy = await self.pool_manager.purchase_policy(
                    pool_id, insured_did, type_enum, coverage_amount_usd, duration_days, metadata
                )
                
                if not policy:
                    raise HTTPException(status_code=500, detail="Échec d'achat de la police")
                
                return {
                    "policy_id": policy.policy_id,
                    "insured_did": policy.insured_did,
                    "pool_id": policy.pool_id,
                    "insurance_type": policy.insurance_type.value,
                    "coverage_amount_usd": policy.coverage_amount_usd,
                    "premium_amount_usd": policy.premium_amount_usd,
                    "deductible_rate": policy.deductible_rate,
                    "risk_category": policy.risk_category.value,
                    "start_date": policy.start_date,
                    "end_date": policy.end_date,
                    "status": policy.status,
                    "metadata": policy.metadata
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur achat police: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/policy/{policy_id}")
        async def get_policy_details(policy_id: str) -> Optional[Dict[str, Any]]:
            """Récupère les détails d'une police d'assurance"""
            try:
                policy = await self.pool_manager.get_policy(policy_id)
                
                if not policy:
                    return None
                
                return {
                    "policy_id": policy.policy_id,
                    "insured_did": policy.insured_did,
                    "pool_id": policy.pool_id,
                    "insurance_type": policy.insurance_type.value,
                    "coverage_amount_usd": policy.coverage_amount_usd,
                    "premium_amount_usd": policy.premium_amount_usd,
                    "deductible_rate": policy.deductible_rate,
                    "risk_category": policy.risk_category.value,
                    "start_date": policy.start_date,
                    "end_date": policy.end_date,
                    "status": policy.status,
                    "claims_filed": policy.claims_filed,
                    "claims_paid": policy.claims_paid,
                    "metadata": policy.metadata
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération détails police: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/risk/assess")
        async def assess_risk(
            insured_did: str = Body(..., description="DID de l'assuré"),
            insurance_type: str = Body(..., description="Type d'assurance"),
            coverage_amount_usd: float = Body(..., description="Montant de couverture en USD"),
            collateral_info: Optional[Dict[str, Any]] = Body(None, description="Informations sur le collatéral")
        ) -> Dict[str, Any]:
            """Évalue le risque pour un assuré potentiel"""
            try:
                # Valide le type d'assurance
                try:
                    type_enum = InsuranceType(insurance_type)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Type d'assurance invalide. Options: {[t.value for t in InsuranceType]}"
                    )
                
                # Effectue l'évaluation
                assessment = await self.risk_assessment.assess_risk(
                    insured_did, type_enum, coverage_amount_usd, collateral_info
                )
                
                return {
                    "insured_did": insured_did,
                    "insurance_type": insurance_type,
                    "overall_risk_score": assessment.overall_risk_score,
                    "risk_category": assessment.risk_category.value,
                    "confidence": assessment.confidence,
                    "factors": assessment.factors,
                    "recommendations": assessment.recommendations,
                    "timestamp": assessment.timestamp
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur évaluation risque: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/claim/file")
        async def file_insurance_claim(
            policy_id: str = Body(..., description="ID de la police"),
            amount_requested_usd: float = Body(..., description="Montant réclamé en USD"),
            description: str = Body(..., description="Description de la réclamation"),
            evidence: List[Dict[str, Any]] = Body(..., description="Preuves de la réclamation"),
            metadata: Optional[Dict[str, Any]] = Body(None, description="Métadonnées additionnelles")
        ) -> Dict[str, Any]:
            """Dépose une réclamation d'assurance"""
            try:
                claim = await self.pool_manager.file_claim(
                    policy_id, amount_requested_usd, description, evidence, metadata
                )
                
                if not claim:
                    raise HTTPException(status_code=500, detail="Échec de dépôt de la réclamation")
                
                return {
                    "claim_id": claim.claim_id,
                    "policy_id": claim.policy_id,
                    "insured_did": claim.insured_did,
                    "amount_requested_usd": claim.amount_requested_usd,
                    "description": claim.description,
                    "status": claim.status.value,
                    "filed_date": claim.filed_date,
                    "metadata": claim.metadata
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur dépôt réclamation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/claim/{claim_id}")
        async def get_claim_details(claim_id: str) -> Optional[Dict[str, Any]]:
            """Récupère les détails d'une réclamation"""
            try:
                claim = await self.pool_manager.get_claim(claim_id)
                
                if not claim:
                    return None
                
                return {
                    "claim_id": claim.claim_id,
                    "policy_id": claim.policy_id,
                    "insured_did": claim.insured_did,
                    "pool_id": claim.pool_id,
                    "amount_requested_usds": claim.amount_requested_usd,
                    "description": claim.description,
                    "status": claim.status.value,
                    "filed_date": claim.filed_date,
                    "reviewed_date": claim.reviewed_date,
                    "approved_amount_usd": claim.approved_amount_usd,
                    "paid_date": claim.paid_date,
                    "reviewer_did": claim.reviewer_did,
                    "rejection_reason": claim.rejection_reason,
                    "metadata": claim.metadata
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération détails réclamation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/claim/{claim_id}/analyze")
        async def analyze_claim(claim_id: str) -> Dict[str, Any]:
            """Analyse une réclamation avec AI"""
            try:
                analysis = await self.claim_processor.analyze_claim(claim_id)
                
                if not analysis:
                    raise HTTPException(status_code=500, detail="Échec de l'analyse de la réclamation")
                
                return {
                    "claim_id": analysis.claim_id,
                    "fraud_score": analysis.fraud_score,
                    "validity_score": analysis.validity_score,
                    "recommended_action": analysis.recommended_action,
                    "confidence": analysis.confidence,
                    "factors": analysis.factors,
                    "timestamp": analysis.timestamp
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur analyse réclamation: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/claim/{claim_id}/process")
        async def process_claim_decision(
            claim_id: str,
            reviewer_did: str = Body(..., description="DID du réviseur"),
            action: str = Body(..., description="Action recommandée (approve/reject/investigate)"),
            approved_amount_usd: Optional[float] = Body(None, description="Montant approuvé en USD (si applicable)"),
            rejection_reason: Optional[str] = Body(None, description="Raison du rejet (si applicable)")
        ) -> Dict[str, Any]:
            """Traite une décision sur une réclamation"""
            try:
                # Valide l'action
                if action not in ["approve", "reject", "investigate"]:
                    raise HTTPException(
                        status_code=400,
                        detail="Action invalide. Options: approve, reject, investigate"
                    )
                
                # Traite la décision
                if action == "approve":
                    success = await self.pool_manager.process_claim(
                        claim_id, reviewer_did, approved_amount_usd, None
                    )
                elif action == "reject":
                    success = await self.pool_manager.process_claim(
                        claim_id, reviewer_did, None, rejection_reason
                    )
                else:  # investigate
                    success = True  # Marque pour investigation
                
                if not success:
                    raise HTTPException(status_code=400, detail="Échec du traitement de la décision")
                
                return {
                    "claim_id": claim_id,
                    "reviewer_did": reviewer_did,
                    "action": action,
                    "processed": True,
                    "timestamp": int(time.time())
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur traitement décision: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/insured/{did}/policies")
        async def get_insured_policies(did: str) -> List[Dict[str, Any]]:
            """Récupère les polices d'un assuré"""
            try:
                # Dans une vraie implémentation, on aurait une méthode pour cela
                # Pour l'exemple, retourne une liste vide
                return []
                
            except Exception as e:
                logger.error(f"Erreur récupération polices assuré: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/insured/{did}/claims")
        async def get_insured_claims(did: str) -> List[Dict[str, Any]]:
            """Récupère les réclamations d'un assuré"""
            try:
                # Dans une vraie implémentation, on aurait une méthode pour cela
                # Pour l'exemple, retourne une liste vide
                return []
                
            except Exception as e:
                logger.error(f"Erreur récupération réclamations assuré: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def get_router(self) -> APIRouter:
        """Retourne le router FastAPI"""
        return self.router