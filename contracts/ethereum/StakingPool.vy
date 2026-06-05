# @version ^0.3.10
"""
Sigui Staking Pool
Système de staking avec slashing et récompenses
"""

from vyper.interfaces import ERC20

# ─── Interfaces ───────────────────────────────────────────────────────────

interface SiguiToken:
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def transfer(_to: address, _value: uint256) -> bool: nonpayable
    def balanceOf(_owner: address) -> uint256: view

# ─── Events ───────────────────────────────────────────────────────────────

event Staked:
    node_id: indexed(bytes32)
    staker: indexed(address)
    amount: uint256
    timestamp: uint256

event Unstaked:
    node_id: indexed(bytes32)
    staker: indexed(address)
    amount: uint256
    timestamp: uint256

event Slashed:
    node_id: indexed(bytes32)
    amount: uint256
    reason: String[32]
    timestamp: uint256

event RewardDistributed:
    node_id: indexed(bytes32)
    staker: indexed(address)
    amount: uint256
    timestamp: uint256

event NodeRegistered:
    node_id: indexed(bytes32)
    owner: indexed(address)
    metadata: String[128]

event NodeStatusChanged:
    node_id: indexed(bytes32)
    old_status: uint8
    new_status: uint8
    timestamp: uint256

# ─── Constants ────────────────────────────────────────────────────────────

APR: constant(uint256) = 1500  # 15% = 1500
SLASH_PERCENTAGE: constant(uint256) = 500  # 5% = 500
UNBONDING_PERIOD: constant(uint256) = 7 * 24 * 60 * 60  # 7 jours en secondes
MIN_STAKE: constant(uint256) = 100 * 10 ** 18  # 100 tokens
MAX_SLASH_PER_DAY: constant(uint256) = 2000  # 20% max par jour

# ─── Storage ──────────────────────────────────────────────────────────────

token: public(address)
owner: public(address)
paused: public(bool)

# Node management
Node: struct({
    id: bytes32,
    owner: address,
    stake_amount: uint256,
    uptime_percentage: uint256,  # 100% = 10000
    performance_score: uint256,  # 0-10000
    last_heartbeat: uint256,
    status: uint8,  # 0=INACTIVE, 1=ACTIVE, 2=SLASHED
    rewards_earned: uint256,
    metadata: String[128]
})

nodes: public(HashMap[bytes32, Node])
node_ids: public(DynArray[bytes32, 1000])

# Staking records
StakeRecord: struct({
    amount: uint256,
    staked_at: uint256,
    unstaking_started: uint256,
    unstaking_amount: uint256
})

stakes: public(HashMap[address, HashMap[bytes32, StakeRecord]])  # staker -> node_id -> record
total_staked: public(uint256)

# Slashing tracking
last_slash_time: public(HashMap[bytes32, uint256])  # node_id -> timestamp
total_slashed: public(HashMap[bytes32, uint256])  # node_id -> amount

# ─── Constructor ──────────────────────────────────────────────────────────

@external
def __init__(_token: address):
    self.token = _token
    self.owner = msg.sender
    self.paused = False

# ─── Public Functions ─────────────────────────────────────────────────────

@external
def register_node(_node_id: bytes32, _metadata: String[128]):
    """
    Enregistre un nouveau nœud
    """
    assert not self.paused, "Contract is paused"
    assert self.nodes[_node_id].id == empty(bytes32), "Node already exists"
    assert len(_metadata) <= 128, "Metadata too long"
    
    node: Node = Node({
        id: _node_id,
        owner: msg.sender,
        stake_amount: 0,
        uptime_percentage: 10000,  # 100%
        performance_score: 10000,  # 100%
        last_heartbeat: block.timestamp,
        status: 1,  # ACTIVE
        rewards_earned: 0,
        metadata: _metadata
    })
    
    self.nodes[_node_id] = node
    self.node_ids.append(_node_id)
    
    log NodeRegistered(_node_id, msg.sender, _metadata)

@external
def stake(_node_id: bytes32, _amount: uint256):
    """
    Stake des tokens sur un nœud
    """
    assert not self.paused, "Contract is paused"
    assert _amount >= MIN_STAKE, "Amount below minimum"
    assert self.nodes[_node_id].status == 1, "Node not active"
    
    # Transfer tokens from staker to contract
    token_contract: SiguiToken = SiguiToken(self.token)
    assert token_contract.transferFrom(msg.sender, self, _amount), "Transfer failed"
    
    # Update stake record
    record: StakeRecord = self.stakes[msg.sender][_node_id]
    if record.amount == 0:
        # New stake
        record = StakeRecord({
            amount: _amount,
            staked_at: block.timestamp,
            unstaking_started: 0,
            unstaking_amount: 0
        })
    else:
        # Additional stake
        record.amount += _amount
    
    self.stakes[msg.sender][_node_id] = record
    
    # Update node total stake
    node: Node = self.nodes[_node_id]
    node.stake_amount += _amount
    self.nodes[_node_id] = node
    
    # Update global total
    self.total_staked += _amount
    
    log Staked(_node_id, msg.sender, _amount, block.timestamp)

@external
def unstake(_node_id: bytes32, _amount: uint256):
    """
    Commence le processus d'unstaking
    """
    assert not self.paused, "Contract is paused"
    
    record: StakeRecord = self.stakes[msg.sender][_node_id]
    assert record.amount >= _amount, "Insufficient staked amount"
    assert record.unstaking_started == 0, "Already unstaking"
    
    # Start unstaking period
    record.unstaking_started = block.timestamp
    record.unstaking_amount = _amount
    record.amount -= _amount
    
    self.stakes[msg.sender][_node_id] = record
    
    log Unstaked(_node_id, msg.sender, _amount, block.timestamp)

