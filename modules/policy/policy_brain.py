"""
modules/policy/policy_brain.py — Compatibility shim

Re-exports PolicyBrain from modules.ai_engines so that imports like
  `from modules.policy.policy_brain import PolicyBrain`
resolve correctly.
"""
from modules.ai_engines import PolicyBrain  # noqa: F401

__all__ = ["PolicyBrain"]
