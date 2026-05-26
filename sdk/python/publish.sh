#!/bin/bash
# ==============================================================================
# Script de publication du SDK Sigui sur PyPI
# ==============================================================================

set -e

echo "📦 Préparation de la publication pour sigui-sdk..."

cd "$(dirname "$0")"

# S'assurer que build et twine sont installés
pip install --upgrade build twine

# Nettoyer les anciens builds
rm -rf dist/ build/ *.egg-info/

echo "🔨 Construction du package (sdist et wheel)..."
python -m build

echo "🔍 Vérification du package..."
twine check dist/*

echo "🚀 Publication sur PyPI..."
# Vous devrez entrer votre token d'API PyPI ou utiliser le fichier .pypirc
# twine upload dist/*

echo ""
echo "✅ Construction réussie ! Les fichiers sont dans le dossier dist/"
echo "Pour publier réellement, exécutez :"
echo "twine upload dist/*"
echo ""
echo "Note: Vous pouvez aussi générer un token sur pypi.org et exécuter:"
echo "TWINE_USERNAME=__token__ TWINE_PASSWORD=pypi-votretocken twine upload dist/*"
