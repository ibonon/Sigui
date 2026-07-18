"""
Tracker de collatéral cross-chain pour Sigui
"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging

from .credit_config import CreditConfig, CollateralType
from ..blockchain.bitcoin.bitcoin_adapter import BitcoinAdapter
from ..blockchain.cardano.cardano_adapter import CardanoAdapter


logger = logging.getLogger(__name__)


@dataclass
class CollateralAsset:
    """Asset utilisé comme collatéral"""
    asset_id: str
    owner_did: str
    collateral_type: CollateralType
    amount: float
    value_usd: float
    locked_at: int
    loan_id: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class CollateralPosition:
    """Position de collatéral pour un utilisateur"""
    owner_did: str
    total_value_usd: float
    assets: List[CollateralAsset]
    health_ratio: float  # Ratio valeur collatéral / valeur prêt
    last_updated: int


class CollateralTracker:
    """Tracker pour gérer le collatéral cross-chain"""
    
    def __init__(self, config: CreditConfig,
                 bitcoin_adapter: Optional[BitcoinAdapter] = None,
                 cardano_adapter: Optional[CardanoAdapter] = None):
        self.config = config
        self.bitcoin_adapter = bitcoin_adapter
        self.cardano_adapter = cardano_adapter
        
        self._collateral_assets: Dict[str, CollateralAsset] = {}  # asset_id -> asset
        self._owner_assets: Dict[str, Set[str]] = {}  # owner_did -> set of asset_ids
        self._loan_collateral: Dict[str, Set[str]] = {}  # loan_id -> set of asset_ids
        
        self._monitoring_tasks: List[asyncio.Task] = []
        self._price_cache: Dict[str, float] = {}
        self._price_cache_ttl = 300  # 5 minutes
    
    async def initialize(self) -> bool:
        """Initialise le tracker de collatéral"""
        try:
            if not self.config.enabled:
                logger.warning("Système de crédit désactivé")
                return False
            
            # Démarre la surveillance des prix
            await self._start_price_monitoring()
            
            # Démarre la surveillance de la santé du collatéral
            await self._start_health_monitoring()
            
            logger.info("Tracker de collatéral initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation tracker collatéral: {e}")
            return False
    
    async def lock_collateral(self, owner_did: str, collateral_type: CollateralType,
                             amount: float, loan_id: str,
                             metadata: Optional[Dict] = None) -> Optional[CollateralAsset]:
        """Verrouille un asset comme collatéral pour un prêt"""
        try:
            # Vérifie que le type est supporté
            if collateral_type.value not in [ct.value for ct in self.config.collateral_requirements.keys()]:
                raise ValueError(f"Type de collatéral non supporté: {collateral_type}")
            
            # Récupère le prix actuel
            price_usd = await self._get_asset_price(collateral_type)
            if price_usd <= 0:
                raise ValueError(f"Prix invalide pour {collateral_type}: {price_usd}")
            
            # Calcule la valeur
            value_usd = amount * price_usd
            
            # Crée l'asset
            asset_id = f"collateral_{collateral_type.value}_{int(time.time())}_{owner_did[:8]}"
            asset = CollateralAsset(
                asset_id=asset_id,
                owner_did=owner_did,
                collateral_type=collateral_type,
                amount=amount,
                value_usd=value_usd,
                locked_at=int(time.time()),
                loan_id=loan_id,
                metadata=metadata
            )
            
            # Enregistre l'asset
            self._collateral_assets[asset_id] = asset
            
            # Met à jour les index
            if owner_did not in self._owner_assets:
                self._owner_assets[owner_did] = set()
            self._owner_assets[owner_did].add(asset_id)
            
            if loan_id not in self._loan_collateral:
                self._loan_collateral[loan_id] = set()
            self._loan_collateral[loan_id].add(asset_id)
            
            logger.info(f"Collatéral verrouillé: {asset_id} - {value_usd} USD pour prêt {loan_id}")
            return asset
            
        except Exception as e:
            logger.error(f"Erreur verrouillage collatéral: {e}")
            return None
    
    async def unlock_collateral(self, asset_id: str) -> bool:
        """Déverrouille un collatéral"""
        try:
            if asset_id not in self._collateral_assets:
                raise ValueError(f"Asset {asset_id} non trouvé")
            
            asset = self._collateral_assets[asset_id]
            
            # Retire des index
            if asset.owner_did in self._owner_assets:
                self._owner_assets[asset.owner_did].discard(asset_id)
                if not self._owner_assets[asset.owner_did]:
                    del self._owner_assets[asset.owner_did]
            
            if asset.loan_id and asset.loan_id in self._loan_collateral:
                self._loan_collateral[asset.loan_id].discard(asset_id)
                if not self._loan_collateral[asset.loan_id]:
                    del self._loan_collateral[asset.loan_id]
            
            # Retire l'asset
            del self._collateral_assets[asset_id]
            
            logger.info(f"Collatéral déverrouillé: {asset_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur déverrouillage collatéral: {e}")
            return False
    
    async def get_collateral_position(self, owner_did: str) -> Optional[CollateralPosition]:
        """Récupère la position de collatéral d'un utilisateur"""
        try:
            if owner_did not in self._owner_assets:
                return None
            
            asset_ids = self._owner_assets[owner_did]
            assets = []
            total_value = 0.0
            
            for asset_id in asset_ids:
                if asset_id in self._collateral_assets:
                    asset = self._collateral_assets[asset_id]
                    assets.append(asset)
                    total_value += asset.value_usd
            
            # Calcule le ratio de santé (simplifié)
            # Dans une vraie implémentation, on utiliserait la valeur des prêts en cours
            health_ratio = 2.0 if total_value > 0 else 0.0  # Exemple
            
            return CollateralPosition(
                owner_did=owner_did,
                total_value_usd=total_value,
                assets=assets,
                health_ratio=health_ratio,
                last_updated=int(time.time())
            )
            
        except Exception as e:
            logger.error(f"Erreur récupération position collatéral: {e}")
            return None
    
    async def get_loan_collateral(self, loan_id: str) -> List[CollateralAsset]:
        """Récupère les collatéraux associés à un prêt"""
        try:
            if loan_id not in self._loan_collateral:
                return []
            
            assets = []
            for asset_id in self._loan_collateral[loan_id]:
                if asset_id in self._collateral_assets:
                    assets.append(self._collateral_assets[asset_id])
            
            return assets
            
        except Exception as e:
            logger.error(f"Erreur récupération collatéral prêt: {e}")
            return []
    
    async def calculate_health_ratio(self, loan_id: str, loan_amount_usd: float) -> float:
        """Calcule le ratio de santé pour un prêt"""
        try:
            collateral_assets = await self.get_loan_collateral(loan_id)
            if not collateral_assets:
                return 0.0
            
            # Met à jour les valeurs
            updated_assets = []
            total_value = 0.0
            
            for asset in collateral_assets:
                # Met à jour le prix
                current_price = await self._get_asset_price(asset.collateral_type)
                current_value = asset.amount * current_price
                
                updated_asset = CollateralAsset(
                    asset_id=asset.asset_id,
                    owner_did=asset.owner_did,
                    collateral_type=asset.collateral_type,
                    amount=asset.amount,
                    value_usd=current_value,
                    locked_at=asset.locked_at,
                    loan_id=asset.loan_id,
                    metadata=asset.metadata
                )
                
                updated_assets.append(updated_asset)
                total_value += current_value
            
            # Met à jour le cache
            for asset in updated_assets:
                self._collateral_assets[asset.asset_id] = asset
            
            # Calcule le ratio
            if loan_amount_usd <= 0:
                return float('inf')
            
            health_ratio = total_value / loan_amount_usd
            return health_ratio
            
        except Exception as e:
            logger.error(f"Erreur calcul ratio santé: {e}")
            return 0.0
    
    async def check_liquidation_risk(self, loan_id: str, loan_amount_usd: float) -> Tuple[bool, float]:
        """Vérifie le risque de liquidation"""
        try:
            health_ratio = await self.calculate_health_ratio(loan_id, loan_amount_usd)
            
            # Vérifie si le ratio est en dessous du seuil de liquidation
            at_risk = health_ratio < self.config.liquidation_threshold
            
            return at_risk, health_ratio
            
        except Exception as e:
            logger.error(f"Erreur vérification risque liquidation: {e}")
            return True, 0.0  # En cas d'erreur, considère comme à risque
    
    async def _get_asset_price(self, collateral_type: CollateralType) -> float:
        """Récupère le prix d'un asset"""
        try:
            cache_key = f"price_{collateral_type.value}"
            current_time = time.time()
            
            # Vérifie le cache
            if cache_key in self._price_cache:
                price, timestamp = self._price_cache[cache_key]
                if current_time - timestamp < self._price_cache_ttl:
                    return price
            
            # Récupère le prix depuis l'oracle (implémentation simplifiée)
            price = await self._fetch_price_from_oracle(collateral_type)
            
            # Met en cache
            self._price_cache[cache_key] = (price, current_time)
            
            return price
            
        except Exception as e:
            logger.error(f"Erreur récupération prix: {e}")
            # Prix par défaut selon le type
            default_prices = {
                CollateralType.BITCOIN: 60000.0,
                CollateralType.ETHEREUM: 3000.0,
                CollateralType.CARDANO: 0.5,
                CollateralType.POLKADOT: 7.0,
                CollateralType.REAL_ESTATE: 1.0,  # Placeholder
                CollateralType.STOCKS: 1.0,  # Placeholder
                CollateralType.BONDS: 1.0  # Placeholder
            }
            return default_prices.get(collateral_type, 0.0)
    
    async def _fetch_price_from_oracle(self, collateral_type: CollateralType) -> float:
        """Récupère le prix depuis un oracle externe"""
        # Implémentation simplifiée
        # Dans une vraie implémentation, on appellerait CoinGecko, CoinMarketCap, etc.
        
        import random
        
        # Prix de base avec une petite variation aléatoire
        base_prices = {
            CollateralType.BITCOIN: 60000.0,
            CollateralType.ETHEREUM: 3000.0,
            CollateralType.CARDANO: 0.5,
            CollateralType.POLKADOT: 7.0
        }
        
        base_price = base_prices.get(collateral_type, 1.0)
        
        # Ajoute une variation aléatoire de ±2%
        variation = random.uniform(-0.02, 0.02)
        price = base_price * (1 + variation)
        
        return max(price, 0.01)  # Minimum 0.01 USD
    
    async def _start_price_monitoring(self):
        """Démarre la surveillance des prix"""
        async def monitor_prices():
            while True:
                try:
                    # Met à jour les prix pour tous les types supportés
                    for collateral_type in self.config.collateral_requirements.keys():
                        await self._get_asset_price(collateral_type)
                    
                    await asyncio.sleep(60)  # Met à jour toutes les minutes
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance prix: {e}")
                    await asyncio.sleep(30)
        
        task = asyncio.create_task(monitor_prices())
        self._monitoring_tasks.append(task)
    
    async def _start_health_monitoring(self):
        """Démarre la surveillance de la santé du collatéral"""
        async def monitor_health():
            while True:
                try:
                    # Vérifie tous les prêts actifs
                    for loan_id in list(self._loan_collateral.keys()):
                        # Récupère le montant du prêt (simplifié)
                        loan_amount = 10000.0  # Exemple
                        
                        at_risk, health_ratio = await self.check_liquidation_risk(loan_id, loan_amount)
                        
                        if at_risk:
                            logger.warning(f"Prêt {loan_id} à risque de liquidation: ratio={health_ratio:.2f}")
                        
                        # Met à jour les valeurs des assets
                        await self.calculate_health_ratio(loan_id, loan_amount)
                    
                    await asyncio.sleep(300)  # Vérifie toutes les 5 minutes
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance santé: {e}")
                    await asyncio.sleep(60)
        
        task = asyncio.create_task(monitor_health())
        self._monitoring_tasks.append(task)
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._collateral_assets.clear()
        self._owner_assets.clear()
        self._loan_collateral.clear()
        self._price_cache.clear()