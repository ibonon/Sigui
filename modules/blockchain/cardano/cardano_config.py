"""
Configuration Cardano pour Sigui
"""

from pydantic import BaseModel, Field
from typing import Optional, List
import os


class CardanoConfig(BaseModel):
    """Configuration pour l'intégration Cardano"""
    
    # Configuration réseau
    network: str = Field(default="preprod", description="Réseau Cardano (mainnet, preprod, preview)")
    node_host: str = Field(default="localhost", description="Hôte Cardano Node")
    node_port: int = Field(default=3001, description="Port Cardano Node")
    ogmios_host: str = Field(default="localhost", description="Hôte Ogmios")
    ogmios_port: int = Field(default=1337, description="Port Ogmios")
    
    # Configuration wallet
    wallet_mnemonic: Optional[str] = Field(default=None, description="Phrase mnémonique du wallet")
    wallet_address: Optional[str] = Field(default=None, description="Adresse principale du wallet")
    
    # Configuration Plutus
    plutus_enabled: bool = Field(default=True, description="Activer Plutus smart contracts")
    plutus_script_path: str = Field(default="", description="Chemin vers les scripts Plutus")
    plutus_validator_hash: Optional[str] = Field(default=None, description="Hash du validateur Plutus")
    
    # Configuration des frais
    min_fee_lovelace: int = Field(default=170000, description="Frais minimum en lovelace")
    max_fee_lovelace: int = Field(default=1000000, description="Frais maximum en lovelace")
    
    # Configuration des limites
    max_transaction_amount_lovelace: int = Field(default=10000000000, description="Montant maximum de transaction")
    min_transaction_amount_lovelace: int = Field(default=1000000, description="Montant minimum de transaction")
    
    # Configuration des assets
    native_assets_enabled: bool = Field(default=True, description="Activer les assets natifs")
    policy_id: Optional[str] = Field(default=None, description="Policy ID pour les assets")
    
    # Configuration de surveillance
    monitor_interval_seconds: int = Field(default=30, description="Intervalle de surveillance en secondes")
    confirmations_required: int = Field(default=15, description="Nombre de confirmations requis")
    
    # Configuration stake pool
    stake_pool_enabled: bool = Field(default=False, description="Activer la délégation stake pool")
    stake_pool_id: Optional[str] = Field(default=None, description="ID du stake pool")
    
    class Config:
        env_prefix = "CARDANO_"
    
    @classmethod
    def from_env(cls) -> "CardanoConfig":
        """Crée une configuration à partir des variables d'environnement"""
        return cls(
            network=os.getenv("CARDANO_NETWORK", "preprod"),
            node_host=os.getenv("CARDANO_NODE_HOST", "localhost"),
            node_port=int(os.getenv("CARDANO_NODE_PORT", "3001")),
            ogmios_host=os.getenv("CARDANO_OGMIOS_HOST", "localhost"),
            ogmios_port=int(os.getenv("CARDANO_OGMIOS_PORT", "1337")),
            wallet_mnemonic=os.getenv("CARDANO_WALLET_MNEMONIC"),
            wallet_address=os.getenv("CARDANO_WALLET_ADDRESS"),
            plutus_enabled=os.getenv("CARDANO_PLUTUS_ENABLED", "true").lower() == "true",
            plutus_script_path=os.getenv("CARDANO_PLUTUS_SCRIPT_PATH", ""),
            plutus_validator_hash=os.getenv("CARDANO_PLUTUS_VALIDATOR_HASH"),
            min_fee_lovelace=int(os.getenv("CARDANO_MIN_FEE_LOVELACE", "170000")),
            max_fee_lovelace=int(os.getenv("CARDANO_MAX_FEE_LOVELACE", "1000000")),
            max_transaction_amount_lovelace=int(os.getenv("CARDANO_MAX_TRANSACTION_AMOUNT_LOVELACE", "10000000000")),
            min_transaction_amount_lovelace=int(os.getenv("CARDANO_MIN_TRANSACTION_AMOUNT_LOVELACE", "1000000")),
            native_assets_enabled=os.getenv("CARDANO_NATIVE_ASSETS_ENABLED", "true").lower() == "true",
            policy_id=os.getenv("CARDANO_POLICY_ID"),
            monitor_interval_seconds=int(os.getenv("CARDANO_MONITOR_INTERVAL_SECONDS", "30")),
            confirmations_required=int(os.getenv("CARDANO_CONFIRMATIONS_REQUIRED", "15")),
            stake_pool_enabled=os.getenv("CARDANO_STAKE_POOL_ENABLED", "false").lower() == "true",
            stake_pool_id=os.getenv("CARDANO_STAKE_POOL_ID"),
        )