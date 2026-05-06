"""
Sigui v2.0 — Modèle Économique (Pricing & Subscriptions)

Ce module remplace l'ancien modèle "flat fee" par un modèle proportionnel plafonné,
et introduit la notion d'abonnements SaaS pour les agents haute fréquence.

- Mode Démo : tarif fixe ultra-bas ($0.001) pour valider l'UX des micropaiements sur le testnet.
- Mode Prod : 5 basis points (0.05%) avec $0.01 de plancher et $100.00 de plafond.
"""
from config import settings

BASIS_POINTS = 5      # 0.05% de la valeur sécurisée
MINIMUM_FEE  = 0.01   # $0.01 plancher — couvre les micro-tx
MAXIMUM_FEE  = 100.00 # $100 plafond — protège les grosses tx


def compute_fee(amount_usdc: float, tier: str = "payg") -> float:
    """
    Calcule les frais d'évaluation Sigui en fonction de la valeur sécurisée.
    
    Args:
        amount_usdc: Le montant de la transaction analysée.
        tier:        Le tier d'abonnement de l'agent ('payg', 'novice', 'hogon', 'sigui').
                     En 'payg' (Pay-As-You-Go), les frais sont calculés.
                     Pour les autres tiers, ils sont inclus (0.0).
    """
    # Si abonnement mensuel actif, les frais par requête sont à zéro.
    if tier in ("novice", "hogon", "sigui"):
        return 0.0

    # Pour le Hackathon : le mode démo garde un fee microscopique ($0.001)
    # pour prouver la faisabilité des nano-paiements sur Arc.
    if settings.demo_mode:
        return settings.arcwarden_eval_price_usdc

    # Modèle de production : 0.05% de la transaction.
    fee = amount_usdc * (BASIS_POINTS / 10_000)
    
    # Applique le plancher (MINIMUM_FEE) et le plafond (MAXIMUM_FEE)
    return round(min(max(fee, MINIMUM_FEE), MAXIMUM_FEE), 6)
