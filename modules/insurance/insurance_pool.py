"""
Pool d'assurance décentralisée pour Sigui
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
import logging

from .insurance_config import InsuranceConfig, InsuranceType, RiskCategory, ClaimStatus
from ..reputation.reputation_oracle import ReputationOracle


logger = logging.getLogger(__name__)


class PoolStatus(Enum):
    """Statuts des pools d'assurance"""
    ACTIVE = "active"
    FULL = "full"
    CLOSED = "closed"
    LIQUIDATING = "liquidating"
    LIQUIDATED = "liquidated"


@dataclass
class InsurancePolicy:
    """Police d'assurance individuelle"""
    policy_id: str
    insured_did: str
    pool_id: str
    insurance_type: InsuranceType
    coverage_amount_usd: float
    premium_amount_usd: float
    deductible_rate: float
    risk_category: RiskCategory
    start_date: int
    end_date: int
    status: str = "active"
    claims_filed: int = 0
    claims_paid: int = 0
    metadata: Optional[Dict] = None


@dataclass
class InsuranceClaim:
    """Réclamation d'assurance"""
    claim_id: str
    policy_id: str
    insured_did: str
    pool_id: str
    amount_requested_usd: float
    description: str
    evidence: List[Dict[str, any]]
    status: ClaimStatus
    filed_date: int
    reviewed_date: Optional[int] = None
    approved_amount_usd: Optional[float] = None
    paid_date: Optional[int] = None
    reviewer_did: Optional[str] = None
    rejection_reason: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class PoolParticipant:
    """Participant à un pool d'assurance"""
    participant_did: str
    pool_id: str
    stake_amount_usd: float
    joined_date: int
    share_percentage: float
    rewards_earned_usd: float = 0.0
    claims_paid_usd: float = 0.0


@dataclass
class InsurancePool:
    """Pool d'assurance décentralisé"""
    pool_id: str
    creator_did: str
    insurance_type: InsuranceType
    total_capital_usd: float
    coverage_provided_usd: float
    reserve_ratio: float
    status: PoolStatus
    created_date: int
    participants: List[PoolParticipant]
    policies: List[InsurancePolicy]
    claims: List[InsuranceClaim]
    metadata: Optional[Dict] = None
    
    def __post_init__(self):
        if self.participants is None:
            self.participants = []
        if self.policies is None:
            self.policies = []
        if self.claims is None:
            self.claims = []


class InsurancePoolManager:
    """Gestionnaire de pools d'assurance décentralisés"""
    
    def __init__(self, config: InsuranceConfig, reputation_oracle: ReputationOracle):
        self.config = config
        self.reputation_oracle = reputation_oracle
        
        self._pools: Dict[str, InsurancePool] = {}
        self._policies: Dict[str, InsurancePolicy] = {}
        self._claims: Dict[str, InsuranceClaim] = {}
        self._monitoring_tasks: List[asyncio.Task] = []
        
    async def initialize(self) -> bool:
        """Initialise le gestionnaire de pools"""
        try:
            if not self.config.enabled:
                logger.warning("Système d'assurance désactivé")
                return False
            
            # Démarre la surveillance des pools
            await self._start_pool_monitoring()
            
            logger.info("Gestionnaire de pools d'assurance initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation gestionnaire pools: {e}")
            return False
    
    async def create_pool(self, creator_did: str, insurance_type: InsuranceType,
                         initial_stake_usd: float, metadata: Optional[Dict] = None) -> Optional[InsurancePool]:
        """Crée un nouveau pool d'assurance"""
        try:
            # Vérifie le stake minimum
            if initial_stake_usd < self.config.pool_creation_min_stake_usd:
                raise ValueError(f"Stake insuffisant: {initial_stake_usd} < {self.config.pool_creation_min_stake_usd}")
            
            # Vérifie la réputation du créateur
            creator_trust = self.reputation_oracle.get_trust_score(creator_did)
            if creator_trust < 0.5:
                raise ValueError(f"Réputation insuffisante: {creator_trust} < 0.5")
            
            # Génère un ID unique
            pool_id = f"pool_{uuid.uuid4().hex[:16]}"
            
            # Calcule la couverture initiale (basée sur le capital et le ratio de réserve)
            initial_coverage = initial_stake_usd * (1 - self.config.pool_reserve_ratio)
            
            # Crée le participant créateur
            creator_participant = PoolParticipant(
                participant_did=creator_did,
                pool_id=pool_id,
                stake_amount_usd=initial_stake_usd,
                joined_date=int(time.time()),
                share_percentage=1.0  # 100% initialement
            )
            
            # Crée le pool
            pool = InsurancePool(
                pool_id=pool_id,
                creator_did=creator_did,
                insurance_type=insurance_type,
                total_capital_usd=initial_stake_usd,
                coverage_provided_usd=initial_coverage,
                reserve_ratio=self.config.pool_reserve_ratio,
                status=PoolStatus.ACTIVE,
                created_date=int(time.time()),
                participants=[creator_participant],
                policies=[],
                claims=[],
                metadata=metadata
            )
            
            # Enregistre le pool
            self._pools[pool_id] = pool
            
            # Met à jour la réputation du créateur
            await self.reputation_oracle.update_trust_score(
                target_did=creator_did,
                increment=0.1,
                reason="insurance_pool_created",
                metadata={
                    "pool_id": pool_id,
                    "insurance_type": insurance_type.value,
                    "initial_stake": initial_stake_usd
                }
            )
            
            logger.info(f"Pool d'assurance créé: {pool_id} - {insurance_type.value} - {initial_stake_usd} USD")
            return pool
            
        except Exception as e:
            logger.error(f"Erreur création pool: {e}")
            return None
    
    async def join_pool(self, pool_id: str, participant_did: str,
                       stake_amount_usd: float) -> Optional[PoolParticipant]:
        """Rejoint un pool d'assurance existant"""
        try:
            if pool_id not in self._pools:
                raise ValueError(f"Pool {pool_id} non trouvé")
            
            pool = self._pools[pool_id]
            
            if pool.status != PoolStatus.ACTIVE:
                raise ValueError(f"Pool {pool_id} n'est pas actif")
            
            # Vérifie la réputation du participant
            participant_trust = self.reputation_oracle.get_trust_score(participant_did)
            if participant_trust < 0.3:
                raise ValueError(f"Réputation insuffisante: {participant_trust} < 0.3")
            
            # Calcule le pourcentage de part
            total_capital = pool.total_capital_usd + stake_amount_usd
            share_percentage = stake_amount_usd / total_capital
            
            # Ajuste les parts existantes
            for participant in pool.participants:
                participant.share_percentage *= (pool.total_capital_usd / total_capital)
            
            # Crée le nouveau participant
            new_participant = PoolParticipant(
                participant_did=participant_did,
                pool_id=pool_id,
                stake_amount_usd=stake_amount_usd,
                joined_date=int(time.time()),
                share_percentage=share_percentage
            )
            
            # Met à jour le pool
            pool.participants.append(new_participant)
            pool.total_capital_usd = total_capital
            pool.coverage_provided_usd = total_capital * (1 - pool.reserve_ratio)
            
            # Vérifie si le pool est plein
            if len(pool.participants) >= self.config.min_pool_participants * 3:
                pool.status = PoolStatus.FULL
            
            logger.info(f"Participant {participant_did} a rejoint le pool {pool_id}")
            return new_participant
            
        except Exception as e:
            logger.error(f"Erreur rejoindre pool: {e}")
            return None
    
    async def purchase_policy(self, pool_id: str, insured_did: str,
                             insurance_type: InsuranceType,
                             coverage_amount_usd: float,
                             duration_days: int = 365,
                             metadata: Optional[Dict] = None) -> Optional[InsurancePolicy]:
        """Achète une police d'assurance"""
        try:
            if pool_id not in self._pools:
                raise ValueError(f"Pool {pool_id} non trouvé")
            
            pool = self._pools[pool_id]
            
            if pool.status not in [PoolStatus.ACTIVE, PoolStatus.FULL]:
                raise ValueError(f"Pool {pool_id} n'est pas actif")
            
            # Vérifie les limites de couverture
            if coverage_amount_usd < self.config.min_coverage_usd:
                raise ValueError(f"Couverture trop faible: {coverage_amount_usd}")
            
            if coverage_amount_usd > self.config.max_coverage_usd:
                raise ValueError(f"Couverture trop élevée: {coverage_amount_usd}")
            
            # Vérifie que le pool a suffisamment de capacité
            if coverage_amount_usd > pool.coverage_provided_usd:
                raise ValueError(f"Capacité insuffisante: {coverage_amount_usd} > {pool.coverage_provided_usd}")
            
            # Vérifie la réputation de l'assuré
            insured_trust = self.reputation_oracle.get_trust_score(insured_did)
            if insured_trust < 0.4:
                raise ValueError(f"Réputation insuffisante: {insured_trust} < 0.4")
            
            # Détermine la catégorie de risque (simplifié)
            risk_category = self._assess_risk_category(insured_did, insurance_type)
            
            # Calcule la prime
            premium_amount = self._calculate_premium(
                coverage_amount_usd, insurance_type, risk_category, duration_days
            )
            
            # Vérifie la prime minimum
            if premium_amount < self.config.min_premium_usd:
                premium_amount = self.config.min_premium_usd
            
            # Génère un ID de police unique
            policy_id = f"policy_{uuid.uuid4().hex[:16]}"
            
            # Crée la police
            policy = InsurancePolicy(
                policy_id=policy_id,
                insured_did=insured_did,
                pool_id=pool_id,
                insurance_type=insurance_type,
                coverage_amount_usd=coverage_amount_usd,
                premium_amount_usd=premium_amount,
                deductible_rate=self.config.deductible_rates.get(insurance_type, 0.1),
                risk_category=risk_category,
                start_date=int(time.time()),
                end_date=int(time.time()) + (duration_days * 86400),
                metadata=metadata
            )
            
            # Enregistre la police
            self._policies[policy_id] = policy
            pool.policies.append(policy)
            
            # Réduit la capacité du pool
            pool.coverage_provided_usd -= coverage_amount_usd
            
            # Distribue la prime aux participants
            await self._distribute_premium(pool_id, premium_amount)
            
            logger.info(f"Police achetée: {policy_id} - {coverage_amount_usd} USD - {premium_amount} USD")
            return policy
            
        except Exception as e:
            logger.error(f"Erreur achat police: {e}")
            return None
    
    async def file_claim(self, policy_id: str, amount_requested_usd: float,
                        description: str, evidence: List[Dict[str, any]],
                        metadata: Optional[Dict] = None) -> Optional[InsuranceClaim]:
        """Dépose une réclamation d'assurance"""
        try:
            if policy_id not in self._policies:
                raise ValueError(f"Police {policy_id} non trouvé")
            
            policy = self._policies[policy_id]
            
            # Vérifie que la police est active
            if policy.status != "active":
                raise ValueError(f"Police {policy_id} n'est pas active")
            
            # Vérifie que la réclamation est dans la période de couverture
            current_time = time.time()
            if current_time < policy.start_date or current_time > policy.end_date:
                raise ValueError("Réclamation hors période de couverture")
            
            # Vérifie le montant maximum
            max_claim = policy.coverage_amount_usd
            if amount_requested_usd > max_claim:
                amount_requested_usd = max_claim
            
            # Génère un ID de réclamation unique
            claim_id = f"claim_{uuid.uuid4().hex[:16]}"
            
            # Crée la réclamation
            claim = InsuranceClaim(
                claim_id=claim_id,
                policy_id=policy_id,
                insured_did=policy.insured_did,
                pool_id=policy.pool_id,
                amount_requested_usd=amount_requested_usd,
                description=description,
                evidence=evidence,
                status=ClaimStatus.PENDING,
                filed_date=int(current_time),
                metadata=metadata
            )
            
            # Enregistre la réclamation
            self._claims[claim_id] = claim
            
            # Met à jour la police
            policy.claims_filed += 1
            
            # Met à jour le pool
            pool = self._pools[policy.pool_id]
            pool.claims.append(claim)
            
            logger.info(f"Réclamation déposée: {claim_id} - {amount_requested_usd} USD")
            return claim
            
        except Exception as e:
            logger.error(f"Erreur dépôt réclamation: {e}")
            return None
    
    async def process_claim(self, claim_id: str, reviewer_did: str,
                           approved_amount_usd: Optional[float] = None,
                           rejection_reason: Optional[str] = None) -> bool:
        """Traite une réclamation d'assurance"""
        try:
            if claim_id not in self._claims:
                raise ValueError(f"Réclamation {claim_id} non trouvé")
            
            claim = self._claims[claim_id]
            
            if claim.status != ClaimStatus.PENDING:
                raise ValueError(f"Réclamation {claim_id} n'est pas en attente")
            
            # Vérifie la réputation du réviseur
            reviewer_trust = self.reputation_oracle.get_trust_score(reviewer_did)
            if reviewer_trust < 0.6:
                raise ValueError(f"Réputation réviseur insuffisante: {reviewer_trust} < 0.6")
            
            # Traite la réclamation
            if approved_amount_usd is not None:
                # Réclamation approuvée
                claim.status = ClaimStatus.APPROVED
                claim.approved_amount_usd = approved_amount_usd
                claim.reviewer_did = reviewer_did
                claim.reviewed_date = int(time.time())
                
                # Met à jour la police
                policy = self._policies[claim.policy_id]
                policy.claims_paid += 1
                
                # Paiement de la réclamation
                await self._pay_claim(claim)
                
                logger.info(f"Réclamation approuvée: {claim_id} - {approved_amount_usd} USD")
                
            elif rejection_reason:
                # Réclamation rejetée
                claim.status = ClaimStatus.REJECTED
                claim.rejection_reason = rejection_reason
                claim.reviewer_did = reviewer_did
                claim.reviewed_date = int(time.time())
                
                logger.info(f"Réclamation rejetée: {claim_id} - {rejection_reason}")
                
            else:
                raise ValueError("Soit approved_amount_usd soit rejection_reason doit être fourni")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur traitement réclamation: {e}")
            return False
    
    def _assess_risk_category(self, insured_did: str, insurance_type: InsuranceType) -> RiskCategory:
        """Évalue la catégorie de risque d'un assuré"""
        # Implémentation simplifiée
        # Dans une vraie implémentation, on utiliserait l'AI et les données historiques
        
        import random
        
        # Base sur le score de réputation
        reputation = self.reputation_oracle.get_trust_score(insured_did)
        
        if reputation >= 0.8:
            base_risk = RiskCategory.LOW
        elif reputation >= 0.6:
            base_risk = RiskCategory.MEDIUM
        elif reputation >= 0.4:
            base_risk = RiskCategory.HIGH
        else:
            base_risk = RiskCategory.EXTREME
        
        # Ajoute une variation aléatoire basée sur le type d'assurance
        risk_adjustment = {
            InsuranceType.SMART_CONTRACT_FAILURE: 0,
            InsuranceType.ORACLE_FAILURE: -1,  # Moins risqué
            InsuranceType.COLLATERAL_LIQUIDATION: 1,  # Plus risqué
            InsuranceType.SERVICE_DISPUTE: 0,
            InsuranceType.AGENT_MALFUNCTION: 1,
            InsuranceType.CROSS_CHAIN_BRIDGE_FAILURE: 2  # Beaucoup plus risqué
        }
        
        adjustment = risk_adjustment.get(insurance_type, 0)
        
        # Convertit l'ajustement en catégorie
        risk_values = list(RiskCategory)
        current_index = risk_values.index(base_risk)
        new_index = max(0, min(len(risk_values) - 1, current_index + adjustment))
        
        return risk_values[new_index]
    
    def _calculate_premium(self, coverage_amount_usd: float, insurance_type: InsuranceType,
                          risk_category: RiskCategory, duration_days: int) -> float:
        """Calcule le montant de la prime"""
        # Taux de base pour ce type d'assurance
        base_rate = self.config.base_premium_rates.get(insurance_type, 0.03)
        
        # Multiplicateur de risque
        risk_multiplier = self.config.risk_multipliers.get(risk_category, 1.0)
        
        # Ajustement pour la durée (taux annuel)
        duration_years = duration_days / 365
        
        # Calcul de la prime
        premium = coverage_amount_usd * base_rate * risk_multiplier * duration_years
        
        return premium
    
    async def _distribute_premium(self, pool_id: str, premium_amount_usd: float):
        """Distribue la prime aux participants du pool"""
        try:
            if pool_id not in self._pools:
                return
            
            pool = self._pools[pool_id]
            
            # Soustrait les frais de gestion
            management_fee = premium_amount_usd * self.config.pool_management_fee_percent
            net_premium = premium_amount_usd - management_fee
            
            # Distribue aux participants proportionnellement à leur part
            for participant in pool.participants:
                participant_share = net_premium * participant.share_percentage
                participant.rewards_earned_usd += participant_share
            
            logger.info(f"Prime distribuée: {premium_amount_usd} USD dans pool {pool_id}")
            
        except Exception as e:
            logger.error(f"Erreur distribution prime: {e}")
    
    async def _pay_claim(self, claim: InsuranceClaim):
        """Paie une réclamation approuvée"""
        try:
            # Marque comme payée
            claim.status = ClaimStatus.PAID
            claim.paid_date = int(time.time())
            
            # Met à jour les statistiques du pool
            pool = self._pools[claim.pool_id]
            
            # Dans une vraie implémentation, on enverrait les fonds à l'assuré
            logger.info(f"Réclamation payée: {claim.claim_id} - {claim.approved_amount_usd} USD")
            
        except Exception as e:
            logger.error(f"Erreur paiement réclamation: {e}")
    
    async def get_pool(self, pool_id: str) -> Optional[InsurancePool]:
        """Récupère un pool par son ID"""
        return self._pools.get(pool_id)
    
    async def get_policy(self, policy_id: str) -> Optional[InsurancePolicy]:
        """Récupère une police par son ID"""
        return self._policies.get(policy_id)
    
    async def get_claim(self, claim_id: str) -> Optional[InsuranceClaim]:
        """Récupère une réclamation par son ID"""
        return self._claims.get(claim_id)
    
    async def get_pools_by_type(self, insurance_type: InsuranceType) -> List[InsurancePool]:
        """Récupère tous les pools d'un type donné"""
        return [pool for pool in self._pools.values() if pool.insurance_type == insurance_type]
    
    async def _start_pool_monitoring(self):
        """Démarre la surveillance des pools"""
        async def monitor_pools():
            while True:
                try:
                    # Vérifie la santé de tous les pools
                    for pool in self._pools.values():
                        await self._check_pool_health(pool)
                    
                    await asyncio.sleep(self.config.monitoring_interval_minutes * 60)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance pools: {e}")
                    await asyncio.sleep(300)
        
        task = asyncio.create_task(monitor_pools())
        self._monitoring_tasks.append(task)
    
    async def _check_pool_health(self, pool: InsurancePool):
        """Vérifie la santé d'un pool"""
        try:
            # Calcule le ratio de réclamations
            total_claims_paid = sum(
                claim.approved_amount_usd or 0
                for claim in pool.claims
                if claim.status == ClaimStatus.PAID
            )
            
            claim_ratio = total_claims_paid / pool.total_capital_usd if pool.total_capital_usd > 0 else 0
            
            # Vérifie les seuils
            if claim_ratio > self.config.max_claim_ratio:
                pool.status = PoolStatus.LIQUIDATING
                logger.warning(f"Pool {pool.pool_id} en liquidation: ratio={claim_ratio:.2f}")
            
            # Vérifie les polices expirées
            current_time = time.time()
            expired_policies = [
                policy for policy in pool.policies
                if policy.status == "active" and policy.end_date < current_time
            ]
            
            for policy in expired_policies:
                policy.status = "expired"
            
            if expired_policies:
                logger.info(f"{len(expired_policies)} polices expirées dans pool {pool.pool_id}")
                
        except Exception as e:
            logger.error(f"Erreur vérification santé pool: {e}")
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._pools.clear()
        self._policies.clear()
        self._claims.clear()