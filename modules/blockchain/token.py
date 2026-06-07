"""
Sigui v4.0 — Token Module
Gestion du token SGT et des fonctionnalités NFT
"""

import json
from typing import Optional, Dict, Any
from web3 import Web3
from web3.contract import Contract
from ...config import settings

class SiguiToken:
    """Client pour interagir avec le contrat SiguiToken"""
    
    def __init__(self, web3: Optional[Web3] = None):
        self.web3 = web3 or Web3(Web3.HTTPProvider(settings.ethereum_rpc_url))
        
        # Load contract ABI and address
        with open('contracts/ethereum/SiguiToken.abi.json', 'r') as f:
            abi = json.load(f)
        
        self.contract_address = settings.sigui_token_address
        self.contract: Contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=abi
        )
        
        # Set default account
        if settings.ethereum_private_key:
            self.account = self.web3.eth.account.from_key(settings.ethereum_private_key)
            self.web3.eth.default_account = self.account.address
    
    def balance_of(self, address: str) -> float:
        """Retourne le solde d'un address"""
        balance = self.contract.functions.balanceOf(address).call()
        return balance / 10 ** 18  # Convert from wei
    
    def transfer(self, from_address: str, to_address: str, amount: float) -> bool:
        """Transfert des tokens"""
        amount_wei = int(amount * 10 ** 18)
        
        # Build transaction
        tx = self.contract.functions.transfer(
            to_address,
            amount_wei
        ).build_transaction({
            'from': from_address,
            'nonce': self.web3.eth.get_transaction_count(from_address),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        # Sign and send
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for confirmation
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def transfer_from(self, from_address: str, to_address: str, amount: float) -> bool:
        """Transfert avec allowance"""
        amount_wei = int(amount * 10 ** 18)
        
        tx = self.contract.functions.transferFrom(
            from_address,
            to_address,
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 150000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def approve(self, spender: str, amount: float) -> bool:
        """Approve des tokens pour un spender"""
        amount_wei = int(amount * 10 ** 18)
        
        tx = self.contract.functions.approve(
            spender,
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def mint(self, to_address: str, amount: float) -> bool:
        """Mint de nouveaux tokens (owner only)"""
        amount_wei = int(amount * 10 ** 18)
        
        tx = self.contract.functions.mint(
            to_address,
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 200000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def burn(self, amount: float) -> bool:
        """Burn des tokens"""
        amount_wei = int(amount * 10 ** 18)
        
        tx = self.contract.functions.burn(amount_wei).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 100000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def mint_skill_nft(self, skill_id: str, author: str, price: float) -> bool:
        """Mint un NFT pour un skill (owner only)"""
        price_wei = int(price * 10 ** 18)
        skill_id_bytes = self.web3.to_bytes(hexstr=skill_id)
        
        tx = self.contract.functions.mint_skill_nft(
            skill_id_bytes,
            author,
            price_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 300000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def transfer_royalty(self, to_address: str, amount: float) -> bool:
        """Transfert de royalties (owner only)"""
        amount_wei = int(amount * 10 ** 18)
        
        tx = self.contract.functions.transfer_royalty(
            to_address,
            amount_wei
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 150000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def get_skill_nft_owner(self, skill_id: str) -> Optional[str]:
        """Retourne le propriétaire d'un skill NFT"""
        skill_id_bytes = self.web3.to_bytes(hexstr=skill_id)
        owner = self.contract.functions.skill_nfts(skill_id_bytes).call()
        return owner if owner != '0x' + '0' * 40 else None
    
    def get_skill_price(self, skill_id: str) -> Optional[float]:
        """Retourne le prix d'un skill"""
        skill_id_bytes = self.web3.to_bytes(hexstr=skill_id)
        price_wei = self.contract.functions.skill_prices(skill_id_bytes).call()
        return price_wei / 10 ** 18 if price_wei > 0 else None
    
    def get_total_supply(self) -> float:
        """Retourne le total supply"""
        supply = self.contract.functions.totalSupply().call()
        return supply / 10 ** 18
    
    def get_royalty_percentage(self) -> float:
        """Retourne le pourcentage de royalties"""
        percentage = self.contract.functions.royalty_percentage().call()
        return percentage / 100  # Convert from basis points