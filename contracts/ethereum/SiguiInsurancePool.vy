# @version ^0.4.3
"""
SiguiInsurancePool.vy - Decentralized Insurance Pool for Autonomous Agents
Phase 3: Sigui Protocol - The AWS of Trust Infrastructure for the Autonomous Economy

Features:
- Risk-based insurance coverage for agent transactions
- Automated claims processing with AI verification
- Staking mechanism for liquidity providers
- Reputation-based premium calculation
- Up to $100,000 coverage per transaction
"""

# Interfaces
interface IERC20:
    def transfer(_to: address, _value: uint256) -> bool: nonpayable
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def balanceOf(_owner: address) -> uint256: view

interface IAgentIdentityRegistry:
    def is_verified_agent(agent_address: address) -> bool: view
    def get_agent_reputation(agent_address: address) -> uint256: view
    def get_agent_verification_tier(agent_address: address) -> uint8: view

interface IThreatMarketplace:
    def get_pattern(_pattern_id: bytes32) -> (address, String[50], String[500], uint8, bytes32, String[1000], uint256, uint8, uint256, bool, uint256, uint256, uint256): view
    def get_marketplace_stats() -> (uint256, uint256, uint256, uint256, uint256): view

# Events
event PolicyCreated:
    policy_id: indexed(bytes32)
    agent_address: indexed(address)
    coverage_amount: uint256
    premium_amount: uint256
    premium_rate: uint256
    duration: uint256

event ClaimFiled:
    claim_id: indexed(bytes32)
    policy_id: indexed(bytes32)
    agent_address: indexed(address)
    claim_amount: uint256
    incident_hash: bytes32

event ClaimApproved:
    claim_id: indexed(bytes32)
    policy_id: indexed(bytes32)
    payout_amount: uint256
    processed_at: uint256

event ClaimRejected:
    claim_id: indexed(bytes32)
    reason: String[100]

event StakeDeposited:
    staker: indexed(address)
    amount: uint256
    total_stake: uint256

event StakeWithdrawn:
    staker: indexed(address)
    amount: uint256
    remaining_stake: uint256

event PremiumCollected:
    policy_id: indexed(bytes32)
    amount: uint256
    staker_rewards: uint256

event RiskAssessmentUpdated:
    agent_address: indexed(address)
    risk_score: uint256
    premium_rate: uint256

# Structs
struct InsurancePolicy:
    agent_address: address
    coverage_amount: uint256
    premium_amount: uint256
    premium_rate: uint256  # Basis points (e.g., 250 = 2.5%)
    start_time: uint256
    duration: uint256
    end_time: uint256
    is_active: bool
    claims_count: uint256
    total_claims_amount: uint256
    risk_score: uint256  # 0-1000
    max_payout: uint256

truct Claim:
    policy_id: bytes32
    claimant: address
    claim_amount: uint256
    incident_hash: bytes32  # Hash of incident details
    incident_description: String[500]
    threat_pattern_id: bytes32
    filed_at: uint256
    processed_at: uint256
    approved: bool
    payout_amount: uint256
    reason: String[100]
    evidence_hash: bytes32

truct StakerInfo:
    stake_amount: uint256
    reward_debt: uint256
    last_claim_time: uint256
    total_rewards: uint256
    risk_multiplier: uint256  # 100 = 1x, 150 = 1.5x

truct RiskAssessment:
    agent_reputation: uint256  # 0-1000
    verification_tier: uint8  # 0-4
    transaction_volume: uint256
    claims_history: uint256
    threat_exposure: uint256  # 0-1000
    risk_score: uint256  # 0-1000 (calculated)
    premium_multiplier: uint256  # 100 = 1x, 200 = 2x

# State Variables
USDC_TOKEN: public(immutable(IERC20))
AGENT_IDENTITY_REGISTRY: public(immutable(IAgentIdentityRegistry))
THREAT_MARKETPLACE: public(immutable(IThreatMarketplace))

# Policy management
policies: public(HashMap[bytes32, InsurancePolicy])
policy_ids: public(bytes32[10000])  # Max 10,000 active policies
policy_count: public(uint256)
agent_policies: public(HashMap[address, bytes32[100]])  # Max 100 policies per agent
agent_policy_count: public(HashMap[address, uint256])

# Claims management
claims: public(HashMap[bytes32, Claim])
claim_ids: public(bytes32[5000])  # Max 5,000 claims
claim_count: public(uint256)
policy_claims: public(HashMap[bytes32, bytes32[50]])  # Max 50 claims per policy
policy_claim_count: public(HashMap[bytes32, uint256])

