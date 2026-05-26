# @version 0.4.3
"""
@title Agent Identity Registry
@notice Decentralized Identity (DID) system for AI agents
@dev Implements cryptographic identity and reputation for autonomous agents
"""

# Agent identity structure
struct AgentIdentity:
    did: String[64]           # Decentralized Identifier: did:sigui:chain:address
    public_key: bytes32      # Ed25519 public key
    verification_tier: uint8  # 0=None, 1=Bronze, 2=Silver, 3=Gold, 4=Platinum
    reputation_score: uint16 # 0-1000 (basis points)
    registration_time: uint256 # Block timestamp
    last_update: uint256      # Last reputation update
    metadata_uri: String[128] # IPFS hash of identity metadata
    is_active: bool          # Whether identity is active
    total_transactions: uint256 # Total evaluated transactions
    successful_transactions: uint256 # Non-blocked transactions

# Verification tier details
struct VerificationTier:
    name: String[32]          # Tier name (Bronze, Silver, etc.)
    requirements: String[256] # Requirements description
    trust_multiplier: uint16  # Multiplier for reputation (100 = 1.0x)
    verification_fee: uint256 # Fee in wei for verification
    validity_period: uint256  # Validity in seconds

# Agent stats structure
struct AgentStats:
    total_evaluations: uint256
    blocked_transactions: uint256
    threat_patterns_contributed: uint256
    insurance_claims_made: uint256
    insurance_payouts: uint256

# Registry statistics structure
struct RegistryStats:
    total_agents: uint256
    verified_agents: uint256
    platinum_agents: uint256
    gold_agents: uint256
    silver_agents: uint256
    bronze_agents: uint256
    average_reputation: uint16
    total_verification_fees: uint256

# Events
event AgentRegistered:
    agent_did: indexed(String[64])
    agent_address: indexed(address)
    verification_tier: uint8
    reputation_score: uint16
    registration_time: uint256

event AgentUpdated:
    agent_did: indexed(String[64])
    reputation_score: uint16
    verification_tier: uint8
    last_update: uint256

event ReputationScoreUpdated:
    agent_did: indexed(String[64])
    old_score: uint16
    new_score: uint16
    update_reason: String[64]

event VerificationTierUpdated:
    agent_did: indexed(String[64])
    old_tier: uint8
    new_tier: uint8
    verification_time: uint256

event AgentDeactivated:
    agent_did: indexed(String[64])
    deactivation_time: uint256
    reason: String[128]

event AgentReactivated:
    agent_did: indexed(String[64])
    reactivation_time: uint256

# State variables
agent_identities: public(HashMap[address, AgentIdentity])
identity_by_did: public(HashMap[String[64], address])
verification_tiers: public(HashMap[uint8, VerificationTier])

# Agent statistics mapping
agent_stats: public(HashMap[address, AgentStats])

# Admin and governance
owner: public(address)
pending_owner: public(address)
registry_paused: public(bool)
verification_authority: public(address)

# Registry statistics
registry_stats: public(RegistryStats)

# Constants
MAX_REPUTATION_SCORE: constant(uint16) = 1000
MIN_REPUTATION_SCORE: constant(uint16) = 0
DEFAULT_TRUST_MULTIPLIER: constant(uint16) = 100

# Modifiers
@internal
def _only_owner():
    assert msg.sender == self.owner, "Only owner can call this function"

@internal
def _only_verification_authority():
    assert msg.sender == self.verification_authority, "Only verification authority can call this function"

@internal
def _when_not_paused():
    assert not self.registry_paused, "Registry is paused"

@internal
def _valid_did(did: String[64]) -> bool:
    # Basic DID validation: must start with "did:sigui:"
    return len(did) >= 15 and slice(did, 0, 10) == "did:sigui:"

@internal
def _valid_public_key(public_key: bytes32) -> bool:
    # Public key must not be zero
    return public_key != empty(bytes32)

@internal
def _valid_verification_tier(tier: uint8) -> bool:
    # Tier must be between 0 and 4
    return tier >= 0 and tier <= 4

