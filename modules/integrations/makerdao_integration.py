"""
MakerDAO Integration Module
Surveillance des vaults DAI, monitoring des ratios de collatéral, détection des risques de liquidation
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from web3 import Web3
from web3.contract import Contract
import numpy as np

from config import settings

logger = logging.getLogger(__name__)


class CollateralType(Enum):
    ETH_A = "ETH-A"
    ETH_B = "ETH-B"
    ETH_C = "ETH-C"
    WBTC_A = "WBTC-A"
    WBTC_B = "WBTC-B"
    WBTC_C = "WBTC-C"
    USDC_A = "USDC-A"
    USDC_B = "USDC-B"


class MakerAlertType(Enum):
    LIQUIDATION_IMMINENT = "liquidation_imminent"
    COLLATERAL_RATIO_LOW = "collateral_ratio_low"
    DEBT_CEILING_REACHED = "debt_ceiling_reached"
    ORACLE_MANIPULATION = "oracle_manipulation"
    SYSTEMIC_RISK = "systemic_risk"


@dataclass
class MakerAlert:
    vault_id: Optional[int]
    alert_type: MakerAlertType
    severity: str
    description: str
    timestamp: datetime
    owner_address: Optional[str] = None
    collateral_amount: Optional[float] = None
    debt_amount: Optional[float] = None
    collateral_ratio: Optional[float] = None
    liquidation_price: Optional[float] = None
    transaction_hash: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class VaultMetrics:
    vault_id: int
    owner: str
    collateral_type: CollateralType
    collateral_amount: float
    debt_amount: float
    collateral_ratio: float
    liquidation_price: float
    liquidation_penalty: float
    stability_fee: float
    timestamp: datetime


@dataclass
class SystemMetrics:
    total_collateral_usd: float
    total_debt_dai: float
    system_collateral_ratio: float
    debt_ceiling: float
    debt_ceiling_used: float
    stability_fee: float
    dai_savings_rate: float
    timestamp: datetime


class MakerDAOIntegration:
    """Intégration complète avec MakerDAO Protocol"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.ETHEREUM_RPC_URL
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Adresses des contrats MakerDAO
        self.vat_address = "0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B"
        self.spot_address = "0x65C79fcB50Ca1594B025960e539eD7A9a6D434A3"
        self.jug_address = "0x19c0976f590D67707E62397C87829d896Dc0f1F1"
        
        # Types de collatéral
        self.collateral_types = {
            CollateralType.ETH_A: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            CollateralType.WBTC_A: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
            CollateralType.USDC_A: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        }
        
        # Seuils d'alerte
        self.alert_thresholds = {
            "collateral_ratio_warning": 1.5,  # 150%
            "collateral_ratio_critical": 1.3,  # 130%
            "liquidation_buffer": 0.05,  # 5% de buffer
            "debt_ceiling_warning": 0.8,  # 80% utilisé
            "system_collateral_ratio_min": 2.0,  # 200% minimum
        }
        
        # Historique
        self.vaults_history: Dict[int, List[VaultMetrics]] = {}
        self.system_history: List[SystemMetrics] = []
        self.alerts_history: List[MakerAlert] = []
        
        # Initialisation des contrats
        self._initialize_contracts()
    
    def _initialize_contracts(self) -> None:
        """Initialise les contrats MakerDAO"""
        # ABIs simplifiés
        self.vat_abi = [
            {
                "constant": True,
                "inputs": [{"name": "", "type": "bytes32"}],
                "name": "ilks",
                "outputs": [
                    {"name": "Art", "type": "uint256"},
                    {"name": "rate", "type": "uint256"},
                    {"name": "spot", "type": "uint256"},
                    {"name": "line", "type": "uint256"},
                    {"name": "dust", "type": "uint256"}
                ],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "", "type": "bytes32"}, {"name": "", "type": "address"}],
                "name": "urns",
                "outputs": [
                    {"name": "ink", "type": "uint256"},
                    {"name": "art", "type": "uint256"}
                ],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "debt",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        self.spot_abi = [
            {
                "constant": True,
                "inputs": [{"name": "", "type": "bytes32"}],
                "name": "ilks",
                "outputs": [
                    {"name": "pip", "type": "address"},
                    {"name": "mat", "type": "uint256"}
                ],
                "type": "function"
            }
        ]
        
        # Initialiser les contrats
        self.vat = self.web3.eth.contract(
            address=self.vat_address,
            abi=self.vat_abi
        )
        
        self.spot = self.web3.eth.contract(
            address=self.spot_address,
            abi=self.spot_abi
        )
    
    async def monitor_vaults(self, callback: Callable[[MakerAlert], None]) -> None:
        """Surveillance continue des vaults MakerDAO"""
        logger.info("Démarrage de la surveillance MakerDAO")
        
        while True:
            try:
                # Surveiller les métriques système
                system_metrics = await self._collect_system_metrics()
                self.system_history.append(system_metrics)
                
                # Analyser les risques système
                system_alerts = await self._analyze_system_metrics(system_metrics)
                for alert in system_alerts:
                    await callback(alert)
                    self.alerts_history.append(alert)
                
                # Surveiller les vaults à risque
                await self._monitor_risky_vaults(callback)
                
                # Attendre avant la prochaine itération
                await asyncio.sleep(120)  # Toutes les 2 minutes
                
            except Exception as e:
                logger.error(f"Erreur dans la surveillance MakerDAO: {e}")
                await asyncio.sleep(300)  # Attendre 5 minutes en cas d'erreur
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collecte les métriques système de MakerDAO"""
        try:
            # Obtenir la dette totale
            total_debt = self.vat.functions.debt().call() / 1e45  # Convertir en DAI
            
            # Calculer le collatéral total (simplifié)
            total_collateral_usd = 0.0
            
            for collateral_type, token_address in self.collateral_types.items():
                ilk = self._collateral_type_to_ilk(collateral_type)
                ilk_data = self.vat.functions.ilks(ilk).call()
                
                # Art (dette) et rate (taux d'accumulation)
                art = ilk_data[0] / 1e18
                rate = ilk_data[1] / 1e27
                
                # Calculer la dette pour ce collatéral
                debt_dai = art * rate if rate > 0 else 0
                
                # Estimer la valeur du collatéral (simplifié)
                # Dans une implémentation réelle, on utiliserait les prix des oracles
                if collateral_type == CollateralType.ETH_A:
                    eth_price = 2000.0
                    # Estimation: 2x la dette pour avoir un ratio de 200%
                    collateral_value = debt_dai * 2 * eth_price
                elif collateral_type == CollateralType.WBTC_A:
                    btc_price = 60000.0
                    collateral_value = debt_dai * 2 * btc_price
                else:
                    collateral_value = debt_dai * 2  # Pour les stablecoins
                
                total_collateral_usd += collateral_value
            
            # Calculer le ratio de collatéral système
            system_collateral_ratio = (total_collateral_usd / (total_debt * 1.0)) * 100 if total_debt > 0 else 0
            
            # Debt ceiling (simplifié)
            debt_ceiling = 1000000000  # 1B DAI
            debt_ceiling_used = (total_debt / debt_ceiling) * 100
            
            # Taux (simplifié)
            stability_fee = 0.05  # 5% APY
            dai_savings_rate = 0.01  # 1% APY
            
            return SystemMetrics(
                total_collateral_usd=total_collateral_usd,
                total_debt_dai=total_debt,
                system_collateral_ratio=system_collateral_ratio,
                debt_ceiling=debt_ceiling,
                debt_ceiling_used=debt_ceiling_used,
                stability_fee=stability_fee,
                dai_savings_rate=dai_savings_rate,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques système: {e}")
            
            return SystemMetrics(
                total_collateral_usd=0.0,
                total_debt_dai=0.0,
                system_collateral_ratio=0.0,
                debt_ceiling=0.0,
                debt_ceiling_used=0.0,
                stability_fee=0.0,
                dai_savings_rate=0.0,
                timestamp=datetime.now()
            )
    
    def _collateral_type_to_ilk(self, collateral_type: CollateralType) -> bytes:
        """Convertit un type de collatéral en ilk (bytes32)"""
        ilk_map = {
            CollateralType.ETH_A: b'ETH-A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            CollateralType.WBTC_A: b'WBTC-A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
            CollateralType.USDC_A: b'USDC-A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        }
        
        return ilk_map.get(collateral_type, b'\x00' * 32)
    
    async def _analyze_system_metrics(self, metrics: SystemMetrics) -> List[MakerAlert]:
        """Analyse les métriques système pour détecter des risques"""
        alerts = []
        
        # Vérifier le ratio de collatéral système
        if metrics.system_collateral_ratio < self.alert_thresholds["system_collateral_ratio_min"]:
            alerts.append(MakerAlert(
                vault_id=None,
                alert_type=MakerAlertType.SYSTEMIC_RISK,
                severity="critical",
                description=f"Ratio de collatéral système trop bas: {metrics.system_collateral_ratio:.1f}%",
                timestamp=datetime.now(),
                evidence={
                    "system_collateral_ratio": metrics.system_collateral_ratio,
                    "minimum_required": self.alert_thresholds["system_collateral_ratio_min"],
                }
            ))
        
        # Vérifier le debt ceiling
        if metrics.debt_ceiling_used > self.alert_thresholds["debt_ceiling_warning"] * 100:
            alerts.append(MakerAlert(
                vault_id=None,
                alert_type=MakerAlertType.DEBT_CEILING_REACHED,
                severity="high",
                description=f"Debt ceiling presque atteint: {metrics.debt_ceiling_used:.1f}%",
                timestamp=datetime.now(),
                evidence={
                    "debt_ceiling_used": metrics.debt_ceiling_used,
                    "warning_threshold": self.alert_thresholds["debt_ceiling_warning"] * 100,
                }
            ))
        
        return alerts
    
    async def _monitor_risky_vaults(self, callback: Callable[[MakerAlert], None]) -> None:
        """Surveille les vaults à risque de liquidation"""
        # Dans une implémentation réelle, on analyserait tous les vaults
        # Pour l'exemple, on simule la détection de vaults à risque
        
        # Vaults à surveiller (exemple)
        risky_vaults = [
            {"id": 12345, "owner": "0x742d35Cc6634C0532925a3b844Bc9e0F2b5B3a5A"},
            {"id": 67890, "owner": "0x53D284357EC70Ce289D6D64134DfAc8E511c8a3D"},
        ]
        
        for vault in risky_vaults:
            metrics = await self._get_vault_metrics(vault["id"], vault["owner"])
            
            if metrics and metrics.collateral_ratio < self.alert_thresholds["collateral_ratio_critical"] * 100:
                alert = MakerAlert(
                    vault_id=vault["id"],
                    alert_type=MakerAlertType.LIQUIDATION_IMMINENT,
                    severity="critical",
                    description=f"Vault {vault['id']} en risque de liquidation immédiate",
                    timestamp=datetime.now(),
                    owner_address=vault["owner"],
                    collateral_amount=metrics.collateral_amount,
                    debt_amount=metrics.debt_amount,
                    collateral_ratio=metrics.collateral_ratio,
                    liquidation_price=metrics.liquidation_price,
                    evidence={
                        "liquidation_threshold": self.alert_thresholds["collateral_ratio_critical"] * 100,
                        "current_ratio": metrics.collateral_ratio,
                    }
                )
                
                await callback(alert)
                self.alerts_history.append(alert)
            
            elif metrics and metrics.collateral_ratio < self.alert_thresholds["collateral_ratio_warning"] * 100:
                alert = MakerAlert(
                    vault_id=vault["id"],
                    alert_type=MakerAlertType.COLLATERAL_RATIO_LOW,
                    severity="warning",
                    description=f"Vault {vault['id']} avec ratio de collatéral bas",
                    timestamp=datetime.now(),
                    owner_address=vault["owner"],
                    collateral_amount=metrics.collateral_amount,
                    debt_amount=metrics.debt_amount,
                    collateral_ratio=metrics.collateral_ratio,
                    evidence={
                        "warning_threshold": self.alert_thresholds["collateral_ratio_warning"] * 100,
                        "current_ratio": metrics.collateral_ratio,
                    }
                )
                
                await callback(alert)
                self.alerts_history.append(alert)
    
    async def _get_vault_metrics(self, vault_id: int, owner_address: str) -> Optional[VaultMetrics]:
        """Obtient les métriques d'un vault spécifique"""
        try:
            # Pour l'exemple, on simule des métriques
            # Dans une implémentation réelle, on interrogerait les contrats
            
            collateral_type = np.random.choice(list(self.collateral_types.keys()))
            collateral_amount = np.random.uniform(10, 100)
            debt_amount = np.random.uniform(5000, 50000)
            
            # Calculer le ratio de collatéral
            # Prix estimés
            if collateral_type == CollateralType.ETH_A:
                collateral_value = collateral_amount * 2000.0
            elif collateral_type == CollateralType.WBTC_A:
                collateral_value = collateral_amount * 60000.0
            else:
                collateral_value = collateral_amount * 1.0
            
            collateral_ratio = (collateral_value / debt_amount) * 100 if debt_amount > 0 else 0
            
            # Prix de liquidation
            liquidation_threshold = 1.3  # 130%
            liquidation_price = (debt_amount * liquidation_threshold) / collateral_amount if collateral_amount > 0 else 0
            
            return VaultMetrics(
                vault_id=vault_id,
                owner=owner_address,
                collateral_type=collateral_type,
                collateral_amount=collateral_amount,
                debt_amount=debt_amount,
                collateral_ratio=collateral_ratio,
                liquidation_price=liquidation_price,
                liquidation_penalty=0.13,  # 13%
                stability_fee=0.05,  # 5%
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'obtention des métriques du vault {vault_id}: {e}")
            return None
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Retourne la santé du système MakerDAO"""
        metrics = await self._collect_system_metrics()
        
        # Calculer le score de santé
        health_score = self._calculate_system_health_score(metrics)
        
        # Identifier les risques
        risks = []
        if metrics.system_collateral_ratio < 200.0:
            risks.append("Ratio de collatéral système bas")
        if metrics.debt_ceiling_used > 80.0:
            risks.append("Debt ceiling presque atteint")
        if metrics.total_debt_dai > 800000000:  # 800M DAI
            risks.append("Dette totale élevée")
        
        return {
            "health_score": health_score,
            "status": "healthy" if health_score > 70 else "warning" if health_score > 40 else "critical",
            "metrics": {
                "total_collateral_usd": metrics.total_collateral_usd,
                "total_debt_dai": metrics.total_debt_dai,
                "system_collateral_ratio": metrics.system_collateral_ratio,
                "debt_ceiling_used": metrics.debt_ceiling_used,
                "stability_fee": metrics.stability_fee,
                "dai_savings_rate": metrics.dai_savings_rate,
            },
            "risks": risks,
            "timestamp": metrics.timestamp.isoformat(),
        }
    
    def _calculate_system_health_score(self, metrics: SystemMetrics) -> float:
        """Calcule un score de santé pour le système"""
        score = 100.0
        
        # Pénalités basées sur les métriques
        if metrics.system_collateral_ratio < 150.0:
            score -= 50
        elif metrics.system_collateral_ratio < 180.0:
            score -= 30
        elif metrics.system_collateral_ratio < 200.0:
            score -= 15
        
        if metrics.debt_ceiling_used > 90.0:
            score -= 40
        elif metrics.debt_ceiling_used > 80.0:
            score -= 25
        elif metrics.debt_ceiling_used > 70.0:
            score -= 10
        
        if metrics.total_debt_dai > 900000000:  # 900M DAI
            score -= 20
        elif metrics.total_debt_dai > 800000000:  # 800M DAI
            score -= 10
        
        # Bonus pour stabilité
        if metrics.stability_fee < 0.1:  # < 10%
            score += 5
        
        return max(0.0, min(100.0, score))
    
    async def simulate_oracle_manipulation(self, collateral_type: CollateralType) -> MakerAlert:
        """Simule une manipulation d'oracle"""
        return MakerAlert(
            vault_id=None,
            alert_type=MakerAlertType.ORACLE_MANIPULATION,
            severity="critical",
            description=f"Manipulation d'oracle suspectée pour {collateral_type.value}",
            timestamp=datetime.now(),
            evidence={
                "collateral_type": collateral_type.value,
                "price_deviation": 0.25,  # 25% de déviation
                "affected_vaults": 150,
                "estimated_impact_usd": 5000000.0,
            }
        )
    
    async def get_vault_recommendations(self, vault_id: int) -> Dict[str, Any]:
        """Retourne des recommandations pour un vault"""
        metrics = await self._get_vault_metrics(vault_id, "unknown")
        
        if not metrics:
            return {"error": "Vault non trouvé"}
        
        recommendations = []
        
        # Recommandations basées sur le ratio
        if metrics.collateral_ratio < 150.0:
            recommendations.append({
                "type": "urgent",
                "action": "Ajouter du collatéral",
                "description": f"Ajouter au moins {self._calculate_collateral_needed(metrics):.2f} {metrics.collateral_type.value}",
                "reason": "Ratio de collatéral critique",
            })
        elif metrics.collateral_ratio < 180.0:
            recommendations.append({
                "type": "warning",
                "action": "Considérer ajouter du collatéral",
                "description": f"Ajouter {self._calculate_collateral_needed(metrics):.2f} {metrics.collateral_type.value} pour atteindre 200%",
                "reason": "Ratio de collatéral bas",
            })
        
        # Recommandation pour les frais de stabilité
        if metrics.stability_fee > 0.1:  # > 10%
            recommendations.append({
                "type": "info",
                "action": "Considérer refinancer",
                "description": "Les frais de stabilité sont élevés",
                "reason": "Coût d'emprunt élevé",
            })
        
        return {
            "vault_id": vault_id,
            "current_ratio": metrics.collateral_ratio,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _calculate_collateral_needed(self, metrics: VaultMetrics) -> float:
        """Calcule le collatéral nécessaire pour atteindre un ratio cible"""
        target_ratio = 200.0  # 200%
        
        if metrics.collateral_ratio >= target_ratio:
            return 0.0
        
        # Formule: nouveau_collatéral = (dette * ratio_cible / prix) - collatéral_actuel
        # Prix estimé
        if metrics.collateral_type == CollateralType.ETH_A:
            price = 2000.0
        elif metrics.collateral_type == CollateralType.WBTC_A:
            price = 60000.0
        else:
            price = 1.0
        
        needed = (metrics.debt_amount * (target_ratio / 100.0) / price) - metrics.collateral_amount
        
        return max(0.0, needed)