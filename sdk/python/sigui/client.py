"""
sigui.client — Client principal du SDK Sigui Protocol

Usage (async):
    from sigui import SiguiClient, Chain

    client = SiguiClient(api_url="http://localhost:8000")  # demo mode auto

    result = await client.evaluate(
        agent_id="my_agent",
        amount=0.50,
        destination="0xRecipient",
        action_type="transfer",
    )
    if result.is_safe:
        print("✅ Payment authorized")
    else:
        print(f"🚫 Blocked — {result.reason}")

Usage (sync, pour les agents non-async):
    from sigui import SiguiClientSync
    result = SiguiClientSync(...).evaluate(...)
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import httpx
from loguru import logger

from .exceptions import (
    SiguiAuthError,
    SiguiBlockedError,
    SiguiConnectionError,
    SiguiEscalationRequiredError,
    SiguiPaymentError,
    SiguiRateLimitError,
    SiguiServiceUnavailableError,
)
from .models import (
    Chain,
    EscalationResult,
    EvaluationResult,
    TreasuryState,
    Verdict,
)
from .x402 import CircleWallet, DemoWallet, WalletAdapter, X402Handler

_DEFAULT_TIMEOUT = 15.0
_SDK_VERSION = "0.2.0"


class SiguiClient:
    """
    Client asynchrone pour le Sigui Protocol.

    Args:
        api_url:          URL de l'API Sigui (ex: "http://localhost:8000").
        wallet:           Adapter de wallet pour les paiements x402.
                          Défaut : DemoWallet (simulation, aucune tx réelle).
        chain:            Chaîne par défaut (arc, ethereum, solana).
        agent_id:         Identifiant par défaut de l'agent appelant.
        raise_on_block:   Si True, lève SiguiBlockedError quand verdict=BLOCK.
        raise_on_escalate:Si True, lève SiguiEscalationRequiredError quand verdict=ESCALATE.
        timeout:          Timeout HTTP en secondes.

    Examples:
        # Mode démo (hackathon / développement)
        client = SiguiClient(api_url="http://localhost:8000")

        # Mode production avec Circle
        from sigui import CircleWallet
        wallet = CircleWallet(api_key="circle_key", wallet_id="wlt_xxx")
        client = SiguiClient(api_url="https://api.sigui.io", wallet=wallet)
    """

    def __init__(
        self,
        api_url: str = "http://localhost:8000",
        wallet: Optional[WalletAdapter] = None,
        chain: str | Chain = Chain.ARC,
        agent_id: str = "sdk_agent",
        raise_on_block: bool = False,
        raise_on_escalate: bool = False,
        timeout: float = _DEFAULT_TIMEOUT,
        config = None,
    ):
        from .config import SiguiConfig
        self.config = config
        if self.config is None:
            self.config = SiguiConfig(
                api_url=api_url,
                chains=[chain.value if isinstance(chain, Chain) else chain]
            )
        self._api_url = self.config.api_url.rstrip("/")
        self._wallet = wallet or DemoWallet()
        self._chain = Chain(chain) if isinstance(chain, str) else chain
        self._default_agent_id = agent_id
        self._raise_on_block = raise_on_block
        self._raise_on_escalate = raise_on_escalate
        self._timeout = timeout
        self._x402 = X402Handler(self._wallet, self._chain.value)
        self._http: Optional[httpx.AsyncClient] = None
        self._mode = self._detect_mode()

        is_demo = isinstance(self._wallet, DemoWallet)
        logger.info(
            f"[SIGUI·SDK v{_SDK_VERSION}] Initialized — "
            f"api={self._api_url} chain={self._chain.value} "
            f"mode={self._mode.upper()}"
        )

    def _detect_mode(self) -> str:
        if self.config and self.config.api_key:
            return "network"
        if "network.sigui.io" in self._api_url:
            return "network"
        if not self.config or not getattr(self.config, "api_key", None):
            return "local"
        return getattr(self.config, "mode", "api")

    # ── Context manager ────────────────────────────────────────────────────────

    async def __aenter__(self) -> "SiguiClient":
        headers = {}
        if self.config and getattr(self.config, "api_key", None):
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        self._http = httpx.AsyncClient(timeout=self._timeout, headers=headers)
        return self

    async def __aexit__(self, *_):
        if self._http:
            await self._http.aclose()
            self._http = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._http is None:
            headers = {}
            if self.config and getattr(self.config, "api_key", None):
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            self._http = httpx.AsyncClient(timeout=self._timeout, headers=headers)
        return self._http

    # ── Base HTTP call with x402 auto-handling ─────────────────────────────────

    async def _post(
        self,
        path: str,
        body: dict,
        chain: str,
        amount_hint: float = 0.0,
    ) -> dict:
        """
        POST to the Sigui API.
        Automatically handles x402 (pay → retry) if needed.
        """
        client = self._get_client()
        url = f"{self._api_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "X-Chain": chain,
            "X-Amount": str(amount_hint),
            "User-Agent": f"sigui-python-sdk/{_SDK_VERSION}",
        }

        try:
            response = await client.post(url, json=body, headers=headers)
        except httpx.ConnectError as exc:
            raise SiguiConnectionError(url, str(exc)) from exc
        except httpx.TimeoutException as exc:
            raise SiguiConnectionError(url, f"timeout after {self._timeout}s") from exc

        # x402 — automatic payment
        if response.status_code == 402:
            logger.debug(f"[SIGUI·SDK] 402 received — initiating x402 payment")
            request = client.build_request(
                "POST", url, json=body, headers=headers
            )
            response = await self._x402.handle_402_and_retry(
                client, request, response, chain, amount_hint
            )

        # Error handling
        if response.status_code == 401:
            raise SiguiAuthError("Invalid credentials or wallet not authorized.")
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            raise SiguiRateLimitError(retry_after)
        if response.status_code == 503:
            raise SiguiServiceUnavailableError(
                "Sigui is in EMERGENCY mode — service temporarily unavailable."
            )
        if response.status_code >= 400:
            detail = ""
            try:
                detail = response.json().get("detail", "")
            except Exception:
                pass
            raise SiguiConnectionError(url, f"HTTP {response.status_code}: {detail}")

        return response.json()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def evaluate(
        self,
        amount: float,
        destination: str,
        agent_id: Optional[str] = None,
        action_type: str = "transfer",
        chain: Optional[str | Chain] = None,
        context: Optional[dict] = None,
        raise_on_block: Optional[bool] = None,
        raise_on_escalate: Optional[bool] = None,
    ) -> EvaluationResult:
        """
        Évalue la sécurité d'une action avant de l'exécuter.

        Args:
            amount:       Montant en USDC de la transaction à évaluer.
            destination:  Adresse de destination (hex ou base58).
            agent_id:     Identifiant de l'agent (défaut: celui du client).
            action_type:  Type d'action ("transfer", "swap", "stake", etc.).
            chain:        Chaîne cible. Défaut: chaîne du client.
            context:      Contexte additionnel (optionnel).
            raise_on_block:   Override du paramètre client.
            raise_on_escalate: Override du paramètre client.

        Returns:
            EvaluationResult avec .verdict, .risk_score, .reason, etc.

        Raises:
            SiguiBlockedError: Si raise_on_block=True et verdict=BLOCK.
            SiguiEscalationRequiredError: Si raise_on_escalate=True et verdict=ESCALATE.
            SiguiConnectionError: Si l'API est injoignable.
            SiguiPaymentError: Si le paiement x402 échoue.

        Example:
            result = await client.evaluate(
                amount=5.0,
                destination="0xAbc...",
                action_type="transfer",
            )
            if result.is_safe:
                # proceed with the transaction
                pass
        """
        _chain = (
            (Chain(chain) if isinstance(chain, str) else chain) or self._chain
        ).value
        _agent_id = agent_id or self._default_agent_id
        _raise_block = raise_on_block if raise_on_block is not None else self._raise_on_block
        _raise_escalate = raise_on_escalate if raise_on_escalate is not None else self._raise_on_escalate

        if self._mode == "local":
            from .local.rules_engine import LocalRulesEngine
            engine = LocalRulesEngine(self.config)
            result = engine.evaluate(amount, destination, context or {})
            
            if _raise_block and result.is_blocked:
                from .exceptions import SiguiBlockedError
                raise SiguiBlockedError(result)
            if _raise_escalate and result.needs_escalation:
                from .exceptions import SiguiEscalateError
                raise SiguiEscalateError(result)
            return result

        body: dict[str, Any] = {
            "agent_id": _agent_id,
            "action_type": action_type,
            "amount_usdc": amount,
            "destination": destination,
            "chain": _chain,
            "context": context or {},
            "weights": self.config.weights,
        }

        t0 = time.perf_counter()
        raw = await self._post("/evaluate", body, _chain, amount_hint=amount)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        result = EvaluationResult(
            verdict=Verdict(raw.get("decision", "BLOCK")),
            risk_score=float(raw.get("risk_score", 1.0)),
            confidence=float(raw.get("confidence", 0.0)),
            reason=str(raw.get("reason", "")),
            action_hash=str(raw.get("action_hash", "")),
            arc_tx_log=str(raw.get("arc_tx_log", "")),
            sigui_mode=str(raw.get("sigui_mode", "NORMAL")),
            escalation_available=bool(raw.get("escalation_available", False)),
            escalation_cost_usdc=float(raw.get("escalation_cost_usdc", 0.003)),
            policy_source=str(raw.get("policy_source", "")),
            processing_time_ms=int(raw.get("processing_time_ms", elapsed_ms)),
            vision_pattern=str(raw.get("vision_pattern", "NORMAL")),
            vision_confidence=float(raw.get("vision_confidence", 0.0)),
            evaluation_price_usdc=float(raw.get("evaluation_price_usdc", 0.001)),
            chain=_chain,
            raw=raw,
        )
        
        from .models import RawSignals
        if "raw_signals" in raw:
            raw_sig = raw["raw_signals"]
            result.raw_signals = RawSignals(
                behavioral=raw_sig.get("behavioral", {}),
                visual_topology=raw_sig.get("visual_topology", {}),
                financial=raw_sig.get("financial", {}),
                provenance=raw_sig.get("provenance", "unknown")
            )

        logger.info(
            f"[SIGUI·SDK] evaluate → {result.verdict.value} "
            f"risk={result.risk_score:.3f} "
            f"agent={_agent_id} amount=${amount:.4f} "
            f"chain={_chain} ({result.processing_time_ms}ms)"
        )

        if _raise_block and result.is_blocked:
            raise SiguiBlockedError(result)
        if _raise_escalate and result.needs_escalation:
            raise SiguiEscalationRequiredError(result)

        return result

    async def escalate(
        self,
        amount: float,
        destination: str,
        agent_id: Optional[str] = None,
        action_type: str = "transfer",
        chain: Optional[str | Chain] = None,
        context: Optional[dict] = None,
    ) -> EscalationResult:
        """
        Demande une analyse approfondie via Lebe (Qwen2.5 AMD) ou Claude.
        Coûte $0.003 USDC supplémentaire, payé automatiquement via x402.

        Utilisez ceci quand evaluate() retourne verdict=ESCALATE.

        Example:
            eval_result = await client.evaluate(amount=100.0, destination="0x...")
            if eval_result.needs_escalation:
                deep = await client.escalate(amount=100.0, destination="0x...")
                print(deep.analysis)
        """
        _chain = (
            (Chain(chain) if isinstance(chain, str) else chain) or self._chain
        ).value
        _agent_id = agent_id or self._default_agent_id

        body: dict[str, Any] = {
            "agent_id": _agent_id,
            "action_type": action_type,
            "amount_usdc": amount,
            "destination": destination,
            "chain": _chain,
            "context": context or {},
        }

        raw = await self._post("/escalate", body, _chain, amount_hint=amount)

        result = EscalationResult(
            verdict=Verdict(raw.get("escalation_result", "BLOCK")),
            cap_amount_usdc=float(raw.get("cap_amount_usdc", 0.0)),
            analysis=str(raw.get("analysis", "")),
            confidence=float(raw.get("confidence", 0.0)),
            paid_by_sigui=bool(raw.get("paid_by_sigui", False)),
            claude_cost_usdc=float(raw.get("claude_cost_usdc", 0.0)),
            arc_tx_log=str(raw.get("arc_tx_log", "")),
            fallback_used=bool(raw.get("fallback_used", False)),
            degraded_mode=bool(raw.get("degraded_mode", False)),
            reason=str(raw.get("reason", "")),
            inference_engine=str(raw.get("inference_engine", "rule_based")),
            inference_device=str(raw.get("inference_device", "CPU")),
            raw=raw,
        )

        logger.info(
            f"[SIGUI·SDK] escalate → {result.verdict.value} "
            f"engine={result.inference_engine} device={result.inference_device}"
        )
        return result

    async def evaluate_and_escalate(
        self,
        amount: float,
        destination: str,
        agent_id: Optional[str] = None,
        action_type: str = "transfer",
        chain: Optional[str | Chain] = None,
        context: Optional[dict] = None,
    ) -> EvaluationResult | EscalationResult:
        """
        Convenience method: évalue, et si ESCALATE est retourné, lance automatiquement
        l'analyse approfondie. Retourne toujours une décision finale.

        Example:
            result = await client.evaluate_and_escalate(
                amount=50.0,
                destination="0xRecipient",
            )
            # result is always a final decision, never ESCALATE
        """
        eval_result = await self.evaluate(
            amount=amount,
            destination=destination,
            agent_id=agent_id,
            action_type=action_type,
            chain=chain,
            context=context,
        )
        if eval_result.needs_escalation:
            logger.info(
                f"[SIGUI·SDK] Auto-escalating for agent={agent_id or self._default_agent_id}"
            )
            return await self.escalate(
                amount=amount,
                destination=destination,
                agent_id=agent_id,
                action_type=action_type,
                chain=chain,
                context=context,
            )
        return eval_result

    async def health(self) -> dict:
        """Vérifie que le serveur Sigui est en ligne et retourne son statut."""
        client = self._get_client()
        try:
            response = await client.get(f"{self._api_url}/health", timeout=5.0)
            return response.json()
        except Exception as exc:
            raise SiguiConnectionError(self._api_url, str(exc)) from exc

    async def treasury(self) -> TreasuryState:
        """Retourne l'état financier actuel du protocole Sigui."""
        client = self._get_client()
        response = await client.get(f"{self._api_url}/treasury", timeout=5.0)
        raw = response.json()
        return TreasuryState(
            balance=float(raw.get("balance", 0)),
            total_earned=float(raw.get("total_earned", 0)),
            total_spent=float(raw.get("total_spent", 0)),
            net_profit=float(raw.get("net_profit", 0)),
            mode=str(raw.get("mode", "NORMAL")),
            balances_by_chain=raw.get("balances_by_chain", {}),
        )

    async def close(self):
        """Ferme la connexion HTTP. Appelé automatiquement avec `async with`."""
        if self._http:
            await self._http.aclose()
            self._http = None


