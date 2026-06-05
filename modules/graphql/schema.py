"""
Sigui v4.0 — GraphQL Schema Definition
Schema complet avec toutes les fonctionnalités
"""

import strawberry
from typing import Optional, List, Any
from datetime import datetime
from strawberry.scalars import JSON

# ─── Scalars ───────────────────────────────────────────────────────────────

@strawberry.scalar
class Address:
    @staticmethod
    def serialize(value: str) -> str:
        return value.lower()
    
    @staticmethod
    def parse_value(value: str) -> str:
        return value.lower()
    
    @staticmethod
    def parse_literal(ast) -> str:
        return ast.value.lower()

# ─── Types ─────────────────────────────────────────────────────────────────

@strawberry.type
class Agent:
    did: str
    address: Address
    reputation_score: float
    verification_tier: str  # Bronze, Silver, Gold, Platinum
    total_transactions: int
    total_volume_usd: float
    threat_count: int
    created_at: datetime
    last_active: datetime
    metadata: JSON

@strawberry.type
class Transaction:
    hash: str
    from_address: Address
    to_address: Address
    amount_usdc: float
    chain: str
    timestamp: datetime
    status: str  # Pending, Confirmed, Failed
    gas_used: Optional[float]
    gas_price: Optional[float]

@strawberry.type
class Verdict:
    decision: str  # ALLOW, BLOCK, ESCALATE
    risk_score: float
    reason: str
    action_hash: str
    processing_time_ms: float
    vision_confidence: Optional[float]
    raw_signals: JSON
    zk_proof: Optional[str]
    encrypted_result: Optional[str]

@strawberry.type
class Threat:
    id: str
    type: str  # DRAIN_STAR, MIXING_CHAIN, COORDINATED_CLUSTER
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    detected_at: datetime
    affected_agents: List[str]
    cross_chain: bool
    evidence: JSON

@strawberry.type
class Skill:
    id: str
    name: str
    description: str
    author: Address
    price_usdc: float
    version: str
    category: str
    rating: float
    review_count: int
    created_at: datetime
    updated_at: datetime
    metadata: JSON

@strawberry.type
class Node:
    id: str
    address: Address
    stake_amount: float
    uptime_percentage: float
    performance_score: float
    last_heartbeat: datetime
    status: str  # ACTIVE, INACTIVE, SLASHED
    rewards_earned: float

@strawberry.type
class Proposal:
    id: str
    title: str
    description: str
    proposer: Address
    created_at: datetime
    voting_start: datetime
    voting_end: datetime
    status: str  # PENDING, ACTIVE, PASSED, FAILED
    for_votes: float
    against_votes: float
    quorum_reached: bool

@strawberry.type
class SimulationResult:
    id: str
    scenario: str
    agent_did: str
    score: float
    weaknesses: List[str]
    recommendations: List[str]
    executed_at: datetime
    details: JSON

@strawberry.type
class ZKProof:
    proof: str
    public_inputs: JSON
    verification_key: str
    verification_result: bool

@strawberry.type
class FHEAnalysis:
    encrypted_input: str
    encrypted_output: str
    analysis_type: str
    metadata: JSON

# ─── Inputs ────────────────────────────────────────────────────────────────

@strawberry.input
class TransactionInput:
    action_type: str
    destination: Address
    amount_usdc: float
    chain: str
    metadata: Optional[JSON] = None

@strawberry.input
class SkillInput:
    name: str
    description: str
    price_usdc: float
    category: str
    metadata: Optional[JSON] = None

@strawberry.input
class StakeInput:
    amount: float
    node_id: str

@strawberry.input
class ProposalInput:
    title: str
    description: str
    voting_duration_hours: int = 24

@strawberry.input
class SimulationInput:
    scenario: str
    agent_did: str
    parameters: Optional[JSON] = None

@strawberry.input
class ZKProofInput:
    private_data: JSON
    circuit_id: str

@strawberry.input
class FHEInput:
    encrypted_data: str
    operation: str
    parameters: Optional[JSON] = None

# ─── Query ─────────────────────────────────────────────────────────────────

