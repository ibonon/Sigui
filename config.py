"""
ArcWarden v3.0 — Configuration
Pydantic Settings with dotenv loading
"""

from typing import Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ─── Circle ───────────────────────────────────────────────────────────────
    circle_api_key: str = Field(default="demo_key", env="CIRCLE_API_KEY")
    arcwarden_wallet_id: str = Field(
        default="demo_wallet_id", env="ARCWARDEN_WALLET_ID"
    )
    arcwarden_wallet_address: str = Field(
        default="0xArcWarden000000000000000000000000000000",
        env="ARCWARDEN_WALLET_ADDRESS",
    )
    payer_wallet_id: str = Field(default="demo_payer_wallet_id", env="PAYER_WALLET_ID")
    payer_wallet_address: str = Field(default="", env="PAYER_WALLET_ADDRESS")
    attacker_wallet_id: str = Field(
        default="demo_attacker_wallet_id", env="ATTACKER_WALLET_ID"
    )
    attacker_wallet_address: str = Field(default="", env="ATTACKER_WALLET_ADDRESS")
    monitor_wallet_id: str = Field(
        default="demo_monitor_wallet_id", env="MONITOR_WALLET_ID"
    )
    monitor_wallet_address: str = Field(default="", env="MONITOR_WALLET_ADDRESS")
    learner_wallet_id: str = Field(
        default="demo_learner_wallet_id", env="LEARNER_WALLET_ID"
    )
    learner_wallet_address: str = Field(default="", env="LEARNER_WALLET_ADDRESS")
    grayzone_wallet_id: str = Field(
        default="demo_grayzone_wallet_id", env="GRAYZONE_WALLET_ID"
    )
    grayzone_wallet_address: str = Field(default="", env="GRAYZONE_WALLET_ADDRESS")

    # ─── Arc Testnet ──────────────────────────────────────────────────────────
    arc_rpc_url: str = Field(
        default="https://rpc.arc-testnet.network", env="ARC_RPC_URL"
    )
    arc_chain_id: int = Field(default=1234, env="ARC_CHAIN_ID")
    # Arc USDC has TWO interfaces (source: https://docs.arc.network/arc/references/contract-addresses):
    #   • Native gas token  → 18 decimals, no contract address needed (tx.value)
    #   • ERC-20 interface  →  6 decimals, address: 0x3600000000000000000000000000000000000000
    # Leave arc_usdc_token_address empty to use the native path (recommended for x402 payments).
    # Set it to 0x3600000000000000000000000000000000000000 to use the ERC-20 interface instead.
    arc_usdc_token_address: str = Field(default="", env="ARC_USDC_TOKEN_ADDRESS")
    arc_usdc_decimals: int = Field(default=18, env="ARC_USDC_DECIMALS")

    # Arc Testnet block explorer — used in demo/report for onchain proof links
    arc_explorer_url: str = Field(
        default="https://testnet.arcscan.app", env="ARC_EXPLORER_URL"
    )
    # ThreatRegistry smart contract (deployed by scripts/deploy_contract.py)
    # Leave empty until deployed. Set after running: python scripts/deploy_contract.py
    threat_registry_address: str = Field(default="", env="THREAT_REGISTRY_ADDRESS")
    arc_signer_private_key: str = Field(default="", env="ARC_SIGNER_PRIVATE_KEY")
    arc_signer_address: str = Field(default="", env="ARC_SIGNER_ADDRESS")
    arc_receipt_timeout_s: int = Field(default=30, env="ARC_RECEIPT_TIMEOUT_S")
    arc_required_confirmations: int = Field(default=1, env="ARC_REQUIRED_CONFIRMATIONS")

    # ─── Anthropic ────────────────────────────────────────────────────────────
    anthropic_api_key: str = Field(default="demo_key", env="ANTHROPIC_API_KEY")
    decision_ai_enabled: bool = Field(default=True, env="DECISION_AI_ENABLED")
    # FIX #21: corrected model name — 'claude-sonnet-4-20250514' does not exist in
    # the Anthropic API and would cause 400 errors on every escalation call.
    decision_ai_model: str = Field(
        default="claude-sonnet-4-5", env="DECISION_AI_MODEL"
    )
    decision_ai_timeout_s: int = Field(default=3, env="DECISION_AI_TIMEOUT_S")
    crewai_enabled: bool = Field(default=True, env="CREWAI_ENABLED")

    # ─── ArcWarden Pricing ────────────────────────────────────────────────────
    arcwarden_eval_price_usdc: float = Field(
        default=0.001, env="ARCWARDEN_EVAL_PRICE_USDC"
    )
    arcwarden_escalate_price_usdc: float = Field(
        default=0.003, env="ARCWARDEN_ESCALATE_PRICE_USDC"
    )
    claude_cost_per_escalation: float = Field(default=0.0006)

    # ─── Sigui P0 Pricing & Chains ────────────────────────────────────────────
    # Pricing proportionnel PRD: max(min_eval_price, amount * eval_rate)
    # Surcharge vision appliquée aux évaluations élevées.
    min_eval_price_usdc: float = Field(default=0.001, env="MIN_EVAL_PRICE_USDC")
    eval_price_rate: float = Field(default=0.0005, env="EVAL_PRICE_RATE")
    vision_fee_usdc: float = Field(default=0.0002, env="VISION_FEE_USDC")
    vision_fee_threshold_usdc: float = Field(
        default=0.01, env="VISION_FEE_THRESHOLD_USDC"
    )
    default_chain: str = Field(default="arc", env="DEFAULT_CHAIN")
    supported_chains_csv: str = Field(
        default="arc,ethereum,solana", env="SUPPORTED_CHAINS_CSV"
    )

    # ─── Sigui P2 Lebe (Escalation Engine — Qwen2.5 AMD MI300X) ─────────────
    # Qwen2.5-3B served via vLLM ROCm on AMD MI300X.
    # Falls back to Claude if endpoint is unreachable and lebe_fallback_to_claude=True.
    lebe_enabled: bool = Field(default=True, env="LEBE_ENABLED")
    lebe_endpoint: str = Field(
        default="http://134.199.201.220:8001/v1/chat/completions",
        env="LEBE_ENDPOINT",
    )
    lebe_model_name: str = Field(default="lebe", env="LEBE_MODEL_NAME")
    lebe_api_key: str = Field(default="sigui-key", env="LEBE_API_KEY")
    lebe_timeout_s: float = Field(default=4.0, env="LEBE_TIMEOUT_S")
    lebe_mock_mode: bool = Field(default=False, env="LEBE_MOCK_MODE")
    # If True, Claude is used as fallback when Lebe is unreachable.
    lebe_fallback_to_claude: bool = Field(default=True, env="LEBE_FALLBACK_TO_CLAUDE")

    # ─── Sigui P3 Hogonat On-Chain ────────────────────────────────────────────
    # Set HOGONAT_CONTRACT_ADDRESS to activate on-chain mode.
    # Leave empty to keep mock_mode=True (safe default for demo).
    hogonat_contract_address: str = Field(default="", env="HOGONAT_CONTRACT_ADDRESS")
    # USDC token used for staking — defaults to Arc native USDC.
    hogonat_usdc_token_address: str = Field(
        default="0x3600000000000000000000000000000000000000",
        env="HOGONAT_USDC_TOKEN_ADDRESS",
    )
    # USDC decimals for staking (6 for ERC-20 USDC, 18 for Arc native)
    hogonat_usdc_decimals: int = Field(default=6, env="HOGONAT_USDC_DECIMALS")

    # ─── Sigui P1 Vision + Kanaga ─────────────────────────────────────────────
    vision_enabled: bool = Field(default=True, env="VISION_ENABLED")
    vision_mock_mode: bool = Field(default=False, env="VISION_MOCK_MODE")
    vision_timeout_s: float = Field(default=1.5, env="VISION_TIMEOUT_S")
    vision_endpoint: str = Field(
        default="http://134.199.201.220:8002/v1/chat/completions", env="VISION_ENDPOINT"
    )
    vision_model_name: str = Field(default="Ibonon/imina_na_lora", env="VISION_MODEL_NAME")
    vision_confidence_block_threshold: float = Field(
        default=0.80, env="VISION_CONFIDENCE_BLOCK_THRESHOLD"
    )

    kanaga_enabled: bool = Field(default=True, env="KANAGA_ENABLED")
    kanaga_prefer_gpu: bool = Field(default=True, env="KANAGA_PREFER_GPU")

    # ─── Sigui P3 Hogonat Governance ──────────────────────────────────────────
    hogonat_enabled: bool = Field(default=True, env="HOGONAT_ENABLED")
    # mock_mode is auto-derived: True if hogonat_contract_address is empty.
    hogonat_mock_mode: bool = Field(default=True, env="HOGONAT_MOCK_MODE")
    hogonat_allow_threshold: float = Field(default=0.30, env="HOGONAT_ALLOW_THRESHOLD")
    hogonat_block_threshold: float = Field(default=0.70, env="HOGONAT_BLOCK_THRESHOLD")
    hogonat_initial_weights_csv: str = Field(
        default="0.40,0.30,0.30", env="HOGONAT_INITIAL_WEIGHTS_CSV"
    )
    hogonat_min_stake_usdc: float = Field(default=0.01, env="HOGONAT_MIN_STAKE_USDC")

    @property
    def hogonat_is_onchain(self) -> bool:
        """True when a real contract address is configured — activates on-chain mode."""
        return bool(self.hogonat_contract_address.strip())

    # ─── Database ─────────────────────────────────────────────────────────────
    db_path: str = Field(default="./db/sigui.db", env="DB_PATH")

    # ─── Demo Mode ────────────────────────────────────────────────────────────
    demo_mode: bool = Field(default=True, env="DEMO_MODE")
    initial_balance_usdc: float = Field(default=0.60, env="INITIAL_BALANCE_USDC")

    # ─── Risk Thresholds ──────────────────────────────────────────────────────
    risk_allow_threshold: float = Field(default=0.35)
    risk_block_threshold: float = Field(default=0.65)

    # ─── Agent Loop ───────────────────────────────────────────────────────────
    agent_cycle_ms: int = Field(default=100)
    treasury_sync_interval_cycles: int = Field(default=30)
    memory_consolidate_interval_cycles: int = Field(default=600)
    ecosystem_base_url: str = Field(
        default="http://localhost:8000", env="ECOSYSTEM_BASE_URL"
    )
    ecosystem_metrics_path: str = Field(
        default="./ecosystem/metrics.json", env="ECOSYSTEM_METRICS_PATH"
    )
    demo_report_path: str = Field(
        default="./ecosystem/demo_report.json", env="DEMO_REPORT_PATH"
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # FIX #8: Validate that critical secrets are present when demo_mode is False.
    # This prevents the server from starting in production with empty/demo keys.
    @model_validator(mode="after")
    def _validate_production_keys(self) -> "Settings":
        if self.demo_mode:
            return self  # demo mode — no key validation required
        errors = []
        if not self.arc_signer_private_key:
            errors.append("ARC_SIGNER_PRIVATE_KEY is required when DEMO_MODE=false")
        if self.anthropic_api_key in ("", "demo_key"):
            errors.append("ANTHROPIC_API_KEY is required when DEMO_MODE=false")
        if self.circle_api_key in ("", "demo_key"):
            errors.append("CIRCLE_API_KEY is required when DEMO_MODE=false")
        if errors:
            raise ValueError(
                "Production configuration errors (set DEMO_MODE=true to bypass):\n"
                + "\n".join(f"  • {e}" for e in errors)
            )
        return self


settings = Settings()
