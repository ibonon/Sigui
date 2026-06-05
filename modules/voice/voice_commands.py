"""
Module de commandes vocales pour le War Room Sigui.
Supporte la reconnaissance vocale en temps réel et les commandes personnalisées.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import re

logger = logging.getLogger(__name__)


class VoiceCommandType(Enum):
    """Types de commandes vocales supportées."""
    NAVIGATION = "navigation"
    SURVEILLANCE = "surveillance"
    SYSTEM = "system"
    HELP = "help"
    SIMULATION = "simulation"
    ALERT = "alert"


class VoiceCommandAction(Enum):
    """Actions spécifiques pour les commandes vocales."""
    RESET_VIEW = "reset_view"
    TOGGLE_AUTO_ROTATE = "toggle_auto_rotate"
    TOGGLE_LABELS = "toggle_labels"
    FULLSCREEN = "fullscreen"
    SHOW_SYSTEM_STATUS = "show_system_status"
    SHOW_ACTIVE_THREATS = "show_active_threats"
    RUN_SIMULATION = "run_simulation"
    GENERATE_TEST_ALERT = "generate_test_alert"
    SHOW_HELP = "show_help"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    ROTATE_LEFT = "rotate_left"
    ROTATE_RIGHT = "rotate_up"
    ROTATE_DOWN = "rotate_down"
    FOCUS_CHAIN = "focus_chain"
    SHOW_METRICS = "show_metrics"


@dataclass
class VoiceCommand:
    """Représente une commande vocale reconnue."""
    type: VoiceCommandType
    action: VoiceCommandAction
    parameters: Dict[str, Any]
    confidence: float
    raw_text: str
    timestamp: float


@dataclass
class VoiceCommandPattern:
    """Pattern pour la reconnaissance de commandes vocales."""
    type: VoiceCommandType
    action: VoiceCommandAction
    patterns: List[str]
    parameters: Dict[str, str]  # Mapping des groupes de capture
    description: str


class VoiceCommandRecognizer:
    """Reconnaisseur de commandes vocales avec support de patterns."""
    
    def __init__(self, language: str = "fr-FR"):
        self.language = language
        self.command_patterns: List[VoiceCommandPattern] = []
        self._initialize_patterns()
        
        # Callbacks
        self.on_command_detected: Optional[Callable[[VoiceCommand], None]] = None
        self.on_partial_result: Optional[Callable[[str], None]] = None
        
        # État
        self.is_listening = False
        self.last_command_time = 0
        self.command_cooldown = 1.0  # secondes
        
        # Configuration
        self.min_confidence = 0.7
        self.enable_partial_results = True
    
    def _initialize_patterns(self):
        """Initialise les patterns de commandes vocales."""
        
        # Commandes de navigation
        self.command_patterns.extend([
            VoiceCommandPattern(
                type=VoiceCommandType.NAVIGATION,
                action=VoiceCommandAction.RESET_VIEW,
                patterns=[
                    r"vue.*réinitialiser",
                    r"réinitialiser.*vue",
                    r"vue.*origine",
                    r"position.*initiale",
                ],
                parameters={},
                description="Réinitialise la vue 3D à la position par défaut"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.NAVIGATION,
                action=VoiceCommandAction.TOGGLE_AUTO_ROTATE,
                patterns=[
                    r"rotation.*auto",
                    r"auto.*rotation",
                    r"rotation.*automatique",
                    r"tourner.*automatiquement",
                ],
                parameters={},
                description="Active/désactive la rotation automatique"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.NAVIGATION,
                action=VoiceCommandAction.TOGGLE_LABELS,
                patterns=[
                    r"labels.*(afficher|cacher)",
                    r"(afficher|cacher).*labels",
                    r"étiquettes.*(afficher|cacher)",
                ],
                parameters={"state": r"(afficher|cacher)"},
                description="Affiche ou cache les labels"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.NAVIGATION,
                action=VoiceCommandAction.FULLSCREEN,
                patterns=[
                    r"plein.*écran",
                    r"écran.*plein",
                    r"mode.*plein.*écran",
                ],
                parameters={},
                description="Active le mode plein écran"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.NAVIGATION,
                action=VoiceCommandAction.ZOOM_IN,
                patterns=[
                    r"zoomer.*in",
                    r"agrandir",
                    r"rapprocher",
                    r"plus.*près",
                ],
                parameters={},
                description="Zoom avant"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.NAVIGATION,
                action=VoiceCommandAction.ZOOM_OUT,
                patterns=[
                    r"zoomer.*out",
                    r"réduire",
                    r"éloigner",
                    r"plus.*loin",
                ],
                parameters={},
                description="Zoom arrière"
            ),
        ])
        
        # Commandes de surveillance
        self.command_patterns.extend([
            VoiceCommandPattern(
                type=VoiceCommandType.SURVEILLANCE,
                action=VoiceCommandAction.SHOW_SYSTEM_STATUS,
                patterns=[
                    r"statut.*système",
                    r"système.*statut",
                    r"état.*système",
                    r"métriques.*système",
                ],
                parameters={},
                description="Affiche le statut du système"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.SURVEILLANCE,
                action=VoiceCommandAction.SHOW_ACTIVE_THREATS,
                patterns=[
                    r"menaces.*actives",
                    r"actives.*menaces",
                    r"alertes.*en.*cours",
                    r"risques.*actuels",
                ],
                parameters={},
                description="Affiche les menaces actives"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.SURVEILLANCE,
                action=VoiceCommandAction.FOCUS_CHAIN,
                patterns=[
                    r"focus.*(ethereum|solana|cosmos|aave|compound|makerdao|uniswap)",
                    r"concentrer.*(ethereum|solana|cosmos|aave|compound|makerdao|uniswap)",
                    r"voir.*(ethereum|solana|cosmos|aave|compound|makerdao|uniswap)",
                ],
                parameters={"chain": r"(ethereum|solana|cosmos|aave|compound|makerdao|uniswap)"},
                description="Se concentre sur une chaîne spécifique"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.SURVEILLANCE,
                action=VoiceCommandAction.SHOW_METRICS,
                patterns=[
                    r"métriques.*(ethereum|solana|cosmos|aave|compound|makerdao|uniswap)",
                    r"statistiques.*(ethereum|solana|cosmos|aave|compound|makerdao|uniswap)",
                ],
                parameters={"chain": r"(ethereum|solana|cosmos|aave|compound|makerdao|uniswap)"},
                description="Affiche les métriques d'une chaîne"
            ),
        ])
        
        # Commandes de simulation
        self.command_patterns.extend([
            VoiceCommandPattern(
                type=VoiceCommandType.SIMULATION,
                action=VoiceCommandAction.RUN_SIMULATION,
                patterns=[
                    r"simuler.*attaque",
                    r"lancer.*simulation",
                    r"test.*résilience",
                    r"scénario.*attaque",
                ],
                parameters={},
                description="Lance une simulation d'attaque"
            ),
            VoiceCommandPattern(
                type=VoiceCommandType.SIMULATION,
                action=VoiceCommandAction.GENERATE_TEST_ALERT,
                patterns=[
                    r"alerte.*test",
                    r"test.*alerte",
                    r"générer.*alerte",
                    r"simuler.*alerte",
                ],
                parameters={},
                description="Génère une alerte de test"
            ),
        ])
        
        # Commandes d'aide
        self.command_patterns.extend([
            VoiceCommandPattern(
                type=VoiceCommandType.HELP,
                action=VoiceCommandAction.SHOW_HELP,
                patterns=[
                    r"aide",
                    r"commandes",
                    r"que.*peux.*tu.*faire",
                    r"instructions",
                ],
                parameters={},
                description="Affiche les commandes disponibles"
            ),
        ])
    
    def recognize(self, text: str, confidence: float = 1.0) -> Optional[VoiceCommand]:
        """Reconnaît une commande vocale à partir du texte."""
        
        # Normaliser le texte
        normalized_text = self._normalize_text(text)
        
        # Vérifier la confiance
        if confidence < self.min_confidence:
            return None
        
        # Chercher un pattern correspondant
        for pattern in self.command_patterns:
            for pattern_str in pattern.patterns:
                regex = self._pattern_to_regex(pattern_str)
                match = re.search(regex, normalized_text, re.IGNORECASE)
                
                if match:
                    # Extraire les paramètres
                    parameters = self._extract_parameters(match, pattern.parameters)
                    
                    # Créer la commande
                    command = VoiceCommand(
                        type=pattern.type,
                        action=pattern.action,
                        parameters=parameters,
                        confidence=confidence,
                        raw_text=text,
                        timestamp=asyncio.get_event_loop().time()
                    )
                    
                    logger.info(f"Commande vocale reconnue: {command.action.value}")
                    return command
        
        return None
    
    def _normalize_text(self, text: str) -> str:
        """Normalise le texte pour la reconnaissance."""
        # Convertir en minuscules
        text = text.lower()
        
        # Supprimer la ponctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remplacer les espaces multiples
        text = re.sub(r'\s+', ' ', text)
        
        # Normaliser les accents (simplifié)
        replacements = {
            'à': 'a', 'â': 'a', 'ä': 'a',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'î': 'i', 'ï': 'i',
            'ô': 'o', 'ö': 'o',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c',
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text.strip()
    
    def _pattern_to_regex(self, pattern: str) -> str:
        """Convertit un pattern en regex."""
        # Échapper les caractères spéciaux
        pattern = re.escape(pattern)
        
        # Remplacer les wildcards
        pattern = pattern.replace(r'\*', '.*')
        pattern = pattern.replace(r'\?', '.')
        
        return f"^{pattern}$"
    
    def _extract_parameters(self, match: re.Match, param_defs: Dict[str, str]) -> Dict[str, Any]:
        """Extrait les paramètres d'une correspondance."""
        parameters = {}
        
        for param_name, param_pattern in param_defs.items():
            # Chercher le paramètre dans le texte
            param_match = re.search(param_pattern, match.string, re.IGNORECASE)
            if param_match:
                parameters[param_name] = param_match.group()
        
        return parameters
    
    async def start_listening(self):
        """Démarre l'écoute des commandes vocales."""
        if self.is_listening:
            return
        
        self.is_listening = True
        logger.info("Démarrage de l'écoute vocale")
        
        # À implémenter: intégration avec Web Speech API
        # Pour l'exemple, on simule l'écoute
        await self._simulate_listening()
    
    async def stop_listening(self):
        """Arrête l'écoute des commandes vocales."""
        self.is_listening = False
        logger.info("Arrêt de l'écoute vocale")
    
    async def _simulate_listening(self):
        """Simule l'écoute pour le développement."""
        # Cette méthode serait remplacée par l'intégration réelle
        # avec l'API Web Speech du navigateur
        
        logger.info("Mode simulation vocale activé")
        
        # Pour l'exemple, on simule des commandes périodiques
        while self.is_listening:
            await asyncio.sleep(30)  # Toutes les 30 secondes
            
            if not self.is_listening:
                break
            
            # Simuler une commande aléatoire
            simulated_commands = [
                "vue réinitialiser",
                "rotation auto",
                "plein écran",
                "statut système",
                "menaces actives",
                "alerte test",
            ]
            
            simulated_text = simulated_commands[
                int(asyncio.get_event_loop().time()) % len(simulated_commands)
            ]
            
            command = self.recognize(simulated_text, confidence=0.9)
            
            if command and self.on_command_detected:
                self.on_command_detected(command)


