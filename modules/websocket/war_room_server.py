"""
Serveur WebSocket pour le War Room Sigui.
Gère les connexions en temps réel pour la visualisation 3D et les commandes vocales.
"""

import asyncio
import logging
import json
import uuid
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect
from websockets.exceptions import ConnectionClosed

from ...modules.integrations.aave_integration import AaveIntegration
from ...modules.integrations.chainlink_integration import ChainlinkIntegration
from ...modules.integrations.uniswap_integration import UniswapIntegration
from ...modules.integrations.compound_integration import CompoundIntegration
from ...modules.integrations.makerdao_integration import MakerDAOIntegration
from ...modules.voice.voice_commands import VoiceCommandManager

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types de messages WebSocket."""
    SYSTEM_STATUS = "system_status"
    THREAT_DETECTED = "threat_detected"
    AGENT_ACTIVITY = "agent_activity"
    TRANSACTION_ALERT = "transaction_alert"
    NEXUSMIND_TOPOLOGY = "nexusmind_topology"
    VOICE_COMMAND = "voice_command"
    VOICE_FEEDBACK = "voice_feedback"
    CONTROL_COMMAND = "control_command"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class WebSocketMessage:
    """Message WebSocket structuré."""
    type: MessageType
    payload: Dict[str, Any]
    timestamp: datetime
    message_id: str = None
    
    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit en dictionnaire pour JSON."""
        return {
            "type": self.type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
        }


class ConnectionManager:
    """Gère les connexions WebSocket."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_data: Dict[str, Dict[str, Any]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accepte une nouvelle connexion."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.connection_data[client_id] = {
            "connected_at": datetime.now(),
            "last_heartbeat": datetime.now(),
            "client_info": {},
            "subscriptions": set(),
        }
        logger.info(f"Client {client_id} connecté")
    
    def disconnect(self, client_id: str):
        """Déconnecte un client."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            del self.connection_data[client_id]
            logger.info(f"Client {client_id} déconnecté")
    
    async def send_personal_message(self, message: WebSocketMessage, client_id: str):
        """Envoie un message à un client spécifique."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message.to_dict())
            except (WebSocketDisconnect, ConnectionClosed):
                self.disconnect(client_id)
    
    async def broadcast(self, message: WebSocketMessage):
        """Diffuse un message à tous les clients connectés."""
        disconnected_clients = []
        
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_json(message.to_dict())
            except (WebSocketDisconnect, ConnectionClosed):
                disconnected_clients.append(client_id)
        
        # Nettoyer les connexions déconnectées
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def send_to_subscribers(self, message: WebSocketMessage, subscription_type: str):
        """Envoie un message aux clients abonnés à un type spécifique."""
        disconnected_clients = []
        
        for client_id, data in self.connection_data.items():
            if subscription_type in data["subscriptions"]:
                try:
                    await self.active_connections[client_id].send_json(message.to_dict())
                except (WebSocketDisconnect, ConnectionClosed):
                    disconnected_clients.append(client_id)
        
        # Nettoyer les connexions déconnectées
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    def update_subscription(self, client_id: str, subscription_type: str, subscribe: bool):
        """Met à jour les abonnements d'un client."""
        if client_id in self.connection_data:
            if subscribe:
                self.connection_data[client_id]["subscriptions"].add(subscription_type)
            else:
                self.connection_data[client_id]["subscriptions"].discard(subscription_type)
    
    def update_heartbeat(self, client_id: str):
        """Met à jour le dernier heartbeat d'un client."""
        if client_id in self.connection_data:
            self.connection_data[client_id]["last_heartbeat"] = datetime.now()
    
    def get_inactive_clients(self, timeout_seconds: int = 30) -> List[str]:
        """Retourne la liste des clients inactifs."""
        inactive = []
        now = datetime.now()
        
        for client_id, data in self.connection_data.items():
            last_heartbeat = data["last_heartbeat"]
            if (now - last_heartbeat).total_seconds() > timeout_seconds:
                inactive.append(client_id)
        
        return inactive
    
    def get_client_count(self) -> int:
        """Retourne le nombre de clients connectés."""
        return len(self.active_connections)


