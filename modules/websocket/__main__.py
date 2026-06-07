"""
Point d'entrée pour le serveur WebSocket War Room.
Exécutez avec: python -m modules.websocket
"""

import asyncio
import uvicorn
import sys
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from .war_room_server import WarRoomWebSocketServer, create_app

async def main():
    """Fonction principale."""
    print("🚀 Démarrage du serveur WebSocket War Room...")
    print("🔗 WebSocket: ws://localhost:8002/ws")
    print("📊 Interface: http://localhost:8000/war-room")
    print("\n🔄 Serveur en cours d'exécution. Appuyez sur Ctrl+C pour arrêter.")
    
    # Créer et exécuter l'application
    app = create_app()
    
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info",
        reload=True,
    )
    
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())