@deploy
def __init__():
    """Initialize the Agent Identity Registry"""
    self.owner = msg.sender
    self.verification_authority = msg.sender
    self.registry_paused = False
    
    # Initialize verification tiers
    self._initialize_verification_tiers()
    
    # Initialize registry stats
    self.registry_stats.total_agents = 0
    self.registry_stats.verified_agents = 0
    self.registry_stats.platinum_agents = 0
    self.registry_stats.gold_agents = 0
    self.registry_stats.silver_agents = 0
    self.registry_stats.bronze_agents = 0
    self.registry_stats.average_reputation = 0
    self.registry_stats.total_verification_fees = 0

@internal
def _initialize_verification_tiers():
    """Initialize default verification tiers"""
    
    # Tier 0: None (basic registration)
    self.verification_tiers[0].name = "None"
    self.verification_tiers[0].requirements = "Basic DID registration"
    self.verification_tiers[0].trust_multiplier = 100
    self.verification_tiers[0].verification_fee = 0
    self.verification_tiers[0].validity_period = 0  # No expiration
    
    # Tier 1: Bronze (email verification)
    self.verification_tiers[1].name = "Bronze"
    self.verification_tiers[1].requirements = "Email verification and basic KYC"
    self.verification_tiers[1].trust_multiplier = 120  # 1.2x multiplier
    self.verification_tiers[1].verification_fee = as_wei_value(0.01, "ether")  # 0.01 ETH
    self.verification_tiers[1].validity_period = 31536000  # 1 year in seconds
    
    # Tier 2: Silver (organization verification)
    self.verification_tiers[2].name = "Silver"
    self.verification_tiers[2].requirements = "Organization registration and enhanced KYC"
    self.verification_tiers[2].trust_multiplier = 150  # 1.5x multiplier
    self.verification_tiers[2].verification_fee = as_wei_value(0.05, "ether")  # 0.05 ETH
    self.verification_tiers[2].validity_period = 63072000  # 2 years in seconds
    
    # Tier 3: Gold (enterprise verification)
    self.verification_tiers[3].name = "Gold"
    self.verification_tiers[3].requirements = "Enterprise audit and comprehensive KYC"
    self.verification_tiers[3].trust_multiplier = 180  # 1.8x multiplier
    self.verification_tiers[3].verification_fee = as_wei_value(0.1, "ether")  # 0.1 ETH
    self.verification_tiers[3].validity_period = 126230400  # 4 years in seconds
    
    # Tier 4: Platinum (premium enterprise)
    self.verification_tiers[4].name = "Platinum"
    self.verification_tiers[4].requirements = "Premium enterprise verification with insurance backing"
    self.verification_tiers[4].trust_multiplier = 200  # 2.0x multiplier
    self.verification_tiers[4].verification_fee = as_wei_value(0.5, "ether")  # 0.5 ETH
    self.verification_tiers[4].validity_period = 315360000  # 10 years in seconds

