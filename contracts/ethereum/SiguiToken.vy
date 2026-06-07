# @version ^0.3.10
"""
Sigui Governance Token (SGT)
ERC-20 token avec fonctionnalités avancées pour le staking et la gouvernance
"""

from vyper.interfaces import ERC20

implements: ERC20

# ─── Events ───────────────────────────────────────────────────────────────

event Transfer:
    sender: indexed(address)
    receiver: indexed(address)
    value: uint256

event Approval:
    owner: indexed(address)
    spender: indexed(address)
    value: uint256

event Mint:
    to: indexed(address)
    amount: uint256

event Burn:
    from: indexed(address)
    amount: uint256

event SkillNFTMinted:
    skill_id: indexed(bytes32)
    author: indexed(address)
    price: uint256

event RoyaltyTransferred:
    to: indexed(address)
    amount: uint256

# ─── Storage ──────────────────────────────────────────────────────────────

name: public(String[32])
symbol: public(String[8])
decimals: public(uint256)

totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

# Governance
owner: public(address)
paused: public(bool)

# Marketplace
skill_nfts: public(HashMap[bytes32, address])  # skill_id -> owner
skill_prices: public(HashMap[bytes32, uint256])  # skill_id -> price
royalty_percentage: public(uint256)  # 5% = 500

# ─── Constructor ──────────────────────────────────────────────────────────

@external
def __init__():
    self.name = "Sigui Governance Token"
    self.symbol = "SGT"
    self.decimals = 18
    self.owner = msg.sender
    self.royalty_percentage = 500  # 5%
    
    # Mint initial supply
    initial_supply: uint256 = 100_000_000 * 10 ** self.decimals  # 100M tokens
    self._mint(msg.sender, initial_supply)

# ─── ERC-20 Functions ─────────────────────────────────────────────────────

@view
@external
def totalSupply() -> uint256:
    return self.totalSupply

@view
@external
def balanceOf(_owner: address) -> uint256:
    return self.balanceOf[_owner]

@view
@external
def allowance(_owner: address, _spender: address) -> uint256:
    return self.allowance[_owner][_spender]

@external
def transfer(_to: address, _value: uint256) -> bool:
    assert not self.paused, "Contract is paused"
    assert _to != empty(address), "Invalid recipient"
    assert self.balanceOf[msg.sender] >= _value, "Insufficient balance"
    
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    
    log Transfer(msg.sender, _to, _value)
    return True

@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    assert not self.paused, "Contract is paused"
    assert _to != empty(address), "Invalid recipient"
    assert self.balanceOf[_from] >= _value, "Insufficient balance"
    assert self.allowance[_from][msg.sender] >= _value, "Insufficient allowance"
    
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowance[_from][msg.sender] -= _value
    
    log Transfer(_from, _to, _value)
    return True

@external
def approve(_spender: address, _value: uint256) -> bool:
    assert not self.paused, "Contract is paused"
    self.allowance[msg.sender][_spender] = _value
    log Approval(msg.sender, _spender, _value)
    return True

# ─── Advanced Functions ───────────────────────────────────────────────────

@external
def mint(_to: address, _amount: uint256):
    assert msg.sender == self.owner, "Only owner can mint"
    assert not self.paused, "Contract is paused"
    
    self._mint(_to, _amount)

@external
def burn(_amount: uint256):
    assert not self.paused, "Contract is paused"
    assert self.balanceOf[msg.sender] >= _amount, "Insufficient balance"
    
    self.totalSupply -= _amount
    self.balanceOf[msg.sender] -= _amount
    
    log Burn(msg.sender, _amount)

@external
def mint_skill_nft(skill_id: bytes32, author: address, price: uint256):
    """
    Mint un NFT pour un skill
    Seulement l'owner peut appeler cette fonction
    """
    assert msg.sender == self.owner, "Only owner can mint skill NFTs"
    assert not self.paused, "Contract is paused"
    assert self.skill_nfts[skill_id] == empty(address), "Skill NFT already exists"
    
    self.skill_nfts[skill_id] = author
    self.skill_prices[skill_id] = price
    
    log SkillNFTMinted(skill_id, author, price)

@external
def transfer_royalty(_to: address, _amount: uint256):
    """
    Transfère des royalties au créateur d'un skill
    """
    assert msg.sender == self.owner, "Only owner can transfer royalties"
    assert not self.paused, "Contract is paused"
    assert self.balanceOf[self] >= _amount, "Insufficient royalty balance"
    
    self.balanceOf[self] -= _amount
    self.balanceOf[_to] += _amount
    
    log RoyaltyTransferred(_to, _amount)

@external
def pause():
    """
    Met le contrat en pause
    Seulement l'owner peut appeler cette fonction
    """
    assert msg.sender == self.owner, "Only owner can pause"
    self.paused = True

@external
def unpause():
    """
    Active le contrat
    Seulement l'owner peut appeler cette fonction
    """
    assert msg.sender == self.owner, "Only owner can unpause"
    self.paused = False

# ─── Internal Functions ───────────────────────────────────────────────────

@internal
def _mint(_to: address, _amount: uint256):
    self.totalSupply += _amount
    self.balanceOf[_to] += _amount
    log Mint(_to, _amount)
    log Transfer(empty(address), _to, _amount)