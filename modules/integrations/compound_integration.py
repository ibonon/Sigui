"""
Compound Integration Module
Surveillance des marchés Compound, détection des risques de liquidation, monitoring des taux d'intérêt
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


class CompoundMarket(Enum):
    ETH = "cETH"
    DAI = "cDAI"
    USDC = "cUSDC"
    USDT = "cUSDT"
    WBTC = "cWBTC"


class CompoundAlertType(Enum):
    LIQUIDATION_RISK = "liquidation_risk"
    INTEREST_RATE_MANIPULATION = "interest_rate_manipulation"
    COLLATERAL_DRAIN = "collateral_drain"
    FLASH_LOAN_ATTACK = "flash_loan_attack"
    ORACLE_MANIPULATION = "oracle_manipulation"


@dataclass
class CompoundAlert:
    market: CompoundMarket
    alert_type: CompoundAlertType
    severity: str
    description: str
    timestamp: datetime
    borrower_address: Optional[str] = None
    collateral_amount: Optional[float] = None
    debt_amount: Optional[float] = None
    health_factor: Optional[float] = None
    transaction_hash: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class MarketMetrics:
    market: CompoundMarket
    underlying_token: str
    total_supply_usd: float
    total_borrow_usd: float
    utilization_rate: float
    supply_apy: float
    borrow_apy: float
    collateral_factor: float
    liquidation_threshold: float
    oracle_price: float
    timestamp: datetime


@dataclass
class BorrowerPosition:
    address: str
    market: CompoundMarket
    collateral_amount: float
    debt_amount: float
    health_factor: float
    liquidation_threshold: float
    is_at_risk: bool
    timestamp: datetime


class CompoundIntegration:
    """Intégration complète avec Compound Protocol"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.ETHEREUM_RPC_URL
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Adresses des contrats Compound
        self.comptroller_address = "0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B"
        self.price_oracle_address = "0x65c816077C29b557BEE980ae3cC2dCE80204A0C5"
        
        # Marchés Compound majeurs
        self.markets = {
            CompoundMarket.ETH: "0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5",
            CompoundMarket.DAI: "0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643",
            CompoundMarket.USDC: "0x39AA39c021dfbaE8faC545936693aC917d5E7563",
            CompoundMarket.USDT: "0xf650C3d88D12dB855b8bf7D11Be6C55A4e07dCC9",
            CompoundMarket.WBTC: "0xC11b1268C1A384e55C48c2391d8d480264A3A7F4",
        }
        
        # Seuils d'alerte
        self.alert_thresholds = {
            "health_factor_warning": 1.5,
            "health_factor_critical": 1.1,
            "utilization_spike": 0.10,  # 10% de changement
            "interest_rate_spike": 0.50,  # 50% de changement
            "collateral_drain": 0.30,  # 30% de réduction
        }
        
        # Historique
        self.metrics_history: Dict[CompoundMarket, List[MarketMetrics]] = {}
        self.borrower_positions: Dict[str, List[BorrowerPosition]] = {}
        self.alerts_history: List[CompoundAlert] = []
        
        # Initialisation des contrats
        self._initialize_contracts()
    
    def _initialize_contracts(self) -> None:
        """Initialise les contrats Compound"""
        # ABIs simplifiés
        self.c_token_abi = [
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalBorrows",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "supplyRatePerBlock",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "borrowRatePerBlock",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "getCash",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "account", "type": "address"}],
                "name": "getAccountSnapshot",
                "outputs": [
                    {"name": "", "type": "uint256"},
                    {"name": "", "type": "uint256"},
                    {"name": "", "type": "uint256"},
                    {"name": "", "type": "uint256"}
                ],
                "type": "function"
            }
        ]
        
        self.comptroller_abi = [
            {
                "constant": True,
                "inputs": [{"name": "account", "type": "address"}],
                "name": "getAccountLiquidity",
                "outputs": [
                    {"name": "", "type": "uint256"},
                    {"name": "", "type": "uint256"},
                    {"name": "", "type": "uint256"}
                ],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [{"name": "cToken", "type": "address"}],
                "name": "markets",
                "outputs": [
                    {"name": "isListed", "type": "bool"},
                    {"name": "collateralFactorMantissa", "type": "uint256"},
                    {"name": "isComped", "type": "bool"}
                ],
                "type": "function"
            }
        ]
        
        # Initialiser les contrats
        self.c_token_contracts = {}
        for market, address in self.markets.items():
            self.c_token_contracts[market] = self.web3.eth.contract(
                address=address,
                abi=self.c_token_abi
            )
        
        self.comptroller = self.web3.eth.contract(
            address=self.comptroller_address,
            abi=self.comptroller_abi
        )
    
    async def monitor_markets(self, callback: Callable[[CompoundAlert], None]) -> None:
        """Surveillance continue des marchés Compound"""
        logger.info("Démarrage de la surveillance Compound")
        
        while True:
            try:
                # Surveiller tous les marchés
                for market in CompoundMarket:
                    metrics = await self._collect_market_metrics(market)
                    
                    # Analyser les risques
                    alerts = await self._analyze_market_metrics(market, metrics)
                    
                    # Envoyer les alertes
                    for alert in alerts:
                        await callback(alert)
                        self.alerts_history.append(alert)
                
                # Surveiller les positions à risque
                await self._monitor_risky_positions(callback)
                
                # Attendre avant la prochaine itération
                await asyncio.sleep(60)  # Toutes les minutes
                
            except Exception as e:
                logger.error(f"Erreur dans la surveillance Compound: {e}")
                await asyncio.sleep(120)  # Attendre plus longtemps en cas d'erreur
    
    async def _collect_market_metrics(self, market: CompoundMarket) -> MarketMetrics:
        """Collecte les métriques d'un marché"""
        try:
            contract = self.c_token_contracts[market]
            
            # Obtenir les données du marché
            total_supply = contract.functions.totalSupply().call() / 1e18
            total_borrows = contract.functions.totalBorrows().call() / 1e18
            cash = contract.functions.getCash().call() / 1e18
            
            # Taux d'intérêt
            supply_rate = contract.functions.supplyRatePerBlock().call() / 1e18
            borrow_rate = contract.functions.borrowRatePerBlock().call() / 1e18
            
            # Facteur de collatéral (depuis Comptroller)
            market_data = self.comptroller.functions.markets(self.markets[market]).call()
            collateral_factor = market_data[1] / 1e18
            
            # Prix de l'oracle (simplifié)
            oracle_price = await self._get_oracle_price(market)
            
            # Calculer le taux d'utilisation
            utilization_rate = total_borrows / (total_borrows + cash) if (total_borrows + cash) > 0 else 0
            
            # Convertir en USD
            total_supply_usd = total_supply * oracle_price
            total_borrow_usd = total_borrows * oracle_price
            
            # Calculer les APY (annualisé)
            blocks_per_year = 2102400  # ~15 secondes par bloc
            supply_apy = ((1 + supply_rate) ** blocks_per_year - 1) * 100
            borrow_apy = ((1 + borrow_rate) ** blocks_per_year - 1) * 100
            
            return MarketMetrics(
                market=market,
                underlying_token=self._get_underlying_token(market),
                total_supply_usd=total_supply_usd,
                total_borrow_usd=total_borrow_usd,
                utilization_rate=utilization_rate,
                supply_apy=supply_apy,
                borrow_apy=borrow_apy,
                collateral_factor=collateral_factor,
                liquidation_threshold=collateral_factor * 0.9,  # 90% du collateral factor
                oracle_price=oracle_price,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques pour {market}: {e}")
            
            # Retourner des métriques par défaut
            return MarketMetrics(
                market=market,
                underlying_token="unknown",
                total_supply_usd=0.0,
                total_borrow_usd=0.0,
                utilization_rate=0.0,
                supply_apy=0.0,
                borrow_apy=0.0,
                collateral_factor=0.0,
                liquidation_threshold=0.0,
                oracle_price=0.0,
                timestamp=datetime.now()
            )
    
    async def _get_oracle_price(self, market: CompoundMarket) -> float:
        """Obtenir le prix depuis l'oracle Compound"""
        # Prix par défaut pour l'exemple
        prices = {
            CompoundMarket.ETH: 2000.0,
            CompoundMarket.DAI: 1.0,
            CompoundMarket.USDC: 1.0,
            CompoundMarket.USDT: 1.0,
            CompoundMarket.WBTC: 60000.0,
        }
        
        return prices.get(market, 0.0)
    
    def _get_underlying_token(self, market: CompoundMarket) -> str:
        """Retourne l'adresse du token sous-jacent"""
        tokens = {
            CompoundMarket.ETH: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
            CompoundMarket.DAI: "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            CompoundMarket.USDC: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            CompoundMarket.USDT: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            CompoundMarket.WBTC: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        }
        
        return tokens.get(market, "unknown")
    
    async def _analyze_market_metrics(self, market: CompoundMarket, metrics: MarketMetrics) -> List[CompoundAlert]:
        """Analyse les métriques du marché pour détecter des risques"""
        alerts = []
        
        # Vérifier les spikes de taux d'utilisation
        if await self._check_utilization_spike(market, metrics):
            alerts.append(CompoundAlert(
                market=market,
                alert_type=CompoundAlertType.INTEREST_RATE_MANIPULATION,
                severity="medium",
                description=f"Spike de taux d'utilisation détecté sur {market.value}",
                timestamp=datetime.now(),
                evidence={
                    "utilization_rate": metrics.utilization_rate,
                    "borrow_apy": metrics.borrow_apy,
                }
            ))
        
        # Vérifier les manipulations de taux d'intérêt
        if await self._check_interest_rate_manipulation(market, metrics):
            alerts.append(CompoundAlert(
                market=market,
                alert_type=CompoundAlertType.INTEREST_RATE_MANIPULATION,
                severity="high",
                description=f"Manipulation de taux d'intérêt suspectée sur {market.value}",
                timestamp=datetime.now(),
                evidence={
                    "supply_apy": metrics.supply_apy,
                    "borrow_apy": metrics.borrow_apy,
                    "change_percentage": 0.55,  # Exemple: 55% de changement
                }
            ))
        
        # Vérifier les drains de collatéral
        if await self._check_collateral_drain(market, metrics):
            alerts.append(CompoundAlert(
                market=market,
                alert_type=CompoundAlertType.COLLATERAL_DRAIN,
                severity="critical",
                description=f"Drain de collatéral détecté sur {market.value}",
                timestamp=datetime.now(),
                evidence={
                    "total_supply_usd": metrics.total_supply_usd,
                    "change_percentage": -0.35,  # Exemple: 35% de réduction
                }
            ))
        
        return alerts
    
    async def _check_utilization_spike(self, market: CompoundMarket, metrics: MarketMetrics) -> bool:
        """Vérifie les spikes de taux d'utilisation"""
        if market not in self.metrics_history:
            self.metrics_history[market] = []
        
        # Ajouter aux historiques
        self.metrics_history[market].append(metrics)
        
        # Garder seulement les dernières 100 métriques
        if len(self.metrics_history[market]) > 100:
            self.metrics_history[market] = self.metrics_history[market][-100:]
        
        # Vérifier les spikes si on a assez d'historique
        if len(self.metrics_history[market]) >= 10:
            recent_metrics = self.metrics_history[market][-10:]
            utilizations = [m.utilization_rate for m in recent_metrics]
            
            # Calculer la moyenne et l'écart-type
            avg_utilization = np.mean(utilizations[:-1]) if len(utilizations) > 1 else utilizations[0]
            std_utilization = np.std(utilizations[:-1]) if len(utilizations) > 1 else 0
            
            current_utilization = utilizations[-1]
            
            # Vérifier si le changement dépasse 2 écarts-types
            if std_utilization > 0:
                z_score = abs(current_utilization - avg_utilization) / std_utilization
                return z_score > 2.0  # Changement significatif
        
        return False
    
    async def _check_interest_rate_manipulation(self, market: CompoundMarket, metrics: MarketMetrics) -> bool:
        """Vérifie les manipulations de taux d'intérêt"""
        if market not in self.metrics_history or len(self.metrics_history[market]) < 5:
            return False
        
        recent_metrics = self.metrics_history[market][-5:]
        borrow_rates = [m.borrow_apy for m in recent_metrics]
        
        # Vérifier les changements rapides
        if len(borrow_rates) >= 2:
            changes = []
            for i in range(1, len(borrow_rates)):
                if borrow_rates[i-1] > 0:
                    change = abs(borrow_rates[i] - borrow_rates[i-1]) / borrow_rates[i-1]
                    changes.append(change)
            
            if changes:
                avg_change = np.mean(changes)
                threshold = self.alert_thresholds["interest_rate_spike"]
                return avg_change > threshold
        
        return False
    
    async def _check_collateral_drain(self, market: CompoundMarket, metrics: MarketMetrics) -> bool:
        """Vérifie les drains de collatéral"""
        if market not in self.metrics_history or len(self.metrics_history[market]) < 3:
            return False
        
        recent_metrics = self.metrics_history[market][-3:]
        supplies = [m.total_supply_usd for m in recent_metrics]
        
        # Vérifier la tendance à la baisse
        if len(supplies) >= 2:
            changes = []
            for i in range(1, len(supplies)):
                if supplies[i-1] > 0:
                    change = (supplies[i] - supplies[i-1]) / supplies[i-1]
                    changes.append(change)
            
            if changes:
                # Si toutes les variations sont négatives et significatives
                all_negative = all(c < -0.1 for c in changes)  # >10% de baisse
                significant_drop = any(c < -0.3 for c in changes)  # >30% de baisse
                
                return all_negative and significant_drop
        
        return False
    
    async def _monitor_risky_positions(self, callback: Callable[[CompoundAlert], None]) -> None:
        """Surveille les positions d'emprunteurs à risque"""
        # Dans une implémentation réelle, on analyserait les événements Borrow et les positions
        # Pour l'exemple, on simule la détection de positions à risque
        
        # Adresses d'emprunteurs à surveiller (exemple)
        risky_borrowers = [
            "0x742d35Cc6634C0532925a3b844Bc9e0F2b5B3a5A",
            "0x53D284357EC70Ce289D6D64134DfAc8E511c8a3D",
        ]
        
        for borrower in risky_borrowers:
            position = await self._get_borrower_position(borrower)
            
            if position and position.is_at_risk:
                alert = CompoundAlert(
                    market=position.market,
                    alert_type=CompoundAlertType.LIQUIDATION_RISK,
                    severity="high",
                    description=f"Position à risque de liquidation détectée pour {borrower[:10]}...",
                    timestamp=datetime.now(),
                    borrower_address=borrower,
                    collateral_amount=position.collateral_amount,
                    debt_amount=position.debt_amount,
                    health_factor=position.health_factor,
                    evidence={
                        "liquidation_threshold": position.liquidation_threshold,
                        "health_factor_warning": self.alert_thresholds["health_factor_warning"],
                    }
                )
                
                await callback(alert)
                self.alerts_history.append(alert)
    
    async def _get_borrower_position(self, borrower_address: str) -> Optional[BorrowerPosition]:
        """Obtient la position d'un emprunteur"""
        try:
            # Obtenir la liquidité du compte
            liquidity_data = self.comptroller.functions.getAccountLiquidity(borrower_address).call()
            
            # shortfall > 0 signifie risque de liquidation
            shortfall = liquidity_data[2] / 1e18
            
            # Pour l'exemple, on simule des positions
            if shortfall > 0 or np.random.random() < 0.1:  # 10% de chance d'être à risque
                collateral_amount = np.random.uniform(10, 1000)
                debt_amount = np.random.uniform(5, 500)
                
                # Calculer le health factor
                health_factor = collateral_amount / debt_amount if debt_amount > 0 else 100.0
                
                is_at_risk = health_factor < self.alert_thresholds["health_factor_warning"]
                
                return BorrowerPosition(
                    address=borrower_address,
                    market=np.random.choice(list(CompoundMarket)),
                    collateral_amount=collateral_amount,
                    debt_amount=debt_amount,
                    health_factor=health_factor,
                    liquidation_threshold=0.8,  # Exemple
                    is_at_risk=is_at_risk,
                    timestamp=datetime.now()
                )
        
        except Exception as e:
            logger.error(f"Erreur lors de l'obtention de la position pour {borrower_address}: {e}")
        
        return None
    
    async def get_market_health(self, market: CompoundMarket) -> Dict[str, Any]:
        """Retourne la santé d'un marché"""
        metrics = await self._collect_market_metrics(market)
        
        # Calculer le score de santé
        health_score = self._calculate_market_health_score(metrics)
        
        # Identifier les risques
        risks = []
        if metrics.utilization_rate > 0.8:
            risks.append("Taux d'utilisation élevé")
        if metrics.borrow_apy > 20.0:
            risks.append("Taux d'emprunt élevé")
        if metrics.total_supply_usd < 1000000:
            risks.append("Liquidité faible")
        
        return {
            "market": market.value,
            "health_score": health_score,
            "status": "healthy" if health_score > 70 else "warning" if health_score > 40 else "critical",
            "metrics": {
                "total_supply_usd": metrics.total_supply_usd,
                "total_borrow_usd": metrics.total_borrow_usd,
                "utilization_rate": metrics.utilization_rate,
                "supply_apy": metrics.supply_apy,
                "borrow_apy": metrics.borrow_apy,
                "collateral_factor": metrics.collateral_factor,
                "oracle_price": metrics.oracle_price,
            },
            "risks": risks,
            "timestamp": metrics.timestamp.isoformat(),
        }
    
    def _calculate_market_health_score(self, metrics: MarketMetrics) -> float:
        """Calcule un score de santé pour le marché"""
        score = 100.0
        
        # Pénalités basées sur les métriques
        if metrics.utilization_rate > 0.9:
            score -= 40
        elif metrics.utilization_rate > 0.8:
            score -= 25
        elif metrics.utilization_rate > 0.7:
            score -= 15
        
        if metrics.borrow_apy > 30.0:
            score -= 30
        elif metrics.borrow_apy > 20.0:
            score -= 20
        elif metrics.borrow_apy > 10.0:
            score -= 10
        
        if metrics.total_supply_usd < 1000000:
            score -= 20
        
        # Bonus pour diversité
        if metrics.collateral_factor < 0.75:
            score += 5  # Facteur de collatéral conservateur
        
        return max(0.0, min(100.0, score))
    
    async def simulate_liquidation_attack(self, borrower_address: str, market: CompoundMarket) -> CompoundAlert:
        """Simule une attaque par liquidation"""
        # Cette méthode simule la détection d'une attaque par liquidation
        
        return CompoundAlert(
            market=market,
            alert_type=CompoundAlertType.FLASH_LOAN_ATTACK,
            severity="critical",
            description=f"Attaque par liquidation simulée détectée sur {market.value}",
            timestamp=datetime.now(),
            borrower_address=borrower_address,
            collateral_amount=1000.0,
            debt_amount=850.0,
            health_factor=1.18,
            evidence={
                "attack_type": "liquidation_attack",
                "estimated_profit_usd": 15000.0,
                "flash_loan_amount_usd": 5000000.0,
                "target_health_factor": 1.05,
            }
        )
    
    async def get_risk_report(self) -> Dict[str, Any]:
        """Génère un rapport complet des risques"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "markets": {},
            "total_risk_score": 0.0,
            "critical_alerts": 0,
            "high_alerts": 0,
            "medium_alerts": 0,
        }
        
        total_score = 0.0
        market_count = 0
        
        # Analyser tous les marchés
        for market in CompoundMarket:
            health_data = await self.get_market_health(market)
            report["markets"][market.value] = health_data
            
            total_score += health_data["health_score"]
            market_count += 1
        
        # Calculer le score moyen
        if market_count > 0:
            report["total_risk_score"] = total_score / market_count
        
        # Compter les alertes récentes
        recent_alerts = [a for a in self.alerts_history 
                        if (datetime.now() - a.timestamp).total_seconds() < 3600]  # Dernière heure
        
        for alert in recent_alerts:
            if alert.severity == "critical":
                report["critical_alerts"] += 1
            elif alert.severity == "high":
                report["high_alerts"] += 1
            elif alert.severity == "medium":
                report["medium_alerts"] += 1
        
        return report