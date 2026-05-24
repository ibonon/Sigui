"""
modules/threat_intel/threat_registry.py — Compatibility shim

Re-exports ThreatRegistry from clients.threat_registry so that imports like
  `from modules.threat_intel.threat_registry import ThreatRegistry`
resolve correctly.
"""
from clients.threat_registry import ThreatRegistryClient as ThreatRegistry  # noqa: F401

__all__ = ["ThreatRegistry"]