# ─────────────────────────────────────────────────────────────────────────────
# Sync wrapper (pour les agents non-async)
# ─────────────────────────────────────────────────────────────────────────────

class SiguiClientSync:
    """
    Version synchrone du SiguiClient.
    Utilise un event loop dédié — idéal pour les agents non-async.

    Example:
        client = SiguiClientSync(api_url="http://localhost:8000")
        result = client.evaluate(amount=1.0, destination="0x...")
        print(result.verdict)
    """

    def __init__(self, **kwargs):
        self._async_client = SiguiClient(**kwargs)
        self._loop = asyncio.new_event_loop()

    def _run(self, coro):
        return self._loop.run_until_complete(coro)

    def evaluate(self, **kwargs) -> EvaluationResult:
        return self._run(self._async_client.evaluate(**kwargs))

    def escalate(self, **kwargs) -> EscalationResult:
        return self._run(self._async_client.escalate(**kwargs))

    def evaluate_and_escalate(self, **kwargs) -> EvaluationResult | EscalationResult:
        return self._run(self._async_client.evaluate_and_escalate(**kwargs))

    def health(self) -> dict:
        return self._run(self._async_client.health())

    def treasury(self) -> TreasuryState:
        return self._run(self._async_client.treasury())

    def close(self):
        self._run(self._async_client.close())
        self._loop.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
