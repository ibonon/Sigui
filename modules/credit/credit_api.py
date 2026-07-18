"""
API FastAPI pour le système de crédit cross-chain Sigui
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from typing import List, Optional, Dict, Any
import time
import uuid
import logging

from .credit_config import CreditConfig, CreditRiskLevel, LoanTerm, CollateralType
from .credit_scoring import CreditScoringSystem, CreditScore, CreditApplication
from .collateral_tracker import CollateralTracker, CollateralAsset, CollateralPosition
from .loan_manager import LoanManager, Loan, LoanStatus, LoanTerms, LoanPayment, PaymentStatus
from ..reputation.reputation_oracle import ReputationOracle
from ..blockchain.bitcoin.bitcoin_adapter import BitcoinAdapter
from ..blockchain.cardano.cardano_adapter import CardanoAdapter


logger = logging.getLogger(__name__)


class CreditAPI:
    """API FastAPI pour le système de crédit"""
    
    def __init__(self, config: CreditConfig,
                 credit_scoring: CreditScoringSystem,
                 collateral_tracker: CollateralTracker,
                 loan_manager: LoanManager,
                 reputation_oracle: ReputationOracle):
        self.config = config
        self.credit_scoring = credit_scoring
        self.collateral_tracker = collateral_tracker
        self.loan_manager = loan_manager
        self.reputation_oracle = reputation_oracle
        
        self.router = APIRouter(prefix="/credit", tags=["credit"])
        self._setup_routes()
    
    def _setup_routes(self):
        """Configure les routes de l'API"""
        
        @self.router.get("/health")
        async def health_check():
            """Vérifie la santé du système de crédit"""
            return {
                "status": "healthy" if self.config.enabled else "disabled",
                "timestamp": int(time.time()),
                "version": "1.0.0"
            }
        
        @self.router.get("/score/{did}")
        async def get_credit_score(did: str) -> Dict[str, Any]:
            """Récupère le score de crédit d'un utilisateur"""
            try:
                score = await self.credit_scoring.calculate_credit_score(did)
                
                return {
                    "applicant_did": did,
                    "overall_score": score.overall_score,
                    "risk_level": score.risk_level.value,
                    "confidence": score.confidence,
                    "factors": score.factors,
                    "timestamp": score.timestamp,
                    "expires_at": score.expires_at
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération score crédit: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/score/calculate")
        async def calculate_detailed_score(
            did: str = Body(..., description="DID de l'emprunteur"),
            requested_amount_usd: Optional[float] = Body(None, description="Montant demandé en USD"),
            collateral_assets: Optional[List[Dict[str, Any]]] = Body(None, description="Assets de collatéral")
        ) -> Dict[str, Any]:
            """Calcule un score de crédit détaillé avec des paramètres spécifiques"""
            try:
                score = await self.credit_scoring.calculate_credit_score(
                    did, requested_amount_usd, collateral_assets
                )
                
                return {
                    "applicant_did": did,
                    "overall_score": score.overall_score,
                    "risk_level": score.risk_level.value,
                    "confidence": score.confidence,
                    "factors": score.factors,
                    "timestamp": score.timestamp,
                    "expires_at": score.expires_at,
                    "eligibility": score.overall_score >= self.config.min_credit_score
                }
                
            except Exception as e:
                logger.error(f"Erreur calcul score détaillé: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/collateral/{did}")
        async def get_collateral_position(did: str) -> Optional[Dict[str, Any]]:
            """Récupère la position de collatéral d'un utilisateur"""
            try:
                position = await self.collateral_tracker.get_collateral_position(did)
                
                if not position:
                    return None
                
                return {
                    "owner_did": position.owner_did,
                    "total_value_usd": position.total_value_usd,
                    "health_ratio": position.health_ratio,
                    "assets": [
                        {
                            "asset_id": asset.asset_id,
                            "type": asset.collateral_type.value,
                            "amount": asset.amount,
                            "value_usd": asset.value_usd,
                            "locked_at": asset.locked_at,
                            "loan_id": asset.loan_id
                        }
                        for asset in position.assets
                    ],
                    "last_updated": position.last_updated
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération position collatéral: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/loan/apply")
        async def apply_for_loan(
            borrower_did: str = Body(..., description="DID de l'emprunteur"),
            requested_amount_usd: float = Body(..., description="Montant demandé en USD"),
            loan_term: str = Body(..., description="Terme du prêt (short_term, medium_term, long_term)"),
            collateral_assets: List[Dict[str, Any]] = Body(..., description="Assets de collatéral"),
            purpose: Optional[str] = Body(None, description="But du prêt")
        ) -> Dict[str, Any]:
            """Soumet une demande de prêt"""
            try:
                # Valide le terme
                try:
                    term_enum = LoanTerm(loan_term)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Terme invalide. Options: {[t.value for t in LoanTerm]}"
                    )
                
                # Crée la demande
                application = CreditApplication(
                    application_id=f"app_{uuid.uuid4().hex[:16]}",
                    applicant_did=borrower_did,
                    requested_amount_usd=requested_amount_usd,
                    loan_term=loan_term,
                    collateral_assets=collateral_assets,
                    purpose=purpose
                )
                
                # Soumet la demande
                result = await self.credit_scoring.submit_credit_application(application)
                
                if not result:
                    raise HTTPException(status_code=500, detail="Échec de soumission de la demande")
                
                return {
                    "application_id": result.application_id,
                    "status": result.status,
                    "requested_amount_usd": result.requested_amount_usd,
                    "loan_term": result.loan_term,
                    "metadata": result.metadata,
                    "submitted_at": result.submitted_at
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur demande prêt: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/loan/create")
        async def create_loan(
            borrower_did: str = Body(..., description="DID de l'emprunteur"),
            requested_amount_usd: float = Body(..., description="Montant demandé en USD"),
            loan_term: str = Body(..., description="Terme du prêt"),
            collateral_assets: List[Dict[str, Any]] = Body(..., description="Assets de collatéral"),
            purpose: Optional[str] = Body(None, description="But du prêt")
        ) -> Dict[str, Any]:
            """Crée un nouveau prêt"""
            try:
                # Valide le terme
                try:
                    term_enum = LoanTerm(loan_term)
                except ValueError:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Terme invalide. Options: {[t.value for t in LoanTerm]}"
                    )
                
                # Crée le prêt
                loan = await self.loan_manager.create_loan(
                    borrower_did=borrower_did,
                    requested_amount_usd=requested_amount_usd,
                    loan_term=term_enum,
                    collateral_assets=collateral_assets,
                    purpose=purpose
                )
                
                if not loan:
                    raise HTTPException(status_code=500, detail="Échec de création du prêt")
                
                return {
                    "loan_id": loan.loan_id,
                    "borrower_did": loan.borrower_did,
                    "status": loan.status.value,
                    "terms": {
                        "principal_amount_usd": loan.terms.principal_amount_usd,
                        "interest_rate": loan.terms.interest_rate,
                        "term_days": loan.terms.term_days,
                        "repayment_schedule": loan.terms.repayment_schedule,
                        "collateral_requirement": loan.terms.collateral_requirement
                    },
                    "collateral_assets": [
                        {
                            "asset_id": asset.asset_id,
                            "type": asset.collateral_type.value,
                            "value_usd": asset.value_usd
                        }
                        for asset in loan.collateral_assets
                    ],
                    "credit_score": {
                        "overall_score": loan.credit_score.overall_score,
                        "risk_level": loan.credit_score.risk_level.value
                    } if loan.credit_score else None,
                    "created_at": loan.created_at,
                    "metadata": loan.metadata
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur création prêt: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/loan/{loan_id}/approve")
        async def approve_loan(
            loan_id: str,
            lender_did: Optional[str] = Body(None, description="DID du prêteur")
        ) -> Dict[str, Any]:
            """Approuve un prêt"""
            try:
                success = await self.loan_manager.approve_loan(loan_id, lender_did)
                
                if not success:
                    raise HTTPException(status_code=400, detail="Échec de l'approbation")
                
                return {
                    "loan_id": loan_id,
                    "approved": True,
                    "lender_did": lender_did,
                    "timestamp": int(time.time())
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur approbation prêt: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/loan/{loan_id}")
        async def get_loan_details(loan_id: str) -> Optional[Dict[str, Any]]:
            """Récupère les détails d'un prêt"""
            try:
                loan = await self.loan_manager.get_loan(loan_id)
                
                if not loan:
                    return None
                
                return {
                    "loan_id": loan.loan_id,
                    "borrower_did": loan.borrower_did,
                    "lender_did": loan.lender_did,
                    "status": loan.status.value,
                    "terms": {
                        "principal_amount_usd": loan.terms.principal_amount_usd,
                        "interest_rate": loan.terms.interest_rate,
                        "term_days": loan.terms.term_days,
                        "repayment_schedule": loan.terms.repayment_schedule,
                        "collateral_requirement": loan.terms.collateral_requirement
                    },
                    "collateral_assets": [
                        {
                            "asset_id": asset.asset_id,
                            "type": asset.collateral_type.value,
                            "amount": asset.amount,
                            "value_usd": asset.value_usd
                        }
                        for asset in loan.collateral_assets
                    ],
                    "payments": [
                        {
                            "payment_id": payment.payment_id,
                            "due_date": payment.due_date,
                            "amount_usd": payment.amount_usd,
                            "status": payment.status.value,
                            "paid_date": payment.paid_date
                        }
                        for payment in loan.payments
                    ],
                    "created_at": loan.created_at,
                    "disbursed_at": loan.disbursed_at,
                    "repaid_at": loan.repaid_at,
                    "metadata": loan.metadata
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération détails prêt: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/borrower/{did}/loans")
        async def get_borrower_loans(did: str) -> List[Dict[str, Any]]:
            """Récupère tous les prêts d'un emprunteur"""
            try:
                loans = await self.loan_manager.get_borrower_loans(did)
                
                return [
                    {
                        "loan_id": loan.loan_id,
                        "status": loan.status.value,
                        "principal_amount_usd": loan.terms.principal_amount_usd,
                        "interest_rate": loan.terms.interest_rate,
                        "created_at": loan.created_at,
                        "disbursed_at": loan.disbursed_at
                    }
                    for loan in loans
                ]
                
            except Exception as e:
                logger.error(f"Erreur récupération prêts emprunteur: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.post("/payment/process")
        async def process_payment(
            loan_id: str = Body(..., description="ID du prêt"),
            payment_id: str = Body(..., description="ID du paiement"),
            amount_usd: float = Body(..., description="Montant payé en USD"),
            payment_method: str = Body("crypto", description="Méthode de paiement"),
            metadata: Optional[Dict[str, Any]] = Body(None, description="Métadonnées additionnelles")
        ) -> Dict[str, Any]:
            """Traite un paiement pour un prêt"""
            try:
                success = await self.loan_manager.process_payment(
                    loan_id, payment_id, amount_usd, payment_method, metadata
                )
                
                if not success:
                    raise HTTPException(status_code=400, detail="Échec du traitement du paiement")
                
                return {
                    "loan_id": loan_id,
                    "payment_id": payment_id,
                    "processed": True,
                    "amount_usd": amount_usd,
                    "timestamp": int(time.time())
                }
                
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Erreur traitement paiement: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/loan/{loan_id}/health")
        async def get_loan_health(loan_id: str) -> Dict[str, Any]:
            """Récupère la santé d'un prêt"""
            try:
                needs_liquidation, health_ratio = await self.loan_manager.check_liquidation(loan_id)
                
                return {
                    "loan_id": loan_id,
                    "health_ratio": health_ratio,
                    "needs_liquidation": needs_liquidation,
                    "liquidation_threshold": self.config.liquidation_threshold,
                    "min_collateralization_ratio": self.config.min_collateralization_ratio,
                    "timestamp": int(time.time())
                }
                
            except Exception as e:
                logger.error(f"Erreur récupération santé prêt: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.router.get("/config")
        async def get_credit_config() -> Dict[str, Any]:
            """Récupère la configuration du système de crédit"""
            return {
                "enabled": self.config.enabled,
                "min_credit_score": self.config.min_credit_score,
                "max_loan_amount_usd": self.config.max_loan_amount_usd,
                "min_loan_amount_usd": self.config.min_loan_amount_usd,
                "base_interest_rate": self.config.base_interest_rate,
                "max_loan_to_value_ratio": self.config.max_loan_to_value_ratio,
                "min_collateralization_ratio": self.config.min_collateralization_ratio,
                "liquidation_threshold": self.config.liquidation_threshold,
                "available_loan_terms": [term.value for term in self.config.available_loan_terms],
                "term_durations": {term.value: days for term, days in self.config.term_durations.items()},
                "supported_blockchains": self.config.supported_blockchains,
                "ai_scoring_enabled": self.config.ai_scoring_enabled
            }
    
    def get_router(self) -> APIRouter:
        """Retourne le router FastAPI"""
        return self.router