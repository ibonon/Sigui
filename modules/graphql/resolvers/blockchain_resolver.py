"""
Resolvers GraphQL pour les fonctionnalités blockchain.
Inclut les oracles cross-chain, token et staking.
"""

import strawberry
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...blockchain.cross_chain_manager import CrossChainManager
from ...blockchain.token import SiguiTokenClient
from ...blockchain.staking import StakingPoolClient
from ..schema import (
    ChainStatus,
    CrossChainAlert,
    AddressRiskScore,
    TokenBalance,
    StakingNode,
    StakingReward,
    ChainStatusInput,
    AddressRiskInput,
    TokenTransferInput,
    StakeInput,
    UnstakeInput,
    DistributeRewardsInput,
)


class BlockchainResolver:
    """Resolvers pour les fonctionnalités blockchain."""
    
    def __init__(self):
        self.cross_chain_manager = CrossChainManager()
        self.token_client = SiguiTokenClient()
        self.staking_client = StakingPoolClient()
    
    # Cross-Chain Resolvers
    
    @strawberry.field
    async def chain_status(
        self,
        input: Optional[ChainStatusInput] = None,
    ) -> List[ChainStatus]:
        """Récupère le statut de toutes les chaînes surveillées."""
        status_data = await self.cross_chain_manager.get_chain_status()
        
        chain_statuses = []
        for chain_name, status in status_data.items():
            chain_statuses.append(
                ChainStatus(
                    chain=chain_name,
                    connected=status.get("connected", False),
                    latest_block=status.get("latest_block", 0),
                    monitored_contracts=status.get("monitored_contracts", 0),
                    active=status.get("active", False),
                    error=status.get("error"),
                )
            )
        
        return chain_statuses
    
    @strawberry.field
    async def address_risk_score(
        self,
        input: AddressRiskInput,
    ) -> AddressRiskScore:
        """Calcule le score de risque d'une adresse sur plusieurs chaînes."""
        results = await self.cross_chain_manager.get_address_risk_across_chains(
            input.addresses
        )
        
        # Extraire les scores par chaîne
        chain_scores = {}
        for chain_name, result in results.items():
            if chain_name != "global":
                chain_scores[chain_name] = {
                    "risk_score": result.get("risk_score", 0.5),
                    "transaction_count": result.get("transaction_count", 0),
                    "balance": result.get("balance_eth") or result.get("balance_sol") or result.get("balance_atom", 0),
                    "last_active": result.get("last_active"),
                }
        
        global_result = results.get("global", {})
        
        return AddressRiskScore(
            addresses=input.addresses,
            global_risk_score=global_result.get("average_risk_score", 0.5),
            highest_risk_chain=global_result.get("highest_risk_chain"),
            chain_scores=chain_scores,
            chain_count=global_result.get("chain_count", 0),
            timestamp=datetime.now(),
        )
    
    @strawberry.field
    async def start_cross_chain_monitoring(self) -> bool:
        """Démarre la surveillance cross-chain."""
        try:
            asyncio.create_task(self.cross_chain_manager.start_monitoring())
            return True
        except Exception as e:
            print(f"Erreur lors du démarrage de la surveillance: {e}")
            return False
    
    @strawberry.field
    async def stop_cross_chain_monitoring(self) -> bool:
        """Arrête la surveillance cross-chain."""
        try:
            await self.cross_chain_manager.stop_monitoring()
            return True
        except Exception as e:
            print(f"Erreur lors de l'arrêt de la surveillance: {e}")
            return False
    
    @strawberry.field
    async def recent_cross_chain_alerts(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[CrossChainAlert]:
        """Récupère les alertes cross-chain récentes."""
        # À implémenter avec la base de données
        return []
    
    # Token Resolvers
    
    @strawberry.field
    async def token_balance(
        self,
        address: str,
    ) -> TokenBalance:
        """Récupère le solde de token SGT d'une adresse."""
        try:
            balance = await self.token_client.get_balance(address)
            return TokenBalance(
                address=address,
                balance=balance,
                symbol="SGT",
                decimals=18,
                last_updated=datetime.now(),
            )
        except Exception as e:
            print(f"Erreur lors de la récupération du solde: {e}")
            return TokenBalance(
                address=address,
                balance=0.0,
                symbol="SGT",
                decimals=18,
                last_updated=datetime.now(),
                error=str(e),
            )
    
    @strawberry.field
    async def transfer_token(
        self,
        input: TokenTransferInput,
    ) -> Dict[str, Any]:
        """Effectue un transfert de token SGT."""
        try:
            success = await self.token_client.transfer(
                input.to_address,
                input.amount,
                input.from_address,
            )
            
            return {
                "success": success,
                "transaction_hash": "simulated_tx_hash",
                "from": input.from_address,
                "to": input.to_address,
                "amount": input.amount,
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors du transfert: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    @strawberry.field
    async def mint_skill_nft(
        self,
        skill_id: str,
        author: str,
        price: float,
    ) -> Dict[str, Any]:
        """Mint un NFT de skill."""
        try:
            success = await self.token_client.mint_skill_nft(
                skill_id,
                author,
                price,
            )
            
            return {
                "success": success,
                "skill_id": skill_id,
                "author": author,
                "price": price,
                "nft_id": f"nft_{skill_id}",
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors du minting: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    @strawberry.field
    async def token_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du token SGT."""
        try:
            total_supply = await self.token_client.get_total_supply()
            
            return {
                "total_supply": total_supply,
                "symbol": "SGT",
                "decimals": 18,
                "contract_address": self.token_client.contract_address,
                "last_updated": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors de la récupération des métriques: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    # Staking Resolvers
    
    @strawberry.field
    async def register_staking_node(
        self,
        node_id: str,
        operator_address: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Enregistre un nouveau nœud de staking."""
        try:
            success = await self.staking_client.register_node(
                node_id,
                operator_address,
                metadata or {},
            )
            
            return {
                "success": success,
                "node_id": node_id,
                "operator_address": operator_address,
                "metadata": metadata,
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors de l'enregistrement: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    @strawberry.field
    async def stake_tokens(
        self,
        input: StakeInput,
    ) -> Dict[str, Any]:
        """Stake des tokens SGT sur un nœud."""
        try:
            success = await self.staking_client.stake(
                input.node_id,
                input.amount,
                input.staker_address,
            )
            
            return {
                "success": success,
                "node_id": input.node_id,
                "staker_address": input.staker_address,
                "amount": input.amount,
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors du staking: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    @strawberry.field
    async def unstake_tokens(
        self,
        input: UnstakeInput,
    ) -> Dict[str, Any]:
        """Unstake des tokens SGT d'un nœud."""
        try:
            success = await self.staking_client.unstake(
                input.node_id,
                input.amount,
                input.staker_address,
            )
            
            return {
                "success": success,
                "node_id": input.node_id,
                "staker_address": input.staker_address,
                "amount": input.amount,
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors de l'unstaking: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    @strawberry.field
    async def calculate_staking_rewards(
        self,
        node_id: str,
        staker_address: str,
    ) -> StakingReward:
        """Calcule les récompenses de staking."""
        try:
            rewards = await self.staking_client.calculate_rewards(
                node_id,
                staker_address,
            )
            
            return StakingReward(
                node_id=node_id,
                staker_address=staker_address,
                rewards=rewards,
                last_calculated=datetime.now(),
                period_days=7,  # Période hebdomadaire
            )
        
        except Exception as e:
            print(f"Erreur lors du calcul des récompenses: {e}")
            return StakingReward(
                node_id=node_id,
                staker_address=staker_address,
                rewards=0.0,
                last_calculated=datetime.now(),
                period_days=7,
                error=str(e),
            )
    
    @strawberry.field
    async def distribute_staking_rewards(
        self,
        input: DistributeRewardsInput,
    ) -> Dict[str, Any]:
        """Distribue les récompenses de staking."""
        try:
            success = await self.staking_client.distribute_rewards(
                input.node_id,
                input.period_days,
            )
            
            return {
                "success": success,
                "node_id": input.node_id,
                "period_days": input.period_days,
                "total_distributed": "simulated_amount",
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors de la distribution: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    @strawberry.field
    async def staking_nodes(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[StakingNode]:
        """Liste les nœuds de staking."""
        try:
            # À implémenter avec la base de données
            nodes = []
            
            # Exemple de données simulées
            if offset == 0:
                nodes.append(
                    StakingNode(
                        id="node_001",
                        operator_address="0x123...",
                        total_staked=1000000.0,
                        active_stakers=50,
                        uptime_percentage=99.8,
                        created_at=datetime.now() - timedelta(days=30),
                        last_updated=datetime.now(),
                        metadata={"location": "Paris", "hardware": "MI300X"},
                    )
                )
            
            return nodes
        
        except Exception as e:
            print(f"Erreur lors de la récupération des nœuds: {e}")
            return []
    
    @strawberry.field
    async def staking_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du staking."""
        try:
            total_staked = await self.staking_client.get_total_staked()
            active_nodes = await self.staking_client.get_active_node_count()
            
            return {
                "total_staked": total_staked,
                "active_nodes": active_nodes,
                "apy_percentage": 12.5,  # APY annuel
                "total_rewards_distributed": 250000.0,
                "last_distribution": datetime.now() - timedelta(days=1),
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors de la récupération des métriques: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now(),
            }
    
    @strawberry.field
    async def slash_node(
        self,
        node_id: str,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Slash un nœud pour mauvaise conduite."""
        try:
            success = await self.staking_client.slash_node(
                node_id,
                reason,
                evidence or {},
            )
            
            return {
                "success": success,
                "node_id": node_id,
                "reason": reason,
                "slash_amount": "simulated_amount",
                "timestamp": datetime.now(),
            }
        
        except Exception as e:
            print(f"Erreur lors du slashing: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now(),
            }