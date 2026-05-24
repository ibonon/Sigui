"""
modules/blockchain/arc_client.py — Compatibility shim

Re-exports the real ArcClient from clients.integrations so that:
  - vision_integration.py
  - tests/test_vision_integration.py
can use `from modules.blockchain.arc_client import ArcClient`.
"""
from clients.integrations import ArcClient  # noqa: F401

__all__ = ["ArcClient"]