class VoiceCommandExecutor:
    """Exécute les commandes vocales reconnues."""
    
    def __init__(self, war_room=None):
        self.war_room = war_room
        self.command_handlers: Dict[VoiceCommandAction, Callable] = {}
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """Initialise les handlers de commandes."""
        
        # Navigation
        self.command_handlers[VoiceCommandAction.RESET_VIEW] = self._handle_reset_view
        self.command_handlers[VoiceCommandAction.TOGGLE_AUTO_ROTATE] = self._handle_toggle_auto_rotate
        self.command_handlers[VoiceCommandAction.TOGGLE_LABELS] = self._handle_toggle_labels
        self.command_handlers[VoiceCommandAction.FULLSCREEN] = self._handle_fullscreen
        self.command_handlers[VoiceCommandAction.ZOOM_IN] = self._handle_zoom_in
        self.command_handlers[VoiceCommandAction.ZOOM_OUT] = self._handle_zoom_out
        
        # Surveillance
        self.command_handlers[VoiceCommandAction.SHOW_SYSTEM_STATUS] = self._handle_show_system_status
        self.command_handlers[VoiceCommandAction.SHOW_ACTIVE_THREATS] = self._handle_show_active_threats
        self.command_handlers[VoiceCommandAction.FOCUS_CHAIN] = self._handle_focus_chain
        self.command_handlers[VoiceCommandAction.SHOW_METRICS] = self._handle_show_metrics
        
        # Simulation
        self.command_handlers[VoiceCommandAction.RUN_SIMULATION] = self._handle_run_simulation
        self.command_handlers[VoiceCommandAction.GENERATE_TEST_ALERT] = self._handle_generate_test_alert
        
        # Aide
        self.command_handlers[VoiceCommandAction.SHOW_HELP] = self._handle_show_help
    
    async def execute(self, command: VoiceCommand):
        """Exécute une commande vocale."""
        
        handler = self.command_handlers.get(command.action)
        if not handler:
            logger.warning(f"Aucun handler pour l'action: {command.action.value}")
            return
        
        try:
            await handler(command)
            logger.info(f"Commande exécutée: {command.action.value}")
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la commande {command.action.value}: {e}")
    
    # Handlers de navigation
    async def _handle_reset_view(self, command: VoiceCommand):
        """Réinitialise la vue 3D."""
        if self.war_room:
            self.war_room.resetView()
    
    async def _handle_toggle_auto_rotate(self, command: VoiceCommand):
        """Active/désactive la rotation automatique."""
        if self.war_room:
            current_state = self.war_room.controls.autoRotate
            self.war_room.setAutoRotate(not current_state)
    
    async def _handle_toggle_labels(self, command: VoiceCommand):
        """Affiche/cache les labels."""
        if self.war_room:
            current_state = self.war_room.config.showLabels
            self.war_room.showLabels(not current_state)
    
    async def _handle_fullscreen(self, command: VoiceCommand):
        """Active le mode plein écran."""
        if self.war_room:
            # À implémenter: activation du mode plein écran
            pass
    
    async def _handle_zoom_in(self, command: VoiceCommand):
        """Zoom avant."""
        if self.war_room:
            # À implémenter: zoom avant
            pass
    
    async def _handle_zoom_out(self, command: VoiceCommand):
        """Zoom arrière."""
        if self.war_room:
            # À implémenter: zoom arrière
            pass
    
    # Handlers de surveillance
    async def _handle_show_system_status(self, command: VoiceCommand):
        """Affiche le statut du système."""
        if self.war_room:
            # À implémenter: afficher le statut système
            pass
    
    async def _handle_show_active_threats(self, command: VoiceCommand):
        """Affiche les menaces actives."""
        if self.war_room:
            # À implémenter: filtrer les menaces actives
            pass
    
    async def _handle_focus_chain(self, command: VoiceCommand):
        """Se concentre sur une chaîne spécifique."""
        chain = command.parameters.get("chain")
        if self.war_room and chain:
            # À implémenter: focus sur la chaîne
            pass
    
    async def _handle_show_metrics(self, command: VoiceCommand):
        """Affiche les métriques d'une chaîne."""
        chain = command.parameters.get("chain")
        if self.war_room and chain:
            # À implémenter: afficher les métriques
            pass
    
    # Handlers de simulation
    async def _handle_run_simulation(self, command: VoiceCommand):
        """Lance une simulation d'attaque."""
        # À implémenter: lancer une simulation
        pass
    
    async def _handle_generate_test_alert(self, command: VoiceCommand):
        """Génère une alerte de test."""
        if self.war_room:
            # Simuler une alerte
            chains = ['ethereum', 'solana', 'cosmos', 'aave', 'compound', 'makerdao', 'uniswap']
            import random
            random_chain = random.choice(chains)
            
            self.war_room.showAlert(
                f"Alerte de test sur {random_chain}",
                "medium",
                "Alerte générée par commande vocale"
            )
    
    # Handlers d'aide
    async def _handle_show_help(self, command: VoiceCommand):
        """Affiche les commandes disponibles."""
        help_text = """
        Commandes vocales disponibles:
        
        Navigation:
        - "vue réinitialiser" : Réinitialise la vue 3D
        - "rotation auto" : Active/désactive la rotation automatique
        - "labels afficher/cacher" : Affiche ou cache les labels
        - "plein écran" : Active le mode plein écran
        - "zoomer in/out" : Zoom avant/arrière
        
        Surveillance:
        - "statut système" : Affiche le statut du système
        - "menaces actives" : Affiche les menaces actives
        - "focus [chaîne]" : Se concentre sur une chaîne spécifique
        - "métriques [chaîne]" : Affiche les métriques d'une chaîne
        
        Simulation:
        - "simuler attaque" : Lance une simulation d'attaque
        - "alerte test" : Génère une alerte de test
        
        Aide:
        - "aide" : Affiche cette liste de commandes
        """
        
        logger.info("Aide vocale affichée")
        # À implémenter: afficher l'aide dans l'interface


