from dataclasses import dataclass, field
from typing import Callable, Optional
import os

@dataclass
class SiguiConfig:
    api_key: Optional[str] = field(default_factory=lambda: os.environ.get("SIGUI_API_KEY"))
    api_url: str = field(default_factory=lambda: os.environ.get("SIGUI_API_URL", "https://api.sigui.io"))
    mode: Optional[str] = field(default_factory=lambda: os.environ.get("SIGUI_MODE"))
    timeout_ms: int = 100
    min_amount_usdc: float = 0.001
    block_on_escalate: bool = False
    chains: list[str] = field(default_factory=lambda: ["ethereum"])
    on_block: Optional[Callable] = None
    on_escalate: Optional[Callable] = None
    on_allow: Optional[Callable] = None
    log_level: str = field(default_factory=lambda: os.environ.get("SIGUI_LOG_LEVEL", "WARNING"))
    cache_ttl_seconds: int = 300
    weights: dict[str, float] = field(default_factory=lambda: {"financial": 1.0, "behavioral": 1.0, "visual_topology": 1.0})
