"""
Configuration du système de crédit pour Sigui
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from enum import Enum
import os


class CreditRiskLevel(Enum):
    """Niveaux de risque de crédit"""
    AAA = "AAA"  # Très faible risque
    AA = "AA"    # Faible risque
    A = "A"      # Risque acceptable
    BBB = "BBB"  # Risque modéré
    BB = "BB"    # Risque élevé
    B = "B"      # Risque très élevé
    C = "C"      # Risque extrême


class CollateralType(Enum):
    """Types de collatéral supportés"""
    BITCOIN = "bitcoin"
    ETHEREUM = "ethereum"
    CARDANO = "cardano"
    POLKADOT = "polkadot"
    REAL_ESTATE = "real_estate"
    STOCKS = "stocks"
    BONDS = "bonds"


class LoanTerm(Enum):
    """Termes de prêt disponibles"""
    SHORT_TERM = "short_term"  # 1-3 mois
    MEDIUM_TERM = "medium_term"  # 3-12 mois
    LONG_TERM = "long_term"  # 1-5 ans


class CreditConfig(BaseModel):
    """Configuration du système de crédit cross-chain"""
    
    # Configuration générale
    enabled: bool = Field(default=True, description="Activer le système de crédit")
    min_credit_score: float = Field(default=0.3, description="Score de crédit minimum requis")
    max_loan_amount_usd: float = Field(default=1000000, description="Montant maximum de prêt en USD")
    min_loan_amount_usd: float = Field(default=1000, description="Montant minimum de prêt en USD")
    
    # Configuration des taux
    base_interest_rate: float = Field(default=0.05, description="Taux d'intérêt de base (5%)")
    risk_premium_multiplier: Dict[CreditRiskLevel, float] = Field(
        default={
            CreditRiskLevel.AAA: 0.8,
            CreditRiskLevel.AA: 0.9,
            CreditRiskLevel.A: 1.0,
            CreditRiskLevel.BBB: 1.2,
            CreditRiskLevel.BB: 1.5,
            CreditRiskLevel.B: 2.0,
            CreditRiskLevel.C: 3.0
        },
        description="Multiplicateur de prime de risque par niveau"
    )
    
    # Configuration du collatéral
    collateral_requirements: Dict[CollateralType, float] = Field(
        default={
            CollateralType.BITCOIN: 1.5,  # 150% de collatéral
            CollateralType.ETHEREUM: 1.6,
            CollateralType.CARDANO: 1.8,
            CollateralType.POLKADOT: 1.7,
            CollateralType.REAL_ESTATE: 1.3,
            CollateralType.STOCKS: 1.4,
            CollateralType.BONDS: 1.2
        },
        description="Exigences de collatéral par type d'asset"
    )
    
    # Configuration des limites
    max_loan_to_value_ratio: float = Field(default=0.7, description="Ratio maximum prêt/valeur (70%)")
    min_collateralization_ratio: float = Field(default=1.3, description="Ratio de collatéralisation minimum (130%)")
    liquidation_threshold: float = Field(default=1.1, description="Seuil de liquidation (110%)")
    
    # Configuration des termes
    available_loan_terms: List[LoanTerm] = Field(
        default=[LoanTerm.SHORT_TERM, LoanTerm.MEDIUM_TERM, LoanTerm.LONG_TERM],
        description="Termes de prêt disponibles"
    )
    
    term_durations: Dict[LoanTerm, int] = Field(
        default={
            LoanTerm.SHORT_TERM: 90,  # jours
            LoanTerm.MEDIUM_TERM: 180,
            LoanTerm.LONG_TERM: 365
        },
        description="Durées des termes en jours"
    )
    
    # Configuration AI
    ai_scoring_enabled: bool = Field(default=True, description="Activer le scoring AI")
    ai_model_path: Optional[str] = Field(default=None, description="Chemin vers le modèle AI")
    ai_confidence_threshold: float = Field(default=0.8, description="Seuil de confiance AI")
    
    # Configuration de surveillance
    monitoring_interval_minutes: int = Field(default=15, description="Intervalle de surveillance en minutes")
    health_check_interval_hours: int = Field(default=1, description="Intervalle de vérification santé en heures")
    
    # Configuration des blockchains
    supported_blockchains: List[str] = Field(
        default=["bitcoin", "ethereum", "cardano", "polkadot"],
        description="Blockchains supportées pour le collatéral"
    )
    
    # Configuration des oracles
    price_oracle_url: str = Field(default="https://api.coingecko.com/api/v3", description="URL de l'oracle de prix")
    reputation_oracle_url: Optional[str] = Field(default=None, description="URL de l'oracle de réputation")
    
    class Config:
        env_prefix = "CREDIT_"
    
    @classmethod
    def from_env(cls) -> "CreditConfig":
        """Crée une configuration à partir des variables d'environnement"""
        # Mappe les chaînes vers les enums
        def parse_risk_levels(value: str) -> Dict[CreditRiskLevel, float]:
            try:
                import json
                raw_dict = json.loads(value)
                return {CreditRiskLevel(k): v for k, v in raw_dict.items()}
            except:
                return cls.__fields__["risk_premium_multiplier"].default
        
        def parse_collateral_types(value: str) -> Dict[CollateralType, float]:
            try:
                import json
                raw_dict = json.loads(value)
                return {CollateralType(k): v for k, v in raw_dict.items()}
            except:
                return cls.__fields__["collateral_requirements"].default
        
        def parse_loan_terms(value: str) -> List[LoanTerm]:
            try:
                import json
                raw_list = json.loads(value)
                return [LoanTerm(term) for term in raw_list]
            except:
                return cls.__fields__["available_loan_terms"].default
        
        def parse_term_durations(value: str) -> Dict[LoanTerm, int]:
            try:
                import json
                raw_dict = json.loads(value)
                return {LoanTerm(k): v for k, v in raw_dict.items()}
            except:
                return cls.__fields__["term_durations"].default
        
        return cls(
            enabled=os.getenv("CREDIT_ENABLED", "true").lower() == "true",
            min_credit_score=float(os.getenv("CREDIT_MIN_SCORE", "0.3")),
            max_loan_amount_usd=float(os.getenv("CREDIT_MAX_AMOUNT_USD", "1000000")),
            min_loan_amount_usd=float(os.getenv("CREDIT_MIN_AMOUNT_USD", "1000")),
            base_interest_rate=float(os.getenv("CREDIT_BASE_INTEREST_RATE", "0.05")),
            risk_premium_multiplier=parse_risk_levels(
                os.getenv("CREDIT_RISK_PREMIUM_MULTIPLIER", "")
            ),
            collateral_requirements=parse_collateral_types(
                os.getenv("CREDIT_COLLATERAL_REQUIREMENTS", "")
            ),
            max_loan_to_value_ratio=float(os.getenv("CREDIT_MAX_LTV_RATIO", "0.7")),
            min_collateralization_ratio=float(os.getenv("CREDIT_MIN_COLLATERAL_RATIO", "1.3")),
            liquidation_threshold=float(os.getenv("CREDIT_LIQUIDATION_THRESHOLD", "1.1")),
            available_loan_terms=parse_loan_terms(
                os.getenv("CREDIT_AVAILABLE_TERMS", "")
            ),
            term_durations=parse_term_durations(
                os.getenv("CREDIT_TERM_DURATIONS", "")
            ),
            ai_scoring_enabled=os.getenv("CREDIT_AI_SCORING_ENABLED", "true").lower() == "true",
            ai_model_path=os.getenv("CREDIT_AI_MODEL_PATH"),
            ai_confidence_threshold=float(os.getenv("CREDIT_AI_CONFIDENCE_THRESHOLD", "0.8")),
            monitoring_interval_minutes=int(os.getenv("CREDIT_MONITORING_INTERVAL_MINUTES", "15")),
            health_check_interval_hours=int(os.getenv("CREDIT_HEALTH_CHECK_INTERVAL_HOURS", "1")),
            supported_blockchains=os.getenv("CREDIT_SUPPORTED_BLOCKCHAINS", "bitcoin,ethereum,cardano,polkadot").split(","),
            price_oracle_url=os.getenv("CREDIT_PRICE_ORACLE_URL", "https://api.coingecko.com/api/v3"),
            reputation_oracle_url=os.getenv("CREDIT_REPUTATION_ORACLE_URL"),
        )