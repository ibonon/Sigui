"""
Configuration du système de gouvernance avancée pour Sigui.
Système de DAO multi-niveaux avec voting quadratique et pondération basée sur la réputation.
"""

from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
import os


class GovernanceLevel(Enum):
    """Niveaux de gouvernance hiérarchique."""
    COMMUNITY = "community"  # Niveau communautaire
    TECHNICAL = "technical"  # Niveau technique
    FINANCIAL = "financial"  # Niveau financier
    STRATEGIC = "strategic"  # Niveau stratégique


class ProposalType(Enum):
    """Types de propositions de gouvernance."""
    PARAMETER_CHANGE = "parameter_change"  # Changement de paramètres
    TREASURY_SPENDING = "treasury_spending"  # Dépense du trésor
    PROTOCOL_UPGRADE = "protocol_upgrade"  # Mise à jour du protocole
    COMMITTEE_ELECTION = "committee_election"  # Élection de comité
    EMERGENCY_ACTION = "emergency_action"  # Action d'urgence


class VotingSystem(Enum):
    """Systèmes de voting supportés."""
    QUADRATIC_VOTING = "quadratic_voting"  # Voting quadratique
    REPUTATION_WEIGHTED = "reputation_weighted"  # Pondération par réputation
    TOKEN_WEIGHTED = "token_weighted"  # Pondération par tokens
    ONE_PERSON_ONE_VOTE = "one_person_one_vote"  # Une personne = un vote


class GovernanceConfig(BaseModel):
    """Configuration principale de la gouvernance."""
    
    # Niveaux de gouvernance
    governance_levels: List[GovernanceLevel] = Field(
        default=[
            GovernanceLevel.COMMUNITY,
            GovernanceLevel.TECHNICAL,
            GovernanceLevel.FINANCIAL,
            GovernanceLevel.STRATEGIC
        ],
        description="Niveaux de gouvernance hiérarchique"
    )
    
    # Paramètres de voting
    voting_system: VotingSystem = Field(
        default=VotingSystem.QUADRATIC_VOTING,
        description="Système de voting principal"
    )
    
    quadratic_voting_cost_factor: float = Field(
        default=0.01,
        ge=0.001,
        le=0.1,
        description="Facteur de coût pour le voting quadratique"
    )
    
    min_voting_power: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Puissance de vote minimale requise"
    )
    
    # Seuils de décision
    quorum_threshold: float = Field(
        default=0.3,
        ge=0.1,
        le=0.8,
        description="Seuil de quorum pour les propositions"
    )
    
    approval_threshold: float = Field(
        default=0.6,
        ge=0.5,
        le=0.9,
        description="Seuil d'approbation pour les propositions"
    )
    
    emergency_threshold: float = Field(
        default=0.8,
        ge=0.7,
        le=0.95,
        description="Seuil pour les actions d'urgence"
    )
    
    # Durées
    proposal_duration_days: int = Field(
        default=7,
        ge=1,
        le=30,
        description="Durée des propositions en jours"
    )
    
    voting_duration_days: int = Field(
        default=3,
        ge=1,
        le=14,
        description="Durée du voting en jours"
    )
    
    execution_delay_days: int = Field(
        default=2,
        ge=0,
        le=7,
        description="Délai d'exécution après approbation"
    )
    
    # Comités et délégation
    max_committee_size: int = Field(
        default=9,
        ge=3,
        le=21,
        description="Taille maximale des comités"
    )
    
    delegation_enabled: bool = Field(
        default=True,
        description="Activer la délégation de votes"
    )
    
    max_delegation_depth: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Profondeur maximale de délégation"
    )
    
    # Réputation et pondération
    reputation_weight_factor: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Facteur de pondération de la réputation"
    )
    
    token_weight_factor: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Facteur de pondération des tokens"
    )
    
    min_reputation_for_voting: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Réputation minimale pour voter"
    )
    
    # Trésorerie
    treasury_address: Optional[str] = Field(
        default=None,
        description="Adresse du trésor de gouvernance"
    )
    
    max_treasury_spend_per_proposal: float = Field(
        default=10000.0,
        ge=100.0,
        le=1000000.0,
        description="Dépense maximale du trésor par proposition"
    )
    
    # Surveillance et sécurité
    fraud_detection_enabled: bool = Field(
        default=True,
        description="Activer la détection de fraude"
    )
    
    sybil_resistance_enabled: bool = Field(
        default=True,
        description="Activer la résistance aux attaques Sybil"
    )
    
    audit_logging_enabled: bool = Field(
        default=True,
        description="Activer la journalisation d'audit"
    )
    
    # Configuration avancée
    enable_ai_analysis: bool = Field(
        default=True,
        description="Activer l'analyse AI des propositions"
    )
    
    enable_sentiment_analysis: bool = Field(
        default=True,
        description="Activer l'analyse de sentiment des discussions"
    )
    
    enable_prediction_markets: bool = Field(
        default=False,
        description="Activer les marchés de prédiction pour les propositions"
    )
    
    class Config:
        use_enum_values = True
        validate_assignment = True
    
    @validator('reputation_weight_factor', 'token_weight_factor')
    def validate_weight_factors(cls, v, values):
        """Valide que les facteurs de pondération sont cohérents."""
        if 'reputation_weight_factor' in values and 'token_weight_factor' in values:
            total = values.get('reputation_weight_factor', 0) + values.get('token_weight_factor', 0)
            if total > 1.0:
                raise ValueError("La somme des facteurs de pondération ne peut pas dépasser 1.0")
        return v
    
    @validator('treasury_address')
    def validate_treasury_address(cls, v):
        """Valide l'adresse du trésor si fournie."""
        if v is not None and len(v) < 20:
            raise ValueError("Adresse du trésor invalide")
        return v


