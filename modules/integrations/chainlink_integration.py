"""
Intégration Chainlink pour la surveillance des oracles et prix.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from web3 import Web3
from web3.middleware import geth_poa_middleware

from ..config import settings

logger = logging.getLogger(__name__)


class ChainlinkIntegration:
    """Intégration avec le réseau Chainlink."""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.ETHEREUM_RPC_URL
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        # Contrats Chainlink
        self.eth_usd_feed = "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419"
        self.btc_usd_feed = "0xF4030086522a5bEEa4988F8cA5B36dbC97BeE88c"
        self.link_usd_feed = "0x2c1d072e956AFFC0D435Cb7AC38EF18d24d9127c"
        
        # ABI simplifié pour les feeds Chainlink
        self.feed_abi = [
            {
                "name": "latestRoundData",
                "type": "function",
                "inputs": [],
                "outputs": [
                    {"name": "roundId", "type": "uint80"},
                    {"name": "answer", "type": "int256"},
                    {"name": "startedAt", "type": "uint256"},
                    {"name": "updatedAt", "type": "uint256"},
                    {"name": "answeredInRound", "type": "uint80"}
                ],
                "stateMutability": "view"
            },
            {
                "name": "decimals",
                "type": "function",
                "inputs": [],
                "outputs": [{"name": "", "type": "uint8"}],
                "stateMutability": "view"
            },
            {
                "name": "description",
                "type": "function",
                "inputs": [],
                "outputs": [{"name": "", "type": "string"}],
                "stateMutability": "view"
            }
        ]
        
        # Initialiser les contrats
        self.eth_feed_contract = self.web3.eth.contract(
            address=self.eth_usd_feed,
            abi=self.feed_abi
        )
        
        self.btc_feed_contract = self.web3.eth.contract(
            address=self.btc_usd_feed,
            abi=self.feed_abi
        )
        
        self.link_feed_contract = self.web3.eth.contract(
            address=self.link_usd_feed,
            abi=self.feed_abi
        )
        
        # Historique des prix pour détection d'anomalies
        self.price_history = {
            "ETH": [],
            "BTC": [],
            "LINK": []
        }
        
        logger.info("Intégration Chainlink initialisée")
    
    async def monitor_price_feeds(self, callback) -> None:
        """Surveille les feeds de prix Chainlink en temps réel."""
        logger.info("Démarrage de la surveillance des feeds Chainlink")
        
        while True:
            try:
                # Récupérer les prix
                eth_price = await self.get_eth_price()
                btc_price = await self.get_btc_price()
                link_price = await self.get_link_price()
                
                # Vérifier les anomalies
                anomalies = await self._check_price_anomalies(
                    eth_price, btc_price, link_price
                )
                
                if anomalies:
                    for anomaly in anomalies:
                        await callback(anomaly)
                
                # Mettre à jour l'historique
                await self._update_price_history(
                    eth_price, btc_price, link_price
                )
                
                await asyncio.sleep(30)  # Vérifier toutes les 30 secondes
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance Chainlink: {e}")
                await asyncio.sleep(60)
    
    async def get_eth_price(self) -> Dict[str, Any]:
        """Récupère le prix ETH/USD."""
        return await self._get_feed_price(
            self.eth_feed_contract,
            "ETH/USD",
            "Ethereum"
        )
    
    async def get_btc_price(self) -> Dict[str, Any]:
        """Récupère le prix BTC/USD."""
        return await self._get_feed_price(
            self.btc_feed_contract,
            "BTC/USD",
            "Bitcoin"
        )
    
    async def get_link_price(self) -> Dict[str, Any]:
        """Récupère le prix LINK/USD."""
        return await self._get_feed_price(
            self.link_feed_contract,
            "LINK/USD",
            "Chainlink"
        )
    
    async def _get_feed_price(self, contract, pair: str, asset: str) -> Dict[str, Any]:
        """Récupère le prix d'un feed Chainlink."""
        try:
            # Récupérer les données du round
            round_data = contract.functions.latestRoundData().call()
            
            # Extraire les valeurs
            round_id = round_data[0]
            answer = round_data[1]
            started_at = round_data[2]
            updated_at = round_data[3]
            answered_in_round = round_data[4]
            
            # Récupérer les décimales
            decimals = contract.functions.decimals().call()
            
            # Calculer le prix
            price = answer / (10 ** decimals)
            
            # Récupérer la description
            description = contract.functions.description().call()
            
            # Vérifier la fraîcheur des données
            current_time = datetime.now().timestamp()
            staleness = current_time - updated_at
            
            return {
                "pair": pair,
                "asset": asset,
                "price": float(price),
                "round_id": round_id,
                "updated_at": datetime.fromtimestamp(updated_at),
                "started_at": datetime.fromtimestamp(started_at),
                "answered_in_round": answered_in_round,
                "decimals": decimals,
                "description": description,
                "staleness_seconds": staleness,
                "is_stale": staleness > 3600,  # Plus d'une heure
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix {pair}: {e}")
            return {
                "pair": pair,
                "asset": asset,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    async def _check_price_anomalies(
        self,
        eth_price: Dict[str, Any],
        btc_price: Dict[str, Any],
        link_price: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Vérifie les anomalies de prix."""
        anomalies = []
        
        # Vérifier la fraîcheur des données
        for price_data in [eth_price, btc_price, link_price]:
            if "error" not in price_data and price_data.get("is_stale"):
                anomalies.append({
                    "type": "STALE_PRICE_FEED",
                    "severity": "HIGH",
                    "description": f"Feed {price_data['pair']} stale ({price_data['staleness_seconds']:.0f}s)",
                    "pair": price_data["pair"],
                    "staleness_seconds": price_data["staleness_seconds"],
                    "last_update": price_data["updated_at"],
                    "timestamp": datetime.now(),
                    "recommendations": [
                        "Vérifier la connectivité du nœud Chainlink",
                        "Surveiller les autres sources de prix",
                        "Considérer la suspension des opérations sensibles"
                    ]
                })
        
        # Vérifier les variations de prix importantes
        for price_data in [eth_price, btc_price, link_price]:
            if "error" not in price_data:
                anomaly = await self._check_price_variation(price_data)
                if anomaly:
                    anomalies.append(anomaly)
        
        # Vérifier les déviations entre les feeds
        if all("error" not in p for p in [eth_price, btc_price, link_price]):
            deviation_anomaly = await self._check_price_deviations(
                eth_price, btc_price, link_price
            )
            if deviation_anomaly:
                anomalies.append(deviation_anomaly)
        
        return anomalies
    
    async def _check_price_variation(self, price_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Vérifie les variations de prix importantes."""
        pair = price_data["pair"]
        current_price = price_data["price"]
        
        # Récupérer l'historique
        history = self.price_history.get(pair.split("/")[0], [])
        
        if len(history) >= 10:  # Au moins 10 points de données
            # Calculer la moyenne des 10 dernières valeurs
            recent_prices = [h["price"] for h in history[-10:]]
            avg_price = sum(recent_prices) / len(recent_prices)
            
            # Calculer la variation
            variation = abs(current_price - avg_price) / avg_price
            
            if variation > 0.05:  # Variation de plus de 5%
                return {
                    "type": "LARGE_PRICE_MOVEMENT",
                    "severity": "MEDIUM",
                    "description": f"Variation de {variation*100:.1f}% sur {pair}",
                    "pair": pair,
                    "current_price": current_price,
                    "average_price": avg_price,
                    "variation_percent": float(variation * 100),
                    "timestamp": datetime.now(),
                    "recommendations": [
                        "Vérifier les autres sources de prix",
                        "Surveiller les liquidations potentielles",
                        "Analyser l'impact sur les positions de levier"
                    ]
                }
        
        return None
    
    async def _check_price_deviations(
        self,
        eth_price: Dict[str, Any],
        btc_price: Dict[str, Any],
        link_price: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Vérifie les déviations importantes entre les feeds."""
        # Calculer les ratios
        eth_btc_ratio = eth_price["price"] / btc_price["price"]
        eth_link_ratio = eth_price["price"] / link_price["price"]
        
        # Vérifier les ratios historiques
        # (simplifié pour l'exemple)
        normal_eth_btc_ratio = 0.05  # 1 ETH = 0.05 BTC
        normal_eth_link_ratio = 15.0  # 1 ETH = 15 LINK
        
        eth_btc_deviation = abs(eth_btc_ratio - normal_eth_btc_ratio) / normal_eth_btc_ratio
        eth_link_deviation = abs(eth_link_ratio - normal_eth_link_ratio) / normal_eth_link_ratio
        
        if eth_btc_deviation > 0.1 or eth_link_deviation > 0.1:  # Déviation de plus de 10%
            return {
                "type": "PRICE_FEED_DEVIATION",
                "severity": "HIGH",
                "description": f"Déviation importante entre les feeds",
                "eth_btc_deviation_percent": float(eth_btc_deviation * 100),
                "eth_link_deviation_percent": float(eth_link_deviation * 100),
                "eth_price": eth_price["price"],
                "btc_price": btc_price["price"],
                "link_price": link_price["price"],
                "timestamp": datetime.now(),
                "recommendations": [
                    "Vérifier l'intégrité des feeds Chainlink",
                    "Comparer avec d'autres sources de prix",
                    "Considérer une manipulation de marché"
                ]
            }
        
        return None
    
    async def _update_price_history(
        self,
        eth_price: Dict[str, Any],
        btc_price: Dict[str, Any],
        link_price: Dict[str, Any]
    ) -> None:
        """Met à jour l'historique des prix."""
        current_time = datetime.now()
        
        # Mettre à jour ETH
        if "error" not in eth_price:
            self.price_history["ETH"].append({
                "price": eth_price["price"],
                "timestamp": current_time,
                "updated_at": eth_price["updated_at"]
            })
            
            # Garder seulement les 100 dernières valeurs
            if len(self.price_history["ETH"]) > 100:
                self.price_history["ETH"] = self.price_history["ETH"][-100:]
        
        # Mettre à jour BTC
        if "error" not in btc_price:
            self.price_history["BTC"].append({
                "price": btc_price["price"],
                "timestamp": current_time,
                "updated_at": btc_price["updated_at"]
            })
            
            if len(self.price_history["BTC"]) > 100:
                self.price_history["BTC"] = self.price_history["BTC"][-100:]
        
        # Mettre à jour LINK
        if "error" not in link_price:
            self.price_history["LINK"].append({
                "price": link_price["price"],
                "timestamp": current_time,
                "updated_at": link_price["updated_at"]
            })
            
            if len(self.price_history["LINK"]) > 100:
                self.price_history["LINK"] = self.price_history["LINK"][-100:]
    
    async def get_feed_health(self, feed_address: str) -> Dict[str, Any]:
        """Vérifie la santé d'un feed Chainlink."""
        try:
            contract = self.web3.eth.contract(
                address=feed_address,
                abi=self.feed_abi
            )
            
            # Récupérer les données
            round_data = contract.functions.latestRoundData().call()
            decimals = contract.functions.decimals().call()
            description = contract.functions.description().call()
            
            updated_at = round_data[3]
            current_time = datetime.now().timestamp()
            staleness = current_time - updated_at
            
            # Vérifier les conditions de santé
            is_healthy = True
            issues = []
            
            if staleness > 3600:  # Plus d'une heure
                is_healthy = False
                issues.append("Feed stale")
            
            if round_data[1] == 0:  # Prix à zéro
                is_healthy = False
                issues.append("Price is zero")
            
            # Vérifier la cohérence du round
            if round_data[0] != round_data[4]:
                issues.append("Round inconsistency")
            
            return {
                "feed_address": feed_address,
                "description": description,
                "decimals": decimals,
                "last_update": datetime.fromtimestamp(updated_at),
                "staleness_seconds": staleness,
                "is_healthy": is_healthy,
                "issues": issues,
                "current_round": round_data[0],
                "answered_in_round": round_data[4],
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la santé: {e}")
            return {
                "feed_address": feed_address,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    async def get_all_feeds_health(self) -> Dict[str, Any]:
        """Vérifie la santé de tous les feeds surveillés."""
        feeds = {
            "ETH/USD": self.eth_usd_feed,
            "BTC/USD": self.btc_usd_feed,
            "LINK/USD": self.link_usd_feed,
        }
        
        results = {}
        unhealthy_count = 0
        
        for pair, address in feeds.items():
            health = await self.get_feed_health(address)
            results[pair] = health
            
            if not health.get("is_healthy", True):
                unhealthy_count += 1
        
        return {
            "feeds": results,
            "total_feeds": len(feeds),
            "unhealthy_feeds": unhealthy_count,
            "health_percentage": (len(feeds) - unhealthy_count) / len(feeds) * 100,
            "timestamp": datetime.now(),
        }
    
    async def detect_oracle_manipulation(self, feed_address: str, 
                                        threshold: float = 0.1) -> Dict[str, Any]:
        """Détecte les manipulations potentielles d'oracle."""
        try:
            contract = self.web3.eth.contract(
                address=feed_address,
                abi=self.feed_abi
            )
            
            # Récupérer les données des derniers rounds
            current_round_data = contract.functions.latestRoundData().call()
            current_price = current_round_data[1]
            
            # Récupérer les données du round précédent
            # (simplifié pour l'exemple)
            previous_price = current_price * 0.95  # Simulation
            
            # Calculer la variation
            variation = abs(current_price - previous_price) / previous_price
            
            is_manipulated = variation > threshold
            
            return {
                "feed_address": feed_address,
                "current_price": float(current_price),
                "previous_price": float(previous_price),
                "variation_percent": float(variation * 100),
                "threshold_percent": threshold * 100,
                "is_manipulated": is_manipulated,
                "confidence": min(variation / threshold, 1.0),
                "timestamp": datetime.now(),
                "recommendations": [
                    "Vérifier les transactions autour du feed",
                    "Surveiller les grandes positions sur les DEX",
                    "Analyser les patterns de flash loans"
                ] if is_manipulated else []
            }
        
        except Exception as e:
            logger.error(f"Erreur lors de la détection de manipulation: {e}")
            return {
                "feed_address": feed_address,
                "error": str(e),
                "timestamp": datetime.now(),
            }