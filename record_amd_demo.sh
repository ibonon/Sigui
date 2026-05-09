#!/bin/bash
# Script de recording pour la démo AMD Hackathon

echo "🎬 ENREGISTREMENT DEMO AMD HACKATHON - SIGUI"
echo "==========================================="

# Configuration
echo "Configuration de l'environnement..."
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export LOG_LEVEL="INFO"

# 1. INTRODUCTION
echo "📹 INTRODUCTION (30s)"
echo "Présentation: Sigui + AMD MI300X"

# 2. DÉPLOIEMENTS
echo "📋 Vérification des déploiements:"
echo "ThreatRegistry: $(cat contracts/ThreatRegistry.deployed.json | jq -r '.address')"
echo "AgentIdentityRegistry: $(cat contracts/AgentIdentityRegistry.deployed.json | jq -r '.address')"

# 3. PHASE 3 - LE MOMENT CRITIQUE
echo "🎯 PHASE 3: DRAIN_STAR Detection"
echo "Lancement de la démo principale..."

# Lancer la démo avec un beau output
python demo_phase3_drain_star.py

echo "🏆 DEMO TERMINÉE"
echo "Prêt pour impressionner les juges AMD!"

# Commandes pour filmer:
echo ""
echo "Pour enregistrer la vidéo:"
echo "1. OBS Studio ou similar"
echo "2. Terminal avec bonne résolution"
echo "3. Montrer les métriques AMD MI300X"
echo "4. Temps réel de 0.5ms inference"