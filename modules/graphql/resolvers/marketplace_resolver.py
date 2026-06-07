"""
Sigui v4.0 — Marketplace Resolver
Résolution des données marketplace et staking
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, List
from ..types import Skill, Node, SkillInput, StakeInput
from ...modules.blockchain.token import SiguiToken
from ...modules.blockchain.staking import StakingPool
from ...modules.database.marketplace import SkillRepository

skill_repo = SkillRepository()
token = SiguiToken()
staking_pool = StakingPool()

def get_skill(id: str) -> Optional[Skill]:
    """Récupère un skill par son ID"""
    skill_data = skill_repo.get(id)
    if not skill_data:
        return None
    
    return Skill(
        id=skill_data["id"],
        name=skill_data["name"],
        description=skill_data["description"],
        author=skill_data["author"],
        price_usdc=skill_data["price_usdc"],
        version=skill_data["version"],
        category=skill_data["category"],
        rating=skill_data["rating"],
        review_count=skill_data["review_count"],
        created_at=skill_data["created_at"],
        updated_at=skill_data["updated_at"],
        metadata=json.dumps(skill_data["metadata"])
    )

def get_skills(category: Optional[str] = None,
              author: Optional[str] = None,
              limit: int = 100,
              offset: int = 0) -> List[Skill]:
    """Récupère la liste des skills"""
    skills_data = skill_repo.list(category, author, limit, offset)
    
    skills = []
    for skill_data in skills_data:
        skills.append(Skill(
            id=skill_data["id"],
            name=skill_data["name"],
            description=skill_data["description"],
            author=skill_data["author"],
            price_usdc=skill_data["price_usdc"],
            version=skill_data["version"],
            category=skill_data["category"],
            rating=skill_data["rating"],
            review_count=skill_data["review_count"],
            created_at=skill_data["created_at"],
            updated_at=skill_data["updated_at"],
            metadata=json.dumps(skill_data["metadata"])
        ))
    
    return skills

def create_skill(input: SkillInput) -> Skill:
    """Crée un nouveau skill"""
    skill_id = hashlib.sha256(
        f"{input.name}{input.author}{datetime.now().timestamp()}".encode()
    ).hexdigest()[:32]
    
    skill_data = {
        "id": skill_id,
        "name": input.name,
        "description": input.description,
        "author": input.author,
        "price_usdc": input.price_usdc,
        "version": "1.0.0",
        "category": input.category,
        "rating": 0.0,
        "review_count": 0,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "metadata": input.metadata or {}
    }
    
    skill_repo.create(skill_data)
    
    # Mint NFT pour le skill
    token.mint_skill_nft(
        skill_id=skill_id,
        author=input.author,
        price=input.price_usdc
    )
    
    return Skill(
        id=skill_id,
        name=input.name,
        description=input.description,
        author=input.author,
        price_usdc=input.price_usdc,
        version="1.0.0",
        category=input.category,
        rating=0.0,
        review_count=0,
        created_at=skill_data["created_at"],
        updated_at=skill_data["updated_at"],
        metadata=json.dumps(skill_data["metadata"])
    )

def purchase_skill(skill_id: str) -> bool:
    """Achète un skill"""
    skill_data = skill_repo.get(skill_id)
    if not skill_data:
        return False
    
    # Transfert de tokens
    success = token.transfer(
        from_address="buyer_address",  # À remplacer par l'adresse réelle
        to_address=skill_data["author"],
        amount=skill_data["price_usdc"]
    )
    
    if success:
        # Mise à jour des ventes
        skill_repo.increment_sales(skill_id)
        
        # Distribution des royalties
        royalty = skill_data["price_usdc"] * 0.05  # 5% de royalties
        token.transfer_royalty(
            to_address=skill_data["author"],
            amount=royalty
        )
    
    return success

def get_node(id: str) -> Optional[Node]:
    """Récupère un nœud par son ID"""
    node_data = staking_pool.get_node(id)
    if not node_data:
        return None
    
    return Node(
        id=node_data["id"],
        address=node_data["address"],
        stake_amount=node_data["stake_amount"],
        uptime_percentage=node_data["uptime_percentage"],
        performance_score=node_data["performance_score"],
        last_heartbeat=node_data["last_heartbeat"],
        status=node_data["status"],
        rewards_earned=node_data["rewards_earned"]
    )

def get_nodes(status: Optional[str] = None) -> List[Node]:
    """Récupère la liste des nœuds"""
    nodes_data = staking_pool.list_nodes(status)
    
    nodes = []
    for node_data in nodes_data:
        nodes.append(Node(
            id=node_data["id"],
            address=node_data["address"],
            stake_amount=node_data["stake_amount"],
            uptime_percentage=node_data["uptime_percentage"],
            performance_score=node_data["performance_score"],
            last_heartbeat=node_data["last_heartbeat"],
            status=node_data["status"],
            rewards_earned=node_data["rewards_earned"]
        ))
    
    return nodes

def stake_tokens(input: StakeInput) -> bool:
    """Stake des tokens sur un nœud"""
    # Vérifier le solde
    balance = token.balance_of("staker_address")  # À remplacer
    if balance < input.amount:
        return False
    
    # Stake les tokens
    success = staking_pool.stake(
        node_id=input.node_id,
        amount=input.amount,
        staker_address="staker_address"  # À remplacer
    )
    
    return success

def unstake_tokens(amount: float) -> bool:
    """Unstake des tokens"""
    success = staking_pool.unstake(
        amount=amount,
        staker_address="staker_address"  # À remplacer
    )
    
    return success