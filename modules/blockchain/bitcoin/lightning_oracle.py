"""
Oracle Lightning Network pour Sigui - Surveillance des paiements instantanés
"""

import asyncio
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
import logging

from .bitcoin_adapter import BitcoinAdapter, LightningInvoice
from ...reputation.reputation_oracle import ReputationOracle


logger = logging.getLogger(__name__)


@dataclass
class LightningPaymentEvent:
    """Événement de paiement Lightning"""
    payment_hash: str
    amount_sats: int
    timestamp: int
    sender_did: Optional[str] = None
    receiver_did: Optional[str] = None
    service_id: Optional[str] = None
    metadata: Optional[Dict] = None


class LightningOracle:
    """Oracle pour surveiller et valider les paiements Lightning Network"""
    
    def __init__(self, bitcoin_adapter: BitcoinAdapter, reputation_oracle: ReputationOracle):
        self.bitcoin_adapter = bitcoin_adapter
        self.reputation_oracle = reputation_oracle
        self._active_invoices: Dict[str, LightningInvoice] = {}
        self._payment_events: Dict[str, LightningPaymentEvent] = {}
        self._monitoring_tasks: List[asyncio.Task] = []
        self._callbacks: List[callable] = []
        
    async def initialize(self) -> bool:
        """Initialise l'oracle Lightning"""
        try:
            # Vérifie que Lightning est activé
            if not self.bitcoin_adapter.config.lightning_enabled:
                logger.warning("Lightning Network désactivé dans la configuration")
                return False
            
            # Démarre la surveillance
            await self._start_invoice_monitoring()
            
            logger.info("Oracle Lightning Network initialisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur initialisation oracle Lightning: {e}")
            return False
    
    async def create_service_invoice(self, service_id: str, amount_sats: int,
                                    provider_did: str, client_did: str,
                                    memo: Optional[str] = None) -> Optional[LightningInvoice]:
        """Crée une facture Lightning pour un service"""
        try:
            # Vérifie la réputation du client
            client_trust = self.reputation_oracle.get_trust_score(client_did)
            if client_trust < 0.3:  # Seuil minimum
                logger.warning(f"Client {client_did} a une réputation trop faible: {client_trust}")
                return None
            
            # Crée la facture
            invoice_memo = memo or f"Service: {service_id} | Provider: {provider_did}"
            invoice = await self.bitcoin_adapter.create_lightning_invoice(
                amount_sats=amount_sats,
                memo=invoice_memo,
                expiry_seconds=7200  # 2 heures
            )
            
            if invoice:
                # Stocke les métadonnées
                invoice.metadata = {
                    "service_id": service_id,
                    "provider_did": provider_did,
                    "client_did": client_did,
                    "created_at": time.time()
                }
                
                # Ajoute à la surveillance
                self._active_invoices[invoice.payment_hash] = invoice
                
                logger.info(f"Facture service créée: {service_id} - {amount_sats} sats")
                
            return invoice
            
        except Exception as e:
            logger.error(f"Erreur création facture service: {e}")
            return None
    
    async def verify_payment(self, payment_hash: str, expected_amount_sats: int) -> bool:
        """Vérifie si un paiement a été effectué"""
        try:
            # Vérifie dans les événements enregistrés
            if payment_hash in self._payment_events:
                event = self._payment_events[payment_hash]
                if event.amount_sats >= expected_amount_sats:
                    return True
            
            # Vérifie avec l'adaptateur Bitcoin (implémentation simplifiée)
            # Dans une vraie implémentation, on vérifierait avec LND gRPC
            
            return False
            
        except Exception as e:
            logger.error(f"Erreur vérification paiement: {e}")
            return False
    
    async def process_escrow_payment(self, escrow_id: str, payment_hash: str,
                                    provider_did: str, client_did: str,
                                    amount_sats: int) -> bool:
        """Traite un paiement d'escrow via Lightning"""
        try:
            # Vérifie le paiement
            if not await self.verify_payment(payment_hash, amount_sats):
                logger.error(f"Paiement non vérifié pour escrow {escrow_id}")
                return False
            
            # Enregistre l'événement
            event = LightningPaymentEvent(
                payment_hash=payment_hash,
                amount_sats=amount_sats,
                timestamp=int(time.time()),
                sender_did=client_did,
                receiver_did=provider_did,
                service_id=f"escrow_{escrow_id}",
                metadata={
                    "escrow_id": escrow_id,
                    "payment_method": "lightning",
                    "processed_at": time.time()
                }
            )
            
            self._payment_events[payment_hash] = event
            
            # Met à jour la réputation
            await self._update_reputation_from_payment(client_did, provider_did, amount_sats)
            
            # Déclenche les callbacks
            await self._trigger_callbacks(event)
            
            logger.info(f"Paiement escrow traité: {escrow_id} - {amount_sats} sats")
            return True
            
        except Exception as e:
            logger.error(f"Erreur traitement paiement escrow: {e}")
            return False
    
    async def _update_reputation_from_payment(self, payer_did: str, payee_did: str, amount_sats: int):
        """Met à jour la réputation basée sur les paiements"""
        try:
            # Le payeur qui paie augmente sa réputation
            payer_increment = min(amount_sats / 1000000, 0.1)  # Max 0.1 pour 1M sats
            await self.reputation_oracle.update_trust_score(
                target_did=payer_did,
                increment=payer_increment,
                reason="successful_payment",
                metadata={"amount_sats": amount_sats, "payee": payee_did}
            )
            
            # Le bénéficiaire qui reçoit un paiement augmente sa réputation
            payee_increment = min(amount_sats / 2000000, 0.05)  # Max 0.05 pour 2M sats
            await self.reputation_oracle.update_trust_score(
                target_did=payee_did,
                increment=payee_increment,
                reason="payment_received",
                metadata={"amount_sats": amount_sats, "payer": payer_did}
            )
            
        except Exception as e:
            logger.error(f"Erreur mise à jour réputation paiement: {e}")
    
    async def get_payment_stats(self, did: str, time_range_hours: int = 24) -> Dict:
        """Récupère les statistiques de paiement pour un DID"""
        try:
            now = time.time()
            cutoff = now - (time_range_hours * 3600)
            
            sent_payments = []
            received_payments = []
            total_sent = 0
            total_received = 0
            
            for event in self._payment_events.values():
                if event.timestamp >= cutoff:
                    if event.sender_did == did:
                        sent_payments.append(event)
                        total_sent += event.amount_sats
                    elif event.receiver_did == did:
                        received_payments.append(event)
                        total_received += event.amount_sats
            
            return {
                "sent_count": len(sent_payments),
                "received_count": len(received_payments),
                "total_sent_sats": total_sent,
                "total_received_sats": total_received,
                "sent_payments": [
                    {
                        "amount_sats": p.amount_sats,
                        "timestamp": p.timestamp,
                        "receiver": p.receiver_did
                    }
                    for p in sent_payments[:10]  # Limite à 10
                ],
                "received_payments": [
                    {
                        "amount_sats": p.amount_sats,
                        "timestamp": p.timestamp,
                        "sender": p.sender_did
                    }
                    for p in received_payments[:10]
                ]
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération stats paiement: {e}")
            return {}
    
    def register_callback(self, callback: callable):
        """Enregistre un callback pour les événements de paiement"""
        self._callbacks.append(callback)
    
    async def _trigger_callbacks(self, event: LightningPaymentEvent):
        """Déclenche les callbacks enregistrés"""
        for callback in self._callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Erreur callback paiement: {e}")
    
    async def _start_invoice_monitoring(self):
        """Démarre la surveillance des factures"""
        async def monitor_invoices():
            while True:
                try:
                    await self._check_invoice_expiry()
                    await asyncio.sleep(60)  # Vérifie toutes les minutes
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Erreur surveillance factures: {e}")
                    await asyncio.sleep(10)
        
        task = asyncio.create_task(monitor_invoices())
        self._monitoring_tasks.append(task)
    
    async def _check_invoice_expiry(self):
        """Vérifie l'expiration des factures"""
        now = time.time()
        expired_hashes = []
        
        for payment_hash, invoice in self._active_invoices.items():
            if invoice.created_at + invoice.expiry_seconds < now:
                expired_hashes.append(payment_hash)
                logger.info(f"Facture expirée: {payment_hash}")
        
        for payment_hash in expired_hashes:
            del self._active_invoices[payment_hash]
    
    async def cleanup(self):
        """Nettoie les ressources"""
        for task in self._monitoring_tasks:
            task.cancel()
        
        if self._monitoring_tasks:
            await asyncio.gather(*self._monitoring_tasks, return_exceptions=True)
        
        self._monitoring_tasks.clear()
        self._active_invoices.clear()
        self._payment_events.clear()
        self._callbacks.clear()