# Staking system
stakers: public(HashMap[address, StakerInfo])
staker_addresses: public(address[200])  # Max 200 stakers
total_stake: public(uint256)
staker_count: public(uint256)
acc_reward_per_share: public(uint256)  # Accumulated rewards per share
last_reward_update: public(uint256)

# Risk assessment
risk_assessments: public(HashMap[address, RiskAssessment])
base_premium_rates: public(uint256[5])  # Premium rates by verification tier
max_coverage_amounts: public(uint256[5])  # Max coverage by verification tier

# Pool statistics
total_premiums_collected: public(uint256)
total_claims_paid: public(uint256)
total_policies_issued: public(uint256)
active_policy_count: public(uint256)

# Governance
owner: public(address)
pending_owner: public(address)
claim_validators: public(HashMap[address, bool])
emergency_pause: public(bool)

# Constants
MAX_COVERAGE_PER_TRANSACTION: constant(uint256) = 100000 * 10**6  # $100,000 USDC
MAX_PREMIUM_RATE: constant(uint256) = 1000  # 10% maximum premium rate
MIN_PREMIUM_RATE: constant(uint256) = 50  # 0.5% minimum premium rate
CLAIM_PROCESSING_TIME: constant(uint256) = 86400  # 24 hours
MAX_CLAIM_AMOUNT: constant(uint256) = 100000 * 10**6  # $100,000 max claim
STAKING_REWARD_RATE: constant(uint256) = 500  # 5% annual reward rate (basis points)
RISK_MULTIPLIER_BASE: constant(uint256) = 100

@external
def __init__(_usdc_token: address, _agent_registry: address, _threat_marketplace: address):
    """
    Initialize the Sigui Insurance Pool
    
    Args:
        _usdc_token: USDC token contract address
        _agent_registry: Agent Identity Registry contract address
        _threat_marketplace: Threat Marketplace contract address
    """
    self.owner = msg.sender
    USDC_TOKEN = IERC20(_usdc_token)
    AGENT_IDENTITY_REGISTRY = IAgentIdentityRegistry(_agent_registry)
    THREAT_MARKETPLACE = IThreatMarketplace(_threat_marketplace)
    
    # Set base premium rates by verification tier (basis points)
    # Bronze: 2.5%, Silver: 2.0%, Gold: 1.5%, Platinum: 1.0%, Diamond: 0.5%
    self.base_premium_rates[0] = 250  # Bronze
    self.base_premium_rates[1] = 200  # Silver
    self.base_premium_rates[2] = 150  # Gold
    self.base_premium_rates[3] = 100  # Platinum
    self.base_premium_rates[4] = 50   # Diamond
    
    # Set max coverage amounts by verification tier (USDC)
    self.max_coverage_amounts[0] = 1000 * 10**6    # Bronze: $1,000
    self.max_coverage_amounts[1] = 5000 * 10**6     # Silver: $5,000
    self.max_coverage_amounts[2] = 25000 * 10**6    # Gold: $25,000
    self.max_coverage_amounts[3] = 100000 * 10**6   # Platinum: $100,000
    self.max_coverage_amounts[4] = 100000 * 10**6   # Diamond: $100,000
    
    self.last_reward_update = block.timestamp

