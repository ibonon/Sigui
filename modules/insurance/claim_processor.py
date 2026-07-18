"""
Processeur de réclamations AI-powered pour l'assurance Sigui
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

from .insurance_config import InsuranceConfig, InsuranceType, ClaimStatus
from .insurance_pool import InsuranceClaim, InsurancePoolManager
from .risk_assessment import RiskAssessmentSystem
from ..reputation.reputation_oracle import ReputationOracle


logger = logging.getLogger(__name__)


@dataclass
class ClaimAnalysis:
    """Analyse d'une réclamation"""
    claim_id: str
    fraud_score: float  # 0.0 (légitime) à 1.0 (frauduleux)
    validity_score: float  # 0.0 (invalide) à 1.0 (valide)
    recommended_action: str  # "approve", "reject", "investigate"
    confidence: float
    factors: Dict[str, float]
    timestamp: int


@dataclass
class ClaimEvidence:
    """Preuve pour une réclamation"""
    evidence_id: str
    claim_id: str
    type: str  # "transaction", "log", "screenshot", "contract_state"
    content: Dict[str, Any]
    submitted_by: str
    submitted_at: int
    verified: bool = False
    verification_notes: Optional[str] = None


class ClaimProcessor:
    """Processeur de réclamations utilisant AI pour l'évaluation"""
    
    def __init__(self, config: InsuranceConfig,
                 pool_manager: InsurancePoolManager,
                 risk_assessment: RiskAssessmentSystem,
                 reputation_oracle: ReputationOracle):
        self.config = config
        self.pool_manager = pool_manager
        self.risk_assessment = risk_assessment
        self.reputation_oracle = reputation_oracle
        
        self._claim_analyses: Dict[str, ClaimAnalysis] = {}
        self._evidence_records: Dict[str, ClaimEvidence] = {}
        self._monitoring_tasks: List[asyncio.Task] = []
        
        # Modèle AI simplifié
        self._ai_model = self._initialize_ai_model()
    
    async def initialize(self) -> bool:
        """Initialise le processeur de réclamations"""
        try:
            if not self.config.enabled:
                logger.warning("Système d'assurance désactivé")
                return False
            
            # Charge les modèles AI si activés
            if self.config.ai_claim_assessment_enabled:
                await self._load_ai_models()
                logger.info("Modèles AI chargés pour l'évaluation de réclamations")
            
            # Démarre la surveillance
            await self._start_monitoring()
            
            logger.info("Processeur de réclamations initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation processeur réclamations: {e}")
            return False
    
    def _initialize_ai_model(self) -> Dict:
        """Initialise un modèle AI simplifié pour l'évaluation de réclamations"""
        return {
            "version": "1.0",
            "features": [
                "claimant_reputation",
                "claim_history",
                "evidence_quality",
                "timing_pattern",
                "amount_consistency",
                "collateral_status",
                "market_conditions"
            ],
            "weights": {
                "claimant_reputation": 0.30,
                "claim_history": 0.20,
                "evidence_quality": 0.15,
                "timing_pattern": 0.10,
                "amount_consistency": 0.10,
                "collateral_status": 0.10,
                "market_conditions": 0.05
            }
        }
    
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
    
    async def analyze_claim(self, claim_id: str) -> Optional[ClaimAnalysis]:
        """Analyse une réclamation en utilisant AI"""
        try:
            # Vérifie si une analyse récente existe
            if claim_id in self._claim_analyses:
                existing_analysis = self._claim_analyses[claim_id]
                if time.time() < existing_analysis.timestamp + 3600:  # 1 heure
                    logger.info(f"Analyse de réclamation récupérée depuis le cache: {claim_id}")
                    return existing_analysis
            
            # Récupère la réclamation
            claim = await self.pool_manager.get_claim(claim_id)
            if not claim:
                raise ValueError(f"Réclamation {claim_id} non trouvée")
            
            # Récupère la police associée
            policy = await self.pool_manager.get_policy(claim.policy_id)
            if not policy:
                raise ValueError(f"Police {claim.policy_id} non trouvée")
            
            # Collecte les données
            data = await self._collect_claim_data(claim, policy)
            
            # Analyse avec AI
            if self.config.ai_claim_assessment_enabled:
                fraud_score, validity_score, action, confidence, factors = await self._perform_ai_analysis(data)
            else:
                fraud_score, validity_score, action, confidence, factors = self._perform_basic_analysis(data)
            
            # Crée l'analyse
            analysis = ClaimAnalysis(
                claim_id=claim_id,
                fraud_score=fraud_score,
                validity_score=validity_score,
                recommended_action=action,
                confidence=confidence,
                factors=factors,
                timestamp=int(time.time())
            )
            
            # Met en cache
            self._claim_analyses[claim_id] = analysis
            
            logger.info(f"Réclamation analysée: {claim_id} - fraude={fraud_score:.3f} - validité={validity_score:.3f}")
            return analysis
            
        except Exception as e:
            logger.error(f"Erreur analyse réclamation: {e}")
            return None
    
    async def _collect_claim_data(self, claim: InsuranceClaim, policy: any) -> Dict[str, Any]:
        """Collecte les données pour l'analyse de réclamation"""
        data = {
            "claim_id": claim.claim_id,
            "policy_id": claim.policy_id,
            "insured_did": claim.insured_did,
            "insurance_type": policy.insurance_type.value,
            "amount_requested_usd": claim.amount_requested_usd,
            "coverage_amount_usd": policy.coverage_amount_usd,
            "description": claim.description,
            "evidence_count": len(claim.evidence),
            "timestamp": time.time()
        }
        
        # 1. Réputation du réclamant
        try:
            claimant_reputation = self.reputation_oracle.get_trust_score(claim.insured_did)
            data["claimant_reputation"] = claimant_reputation
        except Exception as e:
            logger.error(f"Erreur récupération réputation réclamant: {e}")
            data["claimant_reputation"] = 0.5
        
        # 2. Historique des réclamations
        try:
            claim_history = await self._get_claimant_history(claim.insured_did)
            data["claim_history"] = claim_history
        except Exception as e:
            logger.error(f"Erreur récupération historique réclamations: {e}")
            data["claim_history"] = {"total_claims": 0, "fraudulent_claims": 0}
        
        # 3. Qualité des preuves
        try:
            evidence_quality = self._assess_evidence_quality(claim.evidence)
            data["evidence_quality"] = evidence_quality
        except Exception as e:
            logger.error(f"Erreur évaluation qualité preuves: {e}")
            data["evidence_quality"] = {"score": 0.5, "verification_level": "medium"}
        
        # 4. Pattern temporel
        try:
            timing_pattern = self._analyze_timing_pattern(claim, policy)
            data["timing_pattern"] = timing_pattern
        except Exception as e:
            logger.error(f"Erreur analyse pattern temporel: {e}")
            data["timing_pattern"] = {"suspicious": False, "days_since_start": 30}
        
        # 5. Consistance du montant
        try:
            amount_consistency = self._check_amount_consistency(claim, policy)
            data["amount_consistency"] = amount_consistency
        except Exception as e:
            logger.error(f"Erreur vérification consistance montant: {e}")
            data["amount_consistency"] = {"reasonable": True, "ratio_to_coverage": 0.5}
        
        # 6. Statut du collatéral
        try:
            collateral_status = await self._get_collateral_status(policy)
            data["collateral_status"] = collateral_status
        except Exception as e:
            logger.error(f"Erreur récupération statut collatéral: {e}")
            data["collateral_status"] = {"healthy": True, "value_ratio": 1.5}
        
        # 7. Conditions du marché
        try:
            market_conditions = await self._get_market_conditions()
            data["market_conditions"] = market_conditions
        except Exception as e:
            logger.error(f"Erreur récupération conditions marché: {e}")
            data["market_conditions"] = {"volatility": 0.03, "trend": "neutral"}
        
        return data
    
    async def _get_claimant_history(self, did: str) -> Dict[str, Any]:
        """Récupère l'historique des réclamations d'un réclamant"""
        # Implémentation simplifiée
        return {
            "total_claims": 3,
            "fraudulent_claims": 0,
            "total_paid_usd": 15000.0,
            "avg_claim_amount_usd": 5000.0,
            "last_claim_days": 90,
            "dispute_rate": 0.1
        }
    
    def _assess_evidence_quality(self, evidence: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Évalue la qualité des preuves"""
        if not evidence:
            return {"score": 0.0, "verification_level": "low", "issues": ["no_evidence"]}
        
        # Évaluation simplifiée
        total_score = 0.0
        issues = []
        
        for item in evidence:
            evidence_type = item.get("type", "unknown")
            
            # Score selon le type de preuve
            type_scores = {
                "transaction": 0.9,
                "contract_state": 0.8,
                "log": 0.7,
                "screenshot": 0.5,
                "statement": 0.4
            }
            
            score = type_scores.get(evidence_type, 0.3)
            total_score += score
            
            # Vérifie les problèmes communs
            if evidence_type == "screenshot" and not item.get("metadata", {}).get("verified", False):
                issues.append("unverified_screenshot")
        
        avg_score = total_score / len(evidence)
        
        # Détermine le niveau de vérification
        if avg_score >= 0.8:
            verification_level = "high"
        elif avg_score >= 0.6:
            verification_level = "medium"
        else:
            verification_level = "low"
        
        return {
            "score": avg_score,
            "verification_level": verification_level,
            "issues": issues[:3]  # Limite à 3 problèmes
        }
    
    def _analyze_timing_pattern(self, claim: InsuranceClaim, policy: any) -> Dict[str, Any]:
        """Analyse le pattern temporel de la réclamation"""
        current_time = time.time()
        policy_start = policy.start_date
        policy_end = policy.end_date
        
        # Jours depuis le début de la police
        days_since_start = (current_time - policy_start) / 86400
        policy_duration_days = (policy_end - policy_start) / 86400
        
        # Vérifie les patterns suspects
        suspicious = False
        reasons = []
        
        # Réclamation très tôt après le début
        if days_since_start < 7:
            suspicious = True
            reasons.append("claim_very_early")
        
        # Réclamation très tard (juste avant expiration)
        if (policy_end - current_time) < 86400:  # Moins d'un jour avant expiration
            suspicious = True
            reasons.append("claim_just_before_expiry")
        
        # Fréquence élevée de réclamations
        if policy.claims_filed > 2:
            suspicious = True
            reasons.append("high_claim_frequency")
        
        return {
            "suspicious": suspicious,
            "days_since_start": days_since_start,
            "policy_duration_days": policy_duration_days,
            "reasons": reasons
        }
    
    def _check_amount_consistency(self, claim: InsuranceClaim, policy: any) -> Dict[str, Any]:
        """Vérifie la consistance du montant réclamé"""
        requested = claim.amount_requested_usd
        coverage = policy.coverage_amount_usd
        
        # Ratio montant réclamé / couverture
        ratio = requested / coverage if coverage > 0 else 0
        
        # Vérifie la raisonnabilité
        reasonable = True
        issues = []
        
        # Montant très élevé par rapport à la couverture
        if ratio > 0.9:
            reasonable = False
            issues.append("amount_near_max_coverage")
        
        # Montant très rond (potentiellement frauduleux)
        if requested % 1000 == 0 and requested >= 10000:
            issues.append("round_amount_large")
        
        # Montant très faible pour le type d'assurance
        min_reasonable = {
            "smart_contract_failure": 1000.0,
            "oracle_failure": 500.0,
            "collateral_liquidation": 5000.0,
            "service_dispute": 1000.0,
            "agent_malfunction": 2000.0,
            "cross_chain_bridge_failure": 10000.0
        }
        
        insurance_type = policy.insurance_type.value
        if requested < min_reasonable.get(insurance_type, 100.0):
            issues.append("amount_unusually_low")
        
        return {
            "reasonable": reasonable,
            "ratio_to_coverage": ratio,
            "issues": issues
        }
    
    async def _get_collateral_status(self, policy: any) -> Dict[str, Any]:
        """Récupère le statut du collatéral"""
        # Implémentation simplifiée
        return {
            "healthy": True,
            "value_ratio": 1.8,  # Valeur collatéral / couverture
            "volatility": 0.04,
            "liquidation_risk": 0.05
        }
    
    async def _get_market_conditions(self) -> Dict[str, Any]:
        """Récupère les conditions du marché"""
        # Implémentation simplifiée
        import random
        
        return {
            "volatility": random.uniform(0.02, 0.05),
            "trend": random.choice(["bullish", "neutral", "bearish"]),
            "liquidity": random.uniform(0.7, 0.95),
            "stress_level": random.uniform(0.1, 0.3)
        }
    
    async def _perform_ai_analysis(self, data: Dict[str, Any]) -> Tuple[float, float, str, float, Dict[str, float]]:
        """Effectue une analyse AI de la réclamation"""
        try:
            factors = {}
            
            # Calcule chaque facteur
            reputation = data.get("claimant_reputation", 0.5)
            factors["reputation"] = 1.0 - reputation  # Faible réputation = risque élevé
            
            claim_history = data.get("claim_history", {}).get("fraudulent_claims", 0)
            factors["history"] = min(claim_history / 3, 1.0)  # Max 3 réclamations frauduleuses
            
            evidence_quality = data.get("evidence_quality", {}).get("score", 0.5)
            factors["evidence"] = 1.0 - evidence_quality  # Mauvaise qualité = risque élevé
            
            timing_suspicious = data.get("timing_pattern", {}).get("suspicious", False)
            factors["timing"] = 1.0 if timing_suspicious else 0.0
            
            amount_consistency = data.get("amount_consistency", {}).get("reasonable", True)
            factors["amount"] = 0.0 if amount_consistency else 1.0
            
            collateral_healthy = data.get("collateral_status", {}).get("healthy", True)
            factors["collateral"] = 0.0 if collateral_healthy else 1.0
            
            market_volatility = data.get("market_conditions", {}).get("volatility", 0.03)
            factors["market"] = market_volatility * 20  # Normalisé
            
            # Applique les poids du modèle
            weights = self._ai_model["weights"]
            fraud_score = (
                factors["reputation"] * weights["claimant_reputation"] +
                factors["history"] * weights["claim_history"] +
                factors["timing"] * weights["timing_pattern"] +
                factors["amount"] * weights["amount_consistency"]
            ) / (
                weights["claimant_reputation"] +
                weights["claim_history"] +
                weights["timing_pattern"] +
                weights["amount_consistency"]
            )
            
            validity_score = (
                factors["evidence"] * weights["evidence_quality"] +
                factors["collateral"] * weights["collateral_status"] +
                factors["market"] * weights["market_conditions"]
            ) / (
                weights["evidence_quality"] +
                weights["collateral_status"] +
                weights["market_conditions"]
            )
            
            # Normalise les scores
            fraud_score = min(max(fraud_score, 0.0), 1.0)
            validity_score = min(max(validity_score, 0.0), 1.0)
            
            # Détermine l'action recommandée
            if fraud_score > 0.7:
                action = "reject"
            elif validity_score < 0.3:
                action = "reject"
            elif fraud_score > 0.4 or validity_score < 0.6:
                action = "investigate"
            else:
                action = "approve"
            
            # Calcule la confiance
            confidence = min(
                (reputation + evidence_quality + (1.0 if collateral_healthy else 0.0)) / 3,
                1.0
            )
            
            return fraud_score, validity_score, action, confidence, factors
            
        except Exception as e:
            logger.error(f"Erreur analyse AI: {e}")
            return 1.0, 0.0, "reject", 0.0, {"error": 1.0}
    
    def _perform_basic_analysis(self, data: Dict[str, Any]) -> Tuple[float, float, str, float, Dict[str, float]]:
        """Effectue une analyse basique sans AI"""
        try:
            factors = {}
            
            # Facteurs simples
            reputation = data.get("claimant_reputation", 0.5)
            factors["reputation"] = 1.0 - reputation
            
            evidence_quality = data.get("evidence_quality", {}).get("score", 0.5)
            factors["evidence"] = 1.0 - evidence_quality
            
            timing_suspicious = data.get("timing_pattern", {}).get("suspicious", False)
            factors["timing"] = 1.0 if timing_suspicious else 0.0
            
            # Scores basiques
            fraud_score = (factors["reputation"] + factors["timing"]) / 2
            validity_score = 1.0 - factors["evidence"]
            
            # Détermine l'action
            if fraud_score > 0.6:
                action = "reject"
            elif validity_score < 0.4:
                action = "reject"
            else:
                action = "approve"
            
            confidence = 0.7
            
            return fraud_score, validity_score, action, confidence, factors
            
        except Exception as e:
            logger.error(f"Erreur analyse basique: {e}")
            return 1.0, 0.0, "reject", 0.0, {"error": 1.0}
    
    async def submit_claim_decision(self, claim_id: str, reviewer_did: str,
                                   analysis: ClaimAnalysis) -> bool:
        """Soumet une décision basée sur l'analyse"""
        try:
            # Récupère la réclamation
            claim = await self.pool_manager.get_claim(claim_id)
            if not claim:
                raise ValueError(f"Réclamation {claim_id} non trouvée")
            
            # Prend une décision basée sur l'analyse
            if analysis.recommended_action == "approve":
                # Approuve la réclamation
                approved_amount = claim.amount_requested_usd * analysis.validity_score
                success = await self.pool_manager.process_claim(
                    claim_id, reviewer_did, approved_amount, None
                )
                
                if success:
                    logger.info(f"Réclamation approuvée: {claim_id} - {approved_amount} USD")
                    
                    # Met à jour la réputation du réviseur
                    await self.reputation_oracle.update_trust_score(
                        target_did=reviewer_did,
                        increment=0.05,
                        reason="claim_approved",
                        metadata={"claim_id": claim_id, "analysis_confidence": analysis.confidence}
                    )
                
                return success
                
            elif analysis.recommended_action == "reject":
                # Rejette la réclamation
                rejection_reason = f"Analyse AI: fraude={analysis.fraud_score:.3f}, validité={analysis.validity_score:.3f}"
                success = await self.pool_manager.process_claim(
                    claim_id, reviewer_did, None, rejection_reason
                )
                
                if success:
                    logger.info(f"Réclamation rejetée: {claim_id} - {rejection_reason}")
                    
                    # Met à jour la réputation du réclamant (pénalité)
                    await self.reputation_oracle.update_trust_score(
                        target_did=claim.insured_did,
                        increment=-0.1,
                        reason="claim_rejected",
                        metadata={"claim_id": claim_id, "fraud_score": analysis.fraud_score}
                    )
                
                return success
                
            else:  # "investigate"
                # Marque pour investigation manuelle
                logger.info(f"Réclamation nécessite investigation: {claim_id}")
                
                # Met à jour la réputation du réviseur pour avoir identifié un cas complexe
                await self.reputation_oracle.update_trust_score(
                    target_did=reviewer_did,
                    increment=0.02,
                    reason="claim_flagged_for_investigation",
                    metadata={"claim_id": claim_id, "analysis_confidence": analysis.confidence}
                )
                
                return True
                
        except Exception as e:
            logger.error(f"Erreur soumission décision: {e}")
            return False
    
    async def get_claim_analysis(self, claim_id: str) -> Optional[ClaimAnalysis]:
        """Récupère l'analyse d'une réclamation"""
        return self._claim_analyses.get(claim_id)
    
    async def _start_monitoring(self):
        """Démarre la surveillance des analyses"""
        async def monitor_analyses():
            while True:
                try:
                    # Nettoie les analyses expirées
                    await self._cleanup_expired_analyses()
                    
                    await asyncio.sleep(1800)  # Vérifie toutes les 30 minutes
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance analyses: {e}")
                    await asyncio.sleep(300)
        
        task = asyncio.create_task(monitor_analyses())
        self._monitoring_tasks.append(task)
    
    async def _cleanup_expired_analyses(self):
        """Nettoie les analyses de réclamation expirées"""
        try:
            current_time = time.time()
            expired_keys = []
            
            for key, analysis in self._claim_analyses.items():
                if current_time >= analysis.timestamp + 3600:  # 1 heure
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._claim_analyses[key]
            
            if expired_keys:
                logger.info(f"{len(expired_keys)} analyses de réclamation expirées nettoyées")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage analyses expirées: {e}")
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._claim_analyses.clear()
        self._evidence_records.clear()