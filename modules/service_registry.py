"""
ArcWarden v3.0 — Service Registry
Reputation layer for payment destinations (APIs, contracts, services).
Prevents agents from paying known-malicious or unvetted services.
"""
import json
from enum import Enum
from dataclasses import dataclass, field

from loguru import logger

from config import settings
from modules.memory import memory


# ────────────────────────────────────────────────────────────────────────────────
# Trust Levels & Data Model
# ────────────────────────────────────────────────────────────────────────────────

class ServiceTrust(str, Enum):
    VERIFIED   = "VERIFIED"    # Service connu et approuvé
    NEUTRAL    = "NEUTRAL"     # Inconnu mais pas de signaux négatifs
    SUSPICIOUS = "SUSPICIOUS"  # Signaux négatifs (plaintes, patterns)
    MALICIOUS  = "MALICIOUS"   # Confirmé malveillant par MemoClaw


@dataclass
class ServiceProfile:
    address: str
    name: str | None
    trust: ServiceTrust
    category: str
    total_payments_received: float
    unique_payers: int
    complaints: int
    first_seen: str
    last_seen: str
    tags: list[str] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────────────
# ServiceRegistry
# ────────────────────────────────────────────────────────────────────────────────

class ServiceRegistry:
    """Tracks and evaluates the trustworthiness of payment destinations."""

    # Services pré-vérifiés intégrés au démarrage
    BOOTSTRAP_VERIFIED = [
        {"address": addr, "name": name, "category": cat, "tags": tags}
        for addr, name, cat, tags in [
            (
                "0xARCDEX0000000000000000000000000000000001",
                "Arc DEX v2", "defi", ["swap", "liquidity"],
            ),
            (
                "0xARCDATA000000000000000000000000000000001",
                "Arc Data Oracle", "data", ["price_feed", "oracle"],
            ),
            (
                "0xARCAPIS00000000000000000000000000000001",
                "Arc API Gateway", "api", ["compute", "inference"],
            ),
        ]
    ]

    async def initialize(self):
        """Peuple le registre avec les services vérifiés au démarrage."""
        for svc in self.BOOTSTRAP_VERIFIED:
            await memory.run_query(
                """
                INSERT OR IGNORE INTO service_registry
                    (address, name, trust_level, category, tags)
                VALUES (?, ?, 'VERIFIED', ?, ?)
                """,
                (svc["address"], svc["name"],
                 svc["category"], json.dumps(svc["tags"])),
                fetch="none"
            )
        logger.info(
            f"[SERVICE_REGISTRY] Initialized with "
            f"{len(self.BOOTSTRAP_VERIFIED)} verified services"
        )

    # ── Profile Lookup ────────────────────────────────────────────────────────

    async def get_service_profile(self, address: str) -> ServiceProfile | None:
        """Return the full profile for an address, or None if unknown."""
        row = await memory.run_query(
            "SELECT * FROM service_registry WHERE address = ?",
            (address,),
            fetch="one"
        )
        if not row:
            return None
        return ServiceProfile(
            address=row["address"],
            name=row["name"],
            trust=ServiceTrust(row["trust_level"]),
            category=row["category"],
            total_payments_received=row["total_received"],
            unique_payers=row["unique_payers"],
            complaints=row["complaints"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            tags=json.loads(row["tags"] or "[]"),
        )

    # ── Core Evaluation ───────────────────────────────────────────────────────

    async def evaluate_service(self, address: str) -> dict:
        """
        Évalue la fiabilité d'un service et retourne un score de confiance.
        Appelée depuis le Risk Engine via action.context["service_eval"].

        Returns:
            dict with keys: trust, risk_delta, reason, category, name
        """
        profile = await self.get_service_profile(address)

        if profile is None:
            # Service inconnu — premier contact
            return {
                "trust": ServiceTrust.NEUTRAL,
                "risk_delta": +0.15,
                "reason": "service_unknown_first_contact",
                "category": "unknown",
                "name": None,
            }

        if profile.trust == ServiceTrust.VERIFIED:
            return {
                "trust": ServiceTrust.VERIFIED,
                "risk_delta": -0.25,
                "reason": f"verified_service_{profile.category}",
                "category": profile.category,
                "name": profile.name,
            }

        if profile.trust == ServiceTrust.MALICIOUS:
            return {
                "trust": ServiceTrust.MALICIOUS,
                "risk_delta": +0.60,
                "reason": "known_malicious_service",
                "category": profile.category,
                "name": profile.name,
            }

        if profile.trust == ServiceTrust.SUSPICIOUS:
            return {
                "trust": ServiceTrust.SUSPICIOUS,
                "risk_delta": +0.30,
                "reason": f"suspicious_service_{profile.complaints}_complaints",
                "category": profile.category,
                "name": profile.name,
            }

        # NEUTRAL : calcul dynamique basé sur l'historique
        risk_delta = 0.0
        reason_parts: list[str] = []

        if profile.unique_payers > 10 and profile.complaints == 0:
            risk_delta -= 0.15
            reason_parts.append("community_trusted")

        if profile.complaints > 0:
            complaint_rate = profile.complaints / max(profile.unique_payers, 1)
            risk_delta += complaint_rate * 0.50
            reason_parts.append(f"complaint_rate_{complaint_rate:.0%}")

        return {
            "trust": ServiceTrust.NEUTRAL,
            "risk_delta": round(risk_delta, 3),
            "reason": "_".join(reason_parts) or "neutral_service",
            "category": profile.category,
            "name": profile.name,
        }

    # ── Interaction Logging ───────────────────────────────────────────────────

    async def record_interaction(
        self,
        agent_id: str,
        address: str,
        amount: float,
        outcome: str,
    ):
        """
        Met à jour le profil du service après chaque interaction.

        Args:
            outcome: 'paid' | 'blocked' | 'complained'
        """
        # Créer le service s'il n'existe pas
        await memory.run_query(
            "INSERT OR IGNORE INTO service_registry (address) VALUES (?)",
            (address,),
            fetch="none"
        )

        if outcome == "paid":
            await memory.run_query(
                """
                UPDATE service_registry
                SET total_received = total_received + ?,
                    unique_payers  = (SELECT COUNT(DISTINCT agent_id) FROM decisions WHERE destination = ?),
                    last_seen      = datetime('now')
                WHERE address = ?
                """,
                (amount, address, address),
                fetch="none"
            )
        elif outcome == "complained":
            await memory.run_query(
                "UPDATE service_registry SET complaints = complaints + 1 WHERE address = ?",
                (address,),
                fetch="none"
            )

        # Sync back trust levels based on new data
        await self._sync_trust_levels(address)

    async def _sync_trust_levels(self, address: str):
        """Met à jour le trust_level si les plaintes dépassent un seuil."""
        profile = await self.get_service_profile(address)
        if not profile or profile.trust in (ServiceTrust.VERIFIED, ServiceTrust.MALICIOUS):
            return

        new_trust = profile.trust
        if profile.complaints >= 5:
            new_trust = ServiceTrust.MALICIOUS
        elif profile.complaints >= 1:
            new_trust = ServiceTrust.SUSPICIOUS

        if new_trust != profile.trust:
            await memory.run_query(
                "UPDATE service_registry SET trust_level = ? WHERE address = ?",
                (new_trust.value, address),
                fetch="none"
            )
            logger.info(f"[SERVICE_REGISTRY] {address} trust updated: {profile.trust} -> {new_trust}")

    async def flag_malicious(self, address: str, reason: str):
        """Marque un service comme malveillant immédiatement (admin override)."""
        await memory.run_query(
            """
            UPDATE service_registry
            SET trust_level = 'MALICIOUS', last_seen = datetime('now')
            WHERE address = ?
            """,
            (address,),
            fetch="none"
        )
        logger.warning(
            f"[SERVICE_REGISTRY] 🚨 Service flagged MALICIOUS: {address} — {reason}"
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

service_registry = ServiceRegistry()
