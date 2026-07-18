"""
Configuration Bitcoin pour Sigui
"""

from pydantic import BaseModel, Field
from typing import Optional, List
import os


class BitcoinConfig(BaseModel):
    """Configuration pour l'intégration Bitcoin"""
    
    # Configuration réseau
    network: str = Field(default="testnet", description="Réseau Bitcoin (mainnet, testnet, regtest)")
    rpc_host: str = Field(default="localhost", description="Hôte RPC Bitcoin Core")
    rpc_port: int = Field(default=18332, description="Port RPC Bitcoin Core")
    rpc_user: str = Field(default="", description="Utilisateur RPC")
    rpc_password: str = Field(default="", description="Mot de passe RPC")
    
    # Configuration Lightning Network
    lightning_enabled: bool = Field(default=True, description="Activer Lightning Network")
    lightning_node_host: str = Field(default="localhost", description="Hôte LND")
    lightning_node_port: int = Field(default=10009, description="Port LND")
    lightning_macaroon_path: str = Field(default="", description="Chemin vers le macaroon LND")
    lightning_tls_cert_path: str = Field(default="", description="Chemin vers le certificat TLS LND")
    
    # Configuration des frais
    fee_rate_sats_per_byte: int = Field(default=2, description="Taux de frais en satoshis par byte")
    max_fee_rate_sats_per_byte: int = Field(default=50, description="Taux de frais maximum")
    
    # Configuration des limites
    max_payment_amount_sats: int = Field(default=10000000, description="Montant maximum de paiement en satoshis")
    min_payment_amount_sats: int = Field(default=1000, description="Montant minimum de paiement en satoshis")
    
    # Configuration des webhooks
    webhook_url: Optional[str] = Field(default=None, description="URL pour les webhooks de paiement")
    
    # Configuration de surveillance
    monitor_interval_seconds: int = Field(default=30, description="Intervalle de surveillance en secondes")
    confirmations_required: int = Field(default=3, description="Nombre de confirmations requis")
    
    class Config:
        env_prefix = "BITCOIN_"
    
    @classmethod
    def from_env(cls) -> "BitcoinConfig":
        """Crée une configuration à partir des variables d'environnement"""
        return cls(
            network=os.getenv("BITCOIN_NETWORK", "testnet"),
            rpc_host=os.getenv("BITCOIN_RPC_HOST", "localhost"),
            rpc_port=int(os.getenv("BITCOIN_RPC_PORT", "18332")),
            rpc_user=os.getenv("BITCOIN_RPC_USER", ""),
            rpc_password=os.getenv("BITCOIN_RPC_PASSWORD", ""),
            lightning_enabled=os.getenv("BITCOIN_LIGHTNING_ENABLED", "true").lower() == "true",
            lightning_node_host=os.getenv("BITCOIN_LIGHTNING_NODE_HOST", "localhost"),
            lightning_node_port=int(os.getenv("BITCOIN_LIGHTNING_NODE_PORT", "10009")),
            lightning_macaroon_path=os.getenv("BITCOIN_LIGHTNING_MACAROON_PATH", ""),
            lightning_tls_cert_path=os.getenv("BITCOIN_LIGHTNING_TLS_CERT_PATH", ""),
            fee_rate_sats_per_byte=int(os.getenv("BITCOIN_FEE_RATE_SATS_PER_BYTE", "2")),
            max_fee_rate_sats_per_byte=int(os.getenv("BITCOIN_MAX_FEE_RATE_SATS_PER_BYTE", "50")),
            max_payment_amount_sats=int(os.getenv("BITCOIN_MAX_PAYMENT_AMOUNT_SATS", "10000000")),
            min_payment_amount_sats=int(os.getenv("BITCOIN_MIN_PAYMENT_AMOUNT_SATS", "1000")),
            webhook_url=os.getenv("BITCOIN_WEBHOOK_URL"),
            monitor_interval_seconds=int(os.getenv("BITCOIN_MONITOR_INTERVAL_SECONDS", "30")),
            confirmations_required=int(os.getenv("BITCOIN_CONFIRMATIONS_REQUIRED", "3")),
        )