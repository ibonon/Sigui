# @version 0.4.3
# Hogonat — governance + staking for Sigui

interface ERC20:
    def transferFrom(_from: address, _to: address, _value: uint256) -> bool: nonpayable
    def transfer(_to: address, _value: uint256) -> bool: nonpayable

USDC: immutable(address)
owner: public(address)

stakers: public(HashMap[address, uint256])
total_staked: public(uint256)
fee_pool: public(uint256)
risk_weights: public(uint256[3])  # basis points style: [4000,3000,3000]
allow_threshold_milli: public(uint256)  # 300 = 0.30
block_threshold_milli: public(uint256)  # 700 = 0.70


@deploy
def __init__(_usdc: address):
    USDC = _usdc
    self.owner = msg.sender
    self.risk_weights = [4000, 3000, 3000]
    self.allow_threshold_milli = 300
    self.block_threshold_milli = 700


@external
def stake(amount: uint256):
    assert amount > 0, "amount=0"
    assert extcall ERC20(USDC).transferFrom(msg.sender, self, amount), "transferFrom failed"
    self.stakers[msg.sender] += amount
    self.total_staked += amount


@external
def vote_weights(new_weights: uint256[3]):
    assert self.stakers[msg.sender] > 0, "Not a staker"
    total: uint256 = new_weights[0] + new_weights[1] + new_weights[2]
    assert total > 0, "invalid weights"
    self.risk_weights = new_weights


@external
def vote_thresholds(new_allow_milli: uint256, new_block_milli: uint256):
    assert self.stakers[msg.sender] > 0, "Not a staker"
    assert new_allow_milli < new_block_milli, "allow >= block"
    self.allow_threshold_milli = new_allow_milli
    self.block_threshold_milli = new_block_milli


@external
def deposit_fee(amount: uint256):
    assert msg.sender == self.owner, "owner only"
    assert extcall ERC20(USDC).transferFrom(msg.sender, self, amount), "transferFrom failed"
    self.fee_pool += amount


@external
def claim_rewards():
    assert self.stakers[msg.sender] > 0, "Not a staker"
    assert self.total_staked > 0, "no stake"
    share: uint256 = (self.stakers[msg.sender] * self.fee_pool) // self.total_staked
    assert share > 0, "no rewards"
    self.fee_pool -= share
    assert extcall ERC20(USDC).transfer(msg.sender, share), "transfer failed"

# ── NexusMind Worker Governance ──────────────────────────────────────────────

worker_votes: public(HashMap[address, uint256])

@external
def vote_approve_worker(worker: address):
    """
    DAO members vote to approve a new NexusMind node as a Sigui Worker.
    In a real implementation, reaching a threshold of total_staked would
    trigger a callback to NexusMindSiguiBridge.
    """
    assert self.stakers[msg.sender] > 0, "Not a staker"
    self.worker_votes[worker] += self.stakers[msg.sender]
