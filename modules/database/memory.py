"""
modules/database/memory.py — Compatibility shim

Re-exports Memory from modules.memory so that imports like
  `from modules.database.memory import Memory`
resolve correctly.
"""
from modules.memory import Memory  # noqa: F401

__all__ = ["Memory"]
