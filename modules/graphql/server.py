"""
Serveur GraphQL principal pour Sigui.
Intègre tous les resolvers et fournit une API unifiée.
"""

import strawberry
import asyncio
import logging
import json
import numpy as np
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime, timedelta
from strawberry.fastapi import GraphQLRouter
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

from .schema import (
    Query,
    Mutation,
    Subscription,
    Agent,
    Transaction,
    Verdict,
    Threat,
    Skill,
    Node,
    Proposal,
    SimulationResult,
    ZKProof,
    FHEAnalysis,
    AgentInput,
    TransactionInput,
    VerdictInput,
    ThreatInput,
    SkillInput,
    NodeInput,
    ProposalInput,
    SimulationInput,
    ZKProofInput,
    FHEAnalysisInput,
)
from .resolvers.marketplace_resolver import MarketplaceResolver
from .resolvers.security_resolver import SecurityResolver
from .resolvers.blockchain_resolver import BlockchainResolver
from ...modules.database.agent_repository import AgentRepository
from ...modules.database.transaction_repository import TransactionRepository
from ...modules.database.threat_repository import ThreatRepository
from ...modules.database.marketplace import MarketplaceRepository
from ...modules.integrations.aave_integration import AaveIntegration
from ...modules.integrations.chainlink_integration import ChainlinkIntegration
from ...modules.integrations.uniswap_integration import UniswapIntegration
from ...modules.integrations.compound_integration import CompoundIntegration
from ...modules.integrations.makerdao_integration import MakerDAOIntegration