# Policy Management
@external
def create_policy(
    _agent_address: address,
    _coverage_amount: uint256,
    _duration: uint256,
    _threat_pattern_id: bytes32
) -> bytes32:
    """
    Create a new insurance policy for an agent
    
    Args:
        _agent_address: Address of the agent being insured
        _coverage_amount: Amount of coverage requested (USDC)
        _duration: Policy duration in seconds
        _threat_pattern_id: Specific threat pattern to insure against
        
    Returns:
        policy_id: Unique identifier for the policy
    """
    assert not self.emergency_pause, "Contract is paused"
    assert AGENT_IDENTITY_REGISTRY.is_verified_agent(_agent_address), "Agent not verified"
    assert _coverage_amount <= MAX_COVERAGE_PER_TRANSACTION, "Coverage exceeds maximum"
    assert _duration >= 86400 and _duration <= 31536000, "Invalid duration (1 day to 1 year)"
    
    # Get agent verification tier
    verification_tier: uint8 = AGENT_IDENTITY_REGISTRY.get_agent_verification_tier(_agent_address)
    assert verification_tier < 5, "Invalid verification tier"
    
    # Calculate max coverage for agent tier
    max_coverage: uint256 = self.max_coverage_amounts[verification_tier]
    assert _coverage_amount <= max_coverage, "Coverage exceeds tier maximum"
    
    # Calculate risk assessment
    risk_assessment: RiskAssessment = self._calculate_risk_assessment(_agent_address, _coverage_amount)
    
    # Calculate premium rate based on risk
    base_rate: uint256 = self.base_premium_rates[verification_tier]
    premium_rate: uint256 = (base_rate * risk_assessment.premium_multiplier) / RISK_MULTIPLIER_BASE
    
    # Ensure premium rate is within bounds
    if premium_rate > MAX_PREMIUM_RATE:
        premium_rate = MAX_PREMIUM_RATE
    elif premium_rate < MIN_PREMIUM_RATE:
        premium_rate = MIN_PREMIUM_RATE
    
    # Calculate premium amount
    premium_amount: uint256 = (_coverage_amount * premium_rate * _duration) / (31536000 * 10000)  # Annualized
    
    # Collect premium
    assert USDC_TOKEN.transferFrom(msg.sender, self, premium_amount), "Premium payment failed"
    
    # Generate policy ID
    policy_id: bytes32 = keccak256(_abi_encode(_agent_address, _coverage_amount, block.timestamp))
    
    # Create policy
    policy: InsurancePolicy = InsurancePolicy({
        agent_address: _agent_address,
        coverage_amount: _coverage_amount,
        premium_amount: premium_amount,
        premium_rate: premium_rate,
        start_time: block.timestamp,
        duration: _duration,
        end_time: block.timestamp + _duration,
        is_active: True,
        claims_count: 0,
        total_claims_amount: 0,
        risk_score: risk_assessment.risk_score,
        max_payout: min(_coverage_amount, MAX_COVERAGE_PER_TRANSACTION)
    })
    
    # Store policy
    self.policies[policy_id] = policy
    self.policy_ids[self.policy_count] = policy_id
    self.policy_count += 1
    self.active_policy_count += 1
    self.total_policies_issued += 1
    
    # Update agent policies
    agent_policy_idx: uint256 = self.agent_policy_count[_agent_address]
    assert agent_policy_idx < 100, "Agent policy limit reached"
    self.agent_policies[_agent_address][agent_policy_idx] = policy_id
    self.agent_policy_count[_agent_address] = agent_policy_idx + 1
    
    # Update statistics
    self.total_premiums_collected += premium_amount
    
    # Update risk assessment
    self.risk_assessments[_agent_address] = risk_assessment
    
    # Distribute staking rewards
    self._distribute_staking_rewards(premium_amount)
    
    log PolicyCreated(policy_id, _agent_address, _coverage_amount, premium_amount, premium_rate, _duration)
    
    return policy_id

