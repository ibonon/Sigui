"""
modules/governance/hogonat_dao.py — Compatibility shim

Re-exports HogonatDAO (the client class) from governance.hogonat_client so that
imports like `from modules.governance.hogonat_dao import HogonatDAO` work.
"""
from governance.hogonat_client import HogonatClient as HogonatDAO  # noqa: F401

__all__ = ["HogonatDAO"]
