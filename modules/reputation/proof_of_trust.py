"""
Sigui v3.0 — Proof of Trust Algorithm
Algorithme de consensus pour la réputation décentralisée.
Combine Proof-of-Stake avec Proof-of-Reputation.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

import numpy as np
from loguru import logger

from config import settings
from modules.reputation.trust_graph import TrustGraph, TrustEdgeType


class ConsensusRound(Enum):
    """Phases du consensus Proof-of-Trust."""
    PROPOSAL = "proposal"
    VOTING = "voting"
    COMMIT = "commit"
    FINALIZE = "finalize"


@dataclass
class TrustProof:
    """Preuve de confiance pour un agent."""
    agent_did: str
    trust_score: float
    timestamp: datetime
    block_hash: str
    signatures: List[str] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit la preuve en dictionnaire."""
        return {
            "agent_did": self.agent_did,
            "trust_score": self.trust_score,
            "timestamp": self.timestamp.isoformat(),
            "block_hash": self.block_hash,
            "signatures": self.signatures,
            "metadata": self.metadata,
        }
    
    def calculate_hash(self) -> str:
        """Calcule le hash de la preuve."""
        data = json.dumps({
            "agent_did": self.agent_did,
            "trust_score": self.trust_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }, sort_keys=True)
        
        return hashlib.sha256(data.encode()).hexdigest()