class SiguiGraphQLServer:
    """Serveur GraphQL principal."""
    
    def __init__(self):
        # Initialiser les repositories
        self.agent_repo = AgentRepository()
        self.transaction_repo = TransactionRepository()
        self.threat_repo = ThreatRepository()
        self.marketplace_repo = MarketplaceRepository()
        
        # Initialiser les resolvers
        self.marketplace_resolver = MarketplaceResolver()
        self.security_resolver = SecurityResolver()
        self.blockchain_resolver = BlockchainResolver()
        
        # Initialiser les intégrations ecosystemiques
        self.aave_integration = AaveIntegration()
        self.chainlink_integration = ChainlinkIntegration()
        self.uniswap_integration = UniswapIntegration()
        self.compound_integration = CompoundIntegration()
        self.makerdao_integration = MakerDAOIntegration()
        
        # WebSocket connections pour les subscriptions
        self.websocket_connections = []
        
        # Créer le schéma GraphQL
        self.schema = strawberry.Schema(
            query=self._create_query(),
            mutation=self._create_mutation(),
            subscription=self._create_subscription(),
        )
        
        # Créer le router FastAPI
        self.router = GraphQLRouter(
            self.schema,
            graphiql=True,
            websocket_enabled=True,
        )
        
        logger.info("Serveur GraphQL Sigui initialisé")
    
    def _create_query(self) -> type:
        """Crée la classe Query avec tous les resolvers."""
        
        @strawberry.type
        class SiguiQuery:
            # Agents
            @strawberry.field
            async def agent(self, did: str) -> Optional[Agent]:
                agent_data = await self.agent_repo.get_by_did(did)
                if not agent_data:
                    return None
                
                return Agent(
                    did=agent_data["did"],
                    address=agent_data["address"],
                    reputation_score=agent_data["reputation_score"],
                    verification_tier=agent_data["verification_tier"],
                    total_transactions=agent_data["total_transactions"],
                    total_volume_usd=agent_data["total_volume_usd"],
                    threat_count=agent_data["threat_count"],
                    created_at=agent_data["created_at"],
                    last_active=agent_data["last_active"],
                    metadata=agent_data["metadata"],
                )
            
            @strawberry.field
            async def agents(
                self,
                limit: int = 100,
                offset: int = 0,
                min_reputation: Optional[float] = None,
                tier: Optional[str] = None,
            ) -> List[Agent]:
                agents_data = await self.agent_repo.list(
                    limit=limit,
                    offset=offset,
                    min_reputation=min_reputation,
                    tier=tier,
                )
                
                return [
                    Agent(
                        did=agent["did"],
                        address=agent["address"],
                        reputation_score=agent["reputation_score"],
                        verification_tier=agent["verification_tier"],
                        total_transactions=agent["total_transactions"],
                        total_volume_usd=agent["total_volume_usd"],
                        threat_count=agent["threat_count"],
                        created_at=agent["created_at"],
                        last_active=agent["last_active"],
                        metadata=agent["metadata"],
                    )
                    for agent in agents_data
                ]
            
            # Transactions
            @strawberry.field
            async def transaction(self, hash: str) -> Optional[Transaction]:
                tx_data = await self.transaction_repo.get_by_hash(hash)
                if not tx_data:
                    return None
                
                return Transaction(
                    hash=tx_data["hash"],
                    from_address=tx_data["from_address"],
                    to_address=tx_data["to_address"],
                    amount=tx_data["amount"],
                    currency=tx_data["currency"],
                    timestamp=tx_data["timestamp"],
                    status=tx_data["status"],
                    gas_used=tx_data["gas_used"],
                    gas_price=tx_data["gas_price"],
                    block_number=tx_data["block_number"],
                    metadata=tx_data["metadata"],
                )
            
            @strawberry.field
            async def transactions(
                self,
                limit: int = 100,
                offset: int = 0,
                from_address: Optional[str] = None,
                to_address: Optional[str] = None,
                min_amount: Optional[float] = None,
                status: Optional[str] = None,
            ) -> List[Transaction]:
                txs_data = await self.transaction_repo.list(
                    limit=limit,
                    offset=offset,
                    from_address=from_address,
                    to_address=to_address,
                    min_amount=min_amount,
                    status=status,
                )
                
                return [
                    Transaction(
                        hash=tx["hash"],
                        from_address=tx["from_address"],
                        to_address=tx["to_address"],
                        amount=tx["amount"],
                        currency=tx["currency"],
                        timestamp=tx["timestamp"],
                        status=tx["status"],
                        gas_used=tx["gas_used"],
                        gas_price=tx["gas_price"],
                        block_number=tx["block_number"],
                        metadata=tx["metadata"],
                    )
                    for tx in txs_data
                ]
            
            # Threats
            @strawberry.field
            async def threat(self, id: str) -> Optional[Threat]:
                threat_data = await self.threat_repo.get_by_id(id)
                if not threat_data:
                    return None
                
                return Threat(
                    id=threat_data["id"],
                    type=threat_data["type"],
                    severity=threat_data["severity"],
                    description=threat_data["description"],
                    source=threat_data["source"],
                    target=threat_data["target"],
                    detected_at=threat_data["detected_at"],
                    resolved_at=threat_data["resolved_at"],
                    status=threat_data["status"],
                    evidence=threat_data["evidence"],
                    recommendations=threat_data["recommendations"],
                )
            
            @strawberry.field
            async def threats(
                self,
                limit: int = 100,
                offset: int = 0,
                type: Optional[str] = None,
                severity: Optional[str] = None,
                status: Optional[str] = None,
                min_date: Optional[datetime] = None,
                max_date: Optional[datetime] = None,
            ) -> List[Threat]:
                threats_data = await self.threat_repo.list(
                    limit=limit,
                    offset=offset,
                    type=type,
                    severity=severity,
                    status=status,
                    min_date=min_date,
                    max_date=max_date,
                )
                
                return [
                    Threat(
                        id=threat["id"],
                        type=threat["type"],
                        severity=threat["severity"],
                        description=threat["description"],
                    source=threat["source"],
                    target=threat["target"],
                    detected_at=threat["detected_at"],
                    resolved_at=threat["resolved_at"],
                    status=threat["status"],
                    evidence=threat["evidence"],
                    recommendations=threat["recommendations"],
                    )
                    for threat in threats_data
                ]
            
            # Marketplace
            @strawberry.field
            async def skill(self, id: str) -> Optional[Skill]:
                return await self.marketplace_resolver.skill(id)
            
            @strawberry.field
            async def skills(
                self,
                query: Optional[str] = None,
                category: Optional[str] = None,
                min_rating: Optional[float] = None,
                max_price: Optional[float] = None,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Skill]:
                return await self.marketplace_resolver.skills(
                    query, category, min_rating, max_price, limit, offset
                )
            
            # Security
            @strawberry.field
            async def attack_scenario(self, id: str) -> Optional[Any]:
                return await self.security_resolver.attack_scenario(id)
            
            @strawberry.field
            async def attack_scenarios(
                self,
                chain: Optional[str] = None,
                severity: Optional[str] = None,
                attack_type: Optional[str] = None,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Any]:
                return await self.security_resolver.attack_scenarios(
                    chain, severity, attack_type, limit, offset
                )
            
            @strawberry.field
            async def simulation(self, id: str) -> Optional[Any]:
                return await self.security_resolver.simulation(id)
            
            @strawberry.field
            async def simulations(
                self,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Any]:
                return await self.security_resolver.simulations(limit, offset)
            
            @strawberry.field
            async def security_metrics(self) -> Dict[str, Any]:
                return await self.security_resolver.security_metrics()
            
            # ZK-Proofs
            @strawberry.field
            async def zk_proof(self, id: str) -> Optional[Any]:
                return await self.security_resolver.zk_proof(id)
            
            @strawberry.field
            async def zk_proofs(
                self,
                type: Optional[str] = None,
                verified: Optional[bool] = None,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Any]:
                return await self.security_resolver.zk_proofs(
                    type, verified, limit, offset
                )
            
            @strawberry.field
            async def zk_system_metrics(self) -> Dict[str, Any]:
                return await self.security_resolver.zk_system_metrics()
            
            # FHE
            @strawberry.field
            async def fhe_key_pair(self, id: str) -> Optional[Any]:
                return await self.security_resolver.fhe_key_pair(id)
            
            @strawberry.field
            async def fhe_key_pairs(
                self,
                active_only: bool = True,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Any]:
                return await self.security_resolver.fhe_key_pairs(
                    active_only, limit, offset
                )
            
            @strawberry.field
            async def fhe_ciphertext(self, id: str) -> Optional[Any]:
                return await self.security_resolver.fhe_ciphertext(id)
            
            @strawberry.field
            async def fhe_ciphertexts(
                self,
                key_id: Optional[str] = None,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Any]:
                return await self.security_resolver.fhe_ciphertexts(
                    key_id, limit, offset
                )
            
            @strawberry.field
            async def fhe_operation_result(self, id: str) -> Optional[Any]:
                return await self.security_resolver.fhe_operation_result(id)
            
            @strawberry.field
            async def fhe_operations(
                self,
                verified_only: bool = False,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Any]:
                return await self.security_resolver.fhe_operations(
                    verified_only, limit, offset
                )
            
            @strawberry.field
            async def fhe_system_metrics(self) -> Dict[str, Any]:
                return await self.security_resolver.fhe_system_metrics()
            
            # Blockchain
            @strawberry.field
            async def chain_status(self, input: Optional[Any] = None) -> List[Any]:
                return await self.blockchain_resolver.chain_status(input)
            
            @strawberry.field
            async def address_risk_score(self, input: Any) -> Any:
                return await self.blockchain_resolver.address_risk_score(input)
            
            @strawberry.field
            async def token_balance(self, address: str) -> Any:
                return await self.blockchain_resolver.token_balance(address)
            
            @strawberry.field
            async def token_metrics(self) -> Dict[str, Any]:
                return await self.blockchain_resolver.token_metrics()
            
            @strawberry.field
            async def staking_nodes(
                self,
                active_only: bool = True,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Any]:
                return await self.blockchain_resolver.staking_nodes(
                    active_only, limit, offset
                )
            
            @strawberry.field
            async def staking_metrics(self) -> Dict[str, Any]:
                return await self.blockchain_resolver.staking_metrics()
            
            # Intégrations Ecosystemiques
            @strawberry.field
            async def aave_flash_loan_alerts(
                self,
                limit: int = 100,
                offset: int = 0,
            ) -> List[Dict[str, Any]]:
                # Récupérer les alertes flash loan récentes
                alerts = []
                # À implémenter avec les données réelles
                return alerts
            
            @strawberry.field
            async def uniswap_pool_health(
                self,
                pool_address: Optional[str] = None,
            ) -> Dict[str, Any]:
                if pool_address:
                    return await self.uniswap_integration.get_pool_health(pool_address)
                else:
                    # Retourner la santé de tous les pools
                    return {
                        "overall_health": 85.0,
                        "pools": [
                            {"address": "0xB4e16d0168e52d35CaCD2c6185b44281Ec28C9Dc", "health_score": 90.0},
                            {"address": "0x0d4a11d5EEaaC28EC3F61d100daF4d40471f1852", "health_score": 80.0},
                        ]
                    }
            
            @strawberry.field
            async def compound_market_health(
                self,
                market: Optional[str] = None,
            ) -> Dict[str, Any]:
                if market:
                    # Convertir le string en enum
                    market_enum = None
                    for m in self.compound_integration.markets.keys():
                        if m.value == market:
                            market_enum = m
                            break
                    
                    if market_enum:
                        return await self.compound_integration.get_market_health(market_enum)
                
                # Retourner le rapport complet des risques
                return await self.compound_integration.get_risk_report()
            
            @strawberry.field
            async def makerdao_system_health(self) -> Dict[str, Any]:
                return await self.makerdao_integration.get_system_health()
            
            @strawberry.field
            async def chainlink_price_feeds(
                self,
                feed_address: Optional[str] = None,
            ) -> Dict[str, Any]:
                # À implémenter avec les données réelles
                return {
                    "feeds": [
                        {
                            "address": "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
                            "pair": "ETH/USD",
                            "price": 2000.0,
                            "deviation": 0.02,
                            "last_update": datetime.now().isoformat(),
                        }
                    ]
                }
        
        return SiguiQuery
    
    def _create_mutation(self) -> type:
        """Crée la classe Mutation avec tous les resolvers."""
        
        @strawberry.type
        class SiguiMutation:
            # Agents
            @strawberry.mutation
            async def create_agent(self, input: AgentInput) -> Agent:
                agent_id = await self.agent_repo.create(input.__dict__)
                agent_data = await self.agent_repo.get_by_did(agent_id)
                
                return Agent(
                    did=agent_data["did"],
                    address=agent_data["address"],
                    reputation_score=agent_data["reputation_score"],
                    verification_tier=agent_data["verification_tier"],
                    total_transactions=agent_data["total_transactions"],
                    total_volume_usd=agent_data["total_volume_usd"],
                    threat_count=agent_data["threat_count"],
                    created_at=agent_data["created_at"],
                    last_active=agent_data["last_active"],
                    metadata=agent_data["metadata"],
                )
            
            @strawberry.mutation
            async def update_agent_reputation(
                self,
                did: str,
                reputation_score: float,
            ) -> Agent:
                await self.agent_repo.update_reputation(did, reputation_score)
                agent_data = await self.agent_repo.get_by_did(did)
                
                return Agent(
                    did=agent_data["did"],
                    address=agent_data["address"],
                    reputation_score=agent_data["reputation_score"],
                    verification_tier=agent_data["verification_tier"],
                    total_transactions=agent_data["total_transactions"],
                    total_volume_usd=agent_data["total_volume_usd"],
                    threat_count=agent_data["threat_count"],
                    created_at=agent_data["created_at"],
                    last_active=agent_data["last_active"],
                    metadata=agent_data["metadata"],
                )
            
            # Transactions
            @strawberry.mutation
            async def create_transaction(self, input: TransactionInput) -> Transaction:
                tx_id = await self.transaction_repo.create(input.__dict__)
                tx_data = await self.transaction_repo.get_by_hash(tx_id)
                
                return Transaction(
                    hash=tx_data["hash"],
                    from_address=tx_data["from_address"],
                    to_address=tx_data["to_address"],
                    amount=tx_data["amount"],
                    currency=tx_data["currency"],
                    timestamp=tx_data["timestamp"],
                    status=tx_data["status"],
                    gas_used=tx_data["gas_used"],
                    gas_price=tx_data["gas_price"],
                    block_number=tx_data["block_number"],
                    metadata=tx_data["metadata"],
                )
            
            @strawberry.mutation
            async def update_transaction_status(
                self,
                hash: str,
                status: str,
            ) -> Transaction:
                await self.transaction_repo.update_status(hash, status)
                tx_data = await self.transaction_repo.get_by_hash(hash)
                
                return Transaction(
                    hash=tx_data["hash"],
                    from_address=tx_data["from_address"],
                    to_address=tx_data["to_address"],
                    amount=tx_data["amount"],
                    currency=tx_data["currency"],
                    timestamp=tx_data["timestamp"],
                    status=tx_data["status"],
                    gas_used=tx_data["gas_used"],
                    gas_price=tx_data["gas_price"],
                    block_number=tx_data["block_number"],
                    metadata=tx_data["metadata"],
                )
            
            # Threats
            @strawberry.mutation
            async def create_threat(self, input: ThreatInput) -> Threat:
                threat_id = await self.threat_repo.create(input.__dict__)
                threat_data = await self.threat_repo.get_by_id(threat_id)
                
                return Threat(
                    id=threat_data["id"],
                    type=threat_data["type"],
                    severity=threat_data["severity"],
                    description=threat_data["description"],
                    source=threat_data["source"],
                    target=threat_data["target"],
                    detected_at=threat_data["detected_at"],
                    resolved_at=threat_data["resolved_at"],
                    status=threat_data["status"],
                    evidence=threat_data["evidence"],
                    recommendations=threat_data["recommendations"],
                )
            
            @strawberry.mutation
            async def resolve_threat(
                self,
                id: str,
                resolution: str,
            ) -> Threat:
                await self.threat_repo.resolve(id, resolution)
                threat_data = await self.threat_repo.get_by_id(id)
                
                return Threat(
                    id=threat_data["id"],
                    type=threat_data["type"],
                    severity=threat_data["severity"],
                    description=threat_data["description"],
                    source=threat_data["source"],
                    target=threat_data["target"],
                    detected_at=threat_data["detected_at"],
                    resolved_at=threat_data["resolved_at"],
                    status=threat_data["status"],
                    evidence=threat_data["evidence"],
                    recommendations=threat_data["recommendations"],
                )
            
            # Marketplace
            @strawberry.mutation
            async def create_skill(self, input: SkillInput) -> Skill:
                return await self.marketplace_resolver.create_skill(input)
            
            @strawberry.mutation
            async def purchase_skill(
                self,
                skill_id: str,
                buyer_address: str,
                price: float,
            ) -> Dict[str, Any]:
                return await self.marketplace_resolver.purchase_skill(
                    skill_id, buyer_address, price
                )
            
            @strawberry.mutation
            async def review_skill(
                self,
                skill_id: str,
                reviewer_address: str,
                rating: float,
                comment: str,
            ) -> Dict[str, Any]:
                return await self.marketplace_resolver.review_skill(
                    skill_id, reviewer_address, rating, comment
                )
            
            # Security
            @strawberry.mutation
            async def create_attack_scenario(self, input: Any) -> Any:
                return await self.security_resolver.create_attack_scenario(input)
            
            @strawberry.mutation
            async def run_simulation(self, input: Any) -> Any:
                return await self.security_resolver.run_simulation(input)
            
            # ZK-Proofs
            @strawberry.mutation
            async def create_zk_statement(self, input: Any) -> Any:
                return await self.security_resolver.create_zk_statement(input)
            
            @strawberry.mutation
            async def generate_zk_proof(self, input: Any) -> Any:
                return await self.security_resolver.generate_zk_proof(input)
            
            @strawberry.mutation
            async def verify_zk_proof(self, proof_id: str) -> bool:
                return await self.security_resolver.verify_zk_proof(proof_id)
            
            # FHE
            @strawberry.mutation
            async def generate_fhe_key_pair(self, input: Optional[Any] = None) -> Any:
                return await self.security_resolver.generate_fhe_key_pair(input)
            
            @strawberry.mutation
            async def encrypt_data(self, input: Any) -> Any:
                return await self.security_resolver.encrypt_data(input)
            
            @strawberry.mutation
            async def perform_fhe_operation(self, input: Any) -> Any:
                return await self.security_resolver.perform_fhe_operation(input)
            
            @strawberry.mutation
            async def verify_fhe_operation(self, operation_id: str) -> bool:
                return await self.security_resolver.verify_fhe_operation(operation_id)
            
            # Blockchain
            @strawberry.mutation
            async def start_cross_chain_monitoring(self) -> bool:
                return await self.blockchain_resolver.start_cross_chain_monitoring()
            
            @strawberry.mutation
            async def stop_cross_chain_monitoring(self) -> bool:
                return await self.blockchain_resolver.stop_cross_chain_monitoring()
            
            @strawberry.mutation
            async def transfer_token(self, input: Any) -> Dict[str, Any]:
                return await self.blockchain_resolver.transfer_token(input)
            
            @strawberry.mutation
            async def mint_skill_nft(
                self,
                skill_id: str,
                author: str,
                price: float,
            ) -> Dict[str, Any]:
                return await self.blockchain_resolver.mint_skill_nft(
                    skill_id, author, price
                )
            
            @strawberry.mutation
            async def register_staking_node(
                self,
                node_id: str,
                operator_address: str,
                metadata: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
                return await self.blockchain_resolver.register_staking_node(
                    node_id, operator_address, metadata
                )
            
            @strawberry.mutation
            async def stake_tokens(self, input: Any) -> Dict[str, Any]:
                return await self.blockchain_resolver.stake_tokens(input)
            
            @strawberry.mutation
            async def unstake_tokens(self, input: Any) -> Dict[str, Any]:
                return await self.blockchain_resolver.unstake_tokens(input)
            
            @strawberry.mutation
            async def distribute_staking_rewards(self, input: Any) -> Dict[str, Any]:
                return await self.blockchain_resolver.distribute_staking_rewards(input)
            
            @strawberry.mutation
            async def slash_node(
                self,
                node_id: str,
                reason: str,
                evidence: Optional[Dict[str, Any]] = None,
            ) -> Dict[str, Any]:
                return await self.blockchain_resolver.slash_node(
                    node_id, reason, evidence
                )
            
            # Intégrations Ecosystemiques - Mutations
            @strawberry.mutation
            async def simulate_flash_loan_attack(
                self,
                protocol: str,
                amount_usd: float,
            ) -> Dict[str, Any]:
                """Simule une attaque par flash loan"""
                if protocol.lower() == "aave":
                    return await self.aave_integration.simulate_flash_loan_attack(amount_usd)
                elif protocol.lower() == "compound":
                    return await self.compound_integration.simulate_liquidation_attack(
                        "0x742d35Cc6634C0532925a3b844Bc9e0F2b5B3a5A",
                        self.compound_integration.markets[0]
                    )
                else:
                    return {"error": f"Protocol {protocol} non supporté"}
            
            @strawberry.mutation
            async def simulate_oracle_manipulation(
                self,
                protocol: str,
                collateral_type: Optional[str] = None,
            ) -> Dict[str, Any]:
                """Simule une manipulation d'oracle"""
                if protocol.lower() == "makerdao":
                    # Convertir le type de collatéral
                    collateral_enum = None
                    for ct in self.makerdao_integration.collateral_types.keys():
                        if ct.value == collateral_type:
                            collateral_enum = ct
                            break
                    
                    if collateral_enum:
                        return await self.makerdao_integration.simulate_oracle_manipulation(collateral_enum)
                    else:
                        return {"error": f"Type de collatéral {collateral_type} non supporté"}
                elif protocol.lower() == "chainlink":
                    return {
                        "alert": "Manipulation d'oracle Chainlink simulée",
                        "affected_feeds": ["ETH/USD", "BTC/USD"],
                        "price_deviation": 0.15,
                        "timestamp": datetime.now().isoformat(),
                    }
                else:
                    return {"error": f"Protocol {protocol} non supporté"}
            
            @strawberry.mutation
            async def get_vault_recommendations(
                self,
                vault_id: int,
            ) -> Dict[str, Any]:
                """Obtient des recommandations pour un vault MakerDAO"""
                return await self.makerdao_integration.get_vault_recommendations(vault_id)
            
            @strawberry.mutation
            async def detect_flash_swap(
                self,
                transaction_hash: str,
            ) -> Dict[str, Any]:
                """Détecte un flash swap suspect sur Uniswap"""
                return await self.uniswap_integration.detect_flash_loan_attack(transaction_hash)
        
        return SiguiMutation
    
    def _create_subscription(self) -> type:
        """Crée la classe Subscription avec tous les resolvers."""
        
        @strawberry.type
        class SiguiSubscription:
            @strawberry.subscription
            async def real_time_threats(self) -> AsyncGenerator[Threat, None]:
                """Stream en temps réel des nouvelles menaces."""
                # À implémenter avec WebSockets
                while True:
                    await asyncio.sleep(5)
                    yield Threat(
                        id="simulated_threat",
                        type="SIMULATED",
                        severity="medium",
                        description="Menace simulée pour le test",
                        source="test",
                        target="test",
                        detected_at=datetime.now(),
                        resolved_at=None,
                        status="detected",
                        evidence={},
                        recommendations=["Test recommendation"],
                    )
            
            @strawberry.subscription
            async def cross_chain_alerts(self) -> AsyncGenerator[Any, None]:
                """Stream en temps réel des alertes cross-chain."""
                # À implémenter avec WebSockets
                while True:
                    await asyncio.sleep(10)
                    yield {
                        "chain": "ethereum",
                        "alert_type": "SIMULATED_ALERT",
                        "description": "Alerte cross-chain simulée",
                        "timestamp": datetime.now(),
                    }
            
            @strawberry.subscription
            async def simulation_updates(
                self,
                simulation_id: str,
            ) -> AsyncGenerator[Any, None]:
                """Stream des mises à jour d'une simulation."""
                # À implémenter avec WebSockets
                for i in range(5):
                    await asyncio.sleep(2)
                    yield {
                        "simulation_id": simulation_id,
                        "status": f"running_{i+1}/5",
                        "progress": (i + 1) * 20,
                        "timestamp": datetime.now(),
                    }
            
            @strawberry.subscription
            async def ecosystem_alerts(
                self,
                protocol: Optional[str] = None,
            ) -> AsyncGenerator[Dict[str, Any], None]:
                """Stream en temps réel des alertes ecosystemiques."""
                while True:
                    await asyncio.sleep(15)
                    
                    # Générer des alertes simulées
                    protocols = ["aave", "compound", "makerdao", "uniswap", "chainlink"]
                    if protocol and protocol.lower() in protocols:
                        selected_protocol = protocol.lower()
                    else:
                        selected_protocol = np.random.choice(protocols)
                    
                    alert_types = {
                        "aave": ["FLASH_LOAN", "LIQUIDATION_RISK", "INTEREST_RATE_SPIKE"],
                        "compound": ["LIQUIDATION_IMMINENT", "COLLATERAL_DRAIN", "ORACLE_MANIPULATION"],
                        "makerdao": ["VAULT_AT_RISK", "SYSTEMIC_RISK", "DEBT_CEILING_REACHED"],
                        "uniswap": ["PRICE_MANIPULATION", "FLASH_SWAP", "LIQUIDITY_DRAIN"],
                        "chainlink": ["PRICE_DEVIATION", "FEED_STALLED", "ORACLE_ATTACK"],
                    }
                    
                    yield {
                        "protocol": selected_protocol,
                        "alert_type": np.random.choice(alert_types[selected_protocol]),
                        "severity": np.random.choice(["low", "medium", "high", "critical"]),
                        "description": f"Alerte {selected_protocol} simulée",
                        "timestamp": datetime.now(),
                        "data": {
                            "amount_usd": np.random.uniform(1000, 1000000),
                            "address": f"0x{np.random.bytes(20).hex()}",
                            "confidence": np.random.uniform(0.7, 0.99),
                        }
                    }
            
            @strawberry.subscription
            async def war_room_updates(self) -> AsyncGenerator[Dict[str, Any], None]:
                """Stream des mises à jour pour le War Room 3D."""
                while True:
                    await asyncio.sleep(5)
                    
                    # Générer des mises à jour simulées
                    chains = ["ethereum", "solana", "cosmos", "aave", "compound", "makerdao", "uniswap"]
                    selected_chain = np.random.choice(chains)
                    
                    statuses = ["healthy", "warning", "critical"]
                    selected_status = np.random.choice(statuses)
                    
                    yield {
                        "type": "system_status_update",
                        "timestamp": datetime.now().isoformat(),
                        "data": {
                            "chain": selected_chain,
                            "status": selected_status,
                            "threats": np.random.randint(0, 10) if selected_status != "healthy" else 0,
                            "metrics": {
                                "transactions_per_second": np.random.uniform(10, 100),
                                "active_addresses": np.random.randint(1000, 100000),
                                "total_value_locked_usd": np.random.uniform(1e6, 1e9),
                            }
                        }
                    }
        
        return SiguiSubscription
    
    async def handle_websocket(self, websocket: WebSocket):
        """Gère les connexions WebSocket pour les subscriptions."""
        await websocket.accept()
        self.websocket_connections.append(websocket)
        
        try:
            while True:
                # Recevoir des messages
                data = await websocket.receive_text()
                
                # Traiter les messages
                message = json.loads(data)
                
                if message.get("type") == "subscribe":
                    # Gérer les subscriptions
                    await self._handle_subscription(websocket, message)
                
                elif message.get("type") == "unsubscribe":
                    # Gérer les unsubscriptions
                    await self._handle_unsubscription(websocket, message)
        
        except WebSocketDisconnect:
            self.websocket_connections.remove(websocket)
        
        except Exception as e:
            logger.error(f"Erreur WebSocket: {e}")
            self.websocket_connections.remove(websocket)
    
    async def _handle_subscription(self, websocket: WebSocket, message: Dict[str, Any]):
        """Gère une nouvelle subscription."""
        subscription_type = message.get("subscription_type")
        
        if subscription_type == "real_time_threats":
            # Démarrer le stream des menaces
            asyncio.create_task(self._stream_threats(websocket))
        
        elif subscription_type == "cross_chain_alerts":
            # Démarrer le stream des alertes
            asyncio.create_task(self._stream_cross_chain_alerts(websocket))
    
    async def _handle_unsubscription(self, websocket: WebSocket, message: Dict[str, Any]):
        """Gère une unsubscription."""
        # À implémenter
        pass
    
    async def _stream_threats(self, websocket: WebSocket):
        """Stream des menaces en temps réel."""
        while websocket in self.websocket_connections:
            # Récupérer les nouvelles menaces
            # (simulé pour l'exemple)
            threat_data = {
                "id": f"threat_{datetime.now().timestamp()}",
                "type": "SIMULATED",
                "severity": "medium",
                "description": "Nouvelle menace détectée",
                "timestamp": datetime.now().isoformat(),
            }
            
            await websocket.send_json({
                "type": "new_threat",
                "data": threat_data,
            })
            
            await asyncio.sleep(30)  # Toutes les 30 secondes
    
    async def _stream_cross_chain_alerts(self, websocket: WebSocket):
        """Stream des alertes cross-chain en temps réel."""
        while websocket in self.websocket_connections:
            # Récupérer les nouvelles alertes
            # (simulé pour l'exemple)
            alert_data = {
                "chain": "ethereum",
                "alert_type": "LARGE_TRANSFER",
                "description": "Transfert important détecté",
                "amount": 1000.0,
                "currency": "ETH",
                "timestamp": datetime.now().isoformat(),
            }
            
            await websocket.send_json({
                "type": "cross_chain_alert",
                "data": alert_data,
            })
            
            await asyncio.sleep(60)  # Toutes les 60 secondes
    
    def get_router(self) -> GraphQLRouter:
        """Retourne le router GraphQL."""
        return self.router
    
    def attach_to_app(self, app: FastAPI):
        """Attache le serveur GraphQL à une application FastAPI."""
        app.include_router(self.router, prefix="/graphql")
        
        # Ajouter l'endpoint WebSocket
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.handle_websocket(websocket)


# Instance globale du serveur
graphql_server = SiguiGraphQLServer()


def create_app() -> FastAPI:
    """
    Crée une application FastAPI avec le serveur GraphQL.
    Utilisé pour le lancement autonome du serveur GraphQL.
    """
    app = FastAPI(
        title="Sigui GraphQL API",
        description="API GraphQL unifiée pour le système de sécurité cross-chain Sigui",
        version="3.0.0",
    )
    
    # Ajouter CORS middleware
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Attacher le serveur GraphQL
    graphql_server.attach_to_app(app)
    
    # Route de santé
    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "service": "sigui-graphql",
            "version": "3.0.0",
            "timestamp": datetime.now().isoformat(),
        }
    
    return app


if __name__ == "__main__":
    import uvicorn
    print("🚀 Démarrage du serveur GraphQL Sigui...")
    print("📊 GraphQL Playground: http://localhost:8001/graphql")
    uvicorn.run(create_app(), host="0.0.0.0", port=8001, reload=True)