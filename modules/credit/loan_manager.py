"""
Gestionnaire de prêts cross-chain pour Sigui
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging

from .credit_config import CreditConfig, CreditRiskLevel, LoanTerm
from .credit_scoring import CreditScoringSystem, CreditScore
from .collateral_tracker import CollateralTracker, CollateralAsset
from ..reputation.reputation_oracle import ReputationOracle


logger = logging.getLogger(__name__)


class LoanStatus(Enum):
    """Statuts des prêts"""
    PENDING = "pending"
    ACTIVE = "active"
    REPAID = "repaid"
    DEFAULTED = "defaulted"
    LIQUIDATED = "liquidated"
    CANCELLED = "cancelled"


class PaymentStatus(Enum):
    """Statuts des paiements"""
    PENDING = "pending"
    PAID = "paid"
    LATE = "late"
    MISSED = "missed"


@dataclass
class LoanTerms:
    """Termes d'un prêt"""
    principal_amount_usd: float
    interest_rate: float  # Taux annuel
    term_days: int
    repayment_schedule: str  # "monthly", "quarterly", "bullet"
    collateral_requirement: float  % requis


@dataclass
class LoanPayment:
    """Paiement d'un prêt"""
    payment_id: str
    loan_id: str
    due_date: int
    amount_usd: float
    principal_amount: float
    interest_amount: float
    status: PaymentStatus
    paid_date: Optional[int] = None
    late_fee: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class Loan:
    """Prêt dans le système Sigui"""
    loan_id: str
    borrower_did: str
    lender_did: Optional[str]  # Peut être décentralisé
    terms: LoanTerms
    status: LoanStatus
    created_at: int
    disbursed_at: Optional[int] = None
    repaid_at: Optional[int] = None
    collateral_assets: List[CollateralAsset] = None
    credit_score: Optional[CreditScore] = None
    payments: List[LoanPayment] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.collateral_assets is None:
            self.collateral_assets = []
        if self.payments is None:
            self.payments = []