def load_governance_config() -> GovernanceConfig:
    """
    Charge la configuration de gouvernance depuis les variables d'environnement.
    
    Returns:
        GovernanceConfig: Configuration chargée
    """
    return GovernanceConfig(
        quadratic_voting_cost_factor=float(os.getenv('GOV_QUADRATIC_COST_FACTOR', '0.01')),
        min_voting_power=float(os.getenv('GOV_MIN_VOTING_POWER', '0.1')),
        quorum_threshold=float(os.getenv('GOV_QUORUM_THRESHOLD', '0.3')),
        approval_threshold=float(os.getenv('GOV_APPROVAL_THRESHOLD', '0.6')),
        emergency_threshold=float(os.getenv('GOV_EMERGENCY_THRESHOLD', '0.8')),
        proposal_duration_days=int(os.getenv('GOV_PROPOSAL_DURATION_DAYS', '7')),
        voting_duration_days=int(os.getenv('GOV_VOTING_DURATION_DAYS', '3')),
        execution_delay_days=int(os.getenv('GOV_EXECUTION_DELAY_DAYS', '2')),
        max_committee_size=int(os.getenv('GOV_MAX_COMMITTEE_SIZE', '9')),
        delegation_enabled=os.getenv('GOV_DELEGATION_ENABLED', 'true').lower() == 'true',
        max_delegation_depth=int(os.getenv('GOV_MAX_DELEGATION_DEPTH', '3')),
        reputation_weight_factor=float(os.getenv('GOV_REPUTATION_WEIGHT_FACTOR', '0.7')),
        token_weight_factor=float(os.getenv('GOV_TOKEN_WEIGHT_FACTOR', '0.3')),
        min_reputation_for_voting=float(os.getenv('GOV_MIN_REPUTATION_FOR_VOTING', '0.4')),
        treasury_address=os.getenv('GOV_TREASURY_ADDRESS'),
        max_treasury_spend_per_proposal=float(os.getenv('GOV_MAX_TREASURY_SPEND', '10000.0')),
        fraud_detection_enabled=os.getenv('GOV_FRAUD_DETECTION_ENABLED', 'true').lower() == 'true',
        sybil_resistance_enabled=os.getenv('GOV_SYBIL_RESISTANCE_ENABLED', 'true').lower() == 'true',
        audit_logging_enabled=os.getenv('GOV_AUDIT_LOGGING_ENABLED', 'true').lower() == 'true',
        enable_ai_analysis=os.getenv('GOV_ENABLE_AI_ANALYSIS', 'true').lower() == 'true',
        enable_sentiment_analysis=os.getenv('GOV_ENABLE_SENTIMENT_ANALYSIS', 'true').lower() == 'true',
        enable_prediction_markets=os.getenv('GOV_ENABLE_PREDICTION_MARKETS', 'false').lower() == 'true'
    )