# Claims Management
@external
def file_claim(
    _policy_id: bytes32,
    _claim_amount: uint256,
    _incident_hash: bytes32,
    _incident_description: String[500],
    _threat_pattern_id: bytes32,
    _evidence_hash: bytes32
) -> bytes32:
    """
    File an insurance claim
    
    Args:
        _policy_id: ID of the insurance policy
        _claim_amount: Amount being claimed (USDC)
        _incident_hash: Hash of incident details
        _incident_description: Description of the incident
        _threat_pattern_id: Threat pattern that caused the loss
        _evidence_hash: Hash of supporting evidence
        
    Returns:
        claim_id: Unique identifier for the claim
    """
    assert not self.emergency_pause, "Contract is paused"
    
    policy: InsurancePolicy = self.policies[_policy_id]
    assert policy.agent_address != empty(address), "Policy not found"
    assert policy.is_active, "Policy not active"
    assert policy.end_time >= block.timestamp, "Policy expired"
    assert _claim_amount <= policy.coverage_amount, "Claim exceeds coverage"
    assert _claim_amount <= MAX_CLAIM_AMOUNT, "Claim exceeds maximum"
    assert msg.sender == policy.agent_address, "Not policy holder"
    
    # Verify threat pattern exists and is valid
    threat_contributor: address = empty(address)
    threat_type: String[50] = empty(String[50])
    threat_description: String[500] = empty(String[500])
    threat_severity: uint8 = 0
    threat_hash: bytes32 = empty(bytes32)
    threat_code: String[1000] = empty(String[1000])
    threat_created: uint256 = 0
    threat_quality: uint8 = 0
    threat_validations: uint256 = 0
    threat_active: bool = False
    threat_royalties: uint256 = 0
    threat_used: uint256 = 0
    threat_protected: uint256 = 0
    
    (threat_contributor, threat_type, threat_description, threat_severity, threat_hash, 
     threat_code, threat_created, threat_quality, threat_validations, threat_active, 
     threat_royalties, threat_used, threat_protected) = THREAT_MARKETPLACE.get_pattern(_threat_pattern_id)
    
    assert threat_active, "Threat pattern not active"
    assert threat_quality >= 70, "Threat pattern quality too low"
    
    # Generate claim ID
    claim_id: bytes32 = keccak256(_abi_encode(_policy_id, _claim_amount, block.timestamp))
    
    # Create claim
    claim: Claim = Claim({
        policy_id: _policy_id,
        claimant: msg.sender,
        claim_amount: _claim_amount,
        incident_hash: _incident_hash,
        incident_description: _incident_description,
        threat_pattern_id: _threat_pattern_id,
        filed_at: block.timestamp,
        processed_at: 0,
        approved: False,
        payout_amount: 0,
        reason: empty(String[100]),
        evidence_hash: _evidence_hash
    })
    
    # Store claim
    self.claims[claim_id] = claim
    self.claim_ids[self.claim_count] = claim_id
    self.claim_count += 1
    
    # Update policy claims
    policy_claim_idx: uint256 = self.policy_claim_count[_policy_id]
    assert policy_claim_idx < 50, "Policy claim limit reached"
    self.policy_claims[_policy_id][policy_claim_idx] = claim_id
    self.policy_claim_count[_policy_id] = policy_claim_idx + 1
    
    # Update policy statistics
    policy.claims_count += 1
    policy.total_claims_amount += _claim_amount
    
    log ClaimFiled(claim_id, _policy_id, msg.sender, _claim_amount, _incident_hash)
    
    return claim_id

# Claim Processing (simplified - in reality this would involve AI verification)
@external
def process_claim(_claim_id: bytes32, _approve: bool, _reason: String[100]):
    """
    Process an insurance claim (validator function)
    
    Args:
        _claim_id: ID of the claim to process
        _approve: Whether to approve the claim
        _reason: Reason for approval/rejection
    """
    assert self.claim_validators[msg.sender], "Not authorized validator"
    assert not self.emergency_pause, "Contract is paused"
    
    claim: Claim = self.claims[_claim_id]
    assert claim.claimant != empty(address), "Claim not found"
    assert claim.processed_at == 0, "Claim already processed"
    assert claim.filed_at + CLAIM_PROCESSING_TIME <= block.timestamp, "Claim processing period not elapsed"
    
    policy: InsurancePolicy = self.policies[claim.policy_id]
    
    if _approve:
        # Calculate payout amount (full claim amount for now)
        payout_amount: uint256 = claim.claim_amount
        
        # Ensure pool has sufficient funds
        pool_balance: uint256 = USDC_TOKEN.balanceOf(self)
        assert pool_balance >= payout_amount, "Insufficient pool funds"
        
        # Transfer payout to claimant
        assert USDC_TOKEN.transfer(claim.claimant, payout_amount), "Payout transfer failed"
        
        # Update claim
        claim.approved = True
        claim.payout_amount = payout_amount
        claim.processed_at = block.timestamp
        claim.reason = _reason
        
        # Update policy
        policy.total_claims_amount += payout_amount
        
        # Update pool statistics
        self.total_claims_paid += payout_amount
        
        log ClaimApproved(_claim_id, claim.policy_id, payout_amount, block.timestamp)
    else:
        # Reject claim
        claim.approved = False
        claim.processed_at = block.timestamp
        claim.reason = _reason
        
        log ClaimRejected(_claim_id, _reason)

