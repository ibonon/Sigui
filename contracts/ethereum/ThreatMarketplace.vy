# @version ^0.4.3
"""
ThreatMarketplace.vy - Decentralized Threat Intelligence Marketplace
Phase 2: Sigui Protocol - The AWS of Trust Infrastructure for the Autonomous Economy

Features:
- Pattern submission with royalties
- Automatic royalty distribution to contributors
- Real-time protection for all agents
- Quality scoring and validation
- Revenue sharing mechanism
"""

# Interfaces
interface IERC20:
    def transfer(_to: address, _value: uint256) -> bool: nonpayable
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def balanceOf(_owner: address) -> uint256: view

interface IAgentIdentityRegistry:
    def is_verified_agent(agent_address: address) -> bool: view
    def get_agent_reputation(agent_address: address) -> uint256: view

# Events
event PatternSubmitted:
    pattern_id: indexed(bytes32)
    contributor: indexed(address)
    threat_type: String[50]
    severity: uint8
    reward_amount: uint256

event PatternValidated:
    pattern_id: indexed(bytes32)
    validator: indexed(address)
    quality_score: uint8
    is_approved: bool

event RoyaltyDistributed:
    pattern_id: indexed(bytes32)
    contributor: indexed(address)
    amount: uint256
    protected_agents: uint256

event AgentProtected:
    agent_address: indexed(address)
    pattern_id: indexed(bytes32)
    threat_blocked: bool

# Structs
struct ThreatPattern:
    contributor: address
    threat_type: String[50]
    description: String[500]
    severity: uint8  # 1-10
    pattern_hash: bytes32
    detection_code: String[1000]  # Encoded detection logic
    created_at: uint256
    quality_score: uint8  # 0-100
    validation_count: uint256
    is_active: bool
    total_royalties_earned: uint256
    times_used: uint256
    agents_protected: uint256

struct ContributorProfile:
    total_patterns: uint256
    total_royalties: uint256
    reputation_score: uint256  # 0-1000
    successful_detections: uint256
    false_positives: uint256
    last_submission: uint256

struct RoyaltyDistribution:
    contributor: address
    pattern_id: bytes32
    amount: uint256
    distributed_at: uint256
    protected_agents: uint256

# State Variables
USDC_TOKEN: public(immutable(IERC20))
AGENT_IDENTITY_REGISTRY: public(immutable(IAgentIdentityRegistry))

# Pattern storage
threat_patterns: public(HashMap[bytes32, ThreatPattern])
pattern_ids: public(bytes32[1000])  # Max 1000 patterns
pattern_count: public(uint256)

# Contributor management
contributors: public(HashMap[address, ContributorProfile])
contributor_addresses: public(address[200])  # Max 200 contributors
contributor_count: public(uint256)

# Royalty system
royalty_pool: public(uint256)
royalty_distributions: public(HashMap[bytes32, RoyaltyDistribution[50]])  # Max 50 distributions per pattern
distribution_counts: public(HashMap[bytes32, uint256])

# Validation system
validators: public(HashMap[address, bool])
validation_threshold: public(uint8)  # Minimum score to approve
submission_fee: public(uint256)
validation_reward: public(uint256)

# Platform fees
platform_fee_percentage: public(uint256)  # 20% = 2000 basis points
contributor_percentage: public(uint256)  # 80% = 8000 basis points

# Governance
owner: public(address)
pending_owner: public(address)

# Constants
MAX_SEVERITY: constant(uint8) = 10
MIN_QUALITY_SCORE: constant(uint8) = 70
MAX_PATTERNS: constant(uint256) = 1000
ROYALTY_DISTRIBUTION_INTERVAL: constant(uint256) = 86400  # 24 hours

