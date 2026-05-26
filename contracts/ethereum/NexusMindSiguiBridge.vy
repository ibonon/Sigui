# pragma version ^0.4.0

"""
NexusMindSiguiBridge.vy
Bridge contract allowing NexusMind compute nodes to register
as Sigui workers and receive USDC payments based on evaluations.
"""

struct Worker:
    node_id: String[32]
    is_active: bool
    total_earnings: uint256
    evaluations_count: uint256
    last_payout: uint256

workers: public(HashMap[address, Worker])
owner: public(address)
hogonat_dao: public(address)

event WorkerRegistered:
    worker: indexed(address)
    node_id: String[32]

event WorkerPaid:
    worker: indexed(address)
    amount: uint256

@deploy
def __init__(_hogonat_dao: address):
    self.owner = msg.sender
    self.hogonat_dao = _hogonat_dao

@external
def register_worker(node_id: String[32]):
    """Register a new NexusMind node as a Sigui Worker."""
    assert not self.workers[msg.sender].is_active, "Worker already registered"
    self.workers[msg.sender] = Worker(
        node_id=node_id,
        is_active=True,
        total_earnings=0,
        evaluations_count=0,
        last_payout=block.timestamp
    )
    log WorkerRegistered(msg.sender, node_id)

@external
def pay_worker(worker: address, amount: uint256, evaluations: uint256):
    """
    Called by the Sigui Oracle to record payment for evaluations.
    In production, this would transfer actual ERC20 USDC.
    """
    assert msg.sender == self.owner, "Only Oracle can pay"
    assert self.workers[worker].is_active, "Worker not active"
    
    self.workers[worker].total_earnings += amount
    self.workers[worker].evaluations_count += evaluations
    self.workers[worker].last_payout = block.timestamp
    
    log WorkerPaid(worker, amount)

@external
def set_hogonat_dao(new_dao: address):
    assert msg.sender == self.owner, "Only owner"
    self.hogonat_dao = new_dao
