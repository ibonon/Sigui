"""
tests/test_sigui_guard_sdk.py — Tests aux limites du point d'entrée simple check_action().

R1 — check_action(mode local) répond avec le réseau coupé.
R2 — aucun wallet, aucune clé, aucun compte requis pour obtenir un verdict.
R3 — verdict.engine ne ment jamais (pas de "hosted" quand c'est le moteur local).
R4 — mode shadow : verdict calculé, mais jamais appliqué.
"""

import os
import sys
import unittest
from unittest import mock

# Le SDK vit dans son propre projet `packages/sigui-guard/` (pip-installable).
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "sigui-guard"))

from sigui_guard import check_action, reset_frequency_state
from sigui_guard.local_engine import KNOWN_BAD_DESTINATIONS

BAD_ADDRESS = min(KNOWN_BAD_DESTINATIONS)
UNKNOWN_ADDRESS = "0xabc12345678901234567890123456789012345678"
SAFE_ADDRESS = "0x1111222233334444555566667777888899990000"

UNREACHABLE_ENDPOINT = "http://127.0.0.1:1"


class CheckActionLocalTests(unittest.TestCase):
    def setUp(self):
        reset_frequency_state()

    def test_no_context_call_does_not_false_positive(self):
        """Sans historique ni contexte, un petit transfert n'est pas bloqué."""
        verdict = check_action("transfer", amount_usd=0.5, destination=UNKNOWN_ADDRESS)
        self.assertEqual(verdict.decision, "ALLOW")
        self.assertFalse(verdict.blocked)
        self.assertEqual(verdict.engine, "local")

    def test_known_bad_destination_is_blocked(self):
        verdict = check_action("transfer", amount_usd=0.01, destination=BAD_ADDRESS)
        self.assertEqual(verdict.decision, "BLOCK")
        self.assertTrue(verdict.blocked)
        self.assertIn("destination_blacklisted", verdict.rules_triggered)

    def test_large_transfer_to_unknown_destination_is_blocked(self):
        verdict = check_action("transfer", amount_usd=500.0, destination=UNKNOWN_ADDRESS)
        self.assertEqual(verdict.decision, "BLOCK")
        self.assertTrue(verdict.blocked)

    def test_whitelisted_destination_stays_allowed(self):
        verdict = check_action(
            "transfer",
            amount_usd=500.0,
            destination=SAFE_ADDRESS,
            agent_context={
                "known_safe": [SAFE_ADDRESS],
                "avg_amount_usd": 12.0,
                "tx_count": 240,
                "trust_score": 0.9,
            },
        )
        self.assertEqual(verdict.decision, "ALLOW")
        self.assertFalse(verdict.blocked)

    def test_splitting_pattern_is_blocked_regardless_of_score(self):
        """Anti-splitting : 30 micro-transactions cumulées vers la même cible."""
        verdict = check_action(
            "transfer",
            amount_usd=10.0,
            destination=UNKNOWN_ADDRESS,
            agent_context={
                "cumulative_flow": {"total_amount": 5000.0, "tx_count": 30},
                "tx_count": 100,
            },
        )
        self.assertEqual(verdict.decision, "BLOCK")
        self.assertTrue(
            any("splitting" in r or "cumulative_flow" in r for r in verdict.rules_triggered)
        )

    def test_contract_drain_is_blocked(self):
        verdict = check_action(
            "contract_interaction",
            amount_usd=1.0,
            destination=UNKNOWN_ADDRESS,
            agent_context={"contract_eval": {"risk_delta": 0.8, "reason": "drain"}},
        )
        self.assertEqual(verdict.decision, "BLOCK")
        self.assertTrue(verdict.blocked)

    def test_verdict_payload_is_serializable(self):
        verdict = check_action("transfer", amount_usd=0.1, destination=UNKNOWN_ADDRESS)
        payload = verdict.to_dict()
        self.assertIsInstance(payload, dict)
        self.assertIn("decision", payload)
        self.assertIn("blocked", payload)
        self.assertEqual(verdict.action_hash != "", True)
        self.assertGreaterEqual(verdict.latency_ms, 0)


class CheckActionOfflineTests(unittest.TestCase):
    """R1 — le mode local ne doit jamais toucher le réseau."""

    def test_local_mode_never_opens_a_socket(self):
        with mock.patch("urllib.request.urlopen", side_effect=AssertionError("réseau interdit")):
            verdict = check_action("transfer", amount_usd=0.1, destination=UNKNOWN_ADDRESS)
        self.assertEqual(verdict.decision, "ALLOW")


class CheckActionCredentialTests(unittest.TestCase):
    """R2 — aucun wallet, aucune clé, aucun enregistrement."""

    def test_no_credentials_needed(self):
        verdict = check_action(
            "transfer",
            amount_usd=0.05,
            destination=UNKNOWN_ADDRESS,
            agent_context={"trust_score": 0.7},
        )
        self.assertIsInstance(verdict.decision, str)
        self.assertEqual(verdict.engine, "local")


class CheckActionEngineHonestyTests(unittest.TestCase):
    """R3 — verdict.engine doit refléter la réalité."""

    def test_local_engine_is_labelled_local(self):
        verdict = check_action("transfer", amount_usd=0.1, destination=UNKNOWN_ADDRESS)
        self.assertEqual(verdict.engine, "local")

    def test_hosted_fallback_is_labelled_local(self):
        verdict = check_action(
            "transfer",
            amount_usd=0.1,
            destination=UNKNOWN_ADDRESS,
            engine="hosted",
            endpoint=UNREACHABLE_ENDPOINT,
            timeout_s=0.5,
        )
        self.assertEqual(verdict.engine, "local")
        self.assertIn("repli local", verdict.reason)

    def test_hosted_fail_closed_blocks(self):
        verdict = check_action(
            "transfer",
            amount_usd=0.1,
            destination=UNKNOWN_ADDRESS,
            engine="hosted",
            endpoint=UNREACHABLE_ENDPOINT,
            timeout_s=0.5,
            on_hosted_failure="block",
        )
        self.assertEqual(verdict.decision, "BLOCK")
        self.assertTrue(verdict.blocked)
        self.assertEqual(verdict.engine, "hosted")


class CheckActionShadowTests(unittest.TestCase):
    """R4 — shadow : verdict calculé, action jamais bloquée."""

    def test_shadow_never_blocks(self):
        verdict = check_action(
            "transfer",
            amount_usd=0.01,
            destination=BAD_ADDRESS,
            mode="shadow",
        )
        self.assertEqual(verdict.decision, "BLOCK")
        self.assertFalse(verdict.blocked)
        self.assertEqual(verdict.mode, "shadow")

    def test_enforce_blocks_same_input(self):
        verdict = check_action("transfer", amount_usd=0.01, destination=BAD_ADDRESS)
        self.assertTrue(verdict.blocked)


class CheckActionValidationTests(unittest.TestCase):
    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            check_action("transfer", mode="observe")

    def test_invalid_engine_rejected(self):
        with self.assertRaises(ValueError):
            check_action("transfer", engine="quantum")

    def test_invalid_hosted_failure_policy_rejected(self):
        with self.assertRaises(ValueError):
            check_action("transfer", on_hosted_failure="explode")


if __name__ == "__main__":
    unittest.main()