@external
@payable
def register_agent(
    agent_did: String[64],
    public_key: bytes32,
    verification_tier: uint8,
    metadata_uri: String[128]
) -> uint256:
    """
    @notice Register a new agent identity
    @param agent_did Decentralized identifier for the agent
    @param public_key Ed25519 public key for cryptographic verification
    @param verification_tier Verification tier (0-4)
    @param metadata_uri IPFS URI for identity metadata
    @return registration_id Unique registration identifier
    """
    self._when_not_paused()
    
    # Validate inputs
    assert self._valid_did(agent_did), "Invalid DID format"
    assert self._valid_public_key(public_key), "Invalid public key"
    assert self._valid_verification_tier(verification_tier), "Invalid verification tier"
    assert len(metadata_uri) > 0, "Metadata URI cannot be empty"
    
    # Check if agent already exists
    assert self.agent_identities[msg.sender].registration_time == 0, "Agent already registered"
    
    # Check if DID is already taken
    assert self.identity_by_did[agent_did] == empty(address), "DID already exists"
    
    # Get verification tier details
    tier_details: VerificationTier = self.verification_tiers[verification_tier]
    
    # Handle verification fee
    if tier_details.verification_fee > 0:
        assert msg.value >= tier_details.verification_fee, "Insufficient verification fee"
        
        # Refund excess payment
        if msg.value > tier_details.verification_fee:
            send(msg.sender, msg.value - tier_details.verification_fee)
    
    # Calculate initial reputation score based on verification tier
    initial_reputation: uint16 = self._calculate_initial_reputation(verification_tier)
    current_time: uint256 = block.timestamp
    
    # Create agent identity
    self.agent_identities[msg.sender].did = agent_did
    self.agent_identities[msg.sender].public_key = public_key
    self.agent_identities[msg.sender].verification_tier = verification_tier
    self.agent_identities[msg.sender].reputation_score = initial_reputation
    self.agent_identities[msg.sender].registration_time = current_time
    self.agent_identities[msg.sender].last_update = current_time
    self.agent_identities[msg.sender].metadata_uri = metadata_uri
    self.agent_identities[msg.sender].is_active = True
    self.agent_identities[msg.sender].total_transactions = 0
    self.agent_identities[msg.sender].successful_transactions = 0
    
    # Store identity mapping
    self.identity_by_did[agent_did] = msg.sender
    
    # Initialize agent stats
    self.agent_stats[msg.sender].total_evaluations = 0
    self.agent_stats[msg.sender].blocked_transactions = 0
    self.agent_stats[msg.sender].threat_patterns_contributed = 0
    self.agent_stats[msg.sender].insurance_claims_made = 0
    self.agent_stats[msg.sender].insurance_payouts = 0
    
    # Update registry statistics
    self.registry_stats.total_agents += 1
    if verification_tier > 0:
        self.registry_stats.verified_agents += 1
        if verification_tier == 1:
            self.registry_stats.bronze_agents += 1
        elif verification_tier == 2:
            self.registry_stats.silver_agents += 1
        elif verification_tier == 3:
            self.registry_stats.gold_agents += 1
        elif verification_tier == 4:
            self.registry_stats.platinum_agents += 1
    
    self.registry_stats.total_verification_fees += tier_details.verification_fee
    
    log AgentRegistered(agent_did=agent_did, agent_address=msg.sender, verification_tier=verification_tier, reputation_score=initial_reputation, registration_time=current_time)
    
    return current_time

@external
def update_reputation(
    agent_address: address,
    new_reputation_score: uint16,
    update_reason: String[64]
) -> bool:
    """
    @notice Update agent reputation score
    @param agent_address Address of the agent
    @param new_reputation_score New reputation score (0-1000)
    @param update_reason Reason for reputation update
    @return success Whether update was successful
    """
    self._when_not_paused()
    
    # Only authorized contracts can update reputation
    # This would typically be called by the Sigui evaluation engine
    assert msg.sender == self.verification_authority, "Unauthorized reputation update"
    
    # Validate inputs
    assert agent_address != empty(address), "Invalid agent address"
    assert new_reputation_score >= MIN_REPUTATION_SCORE and new_reputation_score <= MAX_REPUTATION_SCORE, "Invalid reputation score"
    assert len(update_reason) > 0, "Update reason required"
    
    # Check if agent exists and is active
    assert self.agent_identities[agent_address].registration_time > 0, "Agent not registered"
    assert self.agent_identities[agent_address].is_active, "Agent is deactivated"
    
    old_score: uint16 = self.agent_identities[agent_address].reputation_score
    current_time: uint256 = block.timestamp
    
    # Update reputation
    self.agent_identities[agent_address].reputation_score = new_reputation_score
    self.agent_identities[agent_address].last_update = current_time
    
    # Update registry statistics
    self._update_average_reputation()
    
    log ReputationScoreUpdated(agent_did=self.agent_identities[agent_address].did, old_score=old_score, new_score=new_reputation_score, update_reason=update_reason)
    
    return True