class WarRoomWebSocketServer:
    """Serveur WebSocket principal pour le War Room."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.voice_command_manager = VoiceCommandManager()
        
        # Intégrations ecosystemiques
        self.aave_integration = AaveIntegration()
        self.chainlink_integration = ChainlinkIntegration()
        self.uniswap_integration = UniswapIntegration()
        self.compound_integration = CompoundIntegration()
        self.makerdao_integration = MakerDAOIntegration()
        
        # État du système
        self.system_status = {
            "ethereum": {"status": "healthy", "threats": 0, "metrics": {}},
            "solana": {"status": "healthy", "threats": 0, "metrics": {}},
            "cosmos": {"status": "healthy", "threats": 0, "metrics": {}},
            "aave": {"status": "healthy", "threats": 0, "metrics": {}},
            "compound": {"status": "healthy", "threats": 0, "metrics": {}},
            "makerdao": {"status": "healthy", "threats": 0, "metrics": {}},
            "uniswap": {"status": "healthy", "threats": 0, "metrics": {}},
        }
        
        # Tâches en arrière-plan
        self.background_tasks = set()
        
        # Initialisation
        self._initialize_background_tasks()
    
    def _initialize_background_tasks(self):
        """Initialise les tâches en arrière-plan."""
        
        # Tâche de surveillance système
        task = asyncio.create_task(self._monitor_system_status())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Tâche de génération d'alertes simulées
        task = asyncio.create_task(self._generate_simulated_alerts())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        
        # Tâche de nettoyage des connexions inactives
        task = asyncio.create_task(self._cleanup_inactive_connections())
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
    
    async def handle_connection(self, websocket: WebSocket):
        """Gère une connexion WebSocket."""
        client_id = str(uuid.uuid4())
        
        try:
            # Accepter la connexion
            await self.connection_manager.connect(websocket, client_id)
            
            # Envoyer le statut initial
            await self._send_initial_status(client_id)
            
            # Boucle principale de traitement des messages
            while True:
                try:
                    # Recevoir le message
                    data = await websocket.receive_json()
                    
                    # Traiter le message
                    await self._process_client_message(client_id, data)
                    
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await self._send_error(client_id, "Message JSON invalide")
                except Exception as e:
                    logger.error(f"Erreur traitement message client {client_id}: {e}")
                    await self._send_error(client_id, f"Erreur interne: {str(e)}")
        
        except Exception as e:
            logger.error(f"Erreur connexion client {client_id}: {e}")
        finally:
            self.connection_manager.disconnect(client_id)
    
    async def _send_initial_status(self, client_id: str):
        """Envoie le statut initial au client."""
        message = WebSocketMessage(
            type=MessageType.SYSTEM_STATUS,
            payload={"system_status": self.system_status},
            timestamp=datetime.now(),
        )
        
        await self.connection_manager.send_personal_message(message, client_id)
    
    async def _process_client_message(self, client_id: str, data: Dict[str, Any]):
        """Traite un message du client."""
        
        message_type = data.get("type")
        
        if message_type == "heartbeat":
            # Mettre à jour le heartbeat
            self.connection_manager.update_heartbeat(client_id)
            
            # Répondre avec un heartbeat
            response = WebSocketMessage(
                type=MessageType.HEARTBEAT,
                payload={"timestamp": datetime.now().isoformat()},
                timestamp=datetime.now(),
            )
            
            await self.connection_manager.send_personal_message(response, client_id)
        
        elif message_type == "subscribe":
            # Gérer les abonnements
            subscription_type = data.get("subscription_type")
            if subscription_type:
                self.connection_manager.update_subscription(
                    client_id, subscription_type, True
                )
                
                feedback = WebSocketMessage(
                    type=MessageType.CONTROL_COMMAND,
                    payload={
                        "action": "subscribed",
                        "subscription_type": subscription_type,
                    },
                    timestamp=datetime.now(),
                )
                
                await self.connection_manager.send_personal_message(feedback, client_id)
        
        elif message_type == "unsubscribe":
            # Gérer les désabonnements
            subscription_type = data.get("subscription_type")
            if subscription_type:
                self.connection_manager.update_subscription(
                    client_id, subscription_type, False
                )
        
        elif message_type == "voice_command":
            # Traiter les commandes vocales
            text = data.get("text")
            confidence = data.get("confidence", 1.0)
            
            if text:
                # Traiter la commande
                success = await self.voice_command_manager.process_text(
                    text, confidence
                )
                
                if success:
                    feedback = WebSocketMessage(
                        type=MessageType.VOICE_FEEDBACK,
                        payload={
                            "message": "Commande exécutée",
                            "command": text,
                        },
                        timestamp=datetime.now(),
                    )
                else:
                    feedback = WebSocketMessage(
                        type=MessageType.VOICE_FEEDBACK,
                        payload={
                            "message": "Commande non reconnue",
                            "command": text,
                        },
                        timestamp=datetime.now(),
                    )
                
                await self.connection_manager.send_personal_message(feedback, client_id)
        
        elif message_type == "control_command":
            # Traiter les commandes de contrôle
            action = data.get("action")
            parameters = data.get("parameters", {})
            
            await self._handle_control_command(client_id, action, parameters)
    
    async def _handle_control_command(self, client_id: str, action: str, parameters: Dict[str, Any]):
        """Traite une commande de contrôle."""
        
        if action == "get_system_status":
            # Retourner le statut système complet
            message = WebSocketMessage(
                type=MessageType.SYSTEM_STATUS,
                payload={"system_status": self.system_status},
                timestamp=datetime.now(),
            )
            
            await self.connection_manager.send_personal_message(message, client_id)
        
        elif action == "get_chain_status":
            # Retourner le statut d'une chaîne spécifique
            chain = parameters.get("chain")
            if chain in self.system_status:
                message = WebSocketMessage(
                    type=MessageType.SYSTEM_STATUS,
                    payload={
                        "chain": chain,
                        "status": self.system_status[chain],
                    },
                    timestamp=datetime.now(),
                )
                
                await self.connection_manager.send_personal_message(message, client_id)
        
        elif action == "run_simulation":
            # Lancer une simulation
            simulation_type = parameters.get("type", "default")
            
            # Simuler une alerte
            await self._simulate_threat_alert(simulation_type)
            
            feedback = WebSocketMessage(
                type=MessageType.CONTROL_COMMAND,
                payload={
                    "action": "simulation_started",
                    "type": simulation_type,
                },
                timestamp=datetime.now(),
            )
            
            await self.connection_manager.send_personal_message(feedback, client_id)
        
        elif action == "get_voice_commands":
            # Retourner la liste des commandes vocales disponibles
            commands = self.voice_command_manager.get_available_commands()
            
            message = WebSocketMessage(
                type=MessageType.CONTROL_COMMAND,
                payload={
                    "action": "voice_commands_list",
                    "commands": commands,
                },
                timestamp=datetime.now(),
            )
            
            await self.connection_manager.send_personal_message(message, client_id)
    
    async def _monitor_system_status(self):
        """Surveille le statut du système en arrière-plan."""
        
        while True:
            try:
                # Mettre à jour les métriques système
                await self._update_system_metrics()
                
                # Mettre à jour la topologie NexusMind
                topology = await self._get_nexusmind_topology()

                # Diffuser les mises à jour aux abonnés
                message = WebSocketMessage(
                    type=MessageType.SYSTEM_STATUS,
                    payload={
                        "system_status": self.system_status,
                        "nexusmind_topology": topology
                    },
                    timestamp=datetime.now(),
                )
                
                await self.connection_manager.broadcast(message)
                
                # Attendre avant la prochaine mise à jour
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Erreur surveillance système: {e}")
                await asyncio.sleep(30)  # Attendre plus longtemps en cas d'erreur
    
    async def _get_nexusmind_topology(self) -> Dict[str, Any]:
        """Récupère la topologie temps-réel du réseau NexusMind."""
        from modules.node_registry import node_registry

        nodes = node_registry.get_all_nodes()
        active_nodes = [n for n in nodes if n.is_online]

        # Simuler des coordonnées 3D pour la galaxie NexusMind
        import math
        topology = {
            "nodes": [],
            "edges": [],
            "metrics": node_registry.get_network_stats()
        }

        for i, node in enumerate(active_nodes):
            # Calculer une position orbitale
            angle = (i / len(active_nodes)) * 2 * math.pi if active_nodes else 0
            radius = 10 + (i % 3) * 5

            topology["nodes"].append({
                "id": node.node_id,
                "address": node.address,
                "position": {
                    "x": radius * math.cos(angle),
                    "y": (i % 2 - 0.5) * 10,
                    "z": radius * math.sin(angle)
                },
                "reputation": node.reputation_score,
                "load": node.current_load,
                "is_vision": node.capabilities.imina_na
            })

            # Créer des liens vers quelques autres nœuds pour la visualisation du mesh
            if i > 0:
                topology["edges"].append({
                    "source": node.node_id,
                    "target": active_nodes[i-1].node_id,
                    "latency": node.stats.avg_latency_ms
                })

        return topology

    async def _update_system_metrics(self):
        """Met à jour les métriques du système."""
        
        # Simuler des changements de métriques
        import random
        
        for chain in self.system_status.keys():
            # Générer des métriques aléatoires
            metrics = {
                "transactions_per_second": random.uniform(10, 100),
                "active_addresses": random.randint(1000, 100000),
                "total_value_locked_usd": random.uniform(1e6, 1e9),
                "gas_price": random.uniform(10, 100) if chain == "ethereum" else 0,
                "block_time": random.uniform(0.4, 2.0),
            }
            
            # Mettre à jour les métriques
            self.system_status[chain]["metrics"] = metrics
            
            # Simuler des changements de statut occasionnels
            if random.random() < 0.05:  # 5% de chance
                statuses = ["healthy", "warning", "critical"]
                new_status = random.choice(statuses)
                
                self.system_status[chain]["status"] = new_status
                
                # Ajuster le nombre de menaces
                if new_status == "healthy":
                    self.system_status[chain]["threats"] = 0
                else:
                    self.system_status[chain]["threats"] = random.randint(1, 10)
    
    async def _generate_simulated_alerts(self):
        """Génère des alertes simulées en arrière-plan."""
        
        import random
        import time
        
        while True:
            try:
                # Attendre un temps aléatoire entre 30 et 120 secondes
                wait_time = random.uniform(30, 120)
                await asyncio.sleep(wait_time)
                
                # Générer une alerte simulée
                await self._simulate_threat_alert()
                
            except Exception as e:
                logger.error(f"Erreur génération alertes simulées: {e}")
                await asyncio.sleep(60)
    
    async def _simulate_threat_alert(self, alert_type: str = "random"):
        """Simule une alerte de menace."""
        
        import random
        
        # Types de menaces
        threat_types = {
            "flash_loan": {
                "chains": ["ethereum", "aave", "compound"],
                "severities": ["high", "critical"],
                "descriptions": [
                    "Flash loan attack detected",
                    "Suspicious flash loan transaction",
                    "Potential flash loan manipulation",
                ],
            },
            "price_manipulation": {
                "chains": ["uniswap", "chainlink"],
                "severities": ["medium", "high"],
                "descriptions": [
                    "Price manipulation detected",
                    "Suspicious price movement",
                    "Potential oracle manipulation",
                ],
            },
            "liquidation_risk": {
                "chains": ["makerdao", "compound"],
                "severities": ["warning", "medium"],
                "descriptions": [
                    "High liquidation risk detected",
                    "Collateral ratio dangerously low",
                    "Potential liquidation cascade",
                ],
            },
        }
        
        # Sélectionner le type d'alerte
        if alert_type == "random":
            selected_type = random.choice(list(threat_types.keys()))
        else:
            selected_type = alert_type
        
        if selected_type not in threat_types:
            selected_type = "flash_loan"
        
        threat_info = threat_types[selected_type]
        
        # Sélectionner une chaîne
        chain = random.choice(threat_info["chains"])
        
        # Sélectionner une sévérité
        severity = random.choice(threat_info["severities"])
        
        # Sélectionner une description
        description = random.choice(threat_info["descriptions"])
        
        # Mettre à jour le statut système
        self.system_status[chain]["status"] = "critical" if severity == "critical" else "warning"
        self.system_status[chain]["threats"] = random.randint(1, 5)
        
        # Créer le message d'alerte
        alert_message = WebSocketMessage(
            type=MessageType.THREAT_DETECTED,
            payload={
                "chain": chain,
                "severity": severity,
                "description": description,
                "timestamp": datetime.now().isoformat(),
                "transaction_hash": f"0x{random.getrandbits(256).to_bytes(32, 'big').hex()}",
                "attacker_address": f"0x{random.getrandbits(160).to_bytes(20, 'big').hex()}",
                "amount_usd": random.uniform(10000, 1000000),
                "evidence": {
                    "attack_type": selected_type,
                    "confidence": random.uniform(0.7, 0.95),
                    "affected_contracts": random.randint(1, 5),
                },
            },
            timestamp=datetime.now(),
        )
        
        # Diffuser l'alerte
        await self.connection_manager.broadcast(alert_message)
        
        logger.info(f"Alerte simulée générée: {description} sur {chain}")
    
    async def _cleanup_inactive_connections(self):
        """Nettoie les connexions inactives."""
        
        while True:
            try:
                # Attendre 60 secondes
                await asyncio.sleep(60)
                
                # Trouver les clients inactifs
                inactive_clients = self.connection_manager.get_inactive_clients()
                
                # Déconnecter les clients inactifs
                for client_id in inactive_clients:
                    logger.info(f"Déconnexion client inactif: {client_id}")
                    self.connection_manager.disconnect(client_id)
                
            except Exception as e:
                logger.error(f"Erreur nettoyage connexions: {e}")
    
    async def _send_error(self, client_id: str, error_message: str):
        """Envoie un message d'erreur au client."""
        
        message = WebSocketMessage(
            type=MessageType.ERROR,
            payload={
                "error": error_message,
                "timestamp": datetime.now().isoformat(),
            },
            timestamp=datetime.now(),
        )
        
        await self.connection_manager.send_personal_message(message, client_id)
    
    async def send_system_alert(self, chain: str, severity: str, description: str, details: Dict[str, Any] = None):
        """Envoie une alerte système à tous les clients."""
        
        payload = {
            "chain": chain,
            "severity": severity,
            "description": description,
            "timestamp": datetime.now().isoformat(),
        }
        
        if details:
            payload.update(details)
        
        message = WebSocketMessage(
            type=MessageType.THREAT_DETECTED,
            payload=payload,
            timestamp=datetime.now(),
        )
        
        await self.connection_manager.broadcast(message)
    
    async def send_agent_activity(self, agent_id: str, action: str, chain: str, details: Dict[str, Any] = None):
        """Envoie une activité d'agent à tous les clients."""
        
        payload = {
            "agent_id": agent_id,
            "action": action,
            "chain": chain,
            "timestamp": datetime.now().isoformat(),
        }
        
        if details:
            payload.update(details)
        
        message = WebSocketMessage(
            type=MessageType.AGENT_ACTIVITY,
            payload=payload,
            timestamp=datetime.now(),
        )
        
        await self.connection_manager.broadcast(message)
    
    async def send_transaction_alert(self, transaction_data: Dict[str, Any]):
        """Envoie une alerte de transaction à tous les clients."""
        
        message = WebSocketMessage(
            type=MessageType.TRANSACTION_ALERT,
            payload=transaction_data,
            timestamp=datetime.now(),
        )
        
        await self.connection_manager.broadcast(message)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de connexion."""
        
        return {
            "active_connections": self.connection_manager.get_client_count(),
            "total_subscriptions": sum(
                len(data["subscriptions"])
                for data in self.connection_manager.connection_data.values()
            ),
            "uptime": datetime.now() - min(
                data["connected_at"]
                for data in self.connection_manager.connection_data.values()
            ) if self.connection_manager.connection_data else timedelta(0),
        }
    
    async def shutdown(self):
        """Arrête le serveur WebSocket."""
        
        # Arrêter les tâches en arrière-plan
        for task in self.background_tasks:
            task.cancel()
        
        # Attendre que les tâches se terminent
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Fermer toutes les connexions
        for client_id in list(self.connection_manager.active_connections.keys()):
            self.connection_manager.disconnect(client_id)
        
        logger.info("Serveur WebSocket War Room arrêté")


# Instance globale du serveur
war_room_server = WarRoomWebSocketServer()