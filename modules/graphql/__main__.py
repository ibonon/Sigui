"""
Point d'entrée pour le serveur GraphQL.
Exécutez avec: python -m modules.graphql
"""

import uvicorn
import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from .server import create_app

if __name__ == "__main__":
    print("🚀 Démarrage du serveur GraphQL Sigui...")
    print("📊 GraphQL Playground: http://localhost:8001/graphql")
    print("📚 Documentation: http://localhost:8001/graphql")
    print("\n🔄 Serveur en cours d'exécution. Appuyez sur Ctrl+C pour arrêter.")
    
    uvicorn.run(
        create_app(),
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )