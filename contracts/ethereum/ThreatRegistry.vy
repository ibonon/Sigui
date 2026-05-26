# @version 0.4.3
# @title ThreatRegistry
# @notice Onchain threat intelligence registry for ArcWarden v3.0.
#         Every BLOCK decision is permanently recorded here.
#         Only the ArcWarden oracle (owner) can write. Anyone can read.
# @dev    Security patterns applied:
#         - Owner-only write access (Checks-Effects-Interactions)
#         - @nonreentrant guard on state-changing functions
#         - Full input validation before any state modification
#         - Anti-replay: same pattern_hash rate-limited (2s minimum gap)
#         - Emergency circuit breaker (pause/unpause)
#         - Ownership transfer with zero-address guard
#         - Immutable by design: no proxy, no selfdestruct
#         - All state changes emit events (full audit trail)
# @license MIT

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_ATTACKS: constant(uint256) = 500_000
MIN_RECORD_INTERVAL_S: constant(uint256) = 2  # anti-replay: min gap between same pattern

# ── Structs ────────────────────────────────────────────────────────────────────
struct AttackRecord:
    agent_address:  address    # agent's Arc wallet (cryptographic identity)
    pattern_hash:   bytes32    # keccak256(action_type + destination + amount_bucket)
    amount_usdc6:   uint256    # amount × 1_000_000 (6-decimal precision)
    risk_milli:     uint256    # risk_score × 1000 (0.871 → 871)
    layer:          uint8      # 1=behavior 2=splitting 3=service 4=contract
    blocked_at:     uint256    # block.timestamp at time of recording

# ── State variables ────────────────────────────────────────────────────────────
owner: public(address)
paused: public(bool)

total_attacks:          public(uint256)
total_usdc_protected6:  public(uint256)   # cumulative in 6-decimal USDC
guaranty_fund6:         public(uint256)   # bonded USDC for insurance

attacks:              public(HashMap[uint256, AttackRecord])
agent_blocks:         public(HashMap[address, uint256])     # wallet → block count
pattern_first_seen:   public(HashMap[bytes32, uint256])     # first occurrence timestamp
pattern_last_seen:    HashMap[bytes32, uint256]              # internal: anti-replay

# ── Events ─────────────────────────────────────────────────────────────────────
event AttackBlocked:
    idx:          indexed(uint256)
    agent:        indexed(address)
    pattern:      indexed(bytes32)
    amount_usdc6: uint256
    risk_milli:   uint256
    layer:        uint8

event OwnershipTransferred:
    prev: indexed(address)
    next: indexed(address)

event RegistryPaused:
    caller: indexed(address)

event RegistryUnpaused:
    caller: indexed(address)

event FundDeposited:
    amount6: uint256
    new_total6: uint256

event FundWithdrawn:
    amount6: uint256
    new_total6: uint256

# ── Constructor ────────────────────────────────────────────────────────────────
@deploy
def __init__():
    """Deploy the ThreatRegistry. Deployer becomes the owner (ArcWarden oracle)."""
    self.owner   = msg.sender
    self.paused  = False

# ── Internal guards ────────────────────────────────────────────────────────────
@internal
def _require_owner():
    assert msg.sender == self.owner, "ThreatRegistry: caller is not owner"

@internal
def _require_active():
    assert not self.paused, "ThreatRegistry: contract is paused"

# ── Write: record attack ───────────────────────────────────────────────────────
@external
@nonreentrant
def recordAttack(
    agent: address,
    pattern: bytes32,
    amount_usdc6: uint256,
    risk_milli: uint256,
    layer: uint8,
):
    """
    @notice Record a blocked attack. Only callable by the ArcWarden oracle (owner).
    @param agent         Agent's Arc wallet address (cryptographic identity)
    @param pattern       keccak256(action_type + destination + amount_bucket)
    @param amount_usdc6  Transaction amount × 1_000_000 (6-decimal USDC)
    @param risk_milli    Risk score × 1000 (e.g. 0.871 → 871, max 1000)
    @param layer         Security layer: 1=behavior 2=splitting 3=service 4=contract
    """
    # ── CHECKS ────────────────────────────────────────────────────────────────
    self._require_owner()
    self._require_active()

    assert agent   != empty(address),  "ThreatRegistry: agent cannot be zero address"
    assert pattern != empty(bytes32),  "ThreatRegistry: pattern cannot be zero hash"
    assert risk_milli   <= 1000,       "ThreatRegistry: risk_milli must be <= 1000"
    assert layer >= 1 and layer <= 4,  "ThreatRegistry: layer must be 1, 2, 3 or 4"
    assert self.total_attacks < MAX_ATTACKS, "ThreatRegistry: registry full"

    # Anti-replay: same attack pattern cannot be recorded twice within MIN_RECORD_INTERVAL_S
    last_seen: uint256 = self.pattern_last_seen[pattern]
    if last_seen > 0:
        assert block.timestamp >= last_seen + MIN_RECORD_INTERVAL_S, \
            "ThreatRegistry: duplicate pattern within anti-replay window"

    # ── EFFECTS ───────────────────────────────────────────────────────────────
    idx: uint256 = self.total_attacks

    self.attacks[idx] = AttackRecord(
        agent_address=agent,
        pattern_hash=pattern,
        amount_usdc6=amount_usdc6,
        risk_milli=risk_milli,
        layer=layer,
        blocked_at=block.timestamp,
    )

    self.agent_blocks[agent]       += 1
    self.total_usdc_protected6     += amount_usdc6
    self.pattern_last_seen[pattern] = block.timestamp

    # Record first occurrence for pattern intelligence
    if self.pattern_first_seen[pattern] == 0:
        self.pattern_first_seen[pattern] = block.timestamp

    self.total_attacks += 1

    # ── INTERACTION (event emission — last, per CEI) ───────────────────────────
    log AttackBlocked(
        idx=idx,
        agent=agent,
        pattern=pattern,
        amount_usdc6=amount_usdc6,
        risk_milli=risk_milli,
        layer=layer
    )


# ── Write: ownership & emergency ──────────────────────────────────────────────
@external
def transferOwnership(new_owner: address):
    """
    @notice Transfer contract ownership to a new ArcWarden signer.
            Used when rotating the oracle signing key.
    """
    self._require_owner()
    assert new_owner != empty(address), "ThreatRegistry: new owner cannot be zero address"
    assert new_owner != self.owner,     "ThreatRegistry: already owner"

    prev: address = self.owner
    self.owner = new_owner
    log OwnershipTransferred(prev=prev, next=new_owner)


@external
def pause():
    """@notice Emergency circuit breaker: halt all new attack recordings."""
    self._require_owner()
    assert not self.paused, "ThreatRegistry: already paused"
    self.paused = True
    log RegistryPaused(caller=msg.sender)


@external
def unpause():
    """@notice Resume recordings after emergency pause."""
    self._require_owner()
    assert self.paused, "ThreatRegistry: not paused"
    self.paused = False
    log RegistryUnpaused(caller=msg.sender)


# ── Read functions ─────────────────────────────────────────────────────────────
@view
@external
def getAttack(idx: uint256) -> AttackRecord:
    """@notice Return full attack record at a given index."""
    assert idx < self.total_attacks, "ThreatRegistry: index out of bounds"
    return self.attacks[idx]


@view
@external
def getStats() -> (uint256, uint256, uint256):
    """
    @notice Returns (total_attacks, total_usdc_protected6, guaranty_fund6).
    @dev    Amounts are in micro-USDC (divide by 1_000_000 for USDC).
    """
    return self.total_attacks, self.total_usdc_protected6, self.guaranty_fund6


@external
@payable
def depositGuaranty():
    """
    @notice Deposit native USDC into the guaranty fund.
            Proves the Oracle has 'skin in the game'.
    """
    self._require_owner()
    self.guaranty_fund6 += msg.value
    log FundDeposited(amount6=msg.value, new_total6=self.guaranty_fund6)


@external
@nonreentrant
def withdrawGuaranty(amount6: uint256):
    """
    @notice Withdraw USDC from the guaranty fund. Only owner.
    """
    self._require_owner()
    assert self.guaranty_fund6 >= amount6, "ThreatRegistry: insufficient fund"
    self.guaranty_fund6 -= amount6
    send(self.owner, amount6)
    log FundWithdrawn(amount6=amount6, new_total6=self.guaranty_fund6)


@view
@external
def isKnownAttacker(agent: address) -> bool:
    """@notice Returns True if this agent has 3 or more confirmed blocked attacks."""
    return self.agent_blocks[agent] >= 3


@view
@external
def getAgentBlockCount(agent: address) -> uint256:
    """@notice Returns the number of confirmed blocks for a given agent address."""
    return self.agent_blocks[agent]


@view
@external
def isPatternKnown(pattern: bytes32) -> bool:
    """@notice Returns True if this attack pattern has been seen before."""
    return self.pattern_first_seen[pattern] > 0


@view
@external
def getPatternFirstSeen(pattern: bytes32) -> uint256:
    """@notice Returns the block.timestamp when this pattern was first recorded."""
    return self.pattern_first_seen[pattern]