class LoanManager:
    """Gestionnaire de prêts décentralisés"""
    
    def __init__(self, config: CreditConfig,
                 credit_scoring: CreditScoringSystem,
                 collateral_tracker: CollateralTracker,
                 reputation_oracle: ReputationOracle):
        self.config = config
        self.credit_scoring = credit_scoring
        self.collateral_tracker = collateral_tracker
        self.reputation_oracle = reputation_oracle
        
        self._loans: Dict[str, Loan] = {}
        self._monitoring_tasks: List[asyncio.Task] = []
        
    async def initialize(self) -> bool:
        """Initialise le gestionnaire de prêts"""
        try:
            if not self.config.enabled:
                logger.warning("Système de crédit désactivé")
                return False
            
            # Démarre la surveillance des paiements
            await self._start_payment_monitoring()
            
            # Démarre la surveillance des liquidations
            await self._start_liquidation_monitoring()
            
            logger.info("Gestionnaire de prêts initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation gestionnaire prêts: {e}")
            return False
    
    async def create_loan(self, borrower_did: str, requested_amount_usd: float,
                         loan_term: LoanTerm, collateral_assets: List[Dict[str, Any]],
                         purpose: Optional[str] = None) -> Optional[Loan]:
        """Crée une nouvelle demande de prêt"""
        try:
            # Génère un ID unique
            loan_id = f"loan_{uuid.uuid4().hex[:16]}"
            
            # Calcule le score de crédit
            credit_score = await self.credit_scoring.calculate_credit_score(
                borrower_did, requested_amount_usd, collateral_assets
            )
            
            # Détermine le taux d'intérêt basé sur le risque
            interest_rate = self._calculate_interest_rate(credit_score.risk_level)
            
            # Détermine la durée
            term_days = self.config.term_durations.get(loan_term, 90)
            
            # Crée les termes du prêt
            terms = LoanTerms(
                principal_amount_usd=requested_amount_usd,
                interest_rate=interest_rate,
                term_days=term_days,
                repayment_schedule="monthly",
                collateral_requirement=self.config.collateral_requirements.get(
                    CollateralType(collateral_assets[0]["type"]), 1.5
                )
            )
            
            # Crée le prêt
            loan = Loan(
                loan_id=loan_id,
                borrower_did=borrower_did,
                lender_did=None,  # Décentralisé pour l'instant
                terms=terms,
                status=LoanStatus.PENDING,
                created_at=int(time.time()),
                credit_score=credit_score,
                metadata={
                    "purpose": purpose,
                    "risk_level": credit_score.risk_level.value,
                    "confidence": credit_score.confidence
                }
            )
            
            # Verrouille le collatéral
            for asset_info in collateral_assets:
                collateral_asset = await self.collateral_tracker.lock_collateral(
                    owner_did=borrower_did,
                    collateral_type=CollateralType(asset_info["type"]),
                    amount=asset_info["amount"],
                    loan_id=loan_id,
                    metadata=asset_info.get("metadata")
                )
                
                if collateral_asset:
                    loan.collateral_assets.append(collateral_asset)
                else:
                    # Échec du verrouillage, annule tout
                    await self._cancel_loan(loan_id)
                    raise ValueError(f"Échec verrouillage collatéral: {asset_info}")
            
            # Génère le calendrier de paiement
            await self._generate_payment_schedule(loan)
            
            # Enregistre le prêt
            self._loans[loan_id] = loan
            
            logger.info(f"Prêt créé: {loan_id} - {requested_amount_usd} USD pour {borrower_did}")
            return loan
            
        except Exception as e:
            logger.error(f"Erreur création prêt: {e}")
            return None
    
    async def approve_loan(self, loan_id: str, lender_did: Optional[str] = None) -> bool:
        """Approuve et débloque un prêt"""
        try:
            if loan_id not in self._loans:
                raise ValueError(f"Prêt {loan_id} non trouvé")
            
            loan = self._loans[loan_id]
            
            if loan.status != LoanStatus.PENDING:
                raise ValueError(f"Prêt {loan_id} n'est pas en attente")
            
            # Vérifie la santé du collatéral
            health_ratio = await self.collateral_tracker.calculate_health_ratio(
                loan_id, loan.terms.principal_amount_usd
            )
            
            if health_ratio < self.config.min_collateralization_ratio:
                raise ValueError(f"Ratio collatéral insuffisant: {health_ratio:.2f}")
            
            # Met à jour le statut
            loan.status = LoanStatus.ACTIVE
            loan.disbursed_at = int(time.time())
            loan.lender_did = lender_did
            
            # Met à jour la réputation de l'emprunteur
            await self.reputation_oracle.update_trust_score(
                target_did=loan.borrower_did,
                increment=0.05,
                reason="loan_approved",
                metadata={"loan_id": loan_id, "amount": loan.terms.principal_amount_usd}
            )
            
            logger.info(f"Prêt approuvé: {loan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur approbation prêt: {e}")
            return False
    
    async def process_payment(self, loan_id: str, payment_id: str,
                             amount_usd: float, payment_method: str = "crypto",
                             metadata: Optional[Dict] = None) -> bool:
        """Traite un paiement pour un prêt"""
        try:
            if loan_id not in self._loans:
                raise ValueError(f"Prêt {loan_id} non trouvé")
            
            loan = self._loans[loan_id]
            
            if loan.status != LoanStatus.ACTIVE:
                raise ValueError(f"Prêt {loan_id} n'est pas actif")
            
            # Trouve le paiement
            payment = None
            for p in loan.payments:
                if p.payment_id == payment_id:
                    payment = p
                    break
            
            if not payment:
                raise ValueError(f"Paiement {payment_id} non trouvé")
            
            # Vérifie le montant
            if amount_usd < payment.amount_usd:
                raise ValueError(f"Montant insuffisant: {amount_usd} < {payment.amount_usd}")
            
            # Met à jour le statut
            payment.status = PaymentStatus.PAID
            payment.paid_date = int(time.time())
            payment.metadata = metadata or {}
            payment.metadata["payment_method"] = payment_method
            
            # Vérifie si c'est en retard
            if payment.paid_date > payment.due_date:
                payment.late_fee = payment.amount_usd * 0.05  # 5% de frais de retard
                logger.warning(f"Paiement en retard: {payment_id}")
            
            # Met à jour la réputation
            await self.reputation_oracle.update_trust_score(
                target_did=loan.borrower_did,
                increment=0.02,
                reason="loan_payment_made",
                metadata={"loan_id": loan_id, "payment_id": payment_id}
            )
            
            # Vérifie si le prêt est entièrement remboursé
            if await self._check_loan_repaid(loan):
                loan.status = LoanStatus.REPAID
                loan.repaid_at = int(time.time())
                
                # Déverrouille le collatéral
                for asset in loan.collateral_assets:
                    await self.collateral_tracker.unlock_collateral(asset.asset_id)
                
                # Met à jour la réputation
                await self.reputation_oracle.update_trust_score(
                    target_did=loan.borrower_did,
                    increment=0.1,
                    reason="loan_fully_repaid",
                    metadata={"loan_id": loan_id}
                )
                
                logger.info(f"Prêt entièrement remboursé: {loan_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur traitement paiement: {e}")
            return False
    
    async def check_liquidation(self, loan_id: str) -> Tuple[bool, float]:
        """Vérifie si un prêt doit être liquidé"""
        try:
            if loan_id not in self._loans:
                return False, 0.0
            
            loan = self._loans[loan_id]
            
            if loan.status != LoanStatus.ACTIVE:
                return False, 0.0
            
            # Calcule le ratio de santé
            health_ratio = await self.collateral_tracker.calculate_health_ratio(
                loan_id, loan.terms.principal_amount_usd
            )
            
            # Vérifie le seuil de liquidation
            needs_liquidation = health_ratio < self.config.liquidation_threshold
            
            return needs_liquidation, health_ratio
            
        except Exception as e:
            logger.error(f"Erreur vérification liquidation: {e}")
            return True, 0.0  # En cas d'erreur, liquide pour sécurité
    
    async def liquidate_loan(self, loan_id: str) -> bool:
        """Liquide un prêt"""
        try:
            if loan_id not in self._loans:
                raise ValueError(f"Prêt {loan_id} non trouvé")
            
            loan = self._loans[loan_id]
            
            if loan.status != LoanStatus.ACTIVE:
                raise ValueError(f"Prêt {loan_id} n'est pas actif")
            
            # Vérifie que la liquidation est nécessaire
            needs_liquidation, health_ratio = await self.check_liquidation(loan_id)
            
            if not needs_liquidation:
                logger.warning(f"Liquidation non nécessaire pour {loan_id}: ratio={health_ratio:.2f}")
                return False
            
            # Met à jour le statut
            loan.status = LoanStatus.LIQUIDATED
            
            # Vente du collatéral (implémentation simplifiée)
            total_collateral_value = sum(asset.value_usd for asset in loan.collateral_assets)
            
            # Calcule le montant à rembourser au prêteur
            outstanding_amount = await self._calculate_outstanding_amount(loan)
            repayment_amount = min(total_collateral_value, outstanding_amount)
            
            # Déverrouille le collatéral (après vente)
            for asset in loan.collateral_assets:
                await self.collateral_tracker.unlock_collateral(asset.asset_id)
            
            # Met à jour la réputation
            await self.reputation_oracle.update_trust_score(
                target_did=loan.borrower_did,
                increment=-0.3,  # Pénalité importante
                reason="loan_liquidated",
                metadata={
                    "loan_id": loan_id,
                    "health_ratio": health_ratio,
                    "collateral_value": total_collateral_value,
                    "outstanding_amount": outstanding_amount
                }
            )
            
            logger.warning(f"Prêt liquidé: {loan_id} - ratio={health_ratio:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur liquidation prêt: {e}")
            return False
    
    async def get_loan(self, loan_id: str) -> Optional[Loan]:
        """Récupère un prêt par son ID"""
        return self._loans.get(loan_id)
    
    async def get_borrower_loans(self, borrower_did: str) -> List[Loan]:
        """Récupère tous les prêts d'un emprunteur"""
        return [loan for loan in self._loans.values() if loan.borrower_did == borrower_did]
    
    async def get_active_loans(self) -> List[Loan]:
        """Récupère tous les prêts actifs"""
        return [loan for loan in self._loans.values() if loan.status == LoanStatus.ACTIVE]
    
    def _calculate_interest_rate(self, risk_level: CreditRiskLevel) -> float:
        """Calcule le taux d'intérêt basé sur le niveau de risque"""
        base_rate = self.config.base_interest_rate
        multiplier = self.config.risk_premium_multiplier.get(risk_level, 1.0)
        
        return base_rate * multiplier
    
    async def _generate_payment_schedule(self, loan: Loan):
        """Génère le calendrier de paiement pour un prêt"""
        try:
            principal = loan.terms.principal_amount_usd
            annual_rate = loan.terms.interest_rate
            term_days = loan.terms.term_days
            
            # Calcule le nombre de paiements (mensuels)
            num_payments = max(1, term_days // 30)
            
            # Taux mensuel
            monthly_rate = annual_rate / 12
            
            # Paiement mensuel (formule d'annuité)
            if monthly_rate > 0:
                monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / ((1 + monthly_rate) ** num_payments - 1)
            else:
                monthly_payment = principal / num_payments
            
            current_time = int(time.time())
            
            for i in range(num_payments):
                # Date d'échéance (30 jours entre chaque paiement)
                due_date = current_time + (i + 1) * 30 * 86400
                
                # Calcule la répartition principal/intérêt
                if i == num_payments - 1:
                    # Dernier paiement
                    interest_amount = principal * monthly_rate
                    principal_amount = monthly_payment - interest_amount
                else:
                    # Simplifié pour l'exemple
                    interest_amount = principal * monthly_rate
                    principal_amount = monthly_payment - interest_amount
                    principal -= principal_amount
                
                payment = LoanPayment(
                    payment_id=f"payment_{loan.loan_id}_{i+1}",
                    loan_id=loan.loan_id,
                    due_date=due_date,
                    amount_usd=monthly_payment,
                    principal_amount=principal_amount,
                    interest_amount=interest_amount,
                    status=PaymentStatus.PENDING
                )
                
                loan.payments.append(payment)
            
            logger.info(f"Calendrier généré pour {loan.loan_id}: {num_payments} paiements")
            
        except Exception as e:
            logger.error(f"Erreur génération calendrier: {e}")
    
    async def _check_loan_repaid(self, loan: Loan) -> bool:
        """Vérifie si un prêt est entièrement remboursé"""
        try:
            # Vérifie si tous les paiements sont payés
            for payment in loan.payments:
                if payment.status != PaymentStatus.PAID:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur vérification remboursement: {e}")
            return False
    
    async def _calculate_outstanding_amount(self, loan: Loan) -> float:
        """Calcule le montant restant dû sur un prêt"""
        try:
            outstanding = 0.0
            
            for payment in loan.payments:
                if payment.status != PaymentStatus.PAID:
                    outstanding += payment.amount_usd
            
            return outstanding
            
        except Exception as e:
            logger.error(f"Erreur calcul montant restant: {e}")
            return loan.terms.principal_amount_usd
    
    async def _cancel_loan(self, loan_id: str):
        """Annule un prêt et déverrouille le collatéral"""
        try:
            if loan_id in self._loans:
                loan = self._loans[loan_id]
                
                # Déverrouille le collatéral
                for asset in loan.collateral_assets:
                    await self.collateral_tracker.unlock_collateral(asset.asset_id)
                
                # Met à jour le statut
                loan.status = LoanStatus.CANCELLED
                
                logger.info(f"Prêt annulé: {loan_id}")
                
        except Exception as e:
            logger.error(f"Erreur annulation prêt: {e}")
    
    async def _start_payment_monitoring(self):
        """Démarre la surveillance des paiements"""
        async def monitor_payments():
            while True:
                try:
                    # Vérifie les paiements en retard
                    for loan in self._loans.values():
                        if loan.status == LoanStatus.ACTIVE:
                            await self._check_late_payments(loan)
                    
                    await asyncio.sleep(86400)  # Vérifie tous les jours
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance paiements: {e}")
                    await asyncio.sleep(3600)
        
        task = asyncio.create_task(monitor_payments())
        self._monitoring_tasks.append(task)
    
    async def _check_late_payments(self, loan: Loan):
        """Vérifie les paiements en retard"""
        try:
            current_time = time.time()
            
            for payment in loan.payments:
                if payment.status == PaymentStatus.PENDING and payment.due_date < current_time:
                    # Paiement en retard
                    payment.status = PaymentStatus.LATE
                    
                    # Met à jour la réputation
                    await self.reputation_oracle.update_trust_score(
                        target_did=loan.borrower_did,
                        increment=-0.05,
                        reason="late_payment",
                        metadata={"loan_id": loan.loan_id, "payment_id": payment.payment_id}
                    )
                    
                    logger.warning(f"Paiement en retard: {payment.payment_id} pour prêt {loan.loan_id}")
                    
        except Exception as e:
            logger.error(f"Erreur vérification paiements retard: {e}")
    
    async def _start_liquidation_monitoring(self):
        """Démarre la surveillance des liquidations"""
        async def monitor_liquidations():
            while True:
                try:
                    # Vérifie tous les prêts actifs
                    for loan in self._loans.values():
                        if loan.status == LoanStatus.ACTIVE:
                            needs_liquidation, health_ratio = await self.check_liquidation(loan.loan_id)
                            
                            if needs_liquidation:
                                logger.warning(f"Prêt {loan.loan_id} nécessite liquidation: ratio={health_ratio:.2f}")
                                # Dans une vraie implémentation, on déclencherait la liquidation
                    
                    await asyncio.sleep(300)  # Vérifie toutes les 5 minutes
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance liquidations: {e}")
                    await asyncio.sleep(60)
        
        task = asyncio.create_task(monitor_liquidations())
        self._monitoring_tasks.append(task)
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._loans.clear()