@external
def update_agent_verification_tier(
    agent_address: address,
    new_verification_tier: uint8
) -> bool:
    """
    @notice Update agent verification tier
    @param agent_address Address of the agent
    @param new_verification_tier New verification tier (0-4)
    @return success Whether update was successful
    """
    self._when_not_paused()
    self._only_verification_authority()
    
    # Validate inputs
    assert agent_address != empty(address), "Invalid agent address"
    assert self._valid_verification_tier(new_verification_tier), "Invalid verification tier"
    
    # Check if agent exists and is active
    assert self.agent_identities[agent_address].registration_time > 0, "Agent not registered"
    assert self.agent_identities[agent_address].is_active, "Agent is deactivated"
    
    old_tier: uint8 = self.agent_identities[agent_address].verification_tier
    current_time: uint256 = block.timestamp
    
    # Update registry statistics
    self._update_verification_tier_stats(old_tier, new_verification_tier)
    
    # Update verification tier
    self.agent_identities[agent_address].verification_tier = new_verification_tier
    self.agent_identities[agent_address].last_update = current_time
    
    # Recalculate reputation based on new tier
    new_reputation: uint16 = self._calculate_reputation_for_tier(new_verification_tier, self.agent_identities[agent_address].reputation_score)
    self.agent_identities[agent_address].reputation_score = new_reputation
    
    log VerificationTierUpdated(agent_did=self.agent_identities[agent_address].did, old_tier=old_tier, new_tier=new_verification_tier, verification_time=current_time)
    log ReputationScoreUpdated(agent_did=self.agent_identities[agent_address].did, old_score=convert(old_tier, uint16), new_score=new_reputation, update_reason="Verification tier update")
    
    return True

@internal
def _update_verification_tier_stats(old_tier: uint8, new_tier: uint8):
    """Update registry statistics when verification tier changes"""
    
    # Remove from old tier count
    if old_tier == 1:
        self.registry_stats.bronze_agents -= 1
    elif old_tier == 2:
        self.registry_stats.silver_agents -= 1
    elif old_tier == 3:
        self.registry_stats.gold_agents -= 1
    elif old_tier == 4:
        self.registry_stats.platinum_agents -= 1
    
    # Add to new tier count
    if new_tier == 1:
        self.registry_stats.bronze_agents += 1
    elif new_tier == 2:
        self.registry_stats.silver_agents += 1
    elif new_tier == 3:
        self.registry_stats.gold_agents += 1
    elif new_tier == 4:
        self.registry_stats.platinum_agents += 1

@internal
def _update_average_reputation():
    """Update average reputation score across all agents"""
    # This is a simplified calculation - in production you'd want a more sophisticated approach
    # For now, we'll just track it as a placeholder
    pass

@external
def deactivate_agent(
    agent_address: address,
    reason: String[128]
) -> bool:
    """
    @notice Deactivate an agent identity
    @param agent_address Address of the agent to deactivate
    @param reason Reason for deactivation
    @return success Whether deactivation was successful
    """
    self._only_verification_authority()
    
    # Validate inputs
    assert agent_address != empty(address), "Invalid agent address"
    assert len(reason) > 0, "Deactivation reason required"
    
    # Check if agent exists
    assert self.agent_identities[agent_address].registration_time > 0, "Agent not registered"
    assert self.agent_identities[agent_address].is_active, "Agent already deactivated"
    
    # Update registry statistics
    if self.agent_identities[agent_address].verification_tier > 0:
        self.registry_stats.verified_agents -= 1
        if self.agent_identities[agent_address].verification_tier == 1:
            self.registry_stats.bronze_agents -= 1
        elif self.agent_identities[agent_address].verification_tier == 2:
            self.registry_stats.silver_agents -= 1
        elif self.agent_identities[agent_address].verification_tier == 3:
            self.registry_stats.gold_agents -= 1
        elif self.agent_identities[agent_address].verification_tier == 4:
            self.registry_stats.platinum_agents -= 1
    
    # Deactivate agent
    self.agent_identities[agent_address].is_active = False
    current_time: uint256 = block.timestamp
    
    log AgentDeactivated(agent_did=self.agent_identities[agent_address].did, deactivation_time=current_time, reason=reason)
    
    return True