# Risk Assessment
@internal
def _calculate_risk_assessment(_agent_address: address, _coverage_amount: uint256) -> RiskAssessment:
    """
    Calculate comprehensive risk assessment for an agent
    
    Args:
        _agent_address: Address of the agent
        _coverage_amount: Amount of coverage requested
        
    Returns:
        risk_assessment: Comprehensive risk assessment
    """
    # Get agent reputation from identity registry
    agent_reputation: uint256 = AGENT_IDENTITY_REGISTRY.get_agent_reputation(_agent_address)
    verification_tier: uint8 = AGENT_IDENTITY_REGISTRY.get_agent_verification_tier(_agent_address)
    
    # Calculate base risk score (inverse of reputation)
    risk_score: uint256 = 1000 - agent_reputation
    
    # Adjust based on verification tier
    tier_multiplier: uint256 = convert(verification_tier + 1, uint256)
    risk_score = risk_score / tier_multiplier
    
    # Calculate premium multiplier based on risk
    premium_multiplier: uint256 = RISK_MULTIPLIER_BASE + (risk_score / 20)  # Max 1.5x multiplier
    
    # Ensure multiplier is reasonable
    if premium_multiplier > 200:  # Max 2x multiplier
        premium_multiplier = 200
    
    return RiskAssessment({
        agent_reputation: agent_reputation,
        verification_tier: verification_tier,
        transaction_volume: 0,  # Would be calculated from historical data
        claims_history: 0,  # Would be calculated from historical data
        threat_exposure: 500,  # Default medium exposure
        risk_score: risk_score,
        premium_multiplier: premium_multiplier
    })

# Staking System
@external
def deposit_stake(_amount: uint256):
    """
    Deposit stake to provide liquidity for the insurance pool
    
    Args:
        _amount: Amount of USDC to stake
    """
    assert _amount >= 100 * 10**6, "Minimum stake is 100 USDC"
    assert USDC_TOKEN.transferFrom(msg.sender, self, _amount), "Stake transfer failed"
    
    # Update staker info
    staker_info: StakerInfo = self.stakers[msg.sender]
    
    if staker_info.stake_amount == 0:
        # New staker
        self.staker_addresses[self.staker_count] = msg.sender
        self.staker_count += 1
        
        staker_info = StakerInfo({
            stake_amount: 0,
            reward_debt: 0,
            last_claim_time: block.timestamp,
            total_rewards: 0,
            risk_multiplier: RISK_MULTIPLIER_BASE
        })
    
    # Update stake amount
    staker_info.stake_amount += _amount
    self.total_stake += _amount
    self.stakers[msg.sender] = staker_info
    
    log StakeDeposited(msg.sender, _amount, staker_info.stake_amount)

@external
def withdraw_stake(_amount: uint256):
    """
    Withdraw stake from the insurance pool
    
    Args:
        _amount: Amount of USDC to withdraw
    """
    staker_info: StakerInfo = self.stakers[msg.sender]
    assert staker_info.stake_amount >= _amount, "Insufficient stake"
    
    # Ensure pool maintains minimum liquidity
    pool_balance: uint256 = USDC_TOKEN.balanceOf(self)
    min_liquidity: uint256 = self.total_premiums_collected / 10  # 10% of total premiums
    assert pool_balance - _amount >= min_liquidity, "Would reduce liquidity below minimum"
    
    # Update staker info
    staker_info.stake_amount -= _amount
    self.total_stake -= _amount
    self.stakers[msg.sender] = staker_info
    
    # Transfer USDC to staker
    assert USDC_TOKEN.transfer(msg.sender, _amount), "Withdrawal transfer failed"
    
    log StakeWithdrawn(msg.sender, _amount, staker_info.stake_amount)

@internal
def _distribute_staking_rewards(_premium_amount: uint256):
    """
    Distribute staking rewards from premium collection
    
    Args:
        _premium_amount: Premium amount collected
    """
    if self.total_stake == 0:
        return  # No stakers to reward
    
    # Calculate reward amount (20% of premium goes to stakers)
    reward_amount: uint256 = (_premium_amount * 2000) / 10000  # 20%
    
    # Update accumulated rewards per share
    reward_per_share: uint256 = (reward_amount * 10**18) / self.total_stake
    self.acc_reward_per_share += reward_per_share

@external
def claim_staking_rewards():
    """
    Claim accumulated staking rewards
    """
    staker_info: StakerInfo = self.stakers[msg.sender]
    assert staker_info.stake_amount > 0, "No stake to claim rewards for"
    
    # Calculate rewards
    pending_rewards: uint256 = (staker_info.stake_amount * self.acc_reward_per_share) / 10**18
    rewards_to_claim: uint256 = pending_rewards - staker_info.reward_debt
    
    assert rewards_to_claim > 0, "No rewards to claim"
    
    # Ensure pool has sufficient USDC
    pool_balance: uint256 = USDC_TOKEN.balanceOf(self)
    assert pool_balance >= rewards_to_claim, "Insufficient pool funds for rewards"
    
    # Update staker info
    staker_info.reward_debt = pending_rewards
    staker_info.total_rewards += rewards_to_claim
    staker_info.last_claim_time = block.timestamp
    self.stakers[msg.sender] = staker_info
    
    # Transfer rewards
    assert USDC_TOKEN.transfer(msg.sender, rewards_to_claim), "Reward transfer failed"