class VoiceFeedback:
    """Gère le feedback vocal pour l'utilisateur."""
    
    def __init__(self):
        self.speech_synthesis = None
        
        # Messages de feedback
        self.feedback_messages = {
            VoiceCommandAction.RESET_VIEW: "Vue réinitialisée",
            VoiceCommandAction.TOGGLE_AUTO_ROTATE: "Rotation automatique modifiée",
            VoiceCommandAction.TOGGLE_LABELS: "Labels modifiés",
            VoiceCommandAction.FULLSCREEN: "Mode plein écran activé",
            VoiceCommandAction.SHOW_SYSTEM_STATUS: "Affichage du statut système",
            VoiceCommandAction.SHOW_ACTIVE_THREATS: "Affichage des menaces actives",
            VoiceCommandAction.GENERATE_TEST_ALERT: "Alerte de test générée",
            VoiceCommandAction.SHOW_HELP: "Voici les commandes disponibles",
        }
    
    async def provide_feedback(self, command: VoiceCommand):
        """Fournit un feedback vocal pour une commande."""
        
        message = self.feedback_messages.get(command.action)
        if not message:
            message = f"Commande {command.action.value} exécutée"
        
        await self.speak(message)
    
    async def speak(self, text: str):
        """Parle le texte fourni."""
        
        # À implémenter: intégration avec Web Speech API
        # Pour l'exemple, on simule la synthèse vocale
        
        logger.info(f"Feedback vocal: {text}")
        
        # Dans une implémentation réelle, on utiliserait:
        # if 'speechSynthesis' in window:
        #     const utterance = new SpeechSynthesisUtterance(text);
        #     utterance.lang = 'fr-FR';
        #     window.speechSynthesis.speak(utterance);
        
        # Pour l'exemple, on simule un délai
        await asyncio.sleep(0.5)


