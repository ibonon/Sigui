"""
Sigui v4.0 — Staking Module
Gestion du staking et des récompenses
"""

import json
from typing import Optional, Dict, List, Any
from web3 import Web3
from web3.contract import Contract
from ...config import settings

class StakingPool:
    """Client pour interagir avec le contrat StakingPool"""
    
    def __init__(self, web3: Optional[Web3] = None):
        self.web3 = web3 or Web3(Web3.HTTPProvider(settings.ethereum_rpc_url))
        
        # Load contract ABI and address
        with open('contracts/ethereum/StakingPool.abi.json', 'r') as f:
            abi = json.load(f)
        
        self.contract_address = settings.staking_pool_address
        self.contract: Contract = self.web3.eth.contract(
            address=self.contract_address,
            abi=abi
        )
        
        # Set default account
        if settings.ethereum_private_key:
            self.account = self.web3.eth.account.from_key(settings.ethereum_private_key)
            self.web3.eth.default_account = self.account.address
    
    def register_node(self, node_id: str, metadata: str) -> bool:
        """Enregistre un nouveau nœud"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        tx = self.contract.functions.register_node(
            node_id_bytes,
            metadata[:128]  # Truncate to 128 chars
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
    
    def stake(self, node_id: str, amount: float, staker_address: str) -> bool:
        """Stake des tokens sur un nœud"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        amount_wei = int(amount * 10 ** 18)
        
        tx = self.contract.functions.stake(
            node_id_bytes,
            amount_wei
        ).build_transaction({
            'from': staker_address,
            'nonce': self.web3.eth.get_transaction_count(staker_address),
            'gas': 400000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def unstake(self, node_id: str, amount: float) -> bool:
        """Commence le processus d'unstaking"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        amount_wei = int(amount * 10 ** 18)
        
        tx = self.contract.functions.unstake(
            node_id_bytes,
            amount_wei
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
    
    def complete_unstake(self, node_id: str) -> bool:
        """Complete l'unstaking"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        tx = self.contract.functions.complete_unstake(node_id_bytes).build_transaction({
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
    
    def slash_node(self, node_id: str, reason: str) -> bool:
        """Slash un nœud (owner only)"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        tx = self.contract.functions.slash_node(
            node_id_bytes,
            reason[:32]  # Truncate to 32 chars
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 400000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def distribute_rewards(self, node_id: str) -> bool:
        """Distribue les récompenses"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        tx = self.contract.functions.distribute_rewards(node_id_bytes).build_transaction({
            'from': self.account.address,
            'nonce': self.web3.eth.get_transaction_count(self.account.address),
            'gas': 500000,
            'gasPrice': self.web3.eth.gas_price
        })
        
        signed_tx = self.web3.eth.account.sign_transaction(
            tx, 
            private_key=settings.ethereum_private_key
        )
        tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        return receipt.status == 1
    
    def update_node_status(self, node_id: str, status: int) -> bool:
        """Met à jour le statut d'un nœud (owner only)"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        tx = self.contract.functions.update_node_status(
            node_id_bytes,
            status
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
    
    # ─── View Functions ───────────────────────────────────────────────────────
    
    def get_node_info(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retourne les informations d'un nœud"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        try:
            node_data = self.contract.functions.get_node_info(node_id_bytes).call()
            
            # Convert tuple to dict
            return {
                'id': node_data[0].hex(),
                'owner': node_data[1],
                'stake_amount': node_data[2] / 10 ** 18,
                'uptime_percentage': node_data[3] / 100,  # Convert from basis points
                'performance_score': node_data[4] / 100,  # Convert from basis points
                'last_heartbeat': node_data[5],
                'status': node_data[6],  # 0=INACTIVE, 1=ACTIVE, 2=SLASHED
                'rewards_earned': node_data[7] / 10 ** 18,
                'metadata': node_data[8]
            }
        except:
            return None
    
    def get_stake_record(self, staker_address: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Retourne le record de stake"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        try:
            record = self.contract.functions.get_stake_record(
                staker_address,
                node_id_bytes
            ).call()
            
            return {
                'amount': record[0] / 10 ** 18,
                'staked_at': record[1],
                'unstaking_started': record[2],
                'unstaking_amount': record[3] / 10 ** 18
            }
        except:
            return None
    
    def calculate_rewards(self, node_id: str, staker_address: str) -> float:
        """Calcule les récompenses non distribuées"""
        node_id_bytes = self.web3.to_bytes(hexstr=node_id)
        
        try:
            rewards_wei = self.contract.functions.calculate_rewards(
                node_id_bytes,
                staker_address
            ).call()
            
            return rewards_wei / 10 ** 18
        except:
            return 0.0
    
    def list_nodes(self, status: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retourne la liste des nœuds"""
        nodes = []
        
        try:
            # Get all node IDs
            node_ids = self.contract.functions.node_ids().call()
            
            for node_id_bytes in node_ids:
                node_info = self.get_node_info(node_id_bytes.hex())
                
                if node_info:
                    if status is None or node_info['status'] == status:
                        nodes.append(node_info)
        except:
            pass
        
        return nodes
    
    def get_total_staked(self) -> float:
        """Retourne le total staké"""
        total = self.contract.functions.total_staked().call()
        return total / 10 ** 18
    
    def get_node_status(self, node_id: str) -> Optional[int]:
        """Retourne le statut d'un nœud"""
        node_info = self.get_node_info(node_id)
        return node_info['status'] if node_info else None
    
    def get_node_stake(self, node_id: str) -> float:
        """Retourne le stake total d'un nœud"""
        node_info = self.get_node_info(node_id)
        return node_info['stake_amount'] if node_info else 0.0
    
    def get_node_owner(self, node_id: str) -> Optional[str]:
        """Retourne le propriétaire d'un nœud"""
        node_info = self.get_node_info(node_id)
        return node_info['owner'] if node_info else None