@strawberry.type
class Query:
    # Agents
    @strawberry.field
    def agent(self, did: str) -> Optional[Agent]:
        from .resolvers.agent_resolver import get_agent
        return get_agent(did)
    
    @strawberry.field
    def agents(self, limit: int = 100, offset: int = 0) -> List[Agent]:
        from .resolvers.agent_resolver import get_agents
        return get_agents(limit, offset)
    
    # Transactions
    @strawberry.field
    def transaction(self, hash: str) -> Optional[Transaction]:
        from .resolvers.transaction_resolver import get_transaction
        return get_transaction(hash)
    
    @strawberry.field
    def transactions(self, 
                    agent_did: Optional[str] = None,
                    limit: int = 100,
                    offset: int = 0) -> List[Transaction]:
        from .resolvers.transaction_resolver import get_transactions
        return get_transactions(agent_did, limit, offset)
    
    # Evaluation
    @strawberry.field
    def evaluate_transaction(self, input: TransactionInput) -> Verdict:
        from .resolvers.transaction_resolver import evaluate_transaction
        return evaluate_transaction(input)
    
    # Threats
    @strawberry.field
    def threat(self, id: str) -> Optional[Threat]:
        from .resolvers.threat_resolver import get_threat
        return get_threat(id)
    
    @strawberry.field
    def threats(self, 
               severity: Optional[str] = None,
               limit: int = 100,
               offset: int = 0) -> List[Threat]:
        from .resolvers.threat_resolver import get_threats
        return get_threats(severity, limit, offset)
    
    # Marketplace
    @strawberry.field
    def skill(self, id: str) -> Optional[Skill]:
        from .resolvers.marketplace_resolver import get_skill
        return get_skill(id)
    
    @strawberry.field
    def skills(self,
              category: Optional[str] = None,
              author: Optional[Address] = None,
              limit: int = 100,
              offset: int = 0) -> List[Skill]:
        from .resolvers.marketplace_resolver import get_skills
        return get_skills(category, author, limit, offset)
    
    # Nodes & Staking
    @strawberry.field
    def node(self, id: str) -> Optional[Node]:
        from .resolvers.marketplace_resolver import get_node
        return get_node(id)
    
    @strawberry.field
    def nodes(self, status: Optional[str] = None) -> List[Node]:
        from .resolvers.marketplace_resolver import get_nodes
        return get_nodes(status)
    
    # Governance
    @strawberry.field
    def proposal(self, id: str) -> Optional[Proposal]:
        from .resolvers.governance_resolver import get_proposal
        return get_proposal(id)
    
    @strawberry.field
    def proposals(self,
                 status: Optional[str] = None,
                 limit: int = 100,
                 offset: int = 0) -> List[Proposal]:
        from .resolvers.governance_resolver import get_proposals
        return get_proposals(status, limit, offset)
    
    # Simulation
    @strawberry.field
    def simulation_result(self, id: str) -> Optional[SimulationResult]:
        from .resolvers.simulation_resolver import get_simulation_result
        return get_simulation_result(id)
    
    @strawberry.field
    def simulation_results(self,
                          agent_did: Optional[str] = None,
                          limit: int = 100,
                          offset: int = 0) -> List[SimulationResult]:
        from .resolvers.simulation_resolver import get_simulation_results
        return get_simulation_results(agent_did, limit, offset)
    
    # ZK Proofs
    @strawberry.field
    def generate_zk_proof(self, input: ZKProofInput) -> ZKProof:
        from .resolvers.zk_resolver import generate_proof
        return generate_proof(input)
    
    # FHE Analysis
    @strawberry.field
    def analyze_fhe(self, input: FHEInput) -> FHEAnalysis:
        from .resolvers.fhe_resolver import analyze_encrypted
        return analyze_encrypted(input)

# ─── Mutation ──────────────────────────────────────────────────────────────

@strawberry.type
class Mutation:
    # Marketplace
    @strawberry.mutation
    def create_skill(self, input: SkillInput) -> Skill:
        from .resolvers.marketplace_resolver import create_skill
        return create_skill(input)
    
    @strawberry.mutation
    def purchase_skill(self, skill_id: str) -> bool:
        from .resolvers.marketplace_resolver import purchase_skill
        return purchase_skill(skill_id)
    
    # Staking
    @strawberry.mutation
    def stake_tokens(self, input: StakeInput) -> bool:
        from .resolvers.marketplace_resolver import stake_tokens
        return stake_tokens(input)
    
    @strawberry.mutation
    def unstake_tokens(self, amount: float) -> bool:
        from .resolvers.marketplace_resolver import unstake_tokens
        return unstake_tokens(amount)
    
    # Governance
    @strawberry.mutation
    def create_proposal(self, input: ProposalInput) -> Proposal:
        from .resolvers.governance_resolver import create_proposal
        return create_proposal(input)
    
    @strawberry.mutation
    def vote(self, proposal_id: str, support: bool, voting_power: float) -> bool:
        from .resolvers.governance_resolver import vote
        return vote(proposal_id, support, voting_power)
    
    # Simulation
    @strawberry.mutation
    def run_simulation(self, input: SimulationInput) -> SimulationResult:
        from .resolvers.simulation_resolver import run_simulation
        return run_simulation(input)

# ─── Subscription ──────────────────────────────────────────────────────────

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def agent_events(self, did: str) -> Agent:
        from .subscriptions import subscribe_to_agent
        async for event in subscribe_to_agent(did):
            yield event
    
    @strawberry.subscription
    async def threat_alerts(self, severity: Optional[str] = None) -> Threat:
        from .subscriptions import subscribe_to_threats
        async for event in subscribe_to_threats(severity):
            yield event
    
    @strawberry.subscription
    async def transaction_updates(self, hash: str) -> Transaction:
        from .subscriptions import subscribe_to_transaction
        async for event in subscribe_to_transaction(hash):
            yield event

# ─── Schema ────────────────────────────────────────────────────────────────

schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    scalar_overrides={
        str: Address,
    }
)