class VoiceCommandManager:
    """Manager principal pour les commandes vocales."""
    
    def __init__(self, war_room=None):
        self.recognizer = VoiceCommandRecognizer()
        self.executor = VoiceCommandExecutor(war_room)
        self.feedback = VoiceFeedback()
        
        # Configurer les callbacks
        self.recognizer.on_command_detected = self._on_command_detected
        
        # État
        self.is_active = False
        self.last_command = None
    
    async def start(self):
        """Démarre le manager de commandes vocales."""
        if self.is_active:
            return
        
        self.is_active = True
        logger.info("Manager de commandes vocales démarré")
        
        # Démarrer la reconnaissance
        await self.recognizer.start_listening()
    
    async def stop(self):
        """Arrête le manager de commandes vocales."""
        self.is_active = False
        logger.info("Manager de commandes vocales arrêté")
        
        # Arrêter la reconnaissance
        await self.recognizer.stop_listening()
    
    async def _on_command_detected(self, command: VoiceCommand):
        """Callback lorsqu'une commande est détectée."""
        self.last_command = command
        
        # Exécuter la commande
        await self.executor.execute(command)
        
        # Fournir un feedback
        await self.feedback.provide_feedback(command)
    
    async def process_text(self, text: str, confidence: float = 1.0):
        """Traite du texte comme une commande vocale."""
        command = self.recognizer.recognize(text, confidence)
        
        if command:
            await self._on_command_detected(command)
            return True
        
        return False
    
    def get_available_commands(self) -> List[Dict[str, Any]]:
        """Retourne la liste des commandes disponibles."""
        commands = []
        
        for pattern in self.recognizer.command_patterns:
            commands.append({
                "type": pattern.type.value,
                "action": pattern.action.value,
                "patterns": pattern.patterns,
                "description": pattern.description,
            })
        
        return commands