@external
def reactivate_agent(
    agent_address: address
) -> bool:
    """
    @notice Reactivate a previously deactivated agent
    @param agent_address Address of the agent to reactivate
    @return success Whether reactivation was successful
    """
    self._only_verification_authority()
    
    # Validate inputs
    assert agent_address != empty(address), "Invalid agent address"
    
    # Check if agent exists and is deactivated
    assert self.agent_identities[agent_address].registration_time > 0, "Agent not registered"
    assert not self.agent_identities[agent_address].is_active, "Agent already active"
    
    # Update registry statistics
    if self.agent_identities[agent_address].verification_tier > 0:
        self.registry_stats.verified_agents += 1
        if self.agent_identities[agent_address].verification_tier == 1:
            self.registry_stats.bronze_agents += 1
        elif self.agent_identities[agent_address].verification_tier == 2:
            self.registry_stats.silver_agents += 1
        elif self.agent_identities[agent_address].verification_tier == 3:
            self.registry_stats.gold_agents += 1
        elif self.agent_identities[agent_address].verification_tier == 4:
            self.registry_stats.platinum_agents += 1
    
    # Reactivate agent
    self.agent_identities[agent_address].is_active = True
    current_time: uint256 = block.timestamp
    
    log AgentReactivated(agent_did=self.agent_identities[agent_address].did, reactivation_time=current_time)
    
    return True

@view
@internal
def _calculate_initial_reputation(verification_tier: uint8) -> uint16:
    """Calculate initial reputation score based on verification tier"""
    
    if verification_tier == 0:  # None
        return 500  # 50% base reputation
    elif verification_tier == 1:  # Bronze
        return 600  # 60% initial reputation
    elif verification_tier == 2:  # Silver
        return 700  # 70% initial reputation
    elif verification_tier == 3:  # Gold
        return 800  # 80% initial reputation
    elif verification_tier == 4:  # Platinum
        return 900  # 90% initial reputation
    else:
        return 500  # Default to 50%

@view
@internal
def _calculate_reputation_for_tier(tier: uint8, current_reputation: uint16) -> uint16:
    """Recalculate reputation when tier changes"""
    
    tier_multiplier: uint16 = self.verification_tiers[tier].trust_multiplier
    base_reputation: uint16 = self._calculate_initial_reputation(tier)
    
    # Apply tier multiplier to base reputation, but don't go below current reputation
    new_reputation: uint256 = convert(base_reputation * tier_multiplier, uint256) // 100
    
    if new_reputation > convert(current_reputation, uint256):
        return convert(new_reputation, uint16)
    else:
        return current_reputation

@view
@external
def get_agent_identity(agent_address: address) -> AgentIdentity:
    """
    @notice Get complete agent identity information
    @param agent_address Address of the agent
    @return identity Complete agent identity
    """
    return self.agent_identities[agent_address]

@view
@external
def get_agent_by_did(agent_did: String[64]) -> AgentIdentity:
    """
    @notice Get agent identity by DID
    @param agent_did Decentralized identifier
    @return identity Agent identity
    """
    return self.agent_identities[self.identity_by_did[agent_did]]

@view
@external
def get_agent_stats(agent_address: address) -> AgentStats:
    """
    @notice Get agent statistics
    @param agent_address Address of the agent
    @return stats Agent statistics
    """
    return self.agent_stats[agent_address]

@view
@external
def calculate_effective_reputation(agent_address: address) -> uint16:
    """
    @notice Calculate effective reputation score with tier multiplier
    @param agent_address Address of the agent
    @return effective_reputation Reputation score with tier multiplier applied
    """
    agent_identity: AgentIdentity = self.agent_identities[agent_address]
    
    if agent_identity.registration_time == 0:
        return 0  # Agent not registered
    
    if not agent_identity.is_active:
        return 0  # Deactivated agent has 0 reputation
    
    base_reputation: uint256 = convert(agent_identity.reputation_score, uint256)
    tier_multiplier: uint256 = convert(self.verification_tiers[agent_identity.verification_tier].trust_multiplier, uint256)
    
    effective_reputation: uint256 = (base_reputation * tier_multiplier) // 100
    
    # Cap at maximum reputation score
    if effective_reputation > convert(MAX_REPUTATION_SCORE, uint256):
        return MAX_REPUTATION_SCORE
    
    return convert(effective_reputation, uint16)

