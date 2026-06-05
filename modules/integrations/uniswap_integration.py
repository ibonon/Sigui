"""
Uniswap Integration Module
Surveillance des pools Uniswap V2/V3, détection de manipulations de prix, arbitrage suspect
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
from scipy import stats

from config import settings

logger = logging.getLogger(__name__)


class UniswapVersion(Enum):
    V2 = "v2"
    V3 = "v3"


class PoolManipulationType(Enum):
    FLASH_SWAP = "flash_swap"
    PRICE_MANIPULATION = "price_manipulation"
    ARBITRAGE = "arbitrage"
    LIQUIDITY_DRAIN = "liquidity_drain"
    FRONT_RUNNING = "front_running"


@dataclass
class PoolAlert:
    pool_address: str
    alert_type: PoolManipulationType
    severity: str
    description: str
    timestamp: datetime
    transaction_hash: Optional[str] = None
    attacker_address: Optional[str] = None
    amount_usd: Optional[float] = None
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class PoolMetrics:
    pool_address: str
    token0: str
    token1: str
    version: UniswapVersion
    liquidity_usd: float
    volume_24h_usd: float
    fees_24h_usd: float
    price_impact_1m: float
    price_volatility_24h: float
    timestamp: datetime


class UniswapIntegration:
    """Intégration complète avec Uniswap V2 et V3"""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.ETHEREUM_RPC_URL
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        # Adresses des contrats Uniswap
        self.uniswap_v2_factory = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
        self.uniswap_v3_factory = "0x1F98431c8aD98523631AE4a59f267346ea31F984"
        
        # Pools majeurs à surveiller
        self.monitored_pools = {
            "eth_usdc_v2": "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc",
            "eth_usdt_v2": "0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852",
            "eth_dai_v2": "0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11",
            "eth_usdc_v3": "0x8ad599c3A0ff1De082011EFDDc58f1908eb6e6D8",
            "eth_usdt_v3": "0x4e68Ccd3E89f51C3074ca5072bbAC773960dFa36",
        }
        
        # Configuration des seuils d'alerte
        self.alert_thresholds = {
            "price_change_5m": 0.05,  # 5% de changement en 5 minutes
            "liquidity_change_1h": 0.20,  # 20% de changement en 1 heure
            "volume_spike_10m": 3.0,  # 3x le volume moyen
            "flash_swap_size": 100000,  # 100k USD
            "arbitrage_profit": 50000,  # 50k USD de profit
        }
        
        # Historique des métriques
        self.metrics_history: Dict[str, List[PoolMetrics]] = {}
        self.alerts_history: List[PoolAlert] = []
        
        # Initialisation des contrats
        self._initialize_contracts()
    
    def _initialize_contracts(self) -> None:
        """Initialise les contrats Uniswap"""
        # ABIs simplifiés pour la surveillance
        self.pair_abi_v2 = [
            {
                "constant": True,
                "inputs": [],
                "name": "getReserves",
                "outputs": [
                    {"name": "reserve0", "type": "uint112"},
                    {"name": "reserve1", "type": "uint112"},
                    {"name": "blockTimestampLast", "type": "uint32"}
                ],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token0",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "token1",
                "outputs": [{"name": "", "type": "address"}],
                "type": "function"
            },
            {
                "constant": True,
                "inputs": [],
                "name": "totalSupply",
                "outputs": [{"name": "", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        # Contrats V2
        self.v2_contracts = {}
        for pool_name, pool_address in self.monitored_pools.items():
            if "v2" in pool_name:
                self.v2_contracts[pool_name] = self.web3.eth.contract(
                    address=pool_address,
                    abi=self.pair_abi_v2
                )
    
    async def monitor_pools(self, callback: Callable[[PoolAlert], None]) -> None:
        """Surveillance continue des pools Uniswap"""
        logger.info("Démarrage de la surveillance Uniswap")
        
        while True:
            try:
                # Collecter les métriques pour tous les pools
                for pool_name, pool_address in self.monitored_pools.items():
                    metrics = await self._collect_pool_metrics(pool_name, pool_address)
                    
                    # Analyser les anomalies
                    alerts = await self._analyze_pool_metrics(pool_name, metrics)
                    
                    # Envoyer les alertes
                    for alert in alerts:
                        await callback(alert)
                        self.alerts_history.append(alert)
                
                # Attendre avant la prochaine itération
                await asyncio.sleep(30)  # Toutes les 30 secondes
                
            except Exception as e:
                logger.error(f"Erreur dans la surveillance Uniswap: {e}")
                await asyncio.sleep(60)  # Attendre plus longtemps en cas d'erreur
    
    async def _collect_pool_metrics(self, pool_name: str, pool_address: str) -> PoolMetrics:
        """Collecte les métriques d'un pool"""
        try:
            # Déterminer la version
            version = UniswapVersion.V2 if "v2" in pool_name else UniswapVersion.V3
            
            if version == UniswapVersion.V2:
                return await self._collect_v2_metrics(pool_name, pool_address)
            else:
                return await self._collect_v3_metrics(pool_name, pool_address)
                
        except Exception as e:
            logger.error(f"Erreur lors de la collecte des métriques pour {pool_name}: {e}")
            # Retourner des métriques par défaut
            return PoolMetrics(
                pool_address=pool_address,
                token0="unknown",
                token1="unknown",
                version=version,
                liquidity_usd=0.0,
                volume_24h_usd=0.0,
                fees_24h_usd=0.0,
                price_impact_1m=0.0,
                price_volatility_24h=0.0,
                timestamp=datetime.now()
            )
    
    async def _collect_v2_metrics(self, pool_name: str, pool_address: str) -> PoolMetrics:
        """Collecte les métriques pour un pool V2"""
        contract = self.v2_contracts[pool_name]
        
        # Obtenir les réserves
        reserves = contract.functions.getReserves().call()
        reserve0 = reserves[0] / 1e18  # ETH
        reserve1 = reserves[1] / 1e6   # USDC/USDT
        
        # Obtenir les tokens
        token0 = contract.functions.token0().call()
        token1 = contract.functions.token1().call()
        
        # Calculer la liquidité (simplifié)
        # Prix ETH = 2000 USD (à remplacer par un oracle)
        eth_price = 2000.0
        liquidity_usd = (reserve0 * eth_price) + (reserve1 * 1.0)
        
        # Calculer l'impact de prix pour 1M USD
        price_impact = self._calculate_price_impact_v2(reserve0, reserve1, 1000000)
        
        # Calculer la volatilité (simplifié)
        volatility = await self._calculate_volatility(pool_name, reserve0, reserve1)
        
        return PoolMetrics(
            pool_address=pool_address,
            token0=token0,
            token1=token1,
            version=UniswapVersion.V2,
            liquidity_usd=liquidity_usd,
            volume_24h_usd=self._estimate_volume(pool_name),
            fees_24h_usd=liquidity_usd * 0.003,  # 0.3% des swaps
            price_impact_1m=price_impact,
            price_volatility_24h=volatility,
            timestamp=datetime.now()
        )
    
    async def _collect_v3_metrics(self, pool_name: str, pool_address: str) -> PoolMetrics:
        """Collecte les métriques pour un pool V3"""
        # Pour V3, on utilise une approche simplifiée
        # Dans une implémentation réelle, on utiliserait le contrat V3
        
        # Estimation basée sur V2
        eth_price = 2000.0
        liquidity_usd = 50000000  # 50M USD estimé
        
        return PoolMetrics(
            pool_address=pool_address,
            token0="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # WETH
            token1="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # USDC
            version=UniswapVersion.V3,
            liquidity_usd=liquidity_usd,
            volume_24h_usd=liquidity_usd * 0.1,  # 10% du volume
            fees_24h_usd=liquidity_usd * 0.0005,  # 0.05% des swaps
            price_impact_1m=0.001,  # 0.1% d'impact
            price_volatility_24h=0.02,  # 2% de volatilité
            timestamp=datetime.now()
        )
    
    def _calculate_price_impact_v2(self, reserve0: float, reserve1: float, amount_usd: float) -> float:
        """Calcule l'impact de prix pour un swap donné"""
        # Formule constante du produit
        k = reserve0 * reserve1
        
        # Pour un swap de amount_usd en token1 vers token0
        new_reserve1 = reserve1 + amount_usd
        new_reserve0 = k / new_reserve1
        
        # Prix avant
        price_before = reserve1 / reserve0
        
        # Prix après
        price_after = new_reserve1 / new_reserve0
        
        # Impact de prix
        impact = abs((price_after - price_before) / price_before)
        
        return impact
    
    async def _calculate_volatility(self, pool_name: str, reserve0: float, reserve1: float) -> float:
        """Calcule la volatilité des prix"""
        # Stocker les métriques historiques
        if pool_name not in self.metrics_history:
            self.metrics_history[pool_name] = []
        
        current_price = reserve1 / reserve0 if reserve0 > 0 else 0
        
        # Ajouter le prix actuel à l'historique
        self.metrics_history[pool_name].append(current_price)
        
        # Garder seulement les dernières 1000 valeurs
        if len(self.metrics_history[pool_name]) > 1000:
            self.metrics_history[pool_name] = self.metrics_history[pool_name][-1000:]
        
        # Calculer la volatilité (écart-type des rendements logarithmiques)
        if len(self.metrics_history[pool_name]) > 10:
            prices = np.array(self.metrics_history[pool_name])
            returns = np.log(prices[1:] / prices[:-1])
            volatility = np.std(returns) * np.sqrt(365 * 24)  # Annualisée
            return float(volatility)
        
        return 0.0
    
    def _estimate_volume(self, pool_name: str) -> float:
        """Estime le volume 24h (simplifié)"""
        # Dans une implémentation réelle, on analyserait les événements Swap
        base_volumes = {
            "eth_usdc_v2": 50000000,  # 50M USD
            "eth_usdt_v2": 30000000,  # 30M USD
            "eth_dai_v2": 10000000,   # 10M USD
            "eth_usdc_v3": 80000000,  # 80M USD
            "eth_usdt_v3": 40000000,  # 40M USD
        }
        
        return base_volumes.get(pool_name, 10000000)
    
    async def _analyze_pool_metrics(self, pool_name: str, metrics: PoolMetrics) -> List[PoolAlert]:
        """Analyse les métriques pour détecter des anomalies"""
        alerts = []
        
        # Vérifier les changements de prix rapides
        if await self._check_price_spike(pool_name, metrics):
            alerts.append(PoolAlert(
                pool_address=metrics.pool_address,
                alert_type=PoolManipulationType.PRICE_MANIPULATION,
                severity="high",
                description=f"Spike de prix détecté sur {pool_name}",
                timestamp=datetime.now(),
                evidence={"price_volatility": metrics.price_volatility_24h}
            ))
        
        # Vérifier les drains de liquidité
        if await self._check_liquidity_drain(pool_name, metrics):
            alerts.append(PoolAlert(
                pool_address=metrics.pool_address,
                alert_type=PoolManipulationType.LIQUIDITY_DRAIN,
                severity="critical",
                description=f"Drain de liquidité détecté sur {pool_name}",
                timestamp=datetime.now(),
                evidence={"liquidity_usd": metrics.liquidity_usd}
            ))
        
        # Vérifier les volumes anormaux
        if await self._check_volume_anomaly(pool_name, metrics):
            alerts.append(PoolAlert(
                pool_address=metrics.pool_address,
                alert_type=PoolManipulationType.FRONT_RUNNING,
                severity="medium",
                description=f"Volume anormal détecté sur {pool_name}",
                timestamp=datetime.now(),
                evidence={"volume_24h_usd": metrics.volume_24h_usd}
            ))
        
        return alerts
    
    async def _check_price_spike(self, pool_name: str, metrics: PoolMetrics) -> bool:
        """Vérifie les spikes de prix"""
        if pool_name in self.metrics_history and len(self.metrics_history[pool_name]) > 5:
            recent_prices = self.metrics_history[pool_name][-5:]
            current_price = recent_prices[-1]
            
            # Calculer le changement moyen
            if len(recent_prices) >= 2:
                price_changes = []
                for i in range(1, len(recent_prices)):
                    change = abs(recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
                    price_changes.append(change)
                
                avg_change = np.mean(price_changes) if price_changes else 0
                
                # Vérifier si le dernier changement dépasse le seuil
                last_change = price_changes[-1] if price_changes else 0
                threshold = self.alert_thresholds["price_change_5m"]
                
                return last_change > threshold * 2  # 2x le seuil normal
        
        return False
    
    async def _check_liquidity_drain(self, pool_name: str, metrics: PoolMetrics) -> bool:
        """Vérifie les drains de liquidité"""
        # Dans une implémentation réelle, on suivrait l'historique de liquidité
        # Pour l'exemple, on simule une détection
        if metrics.liquidity_usd < 1000000:  # Moins de 1M USD
            return True
        
        return False
    
    async def _check_volume_anomaly(self, pool_name: str, metrics: PoolMetrics) -> bool:
        """Vérifie les anomalies de volume"""
        # Volume moyen estimé pour ce pool
        avg_volume = self._estimate_volume(pool_name)
        
        # Vérifier si le volume actuel dépasse significativement la moyenne
        volume_ratio = metrics.volume_24h_usd / avg_volume if avg_volume > 0 else 1
        
        threshold = self.alert_thresholds["volume_spike_10m"]
        
        return volume_ratio > threshold
    
    async def get_pool_health(self, pool_address: str) -> Dict[str, Any]:
        """Retourne la santé d'un pool"""
        # Trouver le pool par adresse
        pool_name = None
        for name, addr in self.monitored_pools.items():
            if addr.lower() == pool_address.lower():
                pool_name = name
                break
        
        if not pool_name:
            return {"error": "Pool non trouvé"}
        
        # Collecter les métriques
        metrics = await self._collect_pool_metrics(pool_name, pool_address)
        
        # Calculer le score de santé
        health_score = self._calculate_health_score(metrics)
        
        return {
            "pool_address": pool_address,
            "pool_name": pool_name,
            "health_score": health_score,
            "metrics": {
                "liquidity_usd": metrics.liquidity_usd,
                "volume_24h_usd": metrics.volume_24h_usd,
                "fees_24h_usd": metrics.fees_24h_usd,
                "price_impact_1m": metrics.price_impact_1m,
                "price_volatility_24h": metrics.price_volatility_24h,
            },
            "timestamp": metrics.timestamp.isoformat(),
        }
    
    def _calculate_health_score(self, metrics: PoolMetrics) -> float:
        """Calcule un score de santé pour le pool"""
        score = 100.0
        
        # Pénalités basées sur les métriques
        if metrics.liquidity_usd < 1000000:  # < 1M USD
            score -= 30
        
        if metrics.price_volatility_24h > 0.5:  # > 50% de volatilité
            score -= 25
        
        if metrics.price_impact_1m > 0.1:  # > 10% d'impact
            score -= 20
        
        # Bonus pour volume élevé
        if metrics.volume_24h_usd > 10000000:  # > 10M USD
            score += 10
        
        return max(0.0, min(100.0, score))
    
    async def detect_flash_loan_attack(self, transaction_hash: str) -> Optional[PoolAlert]:
        """Détecte les attaques par flash loan dans une transaction"""
        # Dans une implémentation réelle, on analyserait la transaction
        # Pour l'exemple, on simule une détection
        
        # Récupérer la transaction
        try:
            tx = self.web3.eth.get_transaction(transaction_hash)
            
            # Vérifier si c'est un flash swap
            if tx["value"] > self.alert_thresholds["flash_swap_size"]:
                return PoolAlert(
                    pool_address=tx["to"] or "unknown",
                    alert_type=PoolManipulationType.FLASH_SWAP,
                    severity="high",
                    description=f"Flash swap suspect détecté: {transaction_hash}",
                    timestamp=datetime.now(),
                    transaction_hash=transaction_hash,
                    attacker_address=tx["from"],
                    amount_usd=tx["value"] / 1e18 * 2000,  # Convertir ETH en USD
                    evidence={
                        "value_eth": tx["value"] / 1e18,
                        "gas_price": tx["gasPrice"],
                        "gas_limit": tx["gas"],
                    }
                )
        
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de la transaction {transaction_hash}: {e}")
        
        return None