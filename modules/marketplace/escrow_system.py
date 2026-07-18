"""
Sigui v3.0 — Escrow System
Système d'escrow décentralisé pour les transactions du marketplace.
"""

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

from loguru import logger
from web3 import Web3

from config import settings


class EscrowStatus(Enum):
    """Statuts d'un escrow."""
    PENDING = "pending"  # En attente de paiement
    FUNDED = "funded"  # Fonds déposés
    IN_PROGRESS = "in_progress"  Service en cours
    COMPLETED = "completed"  # Service terminé, fonds libérés
    DISPUTED = "disputed"  # Litige en cours
    CANCELLED = "cancelled"  # Annulé, fonds remboursés
    REFUNDED = "refunded"  # Remboursé au client


class DisputeStatus(Enum):
    """Statuts d'un litige."""
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class EscrowContract:
    """Contrat d'escrow."""
    escrow_id: str
    client_did: str
    provider_did: str
    service_id: str
    amount: float  # USDC
    status: EscrowStatus
    created_at: datetime
    funded_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    dispute_id: Optional[str] = None
    contract_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit l'escrow en dictionnaire."""
        return {
            "escrow_id": self.escrow_id,
            "client_did": self.client_did,
            "provider_did": self.provider_did,
            "service_id": self.service_id,
            "amount": self.amount,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "funded_at": self.funded_at.isoformat() if self.funded_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "dispute_id": self.dispute_id,
            "contract_address": self.contract_address,
            "transaction_hash": self.transaction_hash,
            "metadata": self.metadata,
        }