class ProofOfTrust:
    """Algorithme Proof-of-Trust pour consensus décentralisé."""
    
    def __init__(self, trust_graph: TrustGraph):
        self.trust_graph = trust_graph
        self.validators: Set[str] = set()
        self.stake_pool: Dict[str, float] = {}  # DID -> stake amount
        self.consensus_round = ConsensusRound.PROPOSAL
        self.current_block_height = 0
        self.proof_history: Dict[int, List[TrustProof]] = {}
        
        # Paramètres de consensus
        self.min_stake = 1000.0  # Minimum stake pour être validateur
        self.block_time = 10.0  # Secondes entre les blocs
        self.quorum_threshold = 0.67  # 67% pour le consensus
        
        logger.info("ProofOfTrust initialisé")
    
    def register_validator(self, agent_did: str, stake_amount: float) -> bool:
        """Enregistre un validateur avec son stake."""
        if stake_amount < self.min_stake:
            logger.warning(f"Stake insuffisant pour {agent_did}: {stake_amount} < {self.min_stake}")
            return False
        
        self.validators.add(agent_did)
        self.stake_pool[agent_did] = stake_amount
        
        # Ajouter une arête de délégation au graphe
        self.trust_graph.add_trust_edge(
            source_did=agent_did,
            target_did="system:validators",
            edge_type=TrustEdgeType.DELEGATION,
            weight=min(1.0, stake_amount / (self.min_stake * 10)),
            metadata={"stake_amount": stake_amount, "action": "validator_registration"},
        )
        
        logger.info(f"Validateur enregistré: {agent_did} avec stake {stake_amount}")
        return True
    
    def calculate_voting_power(self, agent_did: str) -> float:
        """Calcule le pouvoir de vote d'un agent."""
        if agent_did not in self.validators:
            return 0.0
        
        stake = self.stake_pool.get(agent_did, 0.0)
        trust_score = self.trust_graph.calculate_trust_score(agent_did)
        
        # Formule: voting_power = stake * sqrt(trust_score)
        voting_power = stake * np.sqrt(max(0.0, trust_score))
        
        return voting_power
    
    async def propose_block(self, proposer_did: str) -> Optional[Dict[str, any]]:
        """Propose un nouveau bloc de réputation."""
        if proposer_did not in self.validators:
            logger.warning(f"Agent non validateur tente de proposer un bloc: {proposer_did}")
            return None
        
        # Vérifier que c'est le tour de cet agent
        if not self._is_valid_proposer(proposer_did):
            logger.warning(f"Ce n'est pas le tour de {proposer_did} de proposer")
            return None
        
        # Calculer les scores de confiance pour tous les agents
        trust_updates = []
        for agent_did in self.trust_graph.graph.nodes():
            if agent_did.startswith("system:"):
                continue
            
            trust_score = self.trust_graph.calculate_trust_score(agent_did)
            
            proof = TrustProof(
                agent_did=agent_did,
                trust_score=trust_score,
                timestamp=datetime.now(timezone.utc),
                block_hash="",  # À calculer après
                metadata={
                    "block_height": self.current_block_height + 1,
                    "proposer": proposer_did,
                },
            )
            
            trust_updates.append(proof)
        
        # Créer le bloc
        block = {
            "height": self.current_block_height + 1,
            "proposer": proposer_did,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trust_updates": [p.to_dict() for p in trust_updates],
            "previous_hash": self._get_previous_block_hash(),
            "validator_set": list(self.validators),
        }
        
        # Calculer le hash du bloc
        block_hash = self._calculate_block_hash(block)
        block["hash"] = block_hash
        
        # Mettre à jour les preuves avec le hash du bloc
        for proof in trust_updates:
            proof.block_hash = block_hash
        
        logger.info(f"Bloc proposé par {proposer_did} à la hauteur {block['height']}")
        return block
    
    async def validate_block(self, block: Dict[str, any], validator_did: str) -> bool:
        """Valide un bloc proposé."""
        if validator_did not in self.validators:
            return False
        
        # Vérifier la structure du bloc
        required_fields = {"height", "proposer", "timestamp", "trust_updates", "previous_hash", "hash"}
        if not all(field in block for field in required_fields):
            logger.warning(f"Bloc manquant des champs requis: {block.keys()}")
            return False
        
        # Vérifier la hauteur
        if block["height"] != self.current_block_height + 1:
            logger.warning(f"Hauteur de bloc incorrecte: {block['height']} attendu {self.current_block_height + 1}")
            return False
        
        # Vérifier le hash précédent
        if block["previous_hash"] != self._get_previous_block_hash():
            logger.warning(f"Hash précédent incorrect")
            return False
        
        # Vérifier le hash du bloc
        block_copy = block.copy()
        block_hash = block_copy.pop("hash")
        calculated_hash = self._calculate_block_hash(block_copy)
        
        if block_hash != calculated_hash:
            logger.warning(f"Hash de bloc invalide")
            return False
        
        # Vérifier le proposer
        if block["proposer"] not in self.validators:
            logger.warning(f"Proposer non validateur: {block['proposer']}")
            return False
        
        # Vérifier les mises à jour de confiance
        for update in block["trust_updates"]:
            if not self._validate_trust_update(update):
                logger.warning(f"Mise à jour de confiance invalide: {update}")
                return False
        
        logger.debug(f"Bloc validé par {validator_did}")
        return True
    
    async def finalize_block(self, block: Dict[str, any]) -> bool:
        """Finalise un bloc après consensus."""
        # Vérifier le quorum
        if not await self._check_quorum(block["hash"]):
            logger.warning(f"Quorum non atteint pour le bloc {block['height']}")
            return False
        
        # Appliquer les mises à jour de confiance
        for update_data in block["trust_updates"]:
            agent_did = update_data["agent_did"]
            trust_score = update_data["trust_score"]
            
            # Stocker la preuve
            proof = TrustProof(
                agent_did=agent_did,
                trust_score=trust_score,
                timestamp=datetime.fromisoformat(update_data["timestamp"]),
                block_hash=block["hash"],
                signatures=update_data.get("signatures", []),
                metadata=update_data.get("metadata", {}),
            )
            
            if block["height"] not in self.proof_history:
                self.proof_history[block["height"]] = []
            self.proof_history[block["height"]].append(proof)
        
        # Mettre à jour la hauteur du bloc
        self.current_block_height = block["height"]
        
        logger.info(f"Bloc finalisé à la hauteur {block['height']}")
        return True
    
    def _is_valid_proposer(self, agent_did: str) -> bool:
        """Vérifie si un agent est le proposer valide pour ce tour."""
        # Algorithme round-robin basé sur le stake
        if not self.validators:
            return False
        
        # Trier les validateurs par stake
        sorted_validators = sorted(
            self.validators,
            key=lambda x: self.stake_pool.get(x, 0.0),
            reverse=True
        )
        
        # Calculer l'index du proposer
        round_index = self.current_block_height % len(sorted_validators)
        expected_proposer = sorted_validators[round_index]
        
        return agent_did == expected_proposer
    
    def _get_previous_block_hash(self) -> str:
        """Récupère le hash du bloc précédent."""
        if self.current_block_height == 0:
            return "0" * 64  # Genesis block hash
        
        # En production, il faudrait récupérer depuis la blockchain
        return hashlib.sha256(str(self.current_block_height).encode()).hexdigest()
    
    def _calculate_block_hash(self, block_data: Dict[str, any]) -> str:
        """Calcule le hash d'un bloc."""
        data = json.dumps(block_data, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _validate_trust_update(self, update: Dict[str, any]) -> bool:
        """Valide une mise à jour de score de confiance."""
        required_fields = {"agent_did", "trust_score", "timestamp"}
        if not all(field in update for field in required_fields):
            return False
        
        # Vérifier les plages de valeurs
        trust_score = update["trust_score"]
        if not 0.0 <= trust_score <= 1.0:
            return False
        
        # Vérifier le timestamp
        try:
            timestamp = datetime.fromisoformat(update["timestamp"])
            now = datetime.now(timezone.utc)
            
            # Le timestamp ne doit pas être dans le futur
            if timestamp > now:
                return False
            
            # Le timestamp ne doit pas être trop ancien (plus de 24h)
            if (now - timestamp).total_seconds() > 86400:
                return False
        except ValueError:
            return False
        
        return True
    
    async def _check_quorum(self, block_hash: str) -> bool:
        """Vérifie si le quorum est atteint pour un bloc."""
        # En production, il faudrait vérifier les signatures des validateurs
        # Pour l'instant, on simule
        total_voting_power = sum(self.calculate_voting_power(v) for v in self.validators)
        
        if total_voting_power == 0:
            return False
        
        # Simuler l'approbation de 75% des validateurs
        approved_power = total_voting_power * 0.75
        
        return approved_power / total_voting_power >= self.quorum_threshold
    
    def get_agent_proof(self, agent_did: str) -> Optional[TrustProof]:
        """Récupère la dernière preuve de confiance d'un agent."""
        for height in sorted(self.proof_history.keys(), reverse=True):
            for proof in self.proof_history[height]:
                if proof.agent_did == agent_did:
                    return proof
        
        return None
    
    def export_state(self) -> Dict[str, any]:
        """Exporte l'état du consensus."""
        return {
            "block_height": self.current_block_height,
            "validators": list(self.validators),
            "stake_pool": self.stake_pool,
            "proof_history": {
                str(height): [p.to_dict() for p in proofs]
                for height, proofs in self.proof_history.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }