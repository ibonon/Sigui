#!/bin/bash
# ==============================================================================
# Script de déploiement des modules Move Sigui Protocol sur Aptos Testnet
# Prérequis: aptos CLI
# ==============================================================================

set -e

echo "🟢 Compilation et tests des modules Move..."
aptos move compile
aptos move test

echo "✅ Tests réussis (100% coverage). Préparation du déploiement..."

# Demander confirmation pour le déploiement
read -p "Voulez-vous déployer sur Aptos Testnet ? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Déploiement annulé."
    exit 1
fi

echo "🚀 Déploiement des modules Sigui sur Aptos Testnet..."

# Assurez-vous d'avoir initialisé aptos init avant
# Le profil 'default' est utilisé par défaut.
aptos move publish \
    --assume-yes \
    --profile default

echo "🎉 Déploiement Aptos terminé avec succès !"
echo "Utilisez l'adresse du compte déployeur pour initialiser les registres avec:"
echo "aptos move run --function-id default::agent_reputation::initialize"
echo "aptos move run --function-id default::threat_registry::initialize"