@external
def __init__(_usdc_token: address, _agent_registry: address):
    """
    Initialize the ThreatMarketplace
    
    Args:
        _usdc_token: USDC token contract address
        _agent_registry: Agent Identity Registry contract address
    """
    self.owner = msg.sender
    USDC_TOKEN = IERC20(_usdc_token)
    AGENT_IDENTITY_REGISTRY = IAgentIdentityRegistry(_agent_registry)
    
    # Set initial parameters
    self.validation_threshold = 70
    self.submission_fee = 100 * 10**6  # 100 USDC (6 decimals)
    self.validation_reward = 10 * 10**6  # 10 USDC
    self.platform_fee_percentage = 2000  # 20%
    self.contributor_percentage = 8000  # 80%

# Pattern Submission
def submit_pattern(
    _threat_type: String[50],
    _description: String[500],
    _severity: uint8,
    _pattern_hash: bytes32,
    _detection_code: String[1000]
) -> bytes32:
    """
    Submit a new threat pattern to the marketplace
    
    Args:
        _threat_type: Type of threat (e.g., "reentrancy", "flash_loan_attack")
        _description: Detailed description of the threat pattern
        _severity: Severity level (1-10)
        _pattern_hash: Hash of the pattern for verification
        _detection_code: Encoded detection logic
        
    Returns:
        pattern_id: Unique identifier for the submitted pattern
    """
    assert _severity >= 1 and _severity <= MAX_SEVERITY, "Invalid severity"
    assert len(_description) > 0, "Description required"
    assert len(_detection_code) > 0, "Detection code required"
    assert self.pattern_count < MAX_PATTERNS, "Pattern limit reached"
    
    # Collect submission fee
    assert USDC_TOKEN.transferFrom(msg.sender, self, self.submission_fee), "Fee transfer failed"
    
    # Generate unique pattern ID
    pattern_id: bytes32 = keccak256(_abi_encode(msg.sender, _pattern_hash, block.timestamp))
    
    # Create pattern struct
    pattern: ThreatPattern = ThreatPattern({
        contributor: msg.sender,
        threat_type: _threat_type,
        description: _description,
        severity: _severity,
        pattern_hash: _pattern_hash,
        detection_code: _detection_code,
        created_at: block.timestamp,
        quality_score: 0,  # Not validated yet
        validation_count: 0,
        is_active: False,
        total_royalties_earned: 0,
        times_used: 0,
        agents_protected: 0
    })
    
    # Store pattern
    self.threat_patterns[pattern_id] = pattern
    self.pattern_ids[self.pattern_count] = pattern_id
    self.pattern_count += 1
    
    # Update contributor profile
    if self.contributors[msg.sender].total_patterns == 0:
        # New contributor
        self.contributor_addresses[self.contributor_count] = msg.sender
        self.contributor_count += 1
        
        # Initialize contributor profile
        self.contributors[msg.sender] = ContributorProfile({
            total_patterns: 0,
            total_royalties: 0,
            reputation_score: 500,  # Start with neutral reputation
            successful_detections: 0,
            false_positives: 0,
            last_submission: block.timestamp
        })
    
    # Update contributor stats
    self.contributors[msg.sender].total_patterns += 1
    self.contributors[msg.sender].last_submission = block.timestamp
    
    log PatternSubmitted(pattern_id, msg.sender, _threat_type, _severity, self.submission_fee)
    
    return pattern_id

# Pattern Validation
@external
def validate_pattern(_pattern_id: bytes32, _quality_score: uint8, _approve: bool):
    """
    Validate a submitted threat pattern
    
    Args:
        _pattern_id: ID of the pattern to validate
        _quality_score: Quality score (0-100)
        _approve: Whether to approve the pattern
    """
    assert self.validators[msg.sender], "Not authorized validator"
    assert _quality_score <= 100, "Invalid quality score"
    
    pattern: ThreatPattern = self.threat_patterns[_pattern_id]
    assert pattern.contributor != empty(address), "Pattern not found"
    assert not pattern.is_active, "Pattern already validated"
    
    # Update pattern validation
    current_score: uint256 = pattern.quality_score * pattern.validation_count
    new_score: uint256 = (current_score + _quality_score) / (pattern.validation_count + 1)
    
    pattern.quality_score = convert(new_score, uint8)
    pattern.validation_count += 1
    
    # Activate pattern if quality threshold met
    if pattern.quality_score >= self.validation_threshold:
        pattern.is_active = True
        
        # Reward validator
        assert USDC_TOKEN.transfer(msg.sender, self.validation_reward), "Validator reward failed"
    
    log PatternValidated(_pattern_id, msg.sender, pattern.quality_score, pattern.is_active)

# Threat Detection and Protection
@external
def detect_threat(_agent_address: address, _transaction_data: bytes, _transaction_value: uint256) -> bool:
    """
    Detect threats using marketplace patterns
    
    Args:
        _agent_address: Address of the agent being protected
        _transaction_data: Transaction data to analyze
        _transaction_value: Value of the transaction
        
    Returns:
        threat_detected: True if threat was detected and blocked
    """
    threat_detected: bool = False
    protecting_patterns: bytes32[10] = empty(bytes32[10])
    protecting_count: uint256 = 0
    
    # Check all active patterns
    for i in range(MAX_PATTERNS):
        if i >= self.pattern_count:
            break
            
        pattern_id: bytes32 = self.pattern_ids[i]
        pattern: ThreatPattern = self.threat_patterns[pattern_id]
        
        if pattern.is_active and protecting_count < 10:
            # Simulate pattern matching (in real implementation, this would execute detection code)
            if self._match_pattern(pattern_id, _transaction_data, _transaction_value):
                threat_detected = True
                protecting_patterns[protecting_count] = pattern_id
                protecting_count += 1
                
                # Update pattern statistics
                pattern.times_used += 1
                pattern.agents_protected += 1
    
    # Distribute royalties if threat was blocked
    if threat_detected and protecting_count > 0:
        self._distribute_royalties(protecting_patterns, protecting_count, 1)  # Protecting 1 agent
    
    log AgentProtected(_agent_address, protecting_patterns[0], threat_detected)
    return threat_detected

# Royalty Distribution
@internal
def _distribute_royalties(_pattern_ids: bytes32[10], _pattern_count: uint256, _protected_agents: uint256):
    """
    Distribute royalties to pattern contributors
    
    Args:
        _pattern_ids: Array of pattern IDs that contributed to protection
        _pattern_count: Number of protecting patterns
        _protected_agents: Number of agents protected
    """
    if self.royalty_pool == 0:
        return  # No royalties to distribute
    
    # Calculate total royalty to distribute
    total_royalty: uint256 = min(self.royalty_pool, 100 * 10**6)  # Max 100 USDC per distribution
    if total_royalty == 0:
        return
    
    # Calculate royalty per pattern
    royalty_per_pattern: uint256 = total_royalty / _pattern_count
    
    # Distribute to each pattern contributor
    for i in range(10):
        if i >= _pattern_count:
            break
            
        pattern_id: bytes32 = _pattern_ids[i]
        pattern: ThreatPattern = self.threat_patterns[pattern_id]
        
        contributor: address = pattern.contributor
        contributor_royalty: uint256 = (royalty_per_pattern * self.contributor_percentage) / 10000
        
        # Transfer royalty to contributor
        assert USDC_TOKEN.transfer(contributor, contributor_royalty), "Royalty transfer failed"
        
        # Update statistics
        pattern.total_royalties_earned += contributor_royalty
        self.contributors[contributor].total_royalties += contributor_royalty
        
        # Record distribution
        dist_count: uint256 = self.distribution_counts[pattern_id]
        if dist_count < 50:
            self.royalty_distributions[pattern_id][dist_count] = RoyaltyDistribution({
                contributor: contributor,
                pattern_id: pattern_id,
                amount: contributor_royalty,
                distributed_at: block.timestamp,
                protected_agents: _protected_agents
            })
            self.distribution_counts[pattern_id] = dist_count + 1
        
        log RoyaltyDistributed(pattern_id, contributor, contributor_royalty, _protected_agents)
    
    # Update royalty pool
    self.royalty_pool -= total_royalty

# Pattern Matching (simplified for demonstration)
@internal
def _match_pattern(_pattern_id: bytes32, _transaction_data: bytes, _transaction_value: uint256) -> bool:
    """
    Simulate pattern matching (in real implementation, this would execute detection code)
    
    Args:
        _pattern_id: ID of the pattern to match
        _transaction_data: Transaction data to analyze
        _transaction_value: Transaction value
        
    Returns:
        match_found: True if pattern matches
    """
    # Simplified pattern matching based on hash comparison
    pattern: ThreatPattern = self.threat_patterns[_pattern_id]
    
    # Generate transaction hash for comparison
    tx_hash: bytes32 = keccak256(_abi_encode(_transaction_data, _transaction_value))
    
    # Simple hash-based matching (in reality, this would be much more sophisticated)
    return (tx_hash % pattern.severity) == (pattern.pattern_hash % pattern.severity)

# Governance Functions
@external
def add_validator(_validator: address):
    """Add a new validator to the system"""
    assert msg.sender == self.owner, "Only owner"
    self.validators[_validator] = True

@external
def remove_validator(_validator: address):
    """Remove a validator from the system"""
    assert msg.sender == self.owner, "Only owner"
    self.validators[_validator] = False

@external
def update_validation_threshold(_new_threshold: uint8):
    """Update the validation threshold"""
    assert msg.sender == self.owner, "Only owner"
    assert _new_threshold <= 100, "Invalid threshold"
    self.validation_threshold = _new_threshold

@external
def update_submission_fee(_new_fee: uint256):
    """Update the pattern submission fee"""
    assert msg.sender == self.owner, "Only owner"
    self.submission_fee = _new_fee

@external
def update_platform_fees(_platform_percentage: uint256, _contributor_percentage: uint256):
    """Update platform fee distribution"""
    assert msg.sender == self.owner, "Only owner"
    assert _platform_percentage + _contributor_percentage == 10000, "Must sum to 100%"
    self.platform_fee_percentage = _platform_percentage
    self.contributor_percentage = _contributor_percentage

# View Functions
@view
@external
def get_pattern(_pattern_id: bytes32) -> ThreatPattern:
    """Get threat pattern details"""
    return self.threat_patterns[_pattern_id]

@view
@external
def get_contributor_profile(_contributor: address) -> ContributorProfile:
    """Get contributor profile"""
    return self.contributors[_contributor]

@view
@external
def get_active_patterns() -> bytes32[100]:
    """Get all active pattern IDs"""
    active_patterns: bytes32[100] = empty(bytes32[100])
    active_count: uint256 = 0
    
    for i in range(MAX_PATTERNS):
        if i >= self.pattern_count or active_count >= 100:
            break
            
        pattern_id: bytes32 = self.pattern_ids[i]
        pattern: ThreatPattern = self.threat_patterns[pattern_id]
        
        if pattern.is_active:
            active_patterns[active_count] = pattern_id
            active_count += 1
    
    return active_patterns

@view
@external
def get_marketplace_stats() -> (uint256, uint256, uint256, uint256, uint256):
    """
    Get marketplace statistics
    
    Returns:
        total_patterns: Total number of patterns
        active_patterns: Number of active patterns
        total_contributors: Number of contributors
        total_royalties_paid: Total royalties distributed
        royalty_pool_balance: Current royalty pool balance
    """
    total_royalties: uint256 = 0
    
    # Calculate total royalties paid
    for i in range(MAX_PATTERNS):
        if i >= self.pattern_count:
            break
            
        pattern_id: bytes32 = self.pattern_ids[i]
        pattern: ThreatPattern = self.threat_patterns[pattern_id]
        total_royalties += pattern.total_royalties_earned
    
    return (
        self.pattern_count,
        self._count_active_patterns(),
        self.contributor_count,
        total_royalties,
        self.royalty_pool
    )

@internal
@view
def _count_active_patterns() -> uint256:
    """Count number of active patterns"""
    active_count: uint256 = 0
    
    for i in range(MAX_PATTERNS):
        if i >= self.pattern_count:
            break
            
        pattern_id: bytes32 = self.pattern_ids[i]
        pattern: ThreatPattern = self.threat_patterns[pattern_id]
        
        if pattern.is_active:
            active_count += 1
    
    return active_count

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