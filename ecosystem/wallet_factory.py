from dataclasses import dataclass

from loguru import logger

from clients.integrations import circle_client
from config import settings


@dataclass
class WalletSpec:
    name: str
    wallet_id: str
    wallet_address: str
    balance_usdc: float


class WalletFactory:
    async def initialize_agent_wallets(self) -> dict[str, WalletSpec]:
        specs = {
            "payer": WalletSpec("agent_payer", settings.payer_wallet_id or "demo_payer_wallet_id", settings.payer_wallet_address, 0.0),
            "attacker": WalletSpec("agent_attacker", settings.attacker_wallet_id or "demo_attacker_wallet_id", settings.attacker_wallet_address, 0.0),
            "monitor": WalletSpec("agent_monitor", settings.monitor_wallet_id or "demo_monitor_wallet_id", settings.monitor_wallet_address, 0.0),
            "learner": WalletSpec("agent_learner", settings.learner_wallet_id or "demo_learner_wallet_id", settings.learner_wallet_address, 0.0),
            "grayzone": WalletSpec("agent_grayzone", settings.grayzone_wallet_id or "demo_grayzone_wallet_id", settings.grayzone_wallet_address, 0.0),
        }
        for key, spec in specs.items():
            if not spec.wallet_id:
                logger.warning(f"[WALLETS] Missing wallet id for {spec.name}; agent will run observe-only")
                continue
            try:
                spec.balance_usdc = await circle_client.get_wallet_balance(spec.wallet_id)
            except Exception as exc:
                logger.warning(f"[WALLETS] Cannot fetch balance for {spec.name}: {exc}")
                spec.balance_usdc = 0.0
            if spec.balance_usdc <= 0:
                logger.warning(
                    f"[WALLETS] {spec.name} has no USDC. Request Arc testnet USDC and fund wallet id={spec.wallet_id}"
                )
            else:
                logger.info(f"[WALLETS] {spec.name} ready with {spec.balance_usdc:.6f} USDC")
            if not spec.wallet_address:
                spec.wallet_address = f"wallet:{spec.wallet_id}"
            specs[key] = spec
        return specs


wallet_factory = WalletFactory()

