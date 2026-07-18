"""
Système d'évaluation de risque AI-powered pour l'assurance Sigui
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import logging

from .insurance_config import InsuranceConfig, InsuranceType, RiskCategory
from ..reputation.reputation_oracle import ReputationOracle
from ..credit.credit_scoring import CreditScoringSystem


logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    """Évaluation de risque complète"""
    overall_risk_score: float  # 0.0 (faible risque) à 1.0 (risque élevé)
    risk_category: RiskCategory
    confidence: float  # Confiance du modèle AI
    factors: Dict[str, float]  # Facteurs contributifs
    recommendations: List[str]
    timestamp: int


@dataclass
class RiskFactor:
    """Facteur de risque individuel"""
    factor_id: str
    name: str
    weight: float
    score: float
    description: str
    evidence: Optional[List[Dict[str, Any]]] = None


class RiskAssessmentSystem:
    """Système d'évaluation de risque utilisant AI et données cross-chain"""
    
    def __init__(self, config: InsuranceConfig,
                 reputation_oracle: ReputationOracle,
                 credit_scoring: Optional[CreditScoringSystem] = None):
        self.config = config
        self.reputation_oracle = reputation_oracle
        self.credit_scoring = credit_scoring
        
        self._risk_assessments: Dict[str, RiskAssessment] = {}
        self._risk_factors: Dict[str, RiskFactor] = {}
        self._monitoring_tasks: List[asyncio.Task] = []
        
        # Modèle AI simplifié
        self._ai_model = self._initialize_ai_model()
        
        # Facteurs de risque prédéfinis
        self._initialize_risk_factors()
    
    async def initialize(self) -> bool:
        """Initialise le système d'évaluation de risque"""
        try:
            if not self.config.enabled:
                logger.warning("Système d'assurance désactivé")
                return False
            
            # Charge les modèles AI si activés
            if self.config.ai_risk_assessment_enabled:
                await self._load_ai_models()
                logger.info("Modèles AI chargés pour l'évaluation de risque")
            
            # Démarre la surveillance
            await self._start_monitoring()
            
            logger.info("Système d'évaluation de risque initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation évaluation risque: {e}")
            return False
    
    def _initialize_ai_model(self) -> Dict:
        """Initialise un modèle AI simplifié pour l'évaluation de risque"""
        return {
            "version": "1.0",
            "features": [
                "reputation_score",
                "credit_history",
                "transaction_volume",
                "claim_history",
                "network_stability",
                "collateral_quality",
                "market_volatility"
            ],
            "weights": {
                "reputation_score": 0.25,
                "credit_history": 0.20,
                "transaction_volume": 0.15,
                "claim_history": 0.15,
                "network_stability": 0.10,
                "collateral_quality": 0.10,
                "market_volatility": 0.05
            }
        }
    
    def _initialize_risk_factors(self):
        """Initialise les facteurs de risque prédéfinis"""
        factors = [
            RiskFactor(
                factor_id="reputation",
                name="Score de réputation",
                weight=0.25,
                score=0.0,
                description="Score de confiance basé sur l'historique des interactions"
            ),
            RiskFactor(
                factor_id="credit",
                name="Historique de crédit",
                weight=0.20,
                score=0.0,
                description="Historique des prêts et remboursements"
            ),
            RiskFactor(
                factor_id="transactions",
                name="Volume de transactions",
                weight=0.15,
                score=0.0,
                description="Volume et fréquence des transactions"
            ),
            RiskFactor(
                factor_id="claims",
                name="Historique de réclamations",
                weight=0.15,
                score=0.0,
                description="Historique des réclamations d'assurance"
            ),
            RiskFactor(
                factor_id="network",
                name="Stabilité réseau",
                weight=0.10,
                score=0.0,
                description="Stabilité des connexions et des services"
            ),
            RiskFactor(
                factor_id="collateral",
                name="Qualité du collatéral",
                weight=0.10,
                score=0.0,
                description="Qualité et volatilité des assets de collatéral"
            ),
            RiskFactor(
                factor_id="market",
                name="Volatilité du marché",
                weight=0.05,
                score=0.0,
                description="Volatilité générale des marchés crypto"
            )
        ]
        
        for factor in factors:
            self._risk_factors[factor.factor_id] = factor
    
    async def _load_ai_models(self):
        """Charge les modèles AI depuis le chemin configuré"""
        try:
            if self.config.ai_model_path:
                # Implémentation simplifiée
                logger.info(f"Chargement modèles AI depuis: {self.config.ai_model_path}")
            else:
                logger.info("Utilisation des modèles AI par défaut")
                
        except Exception as e:
            logger.error(f"Erreur chargement modèles AI: {e}")
    
    async def assess_risk(self, insured_did: str, insurance_type: InsuranceType,
                         coverage_amount_usd: float,
                         collateral_info: Optional[Dict[str, Any]] = None) -> RiskAssessment:
        """Évalue le risque pour un assuré potentiel"""
        try:
            # Vérifie si une évaluation récente existe
            cache_key = f"{insured_did}_{insurance_type.value}"
            if cache_key in self._risk_assessments:
                existing_assessment = self._risk_assessments[cache_key]
                if time.time() < existing_assessment.timestamp + 86400:  # 24 heures
                    logger.info(f"Évaluation de risque récupérée depuis le cache: {insured_did}")
                    return existing_assessment
            
            # Collecte les données
            data = await self._collect_risk_data(insured_did, insurance_type, coverage_amount_usd, collateral_info)
            
            # Calcule le score de risque
            if self.config.ai_risk_assessment_enabled:
                risk_score, confidence, factors = await self._calculate_ai_risk_score(data)
            else:
                risk_score, confidence, factors = self._calculate_basic_risk_score(data)
            
            # Détermine la catégorie de risque
            risk_category = self._determine_risk_category(risk_score)
            
            # Génère des recommandations
            recommendations = self._generate_recommendations(risk_score, factors, insurance_type)
            
            # Crée l'évaluation
            assessment = RiskAssessment(
                overall_risk_score=risk_score,
                risk_category=risk_category,
                confidence=confidence,
                factors=factors,
                recommendations=recommendations,
                timestamp=int(time.time())
            )
            
            # Met en cache
            self._risk_assessments[cache_key] = assessment
            
            logger.info(f"Évaluation de risque effectuée pour {insured_did}: score={risk_score:.3f} ({risk_category.value})")
            return assessment
            
        except Exception as e:
            logger.error(f"Erreur évaluation risque: {e}")
            # Retourne une évaluation par défaut en cas d'erreur
            return RiskAssessment(
                overall_risk_score=1.0,
                risk_category=RiskCategory.EXTREME,
                confidence=0.0,
                factors={"error": 1.0},
                recommendations=["Évaluation échouée - risque élevé par défaut"],
                timestamp=int(time.time())
            )
    
    async def _collect_risk_data(self, insured_did: str, insurance_type: InsuranceType,
                                coverage_amount_usd: float,
                                collateral_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collecte les données pour l'évaluation de risque"""
        data = {
            "insured_did": insured_did,
            "insurance_type": insurance_type.value,
            "coverage_amount_usd": coverage_amount_usd,
            "timestamp": time.time()
        }
        
        # 1. Score de réputation
        try:
            reputation_score = self.reputation_oracle.get_trust_score(insured_did)
            data["reputation_score"] = reputation_score
        except Exception as e:
            logger.error(f"Erreur récupération réputation: {e}")
            data["reputation_score"] = 0.0
        
        # 2. Historique de crédit
        try:
            if self.credit_scoring:
                credit_score = await self.credit_scoring.calculate_credit_score(insured_did)
                data["credit_history"] = {
                    "overall_score": credit_score.overall_score,
                    "risk_level": credit_score.risk_level.value
                }
            else:
                data["credit_history"] = {"overall_score": 0.5, "risk_level": "medium"}
        except Exception as e:
            logger.error(f"Erreur récupération historique crédit: {e}")
            data["credit_history"] = {"overall_score": 0.5, "risk_level": "medium"}
        
        # 3. Volume de transactions
        try:
            transaction_data = await self._get_transaction_data(insured_did)
            data["transaction_volume"] = transaction_data
        except Exception as e:
            logger.error(f"Erreur récupération volume transactions: {e}")
            data["transaction_volume"] = {"total_usd": 0.0, "frequency": 0.0}
        
        # 4. Historique de réclamations
        try:
            claim_history = await self._get_claim_history(insured_did)
            data["claim_history"] = claim_history
        except Exception as e:
            logger.error(f"Erreur récupération historique réclamations: {e}")
            data["claim_history"] = {"total_claims": 0, "paid_claims": 0}
        
        # 5. Stabilité réseau
        try:
            network_stability = await self._get_network_stability(insured_did)
            data["network_stability"] = network_stability
        except Exception as e:
            logger.error(f"Erreur récupération stabilité réseau: {e}")
            data["network_stability"] = {"uptime": 0.95, "latency": 100}
        
        # 6. Qualité du collatéral
        try:
            collateral_quality = self._assess_collateral_quality(collateral_info)
            data["collateral_quality"] = collateral_quality
        except Exception as e:
            logger.error(f"Erreur évaluation qualité collatéral: {e}")
            data["collateral_quality"] = {"score": 0.5, "volatility": 0.3}
        
        # 7. Volatilité du marché
        try:
            market_volatility = await self._get_market_volatility()
            data["market_volatility"] = market_volatility
        except Exception as e:
            logger.error(f"Erreur récupération volatilité marché: {e}")
            data["market_volatility"] = {"btc_volatility": 0.02, "overall_volatility": 0.03}
        
        return data
    
    async def _get_transaction_data(self, did: str) -> Dict[str, Any]:
        """Récupère les données de transaction"""
        # Implémentation simplifiée
        return {
            "total_usd": 50000.0,
            "frequency": 2.5,  # transactions par jour
            "avg_amount_usd": 500.0,
            "success_rate": 0.98,
            "last_transaction_days": 1
        }
    
    async def _get_claim_history(self, did: str) -> Dict[str, Any]:
        """Récupère l'historique des réclamations"""
        # Implémentation simplifiée
        return {
            "total_claims": 2,
            "paid_claims": 1,
            "total_paid_usd": 5000.0,
            "avg_claim_amount_usd": 2500.0,
            "last_claim_days": 30
        }
    
    async def _get_network_stability(self, did: str) -> Dict[str, Any]:
        """Récupère la stabilité réseau"""
        # Implémentation simplifiée
        return {
            "uptime": 0.99,
            "latency": 50,  # ms
            "error_rate": 0.001,
            "connections": 25,
            "last_outage_days": 60
        }
    
    def _assess_collateral_quality(self, collateral_info: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Évalue la qualité du collatéral"""
        if not collateral_info:
            return {"score": 0.5, "volatility": 0.3, "liquidity": 0.7}
        
        # Évaluation simplifiée basée sur le type d'asset
        asset_type = collateral_info.get("type", "unknown")
        
        quality_scores = {
            "bitcoin": {"score": 0.9, "volatility": 0.04, "liquidity": 0.95},
            "ethereum": {"score": 0.8, "volatility": 0.05, "liquidity": 0.9},
            "cardano": {"score": 0.7, "volatility": 0.06, "liquidity": 0.8},
            "polkadot": {"score": 0.7, "volatility": 0.06, "liquidity": 0.8},
            "real_estate": {"score": 0.6, "volatility": 0.02, "liquidity": 0.5},
            "stocks": {"score": 0.5, "volatility": 0.08, "liquidity": 0.9},
            "bonds": {"score": 0.4, "volatility": 0.01, "liquidity": 0.8}
        }
        
        return quality_scores.get(asset_type, {"score": 0.5, "volatility": 0.3, "liquidity": 0.7})
    
    async def _get_market_volatility(self) -> Dict[str, Any]:
        """Récupère la volatilité du marché"""
        # Implémentation simplifiée
        import random
        
        return {
            "btc_volatility": random.uniform(0.01, 0.05),
            "eth_volatility": random.uniform(0.02, 0.06),
            "overall_volatility": random.uniform(0.02, 0.04),
            "market_sentiment": random.choice(["bullish", "neutral", "bearish"])
        }
    
    async def _calculate_ai_risk_score(self, data: Dict[str, Any]) -> Tuple[float, float, Dict[str, float]]:
        """Calcule un score de risque utilisant AI"""
        try:
            factors = {}
            
            # Calcule chaque facteur
            reputation = data.get("reputation_score", 0.0)
            factors["reputation"] = 1.0 - reputation  # Inversé: haute réputation = faible risque
            
            credit = data.get("credit_history", {}).get("overall_score", 0.5)
            factors["credit"] = 1.0 - credit  # Inversé: bon crédit = faible risque
            
            transactions = min(data.get("transaction_volume", {}).get("total_usd", 0.0) / 100000, 1.0)
            factors["transactions"] = 1.0 - (transactions * 0.5)  # Plus de transactions = risque modéré
            
            claims = min(data.get("claim_history", {}).get("total_claims", 0) / 5, 1.0)
            factors["claims"] = claims  # Plus de réclamations = risque élevé
            
            network = data.get("network_stability", {}).get("uptime", 0.95)
            factors["network"] = 1.0 - network  # Faible uptime = risque élevé
            
            collateral = data.get("collateral_quality", {}).get("score", 0.5)
            factors["collateral"] = 1.0 - collateral  # Mauvaise qualité = risque élevé
            
            market = data.get("market_volatility", {}).get("overall_volatility", 0.03)
            factors["market"] = market * 10  # Normalisé
            
            # Applique les poids du modèle
            weights = self._ai_model["weights"]
            weighted_sum = (
                factors["reputation"] * weights["reputation_score"] +
                factors["credit"] * weights["credit_history"] +
                factors["transactions"] * weights["transaction_volume"] +
                factors["claims"] * weights["claim_history"] +
                factors["network"] * weights["network_stability"] +
                factors["collateral"] * weights["collateral_quality"] +
                factors["market"] * weights["market_volatility"]
            )
            
            # Normalise le score
            risk_score = min(max(weighted_sum, 0.0), 1.0)
            
            # Calcule la confiance (simplifié)
            confidence = min(
                (reputation + credit + network) / 3,
                1.0
            )
            
            return risk_score, confidence, factors
            
        except Exception as e:
            logger.error(f"Erreur calcul AI risque: {e}")
            return 1.0, 0.0, {"error": 1.0}
    
    def _calculate_basic_risk_score(self, data: Dict[str, Any]) -> Tuple[float, float, Dict[str, float]]:
        """Calcule un score de risque basique sans AI"""
        try:
            factors = {}
            
            # Facteurs simples
            reputation = data.get("reputation_score", 0.0)
            factors["reputation"] = 1.0 - reputation
            
            credit = data.get("credit_history", {}).get("overall_score", 0.5)
            factors["credit"] = 1.0 - credit
            
            claims = min(data.get("claim_history", {}).get("total_claims", 0) / 5, 1.0)
            factors["claims"] = claims
            
            # Score moyen
            risk_score = (factors["reputation"] + factors["credit"] + factors["claims"]) / 3
            confidence = 0.7  # Confiance fixe pour le modèle basique
            
            return risk_score, confidence, factors
            
        except Exception as e:
            logger.error(f"Erreur calcul score risque basique: {e}")
            return 1.0, 0.0, {"error": 1.0}
    
    def _determine_risk_category(self, risk_score: float) -> RiskCategory:
        """Détermine la catégorie de risque basé sur le score"""
        if risk_score <= 0.25:
            return RiskCategory.LOW
        elif risk_score <= 0.5:
            return RiskCategory.MEDIUM
        elif risk_score <= 0.75:
            return RiskCategory.HIGH
        else:
            return RiskCategory.EXTREME
    
    def _generate_recommendations(self, risk_score: float, factors: Dict[str, float],
                                 insurance_type: InsuranceType) -> List[str]:
        """Génère des recommandations basées sur l'évaluation de risque"""
        recommendations = []
        
        # Recommandations basées sur le score global
        if risk_score > 0.8:
            recommendations.append("Risque extrême - Déconseillé d'assurer")
            recommendations.append("Exiger un collatéral de 200% minimum")
        elif risk_score > 0.6:
            recommendations.append("Risque élevé - Prime majorée recommandée")
            recommendations.append("Exiger un collatéral de 150% minimum")
        elif risk_score > 0.4:
            recommendations.append("Risque modéré - Prime standard applicable")
            recommendations.append("Surveillance accrue recommandée")
        else:
            recommendations.append("Risque faible - Conditions favorables")
        
        # Recommandations spécifiques aux facteurs
        if factors.get("reputation", 0.0) > 0.7:
            recommendations.append("Améliorer le score de réputation avant assurance")
        
        if factors.get("credit", 0.0) > 0.6:
            recommendations.append("Historique de crédit à améliorer")
        
        if factors.get("claims", 0.0) > 0.5:
            recommendations.append("Historique de réclamations élevé - surveillance requise")
        
        if factors.get("network", 0.0) > 0.6:
            recommendations.append("Stabilité réseau insuffisante")
        
        # Recommandations spécifiques au type d'assurance
        if insurance_type == InsuranceType.SMART_CONTRACT_FAILURE:
            recommendations.append("Vérifier l'audit des smart contracts")
            recommendations.append("Surveiller les mises à jour du contrat")
        elif insurance_type == InsuranceType.COLLATERAL_LIQUIDATION:
            recommendations.append("Surveillance quotidienne du ratio collatéral")
            recommendations.append("Alertes automatiques recommandées")
        
        return recommendations
    
    async def get_risk_assessment(self, insured_did: str, insurance_type: InsuranceType) -> Optional[RiskAssessment]:
        """Récupère une évaluation de risque existante"""
        cache_key = f"{insured_did}_{insurance_type.value}"
        return self._risk_assessments.get(cache_key)
    
    async def _start_monitoring(self):
        """Démarre la surveillance des évaluations"""
        async def monitor_assessments():
            while True:
                try:
                    # Nettoie les évaluations expirées
                    await self._cleanup_expired_assessments()
                    
                    await asyncio.sleep(3600)  # Vérifie toutes les heures
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance évaluations: {e}")
                    await asyncio.sleep(300)
        
        task = asyncio.create_task(monitor_assessments())
        self._monitoring_tasks.append(task)
    
    async def _cleanup_expired_assessments(self):
        """Nettoie les évaluations de risque expirées"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, assessment in self._risk_assessments.items():
                if current_time >= assessment.timestamp + 86400:  # 24 heures
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._risk_assessments[key]
            
            if expired_keys:
                logger.info(f"{len(expired_keys)} évaluations de risque expirées nettoyées")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage évaluations expirées: {e}")
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._risk_assessments.clear()
        self._risk_factors.clear()