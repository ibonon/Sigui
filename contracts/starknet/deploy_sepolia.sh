#!/bin/bash
# ==============================================================================
# Script de déploiement des contrats Sigui Protocol sur Starknet Sepolia Testnet
# Prérequis: scarb, starkli
# ==============================================================================

set -e

echo "🟢 Démarrage du build avec Scarb..."
scarb build

# Configuration Starkli
export STARKNET_RPC="https://starknet-sepolia.public.blastapi.io/rpc/v0_7"
export ACCOUNT_DIR="$HOME/.starkli-wallets/deployer"
export STARKNET_ACCOUNT="$ACCOUNT_DIR/account.json"
export STARKNET_KEYSTORE="$ACCOUNT_DIR/keystore.json"

if [ ! -f "$STARKNET_ACCOUNT" ] || [ ! -f "$STARKNET_KEYSTORE" ]; then
    echo "🔴 Erreur: Les fichiers Starkli account.json et keystore.json n'ont pas été trouvés dans $ACCOUNT_DIR."
    echo "Veuillez configurer votre wallet Braavos ou Argent X avec starkli."
    exit 1
fi

echo "🔐 Configuration du wallet chargée."

# ==============================================================================
# 1. Agent Reputation Contract
# ==============================================================================
echo "📦 Déclaration de AgentReputation..."
REP_CLASS_HASH=$(starkli declare target/dev/sigui_protocol_AgentReputation.contract_class.json --compiler-version 2.8.0 --network sepolia --watch | grep -o "0x[0-9a-fA-F]*")
echo "✅ Class hash AgentReputation: $REP_CLASS_HASH"

echo "🚀 Déploiement de AgentReputation..."
DEPLOYER_ADDRESS=$(jq -r '.deployment.address' $STARKNET_ACCOUNT)
REP_ADDRESS=$(starkli deploy $REP_CLASS_HASH $DEPLOYER_ADDRESS --network sepolia --watch | grep -o "0x[0-9a-fA-F]*")
echo "✅ AgentReputation déployé à l'adresse: $REP_ADDRESS"

# ==============================================================================
# 2. Threat Registry Contract
# ==============================================================================
echo "📦 Déclaration de ThreatRegistry..."
THREAT_CLASS_HASH=$(starkli declare target/dev/sigui_protocol_ThreatRegistry.contract_class.json --compiler-version 2.8.0 --network sepolia --watch | grep -o "0x[0-9a-fA-F]*")
echo "✅ Class hash ThreatRegistry: $THREAT_CLASS_HASH"

echo "🚀 Déploiement de ThreatRegistry..."
THREAT_ADDRESS=$(starkli deploy $THREAT_CLASS_HASH $DEPLOYER_ADDRESS --network sepolia --watch | grep -o "0x[0-9a-fA-F]*")
echo "✅ ThreatRegistry déployé à l'adresse: $THREAT_ADDRESS"

echo "🎉 Déploiement Starknet Sepolia terminé avec succès !"
echo ""
echo "=== RÉSUMÉ DU DÉPLOIEMENT ==="
echo "AgentReputation: $REP_ADDRESS"
echo "ThreatRegistry:  $THREAT_ADDRESS"
echo "============================="
