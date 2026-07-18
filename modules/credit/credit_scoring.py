"""
Système de scoring de crédit AI-powered pour Sigui
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np
import logging

from .credit_config import CreditConfig, CreditRiskLevel, CollateralType
from ..reputation.reputation_oracle import ReputationOracle
from ..blockchain.bitcoin.bitcoin_adapter import BitcoinAdapter
from ..blockchain.cardano.cardano_adapter import CardanoAdapter


logger = logging.getLogger(__name__)


@dataclass
class CreditScore:
    """Score de crédit complet"""
    overall_score: float  # 0.0 à 1.0
    risk_level: CreditRiskLevel
    confidence: float  # Confiance du modèle AI
    factors: Dict[str, float]  # Facteurs contributifs
    timestamp: int
    expires_at: int


@dataclass
class CreditApplication:
    """Demande de crédit"""
    application_id: str
    applicant_did: str
    requested_amount_usd: float
    loan_term: str
    collateral_assets: List[Dict[str, Any]]
    purpose: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    submitted_at: int = 0
    status: str = "pending"


class CreditScoringSystem:
    """Système de scoring de crédit utilisant AI et données cross-chain"""
    
    def __init__(self, config: CreditConfig, reputation_oracle: ReputationOracle,
                 bitcoin_adapter: Optional[BitcoinAdapter] = None,
                 cardano_adapter: Optional[CardanoAdapter] = None):
        self.config = config
        self.reputation_oracle = reputation_oracle
        self.bitcoin_adapter = bitcoin_adapter
        self.cardano_adapter = cardano_adapter
        
        self._credit_scores: Dict[str, CreditScore] = {}
        self._applications: Dict[str, CreditApplication] = {}
        self._monitoring_tasks: List[asyncio.Task] = []
        
        # Modèle AI simplifié (dans une vraie implémentation, on utiliserait scikit-learn ou TensorFlow)
        self._ai_model = self._initialize_ai_model()
    
    async def initialize(self) -> bool:
        """Initialise le système de scoring"""
        try:
            if not self.config.enabled:
                logger.warning("Système de crédit désactivé")
                return False
            
            # Charge les modèles AI si activés
            if self.config.ai_scoring_enabled:
                await self._load_ai_models()
                logger.info("Modèles AI chargés pour le scoring de crédit")
            
            # Démarre la surveillance
            await self._start_monitoring()
            
            logger.info("Système de scoring de crédit initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation scoring crédit: {e}")
            return False
    
    def _initialize_ai_model(self) -> Dict:
        """Initialise un modèle AI simplifié"""
        # Dans une vraie implémentation, on chargerait un modèle entraîné
        return {
            "version": "1.0",
            "features": [
                "reputation_score",
                "transaction_history",
                "collateral_value",
                "payment_history",
                "network_activity"
            ],
            "weights": {
                "reputation_score": 0.35,
                "transaction_history": 0.25,
                "collateral_value": 0.20,
                "payment_history": 0.15,
                "network_activity": 0.05
            }
        }
    
    async def _load_ai_models(self):
        """Charge les modèles AI depuis le chemin configuré"""
        try:
            if self.config.ai_model_path:
                # Implémentation simplifiée
                logger.info(f"Chargement modèle AI depuis: {self.config.ai_model_path}")
            else:
                logger.info("Utilisation du modèle AI par défaut")
                
        except Exception as e:
            logger.error(f"Erreur chargement modèle AI: {e}")
    
    async def calculate_credit_score(self, applicant_did: str,
                                    requested_amount_usd: Optional[float] = None,
                                    collateral_assets: Optional[List[Dict]] = None) -> CreditScore:
        """Calcule un score de crédit pour un applicant"""
        try:
            # Vérifie si un score récent existe
            if applicant_did in self._credit_scores:
                existing_score = self._credit_scores[applicant_did]
                if time.time() < existing_score.expires_at:
                    logger.info(f"Score de crédit récupéré depuis le cache: {applicant_did}")
                    return existing_score
            
            # Collecte les données
            data = await self._collect_scoring_data(applicant_did, requested_amount_usd, collateral_assets)
            
            # Calcule le score
            if self.config.ai_scoring_enabled:
                score, confidence, factors = await self._calculate_ai_score(data)
            else:
                score, confidence, factors = self._calculate_basic_score(data)
            
            # Détermine le niveau de risque
            risk_level = self._determine_risk_level(score)
            
            # Crée l'objet score
            credit_score = CreditScore(
                overall_score=score,
                risk_level=risk_level,
                confidence=confidence,
                factors=factors,
                timestamp=int(time.time()),
                expires_at=int(time.time()) + 86400  # Expire dans 24 heures
            )
            
            # Met en cache
            self._credit_scores[applicant_did] = credit_score
            
            logger.info(f"Score de crédit calculé pour {applicant_did}: {score} ({risk_level.value})")
            return credit_score
            
        except Exception as e:
            logger.error(f"Erreur calcul score crédit: {e}")
            # Retourne un score par défaut en cas d'erreur
            return CreditScore(
                overall_score=0.0,
                risk_level=CreditRiskLevel.C,
                confidence=0.0,
                factors={"error": 1.0},
                timestamp=int(time.time()),
                expires_at=int(time.time()) + 3600
            )
    
    async def _collect_scoring_data(self, applicant_did: str,
                                   requested_amount_usd: Optional[float],
                                   collateral_assets: Optional[List[Dict]]) -> Dict[str, Any]:
        """Collecte les données pour le scoring"""
        data = {
            "applicant_did": applicant_did,
            "timestamp": time.time()
        }
        
        # 1. Score de réputation
        try:
            reputation_score = self.reputation_oracle.get_trust_score(applicant_did)
            data["reputation_score"] = reputation_score
        except Exception as e:
            logger.error(f"Erreur récupération réputation: {e}")
            data["reputation_score"] = 0.0
        
        # 2. Historique des transactions
        try:
            transaction_history = await self._get_transaction_history(applicant_did)
            data["transaction_history"] = transaction_history
        except Exception as e:
            logger.error(f"Erreur récupération historique transactions: {e}")
            data["transaction_history"] = {"total_count": 0, "success_rate": 0.0}
        
        # 3. Valeur du collatéral
        try:
            collateral_value = await self._calculate_collateral_value(applicant_did, collateral_assets)
            data["collateral_value"] = collateral_value
        except Exception as e:
            logger.error(f"Erreur calcul valeur collatéral: {e}")
            data["collateral_value"] = {"total_usd": 0.0, "assets": []}
        
        # 4. Historique des paiements
        try:
            payment_history = await self._get_payment_history(applicant_did)
            data["payment_history"] = payment_history
        except Exception as e:
            logger.error(f"Erreur récupération historique paiements: {e}")
            data["payment_history"] = {"on_time_rate": 0.0, "default_count": 0}
        
        # 5. Activité réseau
        try:
            network_activity = await self._get_network_activity(applicant_did)
            data["network_activity"] = network_activity
        except Exception as e:
            logger.error(f"Erreur récupération activité réseau: {e}")
            data["network_activity"] = {"connections": 0, "activity_score": 0.0}
        
        # 6. Montant demandé (si applicable)
        if requested_amount_usd:
            data["requested_amount_usd"] = requested_amount_usd
        
        return data
    
    async def _get_transaction_history(self, did: str) -> Dict[str, Any]:
        """Récupère l'historique des transactions"""
        # Implémentation simplifiée
        return {
            "total_count": 100,
            "success_rate": 0.95,
            "total_volume_usd": 50000.0,
            "avg_transaction_usd": 500.0,
            "last_transaction_days": 2
        }
    
    async def _calculate_collateral_value(self, did: str, specific_assets: Optional[List[Dict]]) -> Dict[str, Any]:
        """Calcule la valeur du collatéral"""
        assets = []
        total_value_usd = 0.0
        
        # Si des assets spécifiques sont fournis, les utilise
        if specific_assets:
            for asset in specific_assets:
                asset_type = asset.get("type")
                amount = asset.get("amount", 0)
                
                # Prix factice selon le type
                price_usd = {
                    "bitcoin": 60000.0,
                    "ethereum": 3000.0,
                    "cardano": 0.5,
                    "polkadot": 7.0
                }.get(asset_type, 0.0)
                
                value_usd = amount * price_usd
                total_value_usd += value_usd
                
                assets.append({
                    "type": asset_type,
                    "amount": amount,
                    "price_usd": price_usd,
                    "value_usd": value_usd
                })
        else:
            # Sinon, essaie de récupérer depuis les adaptateurs blockchain
            if self.bitcoin_adapter:
                try:
                    btc_balance, _ = await self.bitcoin_adapter.get_balance()
                    btc_value_usd = (btc_balance / 100000000) * 60000.0  # Conversion satoshis -> BTC -> USD
                    total_value_usd += btc_value_usd
                    
                    assets.append({
                        "type": "bitcoin",
                        "amount": btc_balance,
                        "price_usd": 60000.0,
                        "value_usd": btc_value_usd
                    })
                except Exception as e:
                    logger.error(f"Erreur récupération solde Bitcoin: {e}")
            
            if self.cardano_adapter:
                try:
                    ada_balance, ada_assets = await self.cardano_adapter.get_balance()
                    ada_value_usd = (ada_balance / 1000000) * 0.5  # Conversion lovelace -> ADA -> USD
                    total_value_usd += ada_value_usd
                    
                    assets.append({
                        "type": "cardano",
                        "amount": ada_balance,
                        "price_usd": 0.5,
                        "value_usd": ada_value_usd
                    })
                except Exception as e:
                    logger.error(f"Erreur récupération solde Cardano: {e}")
        
        return {
            "total_usd": total_value_usd,
            "assets": assets
        }
    
    async def _get_payment_history(self, did: str) -> Dict[str, Any]:
        """Récupère l'historique des paiements"""
        # Implémentation simplifiée
        return {
            "on_time_rate": 0.98,
            "default_count": 0,
            "late_payments": 2,
            "total_loans": 5,
            "avg_loan_amount_usd": 10000.0
        }
    
    async def _get_network_activity(self, did: str) -> Dict[str, Any]:
        """Récupère l'activité réseau"""
        # Implémentation simplifiée
        return {
            "connections": 25,
            "activity_score": 0.85,
            "last_active_days": 1,
            "services_provided": 10,
            "services_consumed": 15
        }
    
    async def _calculate_ai_score(self, data: Dict[str, Any]) -> Tuple[float, float, Dict[str, float]]:
        """Calcule un score utilisant AI"""
        try:
            factors = {}
            
            # Calcule chaque facteur
            reputation_factor = data.get("reputation_score", 0.0)
            factors["reputation"] = reputation_factor
            
            transaction_factor = data.get("transaction_history", {}).get("success_rate", 0.0)
            factors["transactions"] = transaction_factor
            
            collateral_factor = min(data.get("collateral_value", {}).get("total_usd", 0.0) / 100000, 1.0)
            factors["collateral"] = collateral_factor
            
            payment_factor = data.get("payment_history", {}).get("on_time_rate", 0.0)
            factors["payments"] = payment_factor
            
            network_factor = data.get("network_activity", {}).get("activity_score", 0.0)
            factors["network"] = network_factor
            
            # Applique les poids du modèle
            weights = self._ai_model["weights"]
            weighted_sum = (
                reputation_factor * weights["reputation_score"] +
                transaction_factor * weights["transaction_history"] +
                collateral_factor * weights["collateral_value"] +
                payment_factor * weights["payment_history"] +
                network_factor * weights["network_activity"]
            )
            
            # Normalise le score
            score = min(max(weighted_sum, 0.0), 1.0)
            
            # Calcule la confiance (simplifié)
            confidence = min(
                (reputation_factor + transaction_factor + payment_factor) / 3,
                1.0
            )
            
            return score, confidence, factors
            
        except Exception as e:
            logger.error(f"Erreur calcul AI score: {e}")
            return 0.0, 0.0, {"error": 1.0}
    
    def _calculate_basic_score(self, data: Dict[str, Any]) -> Tuple[float, float, Dict[str, float]]:
        """Calcule un score basique sans AI"""
        try:
            factors = {}
            
            # Facteurs simples
            reputation = data.get("reputation_score", 0.0)
            factors["reputation"] = reputation
            
            transactions = data.get("transaction_history", {}).get("success_rate", 0.0)
            factors["transactions"] = transactions
            
            payments = data.get("payment_history", {}).get("on_time_rate", 0.0)
            factors["payments"] = payments
            
            # Score moyen
            score = (reputation + transactions + payments) / 3
            confidence = 0.7  # Confiance fixe pour le modèle basique
            
            return score, confidence, factors
            
        except Exception as e:
            logger.error(f"Erreur calcul score basique: {e}")
            return 0.0, 0.0, {"error": 1.0}
    
    def _determine_risk_level(self, score: float) -> CreditRiskLevel:
        """Détermine le niveau de risque basé sur le score"""
        if score >= 0.9:
            return CreditRiskLevel.AAA
        elif score >= 0.8:
            return CreditRiskLevel.AA
        elif score >= 0.7:
            return CreditRiskLevel.A
        elif score >= 0.6:
            return CreditRiskLevel.BBB
        elif score >= 0.5:
            return CreditRiskLevel.BB
        elif score >= 0.4:
            return CreditRiskLevel.B
        else:
            return CreditRiskLevel.C
    
    async def submit_credit_application(self, application: CreditApplication) -> Optional[CreditApplication]:
        """Soumet une demande de crédit"""
        try:
            # Valide la demande
            if not await self._validate_application(application):
                raise ValueError("Demande de crédit invalide")
            
            # Calcule le score de crédit
            credit_score = await self.calculate_credit_score(
                application.applicant_did,
                application.requested_amount_usd,
                application.collateral_assets
            )
            
            # Vérifie l'éligibilité
            if credit_score.overall_score < self.config.min_credit_score:
                application.status = "rejected"
                application.metadata = application.metadata or {}
                application.metadata["rejection_reason"] = "credit_score_too_low"
                application.metadata["credit_score"] = credit_score.overall_score
            else:
                application.status = "approved"
                application.metadata = application.metadata or {}
                application.metadata["credit_score"] = credit_score.overall_score
                application.metadata["risk_level"] = credit_score.risk_level.value
            
            application.submitted_at = int(time.time())
            self._applications[application.application_id] = application
            
            logger.info(f"Demande de crédit soumise: {application.application_id} - {application.status}")
            return application
            
        except Exception as e:
            logger.error(f"Erreur soumission demande crédit: {e}")
            return None
    
    async def _validate_application(self, application: CreditApplication) -> bool:
        """Valide une demande de crédit"""
        try:
            # Vérifie le montant
            if application.requested_amount_usd < self.config.min_loan_amount_usd:
                logger.warning(f"Montant trop faible: {application.requested_amount_usd}")
                return False
            
            if application.requested_amount_usd > self.config.max_loan_amount_usd:
                logger.warning(f"Montant trop élevé: {application.requested_amount_usd}")
                return False
            
            # Vérifie le terme
            if application.loan_term not in [t.value for t in self.config.available_loan_terms]:
                logger.warning(f"Terme non supporté: {application.loan_term}")
                return False
            
            # Vérifie le collatéral
            if not application.collateral_assets:
                logger.warning("Aucun collatéral fourni")
                return False
            
            # Calcule la valeur du collatéral
            collateral_value = await self._calculate_collateral_value(
                application.applicant_did,
                application.collateral_assets
            )
            
            # Vérifie le ratio LTV
            ltv_ratio = application.requested_amount_usd / collateral_value["total_usd"]
            if ltv_ratio > self.config.max_loan_to_value_ratio:
                logger.warning(f"Ratio LTV trop élevé: {ltv_ratio}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur validation demande: {e}")
            return False
    
    async def get_application_status(self, application_id: str) -> Optional[CreditApplication]:
        """Récupère le statut d'une demande"""
        return self._applications.get(application_id)
    
    async def _start_monitoring(self):
        """Démarre la surveillance des scores"""
        async def monitor_scores():
            while True:
                try:
                    # Nettoie les scores expirés
                    await self._cleanup_expired_scores()
                    
                    await asyncio.sleep(3600)  # Vérifie toutes les heures
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance scores: {e}")
                    await asyncio.sleep(300)
        
        task = asyncio.create_task(monitor_scores())
        self._monitoring_tasks.append(task)
    
    async def _cleanup_expired_scores(self):
        """Nettoie les scores de crédit expirés"""
        try:
            current_time = time.time()
            expired_dids = []
            
            for did, score in self._credit_scores.items():
                if current_time >= score.expires_at:
                    expired_dids.append(did)
            
            for did in expired_dids:
                del self._credit_scores[did]
            
            if expired_dids:
                logger.info(f"{len(expired_dids)} scores de crédit expirés nettoyés")
                
        except Exception as e:
            logger.error(f"Erreur nettoyage scores expirés: {e}")
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._credit_scores.clear()
        self._applications.clear()