@dataclass
class DisputeCase:
    """Cas de litige."""
    dispute_id: str
    escrow_id: str
    client_did: str
    provider_did: str
    reason: str
    status: DisputeStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    client_share: Optional[float] = None  # Pourcentage pour le client
    provider_share: Optional[float] = None  # Pourcentage pour le fournisseur
    mediator_did: Optional[str] = None
    evidence: List[Dict[str, any]] = field(default_factory=list)
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit le litige en dictionnaire."""
        return {
            "dispute_id": self.dispute_id,
            "escrow_id": self.escrow_id,
            "client_did": self.client_did,
            "provider_did": self.provider_did,
            "reason": self.reason,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
            "client_share": self.client_share,
            "provider_share": self.provider_share,
            "mediator_did": self.mediator_did,
            "evidence": self.evidence,
            "metadata": self.metadata,
        }


class EscrowSystem:
    """Système d'escrow décentralisé."""
    
    def __init__(self):
        self.escrows: Dict[str, EscrowContract] = {}
        self.disputes: Dict[str, DisputeCase] = {}
        self.web3 = Web3(Web3.HTTPProvider(settings.ETHEREUM_RPC_URL))
        
        # Paramètres d'escrow
        self.dispute_timeout_days = 7
        self.completion_timeout_days = 30
        self.mediation_fee_percentage = 0.05  # 5% pour la médiation
        
        logger.info("EscrowSystem initialisé")
    
    async def create_escrow(
        self,
        client_did: str,
        provider_did: str,
        service_id: str,
        amount: float,
        metadata: Optional[Dict[str, any]] = None
    ) -> EscrowContract:
        """Crée un nouvel escrow."""
        escrow_id = self._generate_escrow_id(client_did, provider_did, service_id)
        
        escrow = EscrowContract(
            escrow_id=escrow_id,
            client_did=client_did,
            provider_did=provider_did,
            service_id=service_id,
            amount=amount,
            status=EscrowStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        
        # Stocker l'escrow
        self.escrows[escrow_id] = escrow
        
        logger.info(f"Escrow créé: {escrow_id} pour le service {service_id}")
        return escrow
    
    async def fund_escrow(
        self,
        escrow_id: str,
        transaction_hash: str,
        contract_address: Optional[str] = None
    ) -> Optional[EscrowContract]:
        """Fonde un escrow (dépôt des fonds)."""
        if escrow_id not in self.escrows:
            return None
        
        escrow = self.escrows[escrow_id]
        
        if escrow.status != EscrowStatus.PENDING:
            logger.warning(f"Escrow {escrow_id} n'est pas en attente: {escrow.status}")
            return None
        
        # Mettre à jour l'escrow
        escrow.status = EscrowStatus.FUNDED
        escrow.funded_at = datetime.now(timezone.utc)
        escrow.transaction_hash = transaction_hash
        
        if contract_address:
            escrow.contract_address = contract_address
        
        logger.info(f"Escrow fondé: {escrow_id}")
        return escrow
    
    async def start_service(
        self,
        escrow_id: str
    ) -> Optional[EscrowContract]:
        """Démarre le service (passe en cours)."""
        if escrow_id not in self.escrows:
            return None
        
        escrow = self.escrows[escrow_id]
        
        if escrow.status != EscrowStatus.FUNDED:
            logger.warning(f"Escrow {escrow_id} n'est pas fondé: {escrow.status}")
            return None
        
        # Mettre à jour l'escrow
        escrow.status = EscrowStatus.IN_PROGRESS
        
        logger.info(f"Service démarré pour l'escrow {escrow_id}")
        return escrow
    
    async def complete_service(
        self,
        escrow_id: str,
        release_transaction_hash: Optional[str] = None
    ) -> Optional[EscrowContract]:
        """Termine le service et libère les fonds."""
        if escrow_id not in self.escrows:
            return None
        
        escrow = self.escrows[escrow_id]
        
        if escrow.status != EscrowStatus.IN_PROGRESS:
            logger.warning(f"Escrow {escrow_id} n'est pas en cours: {escrow.status}")
            return None
        
        # Mettre à jour l'escrow
        escrow.status = EscrowStatus.COMPLETED
        escrow.completed_at = datetime.now(timezone.utc)
        
        if release_transaction_hash:
            escrow.transaction_hash = release_transaction_hash
        
        logger.info(f"Service terminé pour l'escrow {escrow_id}")
        return escrow
    
    async def open_dispute(
        self,
        escrow_id: str,
        disputer_did: str,
        reason: str,
        evidence: Optional[List[Dict[str, any]]] = None
    ) -> Optional[DisputeCase]:
        """Ouvre un litige sur un escrow."""
        if escrow_id not in self.escrows:
            return None
        
        escrow = self.escrows[escrow_id]
        
        # Vérifier que l'escrow est dans un état disputable
        if escrow.status not in [EscrowStatus.FUNDED, EscrowStatus.IN_PROGRESS]:
            logger.warning(f"Escrow {escrow_id} n'est pas disputable: {escrow.status}")
            return None
        
        # Vérifier que le disputer est soit le client soit le fournisseur
        if disputer_did not in [escrow.client_did, escrow.provider_did]:
            logger.warning(f"Disputer {disputer_did} n'est pas autorisé")
            return None
        
        # Générer un ID de litige
        dispute_id = self._generate_dispute_id(escrow_id, disputer_did)
        
        # Créer le cas de litige
        dispute = DisputeCase(
            dispute_id=dispute_id,
            escrow_id=escrow_id,
            client_did=escrow.client_did,
            provider_did=escrow.provider_did,
            reason=reason,
            status=DisputeStatus.OPEN,
            created_at=datetime.now(timezone.utc),
            evidence=evidence or [],
        )
        
        # Stocker le litige
        self.disputes[dispute_id] = dispute
        
        # Mettre à jour l'escrow
        escrow.status = EscrowStatus.DISPUTED
        escrow.dispute_id = dispute_id
        
        logger.info(f"Litige ouvert: {dispute_id} pour l'escrow {escrow_id}")
        return dispute
    
    async def resolve_dispute(
        self,
        dispute_id: str,
        resolution: str,
        client_share: float,
        provider_share: float,
        mediator_did: Optional[str] = None
    ) -> Optional[DisputeCase]:
        """Résout un litige."""
        if dispute_id not in self.disputes:
            return None
        
        dispute = self.disputes[dispute_id]
        
        if dispute.status != DisputeStatus.OPEN:
            logger.warning(f"Litige {dispute_id} n'est pas ouvert: {dispute.status}")
            return None
        
        # Vérifier que les parts sont valides
        if abs(client_share + provider_share - 1.0) > 0.001:
            logger.warning(f"Parts invalides: client={client_share}, provider={provider_share}")
            return None
        
        # Mettre à jour le litige
        dispute.status = DisputeStatus.RESOLVED
        dispute.resolved_at = datetime.now(timezone.utc)
        dispute.resolution = resolution
        dispute.client_share = client_share
        dispute.provider_share = provider_share
        dispute.mediator_did = mediator_did
        
        # Mettre à jour l'escrow correspondant
        escrow_id = dispute.escrow_id
        if escrow_id in self.escrows:
            escrow = self.escrows[escrow_id]
            
            # Marquer comme terminé avec litige
            escrow.status = EscrowStatus.COMPLETED
            escrow.completed_at = datetime.now(timezone.utc)
        
        logger.info(f"Litige résolu: {dispute_id}")
        return dispute
    
    async def cancel_escrow(
        self,
        escrow_id: str,
        canceller_did: str,
        refund_transaction_hash: Optional[str] = None
    ) -> Optional[EscrowContract]:
        """Annule un escrow et rembourse les fonds."""
        if escrow_id not in self.escrows:
            return None
        
        escrow = self.escrows[escrow_id]
        
        # Vérifier que l'annulateur est autorisé
        if canceller_did not in [escrow.client_did, escrow.provider_did]:
            logger.warning(f"Annulateur {canceller_did} non autorisé")
            return None
        
        # Vérifier que l'escrow peut être annulé
        if escrow.status not in [EscrowStatus.PENDING, EscrowStatus.FUNDED]:
            logger.warning(f"Escrow {escrow_id} ne peut pas être annulé: {escrow.status}")
            return None
        
        # Mettre à jour l'escrow
        escrow.status = EscrowStatus.CANCELLED
        escrow.cancelled_at = datetime.now(timezone.utc)
        
        if refund_transaction_hash:
            escrow.transaction_hash = refund_transaction_hash
        
        logger.info(f"Escrow annulé: {escrow_id}")
        return escrow
    
    async def refund_escrow(
        self,
        escrow_id: str,
        refund_transaction_hash: str
    ) -> Optional[EscrowContract]:
        """Rembourse un escrow (après litige ou annulation)."""
        if escrow_id not in self.escrows:
            return None
        
        escrow = self.escrows[escrow_id]
        
        if escrow.status not in [EscrowStatus.CANCELLED, EscrowStatus.DISPUTED]:
            logger.warning(f"Escrow {escrow_id} ne peut pas être remboursé: {escrow.status}")
            return None
        
        # Mettre à jour l'escrow
        escrow.status = EscrowStatus.REFUNDED
        escrow.transaction_hash = refund_transaction_hash
        
        logger.info(f"Escrow remboursé: {escrow_id}")
        return escrow
    
    async def check_timeouts(self) -> List[Tuple[str, str]]:
        """Vérifie les timeouts et retourne les actions nécessaires."""
        actions = []
        now = datetime.now(timezone.utc)
        
        for escrow_id, escrow in self.escrows.items():
            # Vérifier les timeouts de complétion
            if escrow.status == EscrowStatus.IN_PROGRESS:
                timeout_date = escrow.funded_at + timedelta(days=self.completion_timeout_days)
                if now > timeout_date:
                    actions.append((escrow_id, "completion_timeout"))
            
            # Vérifier les timeouts de litige
            if escrow.status == EscrowStatus.DISPUTED and escrow.dispute_id:
                dispute = self.disputes.get(escrow.dispute_id)
                if dispute and dispute.status == DisputeStatus.OPEN:
                    timeout_date = dispute.created_at + timedelta(days=self.dispute_timeout_days)
                    if now > timeout_date:
                        actions.append((escrow_id, "dispute_timeout"))
        
        return actions
    
    def get_escrow(self, escrow_id: str) -> Optional[EscrowContract]:
        """Récupère un escrow par son ID."""
        return self.escrows.get(escrow_id)
    
    def get_dispute(self, dispute_id: str) -> Optional[DisputeCase]:
        """Récupère un litige par son ID."""
        return self.disputes.get(dispute_id)
    
    def get_agent_escrows(self, agent_did: str) -> List[EscrowContract]:
        """Récupère tous les escrows d'un agent (en tant que client ou fournisseur)."""
        return [
            escrow for escrow in self.escrows.values()
            if escrow.client_did == agent_did or escrow.provider_did == agent_did
        ]
    
    def _generate_escrow_id(
        self,
        client_did: str,
        provider_did: str,
        service_id: str
    ) -> str:
        """Génère un ID unique pour un escrow."""
        import time
        
        timestamp = str(time.time_ns())
        data = f"{client_did}:{provider_did}:{service_id}:{timestamp}"
        
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def _generate_dispute_id(self, escrow_id: str, disputer_did: str) -> str:
        """Génère un ID unique pour un litige."""
        import time
        
        timestamp = str(time.time_ns())
        data = f"{escrow_id}:{disputer_did}:{timestamp}"
        
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def export_escrow_data(self) -> Dict[str, any]:
        """Exporte toutes les données d'escrow."""
        return {
            "escrows": {
                eid: escrow.to_dict()
                for eid, escrow in self.escrows.items()
            },
            "disputes": {
                did: dispute.to_dict()
                for did, dispute in self.disputes.items()
            },
            "parameters": {
                "dispute_timeout_days": self.dispute_timeout_days,
                "completion_timeout_days": self.completion_timeout_days,
                "mediation_fee_percentage": self.mediation_fee_percentage,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }