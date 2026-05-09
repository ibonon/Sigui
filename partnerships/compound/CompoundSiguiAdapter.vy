# @version 0.4.3
"""
@title Compound-Sigui Security Adapter
@notice Security adapter integrating Sigui threat detection with Compound protocol
@dev Protects Compound users from AI agent-based attacks
"""

# Interfaces
interface ICompoundComptroller:
    def enterMarkets(cTokens: address[100]) -> uint256[100]: nonpayable
    def exitMarket(cToken: address) -> uint256: nonpayable
    def getAssetsIn(account: address) -> address[100]: view
    def getAccountLiquidity(account: address) -> (uint256, uint256, uint256): view
    def markets(cToken: address) -> (bool, uint256): view

interface ICToken:
    def borrow(borrowAmount: uint256) -> uint256: nonpayable
    def mint(mintAmount: uint256) -> uint256: nonpayable
    def redeem(redeemTokens: uint256) -> uint256: nonpayable
    def redeemUnderlying(redeemAmount: uint256) -> uint256: nonpayable
    def repayBorrow(repayAmount: uint256) -> uint256: nonpayable
    def liquidateBorrow(borrower: address, repayAmount: uint256, cTokenCollateral: address) -> uint256: nonpayable
    def balanceOf(owner: address) -> uint256: view
    def borrowBalanceStored(account: address) -> uint256: view
    def exchangeRateStored() -> uint256: view
    def getCash() -> uint256: view
    def totalBorrows() -> uint256: view
    def totalReserves() -> uint256: view

interface ISiguiThreatRegistry:
    def recordAttack(agent: address, pattern: bytes32, amount_usdc6: uint256, risk_milli: uint256, layer: uint256): nonpayable
    def isKnownAttacker(agent: address) -> bool: view
    def getAgentBlockCount(agent: address) -> uint256: view

interface ISiguiAgentRegistry:
    def getAgentIdentity(agent_address: address) -> (String[64], bytes32, uint8, uint16, uint256, uint256, String[128], bool, uint256, uint256): view
    def calculateEffectiveReputation(agent_address: address) -> uint16: view
    def isAgentVerified(agent_address: address) -> bool: view

# Events
event TransactionProtected(
    user: indexed(address),
    cToken: indexed(address),
    action: String[32],
    amount: uint256,
    risk_score: uint256,
    allowed: bool
)

event ThreatDetected(
    agent: indexed(address),
    pattern: indexed(bytes32),
    cToken: indexed(address),
    amount: uint256,
    risk_score: uint256
)

event RiskParametersUpdated(
    borrow_threshold: uint256,
    supply_threshold: uint256,
    liquidation_threshold: uint256,
    reputation_multiplier: uint256
)

# State Variables
COMPTROLLER: public(immutable(ICompoundComptroller))
SIGUI_THREAT_REGISTRY: public(immutable(ISiguiThreatRegistry))
SIGUI_AGENT_REGISTRY: public(immutable(ISiguiAgentRegistry))

owner: public(address)
pending_owner: public(address)

# Risk Parameters
borrow_risk_threshold: public(uint256)  # Max risk score for borrowing (0-1000)
supply_risk_threshold: public(uint256)    # Max risk score for supplying (0-1000)
liquidation_risk_threshold: public(uint256)  # Max risk score for liquidation (0-1000)
reputation_multiplier: public(uint256)    # Multiplier for reputation scoring

# Protection Stats
total_protected_transactions: public(uint256)
total_blocked_transactions: public(uint256)
total_usdc_protected: public(uint256)    # In USDC 6-decimal format

# Agent Risk Tracking
agent_risk_scores: public(HashMap[address, uint256])
agent_transaction_counts: public(HashMap[address, uint256])

# Emergency Controls
paused: public(bool)
protected_cTokens: public(HashMap[address, bool])

@external
def __init__(_comptroller: address, _sigui_threat_registry: address, _sigui_agent_registry: address):
    """Initialize the Compound-Sigui Security Adapter"""
    COMPTROLLER = ICompoundComptroller(_comptroller)
    SIGUI_THREAT_REGISTRY = ISiguiThreatRegistry(_sigui_threat_registry)
    SIGUI_AGENT_REGISTRY = ISiguiAgentRegistry(_sigui_agent_registry)
    
    self.owner = msg.sender
    self.borrow_risk_threshold = 300      # Conservative: 0.30 risk score max
    self.supply_risk_threshold = 400      # Medium: 0.40 risk score max  
    self.liquidation_risk_threshold = 200  # Very conservative: 0.20 risk score max
    self.reputation_multiplier = 150       # 1.5x multiplier for good reputation
    
    self.total_protected_transactions = 0
    self.total_blocked_transactions = 0
    self.total_usdc_protected = 0
    self.paused = False

# Risk Assessment Functions
@internal
def _assess_transaction_risk(agent: address, amount: uint256, action: String[32]) -> (bool, uint256, String[64]):
    """Assess transaction risk using Sigui intelligence"""
    
    if self.paused:
        return (True, 0, "System paused - allowing transaction")
    
    # Check if agent is known attacker
    if SIGUI_THREAT_REGISTRY.isKnownAttacker(agent):
        return (False, 1000, "Known attacker - transaction blocked")
    
    # Get agent reputation from Sigui
    effective_reputation: uint16 = SIGUI_AGENT_REGISTRY.calculateEffectiveReputation(agent)
    is_verified: bool = SIGUI_AGENT_REGISTRY.isAgentVerified(agent)
    
    # Base risk calculation
    base_risk: uint256 = 500  # Start with 50% base risk
    
    # Adjust based on reputation
    if effective_reputation >= 800:  # High reputation
        base_risk = 100
    elif effective_reputation >= 600:  # Medium reputation
        base_risk = 250
    elif effective_reputation >= 400:  # Low reputation
        base_risk = 400
    else:  # Very low reputation
        base_risk = 700
    
    # Apply reputation multiplier for good agents
    if effective_reputation >= 700 and is_verified:
        base_risk = base_risk * 100 / self.reputation_multiplier  # Reduce risk for good agents
    
    # Amount-based risk adjustment
    if amount > convert(1000000 * 1000000, uint256):  # >$1M
        base_risk += 200
    elif amount > convert(100000 * 1000000, uint256):  # >$100K
        base_risk += 100
    
    # Action-based risk threshold
    risk_threshold: uint256 = 0
    if action == "borrow":
        risk_threshold = self.borrow_risk_threshold
    elif action == "supply":
        risk_threshold = self.supply_risk_threshold
    elif action == "liquidate":
        risk_threshold = self.liquidation_risk_threshold
    
    # Final risk score (cap at 1000)
    final_risk: uint256 = min(base_risk, 1000)
    
    # Decision
    allowed: bool = final_risk <= risk_threshold
    reason: String[64] = ""
    
    if allowed:
        reason = "Transaction approved - risk within threshold"
    else:
        reason = "Transaction blocked - risk exceeds threshold"
    
    return (allowed, final_risk, reason)

@internal
def _record_threat_if_blocked(agent: address, pattern: bytes32, amount: uint256, risk_score: uint256, action: String[32]):
    """Record threat pattern if transaction is blocked"""
    if risk_score > 500:  # Significant risk
        amount_usdc6: uint256 = amount / 1000000  # Convert to USDC 6-decimal
        
        # Determine threat layer based on action
        layer: uint256 = 1  # Default: behavior layer
        if action == "borrow":
            layer = 2  # Borrowing pattern
        elif action == "liquidate":
            layer = 3  # Liquidation pattern
        
        SIGUI_THREAT_REGISTRY.recordAttack(agent, pattern, amount_usdc6, risk_score, layer)
        
        log ThreatDetected(agent, pattern, empty(address), amount, risk_score)

# Protected Transaction Functions
@external
def protectedBorrow(cToken: address, borrowAmount: uint256) -> uint256:
    """Protected borrow with Sigui security assessment"""
    
    # Risk assessment
    (allowed, risk_score, reason) = self._assess_transaction_risk(msg.sender, borrowAmount, "borrow")
    
    # Update stats
    self.agent_risk_scores[msg.sender] = risk_score
    self.agent_transaction_counts[msg.sender] += 1
    self.total_protected_transactions += 1
    
    if not allowed:
        self.total_blocked_transactions += 1
        self._record_threat_if_blocked(msg.sender, keccak256("COMPOUND_BORROW"), borrowAmount, risk_score, "borrow")
        
        log TransactionProtected(msg.sender, cToken, "borrow", borrowAmount, risk_score, False)
        raise "Transaction blocked by Sigui security - risk too high"
    
    # Record protection success
    self.total_usdc_protected += borrowAmount / 1000000  # Convert to USDC 6-decimal
    log TransactionProtected(msg.sender, cToken, "borrow", borrowAmount, risk_score, True)
    
    # Execute borrow through Compound
    return ICToken(cToken).borrow(borrowAmount)

@external
def protectedSupply(cToken: address, supplyAmount: uint256) -> uint256:
    """Protected supply with Sigui security assessment"""
    
    # Risk assessment
    (allowed, risk_score, reason) = self._assess_transaction_risk(msg.sender, supplyAmount, "supply")
    
    # Update stats
    self.agent_risk_scores[msg.sender] = risk_score
    self.agent_transaction_counts[msg.sender] += 1
    self.total_protected_transactions += 1
    
    if not allowed:
        self.total_blocked_transactions += 1
        self._record_threat_if_blocked(msg.sender, keccak256("COMPOUND_SUPPLY"), supplyAmount, risk_score, "supply")
        
        log TransactionProtected(msg.sender, cToken, "supply", supplyAmount, risk_score, False)
        raise "Transaction blocked by Sigui security - risk too high"
    
    # Record protection success
    self.total_usdc_protected += supplyAmount / 1000000  # Convert to USDC 6-decimal
    log TransactionProtected(msg.sender, cToken, "supply", supplyAmount, risk_score, True)
    
    # Execute supply through Compound
    return ICToken(cToken).mint(supplyAmount)

@external
def protectedLiquidate(cTokenBorrowed: address, cTokenCollateral: address, borrower: address, repayAmount: uint256) -> uint256:
    """Protected liquidation with Sigui security assessment"""
    
    # Risk assessment for liquidator
    (allowed, risk_score, reason) = self._assess_transaction_risk(msg.sender, repayAmount, "liquidate")
    
    # Update stats
    self.agent_risk_scores[msg.sender] = risk_score
    self.agent_transaction_counts[msg.sender] += 1
    self.total_protected_transactions += 1
    
    if not allowed:
        self.total_blocked_transactions += 1
        self._record_threat_if_blocked(msg.sender, keccak256("COMPOUND_LIQUIDATE"), repayAmount, risk_score, "liquidate")
        
        log TransactionProtected(msg.sender, cTokenBorrowed, "liquidate", repayAmount, risk_score, False)
        raise "Transaction blocked by Sigui security - risk too high"
    
    # Record protection success
    self.total_usdc_protected += repayAmount / 1000000  # Convert to USDC 6-decimal
    log TransactionProtected(msg.sender, cTokenBorrowed, "liquidate", repayAmount, risk_score, True)
    
    # Execute liquidation through Compound
    return ICToken(cTokenBorrowed).liquidateBorrow(borrower, repayAmount, cTokenCollateral)

# Risk Parameter Management
@external
def updateRiskParameters(
    _borrow_threshold: uint256,
    _supply_threshold: uint256,
    _liquidation_threshold: uint256,
    _reputation_multiplier: uint256
):
    """Update risk assessment parameters"""
    assert msg.sender == self.owner, "Only owner"
    assert _borrow_threshold <= 1000, "Borrow threshold too high"
    assert _supply_threshold <= 1000, "Supply threshold too high"
    assert _liquidation_threshold <= 1000, "Liquidation threshold too high"
    assert _reputation_multiplier >= 100 and _reputation_multiplier <= 300, "Invalid reputation multiplier"
    
    self.borrow_risk_threshold = _borrow_threshold
    self.supply_risk_threshold = _supply_threshold
    self.liquidation_risk_threshold = _liquidation_threshold
    self.reputation_multiplier = _reputation_multiplier
    
    log RiskParametersUpdated(_borrow_threshold, _supply_threshold, _liquidation_threshold, _reputation_multiplier)

# Emergency Controls
@external
def pause():
    """Emergency pause all protections"""
    assert msg.sender == self.owner, "Only owner"
    self.paused = True

@external
def unpause():
    """Resume protections"""
    assert msg.sender == self.owner, "Only owner"
    self.paused = False

@external
def addProtectedCToken(cToken: address):
    """Add cToken to protected list"""
    assert msg.sender == self.owner, "Only owner"
    self.protected_cTokens[cToken] = True

@external
def removeProtectedCToken(cToken: address):
    """Remove cToken from protected list"""
    assert msg.sender == self.owner, "Only owner"
    self.protected_cTokens[cToken] = False

# Governance Functions
@external
def transferOwnership(new_owner: address):
    """Transfer contract ownership"""
    assert msg.sender == self.owner, "Only owner"
    self.pending_owner = new_owner

@external
def acceptOwnership():
    """Accept ownership transfer"""
    assert msg.sender == self.pending_owner, "Not pending owner"
    self.owner = msg.sender
    self.pending_owner = empty(address)

# View Functions
@view
@external
def getProtectionStats() -> (uint256, uint256, uint256):
    """Get protection statistics"""
    return (self.total_protected_transactions, self.total_blocked_transactions, self.total_usdc_protected)

@view
@external
def getAgentRiskScore(agent: address) -> uint256:
    """Get agent's current risk score"""
    return self.agent_risk_scores[agent]

@view
@external
def getAgentTransactionCount(agent: address) -> uint256:
    """Get agent's transaction count"""
    return self.agent_transaction_counts[agent]

@view
@external
def isCTokenProtected(cToken: address) -> bool:
    """Check if cToken is protected"""
    return self.protected_cTokens[cToken]

@view
@external
def getRiskParameters() -> (uint256, uint256, uint256, uint256):
    """Get current risk parameters"""
    return (self.borrow_risk_threshold, self.supply_risk_threshold, self.liquidation_risk_threshold, self.reputation_multiplier)