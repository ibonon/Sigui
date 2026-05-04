"""
ArcWarden v3.0 — Configuration
Pydantic Settings with dotenv loading
"""

from typing import Optional

from pydantic import Field
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
    decision_ai_model: str = Field(
        default="claude-sonnet-4-20250514", env="DECISION_AI_MODEL"
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

    # ─── Database ─────────────────────────────────────────────────────────────
    db_path: str = Field(default="./db/arcwarden.db", env="DB_PATH")

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


settings = Settings()
