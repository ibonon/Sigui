"""
Configuration du système d'assurance décentralisée pour Sigui
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import os


class InsuranceType(Enum):
    """Types d'assurance disponibles"""
    SMART_CONTRACT_FAILURE = "smart_contract_failure"
    ORACLE_FAILURE = "oracle_failure"
    COLLATERAL_LIQUIDATION = "collateral_liquidation"
    SERVICE_DISPUTE = "service_dispute"
    AGENT_MALFUNCTION = "agent_malfunction"
    CROSS_CHAIN_BRIDGE_FAILURE = "cross_chain_bridge_failure"


class RiskCategory(Enum):
    """Catégories de risque"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class ClaimStatus(Enum):
    """Statuts des réclamations"""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class InsuranceConfig(BaseModel):
    """Configuration du système d'assurance décentralisée"""
    
    # Configuration générale
    enabled: bool = Field(default=True, description="Activer le système d'assurance")
    min_premium_usd: float = Field(default=10.0, description="Prime minimum en USD")
    max_coverage_usd: float = Field(default=1000000, description="Couverture maximum en USD")
    min_coverage_usd: float = Field(default=1000, description="Couverture minimum en USD")
    
    # Configuration des pools
    pool_creation_min_stake_usd: float = Field(default=10000, description="Stake minimum pour créer un pool")
    pool_management_fee_percent: float = Field(default=0.05, description="Frais de gestion du pool (5%)")
    pool_reserve_ratio: float = Field(default=0.3, description="Ratio de réserve minimum (30%)")
    
    # Configuration des primes
    base_premium_rates: Dict[InsuranceType, float] = Field(
        default={
            InsuranceType.SMART_CONTRACT_FAILURE: 0.03,  # 3% par an
            InsuranceType.ORACLE_FAILURE: 0.02,  # 2% par an
            InsuranceType.COLLATERAL_LIQUIDATION: 0.05,  # 5% par an
            InsuranceType.SERVICE_DISPUTE: 0.04,  # 4% par an
            InsuranceType.AGENT_MALFUNCTION: 0.06,  # 6% par an
            InsuranceType.CROSS_CHAIN_BRIDGE_FAILURE: 0.08  # 8% par an
        },
        description="Taux de prime de base par type d'assurance"
    )
    
    risk_multipliers: Dict[RiskCategory, float] = Field(
        default={
            RiskCategory.LOW: 0.8,
            RiskCategory.MEDIUM: 1.0,
            RiskCategory.HIGH: 1.5,
            RiskCategory.EXTREME: 2.5
        },
        description="Multiplicateurs de risque"
    )
    
    # Configuration des franchises
    deductible_rates: Dict[InsuranceType, float] = Field(
        default={
            InsuranceType.SMART_CONTRACT_FAILURE: 0.1,  # 10% de franchise
            InsuranceType.ORACLE_FAILURE: 0.05,  # 5% de franchise
            InsuranceType.COLLATERAL_LIQUIDATION: 0.15,  # 15% de franchise
            InsuranceType.SERVICE_DISPUTE: 0.2,  # 20% de franchise
            InsuranceType.AGENT_MALFUNCTION: 0.1,  # 10% de franchise
            InsuranceType.CROSS_CHAIN_BRIDGE_FAILURE: 0.25  # 25% de franchise
        },
        description="Taux de franchise par type d'assurance"
    )
    
    # Configuration des limites
    max_coverage_per_pool_usd: float = Field(default=5000000, description="Couverture maximum par pool")
    min_pool_participants: int = Field(default=10, description="Nombre minimum de participants par pool")
    max_claim_ratio: float = Field(default=0.7, description="Ratio maximum de réclamations/pool (70%)")
    
    # Configuration AI
    ai_risk_assessment_enabled: bool = Field(default=True, description="Activer l'évaluation de risque AI")
    ai_claim_assessment_enabled: bool = Field(default=True, description="Activer l'évaluation de réclamation AI")
    ai_model_path: Optional[str] = Field(default=None, description="Chemin vers les modèles AI")
    
    # Configuration de surveillance
    monitoring_interval_minutes: int = Field(default=30, description="Intervalle de surveillance en minutes")
    claim_review_period_days: int = Field(default=7, description="Période de revue des réclamations en jours")
    
    # Configuration des blockchains
    supported_blockchains: List[str] = Field(
        default=["ethereum", "cardano", "polkadot", "solana"],
        description="Blockchains supportées pour les polices d'assurance"
    )
    
    # Configuration des oracles
    risk_oracle_url: Optional[str] = Field(default=None, description="URL de l'oracle de risque")
    claim_oracle_url: Optional[str] = Field(default=None, description="URL de l'oracle de réclamation")
    
    class Config:
        env_prefix = "INSURANCE_"
    
    @classmethod
    def from_env(cls) -> "InsuranceConfig":
        """Crée une configuration à partir des variables d'environnement"""
        # Mappe les chaînes vers les enums
        def parse_insurance_types(value: str) -> Dict[InsuranceType, float]:
            try:
                import json
                raw_dict = json.loads(value)
                return {InsuranceType(k): v for k, v in raw_dict.items()}
            except:
                return cls.__fields__["base_premium_rates"].default
        
        def parse_risk_categories(value: str) -> Dict[RiskCategory, float]:
            try:
                import json
                raw_dict = json.loads(value)
                return {RiskCategory(k): v for k, v in raw_dict.items()}
            except:
                return cls.__fields__["risk_multipliers"].default
        
        def parse_deductible_rates(value: str) -> Dict[InsuranceType, float]:
            try:
                import json
                raw_dict = json.loads(value)
                return {InsuranceType(k): v for k, v in raw_dict.items()}
            except:
                return cls.__fields__["deductible_rates"].default
        
        return cls(
            enabled=os.getenv("INSURANCE_ENABLED", "true").lower() == "true",
            min_premium_usd=float(os.getenv("INSURANCE_MIN_PREMIUM_USD", "10.0")),
            max_coverage_usd=float(os.getenv("INSURANCE_MAX_COVERAGE_USD", "1000000")),
            min_coverage_usd=float(os.getenv("INSURANCE_MIN_COVERAGE_USD", "1000")),
            pool_creation_min_stake_usd=float(os.getenv("INSURANCE_POOL_CREATION_MIN_STAKE_USD", "10000")),
            pool_management_fee_percent=float(os.getenv("INSURANCE_POOL_MANAGEMENT_FEE_PERCENT", "0.05")),
            pool_reserve_ratio=float(os.getenv("INSURANCE_POOL_RESERVE_RATIO", "0.3")),
            base_premium_rates=parse_insurance_types(
                os.getenv("INSURANCE_BASE_PREMIUM_RATES", "")
            ),
            risk_multipliers=parse_risk_categories(
                os.getenv("INSURANCE_RISK_MULTIPLIERS", "")
            ),
            deductible_rates=parse_deductible_rates(
                os.getenv("INSURANCE_DEDUCTIBLE_RATES", "")
            ),
            max_coverage_per_pool_usd=float(os.getenv("INSURANCE_MAX_COVERAGE_PER_POOL_USD", "5000000")),
            min_pool_participants=int(os.getenv("INSURANCE_MIN_POOL_PARTICIPANTS", "10")),
            max_claim_ratio=float(os.getenv("INSURANCE_MAX_CLAIM_RATIO", "0.7")),
            ai_risk_assessment_enabled=os.getenv("INSURANCE_AI_RISK_ASSESSMENT_ENABLED", "true").lower() == "true",
            ai_claim_assessment_enabled=os.getenv("INSURANCE_AI_CLAIM_ASSESSMENT_ENABLED", "true").lower() == "true",
            ai_model_path=os.getenv("INSURANCE_AI_MODEL_PATH"),
            monitoring_interval_minutes=int(os.getenv("INSURANCE_MONITORING_INTERVAL_MINUTES", "30")),
            claim_review_period_days=int(os.getenv("INSURANCE_CLAIM_REVIEW_PERIOD_DAYS", "7")),
            supported_blockchains=os.getenv("INSURANCE_SUPPORTED_BLOCKCHAINS", "ethereum,cardano,polkadot,solana").split(","),
            risk_oracle_url=os.getenv("INSURANCE_RISK_ORACLE_URL"),
            claim_oracle_url=os.getenv("INSURANCE_CLAIM_ORACLE_URL"),
        )