@view
@external
def is_agent_verified(agent_address: address) -> bool:
    """
    @notice Check if agent is verified (tier > 0)
    @param agent_address Address of the agent
    @return is_verified Whether agent is verified
    """
    agent_identity: AgentIdentity = self.agent_identities[agent_address]
    return agent_identity.registration_time > 0 and agent_identity.is_active and agent_identity.verification_tier > 0

@view
@external
def get_verification_tier_details(tier: uint8) -> (String[32], String[256], uint16, uint256, uint256):
    """
    @notice Get verification tier details
    @param tier Verification tier (0-4)
    @return name Tier name
    @return requirements Requirements description
    @return trust_multiplier Trust multiplier
    @return verification_fee Verification fee
    @return validity_period Validity period
    """
    assert tier >= 0 and tier <= 4, "Invalid verification tier"
    tier_details: VerificationTier = self.verification_tiers[tier]
    return (tier_details.name, tier_details.requirements, tier_details.trust_multiplier, tier_details.verification_fee, tier_details.validity_period)

@view
@external
def get_registry_statistics() -> (uint256, uint256, uint256, uint256, uint256, uint256, uint16, uint256):
    """
    @notice Get registry statistics
    @return total_agents Total agents
    @return verified_agents Verified agents
    @return platinum_agents Platinum agents
    @return gold_agents Gold agents
    @return silver_agents Silver agents
    @return bronze_agents Bronze agents
    @return average_reputation Average reputation
    @return total_verification_fees Total verification fees
    """
    return (
        self.registry_stats.total_agents,
        self.registry_stats.verified_agents,
        self.registry_stats.platinum_agents,
        self.registry_stats.gold_agents,
        self.registry_stats.silver_agents,
        self.registry_stats.bronze_agents,
        self.registry_stats.average_reputation,
        self.registry_stats.total_verification_fees
    )

# Governance functions
@external
def transfer_ownership(new_owner: address):
    """
    @notice Transfer ownership of the registry
    @param new_owner Address of the new owner
    """
    self._only_owner()
    self.pending_owner = new_owner

@external
def accept_ownership():
    """
    @notice Accept ownership transfer
    """
    assert msg.sender == self.pending_owner, "Not the pending owner"
    self.owner = msg.sender
    self.pending_owner = empty(address)

@external
def set_verification_authority(new_authority: address):
    """
    @notice Set the verification authority
    @param new_authority Address of the new verification authority
    """
    self._only_owner()
    self.verification_authority = new_authority

@external
def pause_registry():
    """
    @notice Pause the registry (emergency stop)
    """
    self._only_owner()
    self.registry_paused = True

@external
def unpause_registry():
    """
    @notice Unpause the registry
    """
    self._only_owner()
    self.registry_paused = False

@external
def set_verification_tier_config(
    tier: uint8,
    name: String[32],
    requirements: String[256],
    trust_multiplier: uint16,
    verification_fee: uint256,
    validity_period: uint256
):
    """
    @notice Set verification tier configuration
    @param tier Verification tier to update
    @param name New tier name
    @param requirements New requirements
    @param trust_multiplier New trust multiplier
    @param verification_fee New verification fee
    @param validity_period New validity period
    """
    self._only_owner()
    assert tier >= 0 and tier <= 4, "Invalid verification tier"
    assert trust_multiplier >= 100, "Trust multiplier must be >= 100"
    
    self.verification_tiers[tier].name = name
    self.verification_tiers[tier].requirements = requirements
    self.verification_tiers[tier].trust_multiplier = trust_multiplier
    self.verification_tiers[tier].verification_fee = verification_fee
    self.verification_tiers[tier].validity_period = validity_period

# Fallback function to accept payments
@payable
@external
def __default__():
    """Accept payments for verification fees"""
    pass