@external
def complete_unstake(_node_id: bytes32):
    """
    Complete l'unstaking après la période d'attente
    """
    assert not self.paused, "Contract is paused"
    
    record: StakeRecord = self.stakes[msg.sender][_node_id]
    assert record.unstaking_started > 0, "No unstaking in progress"
    assert block.timestamp >= record.unstaking_started + UNBONDING_PERIOD, "Unbonding period not over"
    
    amount: uint256 = record.unstaking_amount
    
    # Reset unstaking
    record.unstaking_started = 0
    record.unstaking_amount = 0
    self.stakes[msg.sender][_node_id] = record
    
    # Update node total stake
    node: Node = self.nodes[_node_id]
    node.stake_amount -= amount
    self.nodes[_node_id] = node
    
    # Update global total
    self.total_staked -= amount
    
    # Transfer tokens back to staker
    token_contract: SiguiToken = SiguiToken(self.token)
    assert token_contract.transfer(msg.sender, amount), "Transfer failed"

@external
def slash_node(_node_id: bytes32, _reason: String[32]):
    """
    Slash un nœud pour mauvaise conduite
    """
    assert msg.sender == self.owner, "Only owner can slash"
    assert not self.paused, "Contract is paused"
    
    node: Node = self.nodes[_node_id]
    assert node.status == 1, "Node not active"
    
    # Check daily slash limit
    last_slash: uint256 = self.last_slash_time[_node_id]
    if block.timestamp < last_slash + 24 * 60 * 60:
        # Within 24 hours of last slash
        already_slashed: uint256 = self.total_slashed[_node_id]
        max_slash_today: uint256 = (node.stake_amount * MAX_SLASH_PER_DAY) / 10000
        assert already_slashed < max_slash_today, "Daily slash limit reached"
    
    # Calculate slash amount (5% of stake)
    slash_amount: uint256 = (node.stake_amount * SLASH_PERCENTAGE) / 10000
    
    # Update node
    node.stake_amount -= slash_amount
    node.status = 2  # SLASHED
    self.nodes[_node_id] = node
    
    # Update tracking
    self.last_slash_time[_node_id] = block.timestamp
    self.total_slashed[_node_id] += slash_amount
    self.total_staked -= slash_amount
    
    log Slashed(_node_id, slash_amount, _reason, block.timestamp)

@external
def distribute_rewards(_node_id: bytes32):
    """
    Distribue les récompenses aux stakers d'un nœud
    """
    assert not self.paused, "Contract is paused"
    
    node: Node = self.nodes[_node_id]
    assert node.status == 1, "Node not active"
    assert node.stake_amount > 0, "No stake on node"
    
    # Calculate rewards (simplified - in reality would be more complex)
    time_elapsed: uint256 = block.timestamp - node.last_heartbeat
    rewards: uint256 = (node.stake_amount * APR * time_elapsed) / (365 * 24 * 60 * 60 * 10000)
    
    if rewards > 0:
        # Mint new tokens as rewards
        token_contract: SiguiToken = SiguiToken(self.token)
        token_contract.mint(self, rewards)
        
        # Distribute proportionally to stakers (simplified)
        # In reality would iterate through all stakers
        node.rewards_earned += rewards
        self.nodes[_node_id] = node
        
        log RewardDistributed(_node_id, msg.sender, rewards, block.timestamp)

@external
def update_node_status(_node_id: bytes32, _status: uint8):
    """
    Met à jour le statut d'un nœud
    """
    assert msg.sender == self.owner, "Only owner can update status"
    assert not self.paused, "Contract is paused"
    assert _status <= 2, "Invalid status"
    
    node: Node = self.nodes[_node_id]
    old_status: uint8 = node.status
    
    node.status = _status
    node.last_heartbeat = block.timestamp
    self.nodes[_node_id] = node
    
    log NodeStatusChanged(_node_id, old_status, _status, block.timestamp)

@external
def pause():
    """
    Met le contrat en pause
    """
    assert msg.sender == self.owner, "Only owner can pause"
    self.paused = True

@external
def unpause():
    """
    Active le contrat
    """
    assert msg.sender == self.owner, "Only owner can unpause"
    self.paused = False

# ─── View Functions ───────────────────────────────────────────────────────

@view
@external
def get_node_info(_node_id: bytes32) -> Node:
    """
    Retourne les informations d'un nœud
    """
    return self.nodes[_node_id]

@view
@external
def get_stake_record(_staker: address, _node_id: bytes32) -> StakeRecord:
    """
    Retourne le record de stake d'un staker sur un nœud
    """
    return self.stakes[_staker][_node_id]

@view
@external
def calculate_rewards(_node_id: bytes32, _staker: address) -> uint256:
    """
    Calcule les récompenses non distribuées pour un staker
    """
    record: StakeRecord = self.stakes[_staker][_node_id]
    if record.amount == 0:
        return 0
    
    node: Node = self.nodes[_node_id]
    time_elapsed: uint256 = block.timestamp - node.last_heartbeat
    
    # Calculate proportional rewards
    stake_share: uint256 = (record.amount * 10000) / node.stake_amount
    rewards: uint256 = (node.rewards_earned * stake_share * time_elapsed) / (10000 * (365 * 24 * 60 * 60))
    
    return rewards