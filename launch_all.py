#!/usr/bin/env python3
"""
Script pour lancer tous les serveurs Sigui simultanément.
"""

import asyncio
import subprocess
import sys
import time
import signal
import os
from pathlib import Path

# Configuration des serveurs
SERVERS = [
    {
        "name": "FastAPI Principal",
        "command": ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        "url": "http://localhost:8000",
        "health_check": "/health",
    },
    {
        "name": "GraphQL API",
        "command": ["uvicorn", "modules.graphql.server:create_app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        "url": "http://localhost:8001/graphql",
        "health_check": "/graphql",
    },
    {
        "name": "WebSocket War Room",
        "command": ["python", "-m", "modules.websocket.war_room_server"],
        "url": "ws://localhost:8002/ws",
        "health_check": None,
    },
]

class ServerManager:
    def __init__(self):
        self.processes = []
        self.running = True
        
        # Gestion des signaux
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        print(f"\n📡 Signal {signum} reçu, arrêt des serveurs...")
        self.running = False
        self.stop_all()
    
    async def start_server(self, server_config):
        """Démarre un serveur en sous-processus."""
        name = server_config["name"]
        command = server_config["command"]
        url = server_config["url"]
        
        print(f"🚀 Démarrage de {name}...")
        print(f"   Commande: {' '.join(command)}")
        print(f"   URL: {url}")
        
        # Créer le sous-processus
        env = os.environ.copy()
        env["PYTHONPATH"] = str(Path.cwd())
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            env=env,
        )
        
        self.processes.append((name, process))
        
        # Lire la sortie en temps réel
        async def read_output():
            while self.running and process.poll() is None:
                line = process.stdout.readline()
                if line:
                    print(f"[{name}] {line}", end="")
                await asyncio.sleep(0.1)
        
        # Démarrer la lecture de la sortie
        asyncio.create_task(read_output())
        
        # Attendre que le serveur soit prêt
        await asyncio.sleep(3)
        
        if process.poll() is None:
            print(f"✅ {name} démarré avec succès")
            return True
        else:
            print(f"❌ {name} a échoué à démarrer")
            return False
    
    async def start_all(self):
        """Démarre tous les serveurs."""
        print("=" * 60)
        print("🛡️  SIGUI - Démarrage de tous les serveurs")
        print("=" * 60)
        
        tasks = [self.start_server(server) for server in SERVERS]
        results = await asyncio.gather(*tasks)
        
        if all(results):
            print("\n" + "=" * 60)
            print("🎉 TOUS LES SERVEURS SONT OPÉRATIONNELS !")
            print("=" * 60)
            print("\n📊 Accès aux interfaces:")
            print(f"   • FastAPI Principal: http://localhost:8000")
            print(f"   • GraphQL Playground: http://localhost:8001/graphql")
            print(f"   • War Room 3D: http://localhost:8000/war-room")
            print(f"   • Documentation API: http://localhost:8000/docs")
            print(f"   • Redoc: http://localhost:8000/redoc")
            print("\n🔗 WebSocket War Room: ws://localhost:8002/ws")
            print("\n🔄 Serveurs en cours d'exécution. Appuyez sur Ctrl+C pour arrêter.")
            print("=" * 60)
            
            # Garder le script en vie
            while self.running:
                await asyncio.sleep(1)
        else:
            print("\n❌ Certains serveurs ont échoué à démarrer")
            self.stop_all()
    
    def stop_all(self):
        """Arrête tous les serveurs."""
        print("\n🛑 Arrêt de tous les serveurs...")
        
        for name, process in self.processes:
            if process.poll() is None:
                print(f"   Arrêt de {name}...")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    print(f"   Forçage de l'arrêt de {name}...")
                    process.kill()
        
        self.processes.clear()
        print("✅ Tous les serveurs sont arrêtés")

async def main():
    """Fonction principale."""
    manager = ServerManager()
    
    try:
        await manager.start_all()
    except KeyboardInterrupt:
        print("\n🛑 Interruption par l'utilisateur")
    finally:
        manager.stop_all()

if __name__ == "__main__":
    # Vérifier que nous sommes dans le bon répertoire
    if not Path("main.py").exists():
        print("❌ Erreur: Veuillez exécuter ce script depuis le répertoire racine de Sigui")
        print(f"   Répertoire actuel: {Path.cwd()}")
        sys.exit(1)
    
    # Démarrer le gestionnaire de serveurs
    asyncio.run(main())