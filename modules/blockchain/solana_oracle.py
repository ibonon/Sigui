"""
Oracle Solana pour la surveillance cross-chain.
Surveille les transactions, programmes et activités suspectes sur Solana.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import base58
import base64

from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from solana.rpc.types import TokenAccountOpts
from solana.publickey import PublicKey
from solana.transaction import Transaction

from ..config import settings

logger = logging.getLogger(__name__)


class SolanaOracle:
    """Oracle pour la surveillance Solana."""
    
    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url or settings.SOLANA_RPC_URL
        self.client = AsyncClient(self.rpc_url)
        
        # Programmes à surveiller
        self.monitored_programs = {
            "raydium": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
            "orca": "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",
            "serum": "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin",
            "marinade": "MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD",
        }
        
        # Patterns de transactions suspectes
        self.suspicious_patterns = [
            {"name": "arbitrage_frontrun", "description": "Arbitrage avec front-running"},
            {"name": "sandwich_attack", "description": "Attaque sandwich sur DEX"},
            {"name": "flash_loan", "description": "Flash loan sur Solana"},
            {"name": "rug_pull", "description": "Pattern de rug pull"},
        ]
        
        logger.info(f"Solana Oracle initialisé sur {self.rpc_url}")
    
    async def monitor_slot(self, slot: int) -> List[Dict[str, Any]]:
        """Surveille un slot spécifique pour détecter des activités suspectes."""
        threats = []
        
        try:
            # Récupérer les transactions du slot
            block = await self.client.get_block(slot, max_supported_transaction_version=0)
            
            if not block or not block.value.transactions:
                return threats
            
            for tx_with_meta in block.value.transactions:
                tx = tx_with_meta.transaction
                meta = tx_with_meta.meta
                
                # Analyser chaque transaction
                tx_threats = await self._analyze_transaction(tx, meta, slot)
                threats.extend(tx_threats)
                
                # Surveiller les interactions avec les programmes
                for program_id in tx.message.program_ids():
                    if str(program_id) in self.monitored_programs.values():
                        program_threats = await self._analyze_program_interaction(
                            tx, meta, str(program_id)
                        )
                        threats.extend(program_threats)
        
        except Exception as e:
            logger.error(f"Erreur lors de la surveillance du slot {slot}: {e}")
        
        return threats
    
    async def _analyze_transaction(self, tx, meta, slot: int) -> List[Dict[str, Any]]:
        """Analyse une transaction Solana pour détecter des patterns suspects."""
        threats = []
        
        # Vérifier les frais élevés
        if meta and hasattr(meta, "fee"):
            fee_lamports = meta.fee
            fee_sol = fee_lamports / 1_000_000_000
            
            if fee_sol > 0.1:  # Plus de 0.1 SOL en frais
                threats.append({
                    "type": "HIGH_FEE_TRANSACTION",
                    "severity": "MEDIUM",
                    "description": f"Transaction avec {fee_sol} SOL en frais",
                    "signature": tx.signatures[0].hex() if tx.signatures else "unknown",
                    "fee_sol": float(fee_sol),
                    "slot": slot,
                    "timestamp": datetime.now(),
                })
        
        # Vérifier le nombre d'instructions
        num_instructions = len(tx.message.instructions)
        if num_instructions > 20:
            threats.append({
                "type": "COMPLEX_TRANSACTION",
                "severity": "LOW",
                "description": f"Transaction complexe avec {num_instructions} instructions",
                "signature": tx.signatures[0].hex() if tx.signatures else "unknown",
                "instruction_count": num_instructions,
                "slot": slot,
                "timestamp": datetime.now(),
            })
        
        # Vérifier les erreurs
        if meta and hasattr(meta, "err") and meta.err:
            threats.append({
                "type": "FAILED_TRANSACTION",
                "severity": "LOW",
                "description": f"Transaction échouée: {meta.err}",
                "signature": tx.signatures[0].hex() if tx.signatures else "unknown",
                "error": str(meta.err),
                "slot": slot,
                "timestamp": datetime.now(),
            })
        
        # Vérifier les transferts importants
        if meta and hasattr(meta, "pre_balances") and hasattr(meta, "post_balances"):
            for i, (pre, post) in enumerate(zip(meta.pre_balances, meta.post_balances)):
                diff = post - pre
                if diff > 100_000_000_000:  # Plus de 100 SOL
                    account = tx.message.account_keys[i]
                    threats.append({
                        "type": "LARGE_TRANSFER",
                        "severity": "MEDIUM",
                        "description": f"Transfert de {diff/1_000_000_000} SOL détecté",
                        "signature": tx.signatures[0].hex() if tx.signatures else "unknown",
                        "account": str(account),
                        "amount_sol": float(diff / 1_000_000_000),
                        "slot": slot,
                        "timestamp": datetime.now(),
                    })
        
        return threats
    
    async def _analyze_program_interaction(self, tx, meta, program_id: str) -> List[Dict[str, Any]]:
        """Analyse les interactions avec les programmes surveillés."""
        threats = []
        
        # Identifier le programme
        program_name = None
        for name, pid in self.monitored_programs.items():
            if pid == program_id:
                program_name = name
                break
        
        if not program_name:
            return threats
        
        # Analyser selon le programme
        if program_name == "raydium":
            # Vérifier les swaps importants
            threats.append({
                "type": "DEX_INTERACTION",
                "severity": "MEDIUM",
                "description": f"Interaction avec {program_name}",
                "signature": tx.signatures[0].hex() if tx.signatures else "unknown",
                "program": program_name,
                "program_id": program_id,
                "slot": meta.slot if hasattr(meta, "slot") else "unknown",
                "timestamp": datetime.now(),
            })
        
        elif program_name == "marinade":
            # Vérifier les staking/unstaking
            threats.append({
                "type": "STAKING_INTERACTION",
                "severity": "LOW",
                "description": f"Interaction avec {program_name}",
                "signature": tx.signatures[0].hex() if tx.signatures else "unknown",
                "program": program_name,
                "program_id": program_id,
                "slot": meta.slot if hasattr(meta, "slot") else "unknown",
                "timestamp": datetime.now(),
            })
        
        return threats
    
    async def get_address_risk_score(self, address: str) -> Dict[str, Any]:
        """Calcule un score de risque pour une adresse Solana."""
        try:
            pubkey = PublicKey(address)
            
            # Récupérer les informations du compte
            account_info = await self.client.get_account_info(pubkey)
            balance_info = await self.client.get_balance(pubkey)
            
            balance_sol = balance_info.value / 1_000_000_000 if balance_info.value else 0
            
            # Récupérer les transactions récentes
            signatures = await self.client.get_signatures_for_address(
                pubkey, limit=10
            )
            
            tx_count = len(signatures.value) if signatures.value else 0
            
            # Calculer le score de risque
            risk_score = 0.0
            
            # Facteurs de risque
            if tx_count < 5:
                risk_score += 0.3  # Nouvelle adresse
            
            if balance_sol > 1000:
                risk_score += 0.2  # Gros portefeuille
            
            # Vérifier si c'est un programme
            is_program = False
            if account_info.value:
                is_program = account_info.value.executable
            
            if is_program:
                risk_score += 0.1  # Programme peut être risqué
            
            return {
                "address": address,
                "risk_score": min(risk_score, 1.0),
                "transaction_count": tx_count,
                "balance_sol": float(balance_sol),
                "is_program": is_program,
                "last_active": await self._get_last_active(signatures),
                "is_token_account": await self._is_token_account(pubkey),
            }
        
        except Exception as e:
            logger.error(f"Erreur lors du calcul du score de risque: {e}")
            return {
                "address": address,
                "risk_score": 0.5,
                "error": str(e),
            }
    
    async def _get_last_active(self, signatures_response) -> Optional[datetime]:
        """Récupère la dernière activité d'une adresse."""
        try:
            if signatures_response and signatures_response.value:
                latest_sig = signatures_response.value[0]
                if hasattr(latest_sig, "block_time") and latest_sig.block_time:
                    return datetime.fromtimestamp(latest_sig.block_time)
            return None
        except:
            return None
    
    async def _is_token_account(self, pubkey: PublicKey) -> bool:
        """Vérifie si une adresse est un compte de token."""
        try:
            # Vérifier via l'API des tokens
            token_accounts = await self.client.get_token_accounts_by_owner(
                pubkey, TokenAccountOpts(program_id=PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
            )
            return len(token_accounts.value) > 0
        except:
            return False
    
    async def start_monitoring(self, callback):
        """Démarre la surveillance en temps réel."""
        logger.info("Démarrage de la surveillance Solana en temps réel")
        
        last_slot = await self.client.get_slot()
        
        while True:
            try:
                current_slot = await self.client.get_slot()
                
                if current_slot > last_slot:
                    # Surveiller les nouveaux slots
                    for slot in range(last_slot + 1, current_slot + 1):
                        threats = await self.monitor_slot(slot)
                        
                        if threats:
                            await callback({
                                "chain": "solana",
                                "slot": slot,
                                "threats": threats,
                                "timestamp": datetime.now(),
                            })
                    
                    last_slot = current_slot
                
                await asyncio.sleep(2)  # Vérifier toutes les 2 secondes
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance: {e}")
                await asyncio.sleep(10)