# Governance Functions
@external
def add_claim_validator(_validator: address):
    """Add a claim validator"""
    assert msg.sender == self.owner, "Only owner"
    self.claim_validators[_validator] = True

@external
def remove_claim_validator(_validator: address):
    """Remove a claim validator"""
    assert msg.sender == self.owner, "Only owner"
    self.claim_validators[_validator] = False

@external
def set_emergency_pause(_paused: bool):
    """Set emergency pause state"""
    assert msg.sender == self.owner, "Only owner"
    self.emergency_pause = _paused

@external
def update_base_premium_rate(_tier: uint8, _new_rate: uint256):
    """Update base premium rate for a verification tier"""
    assert msg.sender == self.owner, "Only owner"
    assert _tier < 5, "Invalid tier"
    assert _new_rate >= MIN_PREMIUM_RATE and _new_rate <= MAX_PREMIUM_RATE, "Invalid rate"
    self.base_premium_rates[_tier] = _new_rate

@external
def update_max_coverage_amount(_tier: uint8, _new_amount: uint256):
    """Update max coverage amount for a verification tier"""
    assert msg.sender == self.owner, "Only owner"
    assert _tier < 5, "Invalid tier"
    assert _new_amount <= MAX_COVERAGE_PER_TRANSACTION, "Exceeds global maximum"
    self.max_coverage_amounts[_tier] = _new_amount

# View Functions
@view
@external
def get_policy(_policy_id: bytes32) -> InsurancePolicy:
    """Get policy details"""
    return self.policies[_policy_id]

@view
@external
def get_claim(_claim_id: bytes32) -> Claim:
    """Get claim details"""
    return self.claims[_claim_id]

@view
@external
def get_staker_info(_staker: address) -> StakerInfo:
    """Get staker information"""
    return self.stakers[_staker]

@view
@external
def get_pool_stats() -> (uint256, uint256, uint256, uint256, uint256, uint256):
    """
    Get pool statistics
    
    Returns:
        total_premiums_collected: Total premiums collected
        total_claims_paid: Total claims paid out
        total_policies_issued: Total policies issued
        active_policy_count: Number of active policies
        total_stake: Total amount staked
        pool_balance: Current USDC balance
    """
    pool_balance: uint256 = USDC_TOKEN.balanceOf(self)
    return (
        self.total_premiums_collected,
        self.total_claims_paid,
        self.total_policies_issued,
        self.active_policy_count,
        self.total_stake,
        pool_balance
    )

@view
@external
def calculate_premium(_agent_address: address, _coverage_amount: uint256, _duration: uint256) -> uint256:
    """
    Calculate premium for a potential policy
    
    Args:
        _agent_address: Address of the agent
        _coverage_amount: Coverage amount requested
        _duration: Policy duration in seconds
        
    Returns:
        premium_amount: Calculated premium amount
    """
    verification_tier: uint8 = AGENT_IDENTITY_REGISTRY.get_agent_verification_tier(_agent_address)
    assert verification_tier < 5, "Invalid verification tier"
    
    risk_assessment: RiskAssessment = self._calculate_risk_assessment(_agent_address, _coverage_amount)
    base_rate: uint256 = self.base_premium_rates[verification_tier]
    premium_rate: uint256 = (base_rate * risk_assessment.premium_multiplier) / RISK_MULTIPLIER_BASE
    
    # Ensure premium rate is within bounds
    if premium_rate > MAX_PREMIUM_RATE:
        premium_rate = MAX_PREMIUM_RATE
    elif premium_rate < MIN_PREMIUM_RATE:
        premium_rate = MIN_PREMIUM_RATE
    
    # Calculate premium amount (annualized)
    premium_amount: uint256 = (_coverage_amount * premium_rate * _duration) / (31536000 * 10000)
    
    return premium_amount

# Ownership Transfer
@external
def transfer_ownership(_new_owner: address):
    """Transfer contract ownership"""
    assert msg.sender == self.owner, "Only owner"
    self.pending_owner = _new_owner

@external
def accept_ownership():
    """Accept contract ownership"""
    assert msg.sender == self.pending_owner, "Not pending owner"
    self.owner = msg.sender
    self.pending_owner = empty(address)