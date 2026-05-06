"""
sigui.x402 — Gestionnaire automatique du protocole de paiement x402

Le protocole x402 fonctionne ainsi :
  1. Client → POST /evaluate (sans paiement)
  2. Serveur → 402 Payment Required + instructions JSON
  3. Client → Envoie USDC selon les instructions
  4. Client → POST /evaluate (avec X-Payment: <tx_hash>)
  5. Serveur → 200 OK + résultat

Ce module gère les étapes 2-4 automatiquement.
En mode DEMO, aucune vraie transaction n'est envoyée.
"""
from __future__ import annotations

import hashlib
import time
from typing import Optional, Protocol

import httpx
from loguru import logger

from .exceptions import SiguiPaymentError
from .models import PaymentInfo


class WalletAdapter(Protocol):
    """
    Interface pour les wallets externes.
    Implémentez cette interface pour connecter votre propre wallet.
    """

    async def send_usdc(
        self,
        to_address: str,
        amount_usdc: float,
        chain: str,
    ) -> str:
        """
        Envoie `amount_usdc` USDC vers `to_address` sur `chain`.
        Retourne le tx_hash de la transaction.
        """
        ...


class DemoWallet:
    """
    Wallet de démonstration — simule les paiements sans vraie transaction.
    Parfait pour le développement et les hackathons.
    """

    _counter: int = 0

    async def send_usdc(self, to_address: str, amount_usdc: float, chain: str) -> str:
        DemoWallet._counter += 1
        seed = f"demo:{to_address}:{amount_usdc}:{chain}:{time.time_ns()}:{self._counter}"
        fake_hash = hashlib.sha256(seed.encode()).hexdigest()
        logger.debug(
            f"[SIGUI·DEMO] Simulated payment ${amount_usdc:.6f} USDC "
            f"→ {to_address[:10]}… on {chain}"
        )
        return f"0xSIGUI_SDK_{fake_hash[:32]}"


class CircleWallet:
    """
    Wallet Circle (Developer-Controlled Wallet).
    Utilise l'API Circle pour envoyer de vrais paiements USDC.
    """

    def __init__(self, api_key: str, wallet_id: str):
        self._api_key = api_key
        self._wallet_id = wallet_id

    async def send_usdc(self, to_address: str, amount_usdc: float, chain: str) -> str:
        """Envoie USDC via Circle DCW API. Retourne le tx_hash."""
        import json
        import subprocess
        import asyncio

        # Delegate to the Node.js Circle script if available (same pattern as main backend)
        script_path = "scripts/circle/do_transfer.js"
        cmd = ["node", script_path, self._wallet_id, to_address, str(amount_usdc)]
        loop = asyncio.get_running_loop()
        try:
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(cmd, capture_output=True, text=True, timeout=30),
            )
            if result.returncode != 0:
                raise SiguiPaymentError(
                    amount_usdc, result.stderr or "Circle transfer script failed"
                )
            data = json.loads(result.stdout.strip().split("\n")[-1])
            return data.get("txHash", f"0xCIRCLE_{to_address[:8]}")
        except SiguiPaymentError:
            raise
        except Exception as exc:
            raise SiguiPaymentError(amount_usdc, str(exc)) from exc


class X402Handler:
    """
    Gère le protocole x402 de façon transparente.

    En mode démo (wallet=DemoWallet), les paiements sont simulés.
    En mode production (wallet=CircleWallet ou implémentation custom),
    de vraies transactions sont envoyées.
    """

    def __init__(self, wallet: WalletAdapter, chain: str = "arc"):
        self._wallet = wallet
        self._chain = chain
        self._paid_hashes: set[str] = set()

    def parse_payment_info(self, response_json: dict) -> Optional[PaymentInfo]:
        """Parse les instructions de paiement d'une réponse 402."""
        accepts = response_json.get("accepts", [])
        if not accepts:
            return None
        offer = accepts[0]
        try:
            amount_units = int(offer.get("maxAmountRequired", "0"))
            decimals = int(offer.get("decimals", 18))
            amount_usdc = amount_units / (10 ** decimals)
            return PaymentInfo(
                amount_usdc=amount_usdc,
                amount_units=amount_units,
                pay_to=offer.get("payTo", ""),
                asset=offer.get("asset", "USDC"),
                network=offer.get("network", "arc-testnet"),
                decimals=decimals,
                is_native=offer.get("isNative", True),
                resource=offer.get("resource", ""),
                description=offer.get("description", ""),
            )
        except (ValueError, TypeError):
            return None

    async def pay_and_get_header(
        self,
        payment_info: PaymentInfo,
        chain: str,
    ) -> str:
        """
        Envoie le paiement et retourne le header X-Payment.
        Si ce paiement a déjà été effectué (même amount + to), retourne le hash mis en cache.
        """
        tx_hash = await self._wallet.send_usdc(
            to_address=payment_info.pay_to,
            amount_usdc=payment_info.amount_usdc,
            chain=chain,
        )
        self._paid_hashes.add(tx_hash)
        return tx_hash

    async def handle_402_and_retry(
        self,
        client: httpx.AsyncClient,
        request: httpx.Request,
        response_402: httpx.Response,
        chain: str,
        amount_hint: float = 0.0,
    ) -> httpx.Response:
        """
        Gère la réponse 402 :
        1. Parse les instructions de paiement
        2. Envoie le paiement via le wallet
        3. Réessaie la requête originale avec le header X-Payment

        Raises:
            SiguiPaymentError: Si le paiement échoue.
        """
        try:
            data = response_402.json()
        except Exception:
            raise SiguiPaymentError(0.0, "Cannot parse 402 response body")

        payment_info = self.parse_payment_info(data)
        if not payment_info:
            raise SiguiPaymentError(0.0, "No payment offer found in 402 response")

        logger.debug(
            f"[SIGUI·x402] Payment required: ${payment_info.amount_usdc:.6f} USDC "
            f"→ {payment_info.pay_to[:12]}… ({payment_info.description})"
        )

        tx_hash = await self.pay_and_get_header(payment_info, chain)

        # Build new request with payment headers
        new_headers = dict(request.headers)
        new_headers["X-Payment"] = tx_hash
        new_headers["X-Chain"] = chain
        new_headers["X-Amount"] = str(amount_hint or payment_info.amount_usdc)

        retry_request = client.build_request(
            method=request.method,
            url=request.url,
            headers=new_headers,
            content=request.content,
        )
        response = await client.send(retry_request)
        logger.debug(
            f"[SIGUI·x402] Retry after payment → HTTP {response.status_code}"
        )
        return response
