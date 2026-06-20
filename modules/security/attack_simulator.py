"""
Simulateur d'attaque pour tester la résilience du système.
Sandbox sécurisée pour exécuter des scénarios d'attaque.
"""

import asyncio
import json
import logging
import random
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import docker
from docker.models.containers import Container

from config import settings
from modules.database.threat_intel.threat_registry import ThreatRegistry as ThreatRepository

logger = logging.getLogger(__name__)


class AttackType(Enum):
    """Types d'attaques supportées."""
    REENTRANCY = "reentrancy"
    FRONT_RUNNING = "front_running"
    FLASH_LOAN = "flash_loan"
    ORACLE_MANIPULATION = "oracle_manipulation"
    BRIDGE_ATTACK = "bridge_attack"
    GOVERNANCE_ATTACK = "governance_attack"
    TOKEN_DRAIN = "token_drain"
    SANDWICH_ATTACK = "sandwich_attack"
    RUG_PULL = "rug_pull"
    PHISHING = "phishing"


class AttackSeverity(Enum):
    """Sévérité des attaques."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AttackScenario:
    """Scénario d'attaque."""
    id: str
    name: str
    description: str
    attack_type: AttackType
    severity: AttackSeverity
    chain: str
    target: str
    steps: List[Dict[str, Any]]
    expected_outcome: str
    success_criteria: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


@dataclass
class SimulationResult:
    """Résultat de simulation."""
    id: str
    scenario_id: str
    status: str  # pending, running, completed, failed
    start_time: datetime
    end_time: Optional[datetime]
    execution_time_seconds: Optional[float]
    detected_threats: List[Dict[str, Any]]
    missed_threats: List[Dict[str, Any]]
    false_positives: List[Dict[str, Any]]
    security_score: float  # 0.0 à 1.0
    recommendations: List[str]
    logs: List[str]
    metadata: Dict[str, Any]


class AttackSimulator:
    """Simulateur d'attaques avec sandbox Docker."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.threat_repo = ThreatRepository()
        self.scenarios_db = {}
        self.simulations_db = {}
        
        # Charger les scénarios par défaut
        self._load_default_scenarios()
        
        logger.info("Attack Simulator initialisé")
    
    def _load_default_scenarios(self):
        """Charge les scénarios d'attaque par défaut."""
        default_scenarios = [
            {
                "id": "reentrancy_attack_001",
                "name": "Attaque Reentrancy Classique",
                "description": "Attaque reentrancy sur un contrat vulnérable",
                "attack_type": AttackType.REENTRANCY,
                "severity": AttackSeverity.HIGH,
                "chain": "ethereum",
                "target": "vulnerable_contract",
                "steps": [
                    {
                        "step": 1,
                        "action": "Déployer un contrat vulnérable",
                        "code": "contract Vulnerable { mapping(address => uint) balances; function withdraw() public { uint amount = balances[msg.sender]; (bool success, ) = msg.sender.call{value: amount}(''); require(success); balances[msg.sender] = 0; }}"
                    },
                    {
                        "step": 2,
                        "action": "Déployer un contrat attaquant",
                        "code": "contract Attacker { Vulnerable vulnerable; constructor(address _vulnerable) { vulnerable = Vulnerable(_vulnerable); } fallback() external payable { if (address(vulnerable).balance >= 1 ether) { vulnerable.withdraw(); } } function attack() public payable { vulnerable.deposit{value: 1 ether}(); vulnerable.withdraw(); }}"
                    },
                    {
                        "step": 3,
                        "action": "Exécuter l'attaque",
                        "parameters": {"amount": "1 ether"}
                    }
                ],
                "expected_outcome": "Le contrat attaquant draine tous les fonds",
                "success_criteria": {
                    "detection_required": True,
                    "max_execution_time": 30,
                    "min_security_score": 0.7
                }
            },
            {
                "id": "flash_loan_attack_001",
                "name": "Attaque Flash Loan",
                "description": "Attaque par flash loan sur un DEX",
                "attack_type": AttackType.FLASH_LOAN,
                "severity": AttackSeverity.CRITICAL,
                "chain": "ethereum",
                "target": "aave_flash_loan",
                "steps": [
                    {
                        "step": 1,
                        "action": "Emprunter un flash loan de 10,000 ETH",
                        "parameters": {"amount": "10000 ether"}
                    },
                    {
                        "step": 2,
                        "action": "Manipuler le prix sur Uniswap",
                        "parameters": {"pool": "ETH/USDC"}
                    },
                    {
                        "step": 3,
                        "action": "Arbitrage profit",
                        "parameters": {"profit_target": "100 ether"}
                    }
                ],
                "expected_outcome": "Profit de 100 ETH via arbitrage",
                "success_criteria": {
                    "detection_required": True,
                    "max_execution_time": 60,
                    "min_security_score": 0.8
                }
            },
            {
                "id": "front_running_001",
                "name": "Attaque Front Running",
                "description": "Front running d'une transaction importante",
                "attack_type": AttackType.FRONT_RUNNING,
                "severity": AttackSeverity.MEDIUM,
                "chain": "ethereum",
                "target": "mempool",
                "steps": [
                    {
                        "step": 1,
                        "action": "Surveiller le mempool",
                        "parameters": {"gas_price_threshold": "100 gwei"}
                    },
                    {
                        "step": 2,
                        "action": "Détecter une transaction profitable",
                        "parameters": {"min_profit": "10 ether"}
                    },
                    {
                        "step": 3,
                        "action": "Soumettre une transaction avec gas price plus élevé",
                        "parameters": {"gas_price_multiplier": 1.2}
                    }
                ],
                "expected_outcome": "Interception de la transaction",
                "success_criteria": {
                    "detection_required": True,
                    "max_execution_time": 10,
                    "min_security_score": 0.6
                }
            }
        ]
        
        for scenario_data in default_scenarios:
            scenario = AttackScenario(
                id=scenario_data["id"],
                name=scenario_data["name"],
                description=scenario_data["description"],
                attack_type=AttackType(scenario_data["attack_type"]),
                severity=AttackSeverity(scenario_data["severity"]),
                chain=scenario_data["chain"],
                target=scenario_data["target"],
                steps=scenario_data["steps"],
                expected_outcome=scenario_data["expected_outcome"],
                success_criteria=scenario_data["success_criteria"],
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            self.scenarios_db[scenario.id] = scenario
    
    async def create_scenario(self, scenario_data: Dict[str, Any]) -> AttackScenario:
        """Crée un nouveau scénario d'attaque."""
        scenario_id = hashlib.sha256(
            f"{scenario_data['name']}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:32]
        
        scenario = AttackScenario(
            id=scenario_id,
            name=scenario_data["name"],
            description=scenario_data["description"],
            attack_type=AttackType(scenario_data["attack_type"]),
            severity=AttackSeverity(scenario_data["severity"]),
            chain=scenario_data["chain"],
            target=scenario_data["target"],
            steps=scenario_data["steps"],
            expected_outcome=scenario_data["expected_outcome"],
            success_criteria=scenario_data["success_criteria"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        
        self.scenarios_db[scenario_id] = scenario
        logger.info(f"Scénario créé: {scenario_id} - {scenario.name}")
        
        return scenario
    
    async def run_simulation(self, scenario_id: str, sandbox_config: Optional[Dict] = None) -> SimulationResult:
        """Exécute une simulation d'attaque dans une sandbox."""
        if scenario_id not in self.scenarios_db:
            raise ValueError(f"Scénario {scenario_id} non trouvé")
        
        scenario = self.scenarios_db[scenario_id]
        
        # Créer le résultat de simulation
        simulation_id = hashlib.sha256(
            f"{scenario_id}{datetime.now().timestamp()}{random.randint(0, 1000000)}".encode()
        ).hexdigest()[:32]
        
        result = SimulationResult(
            id=simulation_id,
            scenario_id=scenario_id,
            status="running",
            start_time=datetime.now(),
            end_time=None,
            execution_time_seconds=None,
            detected_threats=[],
            missed_threats=[],
            false_positives=[],
            security_score=0.0,
            recommendations=[],
            logs=[],
            metadata={"sandbox_config": sandbox_config or {}},
        )
        
        self.simulations_db[simulation_id] = result
        
        logger.info(f"Démarrage de la simulation {simulation_id} pour le scénario {scenario.name}")
        
        try:
            # Exécuter dans une sandbox Docker
            await self._run_in_sandbox(scenario, result, sandbox_config)
            
            # Calculer le score de sécurité
            await self._calculate_security_score(result)
            
            # Générer les recommandations
            await self._generate_recommendations(result)
            
            result.status = "completed"
            result.end_time = datetime.now()
            result.execution_time_seconds = (
                result.end_time - result.start_time
            ).total_seconds()
            
            logger.info(f"Simulation {simulation_id} terminée avec score: {result.security_score}")
        
        except Exception as e:
            result.status = "failed"
            result.end_time = datetime.now()
            result.logs.append(f"Erreur: {str(e)}")
            logger.error(f"Simulation {simulation_id} échouée: {e}")
        
        return result
    
    async def _run_in_sandbox(self, scenario: AttackScenario, result: SimulationResult, sandbox_config: Optional[Dict]):
        """Exécute le scénario dans une sandbox Docker."""
        container: Optional[Container] = None
        
        try:
            # Configuration de la sandbox
            config = sandbox_config or {
                "image": "python:3.11-slim",
                "network_disabled": True,
                "mem_limit": "512m",
                "cpu_period": 100000,
                "cpu_quota": 50000,
                "read_only": True,
                "security_opt": ["no-new-privileges"],
            }
            
            # Démarrer le conteneur
            container = self.docker_client.containers.run(
                image=config["image"],
                command="sleep 3600",  # Garder le conteneur en vie
                detach=True,
                network_disabled=config.get("network_disabled", True),
                mem_limit=config.get("mem_limit"),
                cpu_period=config.get("cpu_period"),
                cpu_quota=config.get("cpu_quota"),
                read_only=config.get("read_only", True),
                security_opt=config.get("security_opt", []),
            )
            
            result.logs.append(f"Conteneur démarré: {container.id}")
            
            # Exécuter les étapes du scénario
            for step in scenario.steps:
                await self._execute_step(container, step, result)
            
            # Vérifier les menaces détectées
            await self._check_threat_detection(scenario, result)
            
            # Nettoyer
            container.stop()
            container.remove()
            
            result.logs.append("Conteneur nettoyé")
        
        except Exception as e:
            result.logs.append(f"Erreur sandbox: {str(e)}")
            if container:
                try:
                    container.stop()
                    container.remove()
                except:
                    pass
            raise
    
    async def _execute_step(self, container: Container, step: Dict[str, Any], result: SimulationResult):
        """Exécute une étape du scénario."""
        try:
            action = step["action"]
            result.logs.append(f"Exécution: {action}")
            
            # Simuler l'exécution
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Générer des menaces simulées
            if "attack" in action.lower():
                threat = self._generate_simulated_threat(step)
                result.detected_threats.append(threat)
                result.logs.append(f"Menace générée: {threat['type']}")
        
        except Exception as e:
            result.logs.append(f"Erreur étape: {str(e)}")
    
    def _generate_simulated_threat(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Génère une menace simulée pour le test."""
        threat_types = [
            "REENTRANCY_ATTACK",
            "FLASH_LOAN_ATTACK",
            "FRONT_RUNNING",
            "ORACLE_MANIPULATION",
            "BRIDGE_ATTACK",
        ]
        
        threat_type = random.choice(threat_types)
        
        return {
            "id": hashlib.sha256(f"{threat_type}{datetime.now().timestamp()}".encode()).hexdigest()[:32],
            "type": threat_type,
            "severity": random.choice(["low", "medium", "high", "critical"]),
            "description": f"Menace simulée: {threat_type}",
            "timestamp": datetime.now(),
            "step": step.get("step", 0),
            "action": step.get("action", "unknown"),
            "simulated": True,
        }
    
    async def _check_threat_detection(self, scenario: AttackScenario, result: SimulationResult):
        """Vérifie si les menaces ont été correctement détectées."""
        # Pour une simulation réelle, on comparerait avec les détections du système
        # Ici on simule la détection
        
        expected_threats = len([s for s in scenario.steps if "attack" in s.get("action", "").lower()])
        detected = len(result.detected_threats)
        
        if detected < expected_threats:
            missed_count = expected_threats - detected
            for i in range(missed_count):
                result.missed_threats.append({
                    "type": scenario.attack_type.value.upper(),
                    "reason": "Non détecté par le système",
                    "step": i + 1,
                })
        
        # Ajouter quelques faux positifs aléatoires
        if random.random() < 0.3:  # 30% de chance
            fp_count = random.randint(1, 3)
            for i in range(fp_count):
                result.false_positives.append({
                    "type": random.choice(["FALSE_POSITIVE_ALERT", "BENIGN_ACTIVITY"]),
                    "description": "Activité bénigne détectée comme menace",
                    "confidence": random.uniform(0.3, 0.7),
                })
    
    async def _calculate_security_score(self, result: SimulationResult) -> float:
        """Calcule le score de sécurité basé sur les résultats."""
        if not result.detected_threats and not result.missed_threats and not result.false_positives:
            result.security_score = 1.0
            return 1.0
        
        # Poids pour chaque métrique
        weights = {
            "detection_rate": 0.4,
            "false_positive_rate": 0.3,
            "response_time": 0.2,
            "coverage": 0.1,
        }
        
        # Taux de détection
        total_threats = len(result.detected_threats) + len(result.missed_threats)
        detection_rate = len(result.detected_threats) / total_threats if total_threats > 0 else 1.0
        
        # Taux de faux positifs
        total_alerts = len(result.detected_threats) + len(result.false_positives)
        false_positive_rate = 1.0 - (len(result.false_positives) / total_alerts) if total_alerts > 0 else 1.0
        
        # Temps de réponse (simulé)
        avg_response_time = random.uniform(0.5, 5.0)
        response_time_score = max(0.0, 1.0 - (avg_response_time / 10.0))
        
        # Couverture (simulée)
        coverage_score = random.uniform(0.7, 0.95)
        
        # Score final
        score = (
            detection_rate * weights["detection_rate"] +
            false_positive_rate * weights["false_positive_rate"] +
            response_time_score * weights["response_time"] +
            coverage_score * weights["coverage"]
        )
        
        result.security_score = round(score, 3)
        return result.security_score
    
    async def _generate_recommendations(self, result: SimulationResult):
        """Génère des recommandations basées sur les résultats."""
        recommendations = []
        
        # Basé sur les menaces manquées
        if result.missed_threats:
            recommendations.append(
                "Améliorer les règles de détection pour les types d'attaques manqués"
            )
        
        # Basé sur les faux positifs
        if result.false_positives:
            recommendations.append(
                "Ajuster les seuils de détection pour réduire les faux positifs"
            )
        
        # Basé sur le score
        if result.security_score < 0.7:
            recommendations.append(
                "Mettre à jour les modèles de menace avec les dernières signatures d'attaque"
            )
        
        if result.security_score < 0.5:
            recommendations.append(
                "Considérer l'ajout de nouvelles couches de sécurité (FHE, ZK-proofs)"
            )
        
        # Recommandations générales
        recommendations.extend([
            "Mettre en place une surveillance continue des nouvelles vulnérabilités",
            "Automatiser les tests de pénétration réguliers",
            "Former l'équipe de sécurité aux dernières techniques d'attaque",
        ])
        
        result.recommendations = recommendations
    
    async def get_scenario(self, scenario_id: str) -> Optional[AttackScenario]:
        """Récupère un scénario par son ID."""
        return self.scenarios_db.get(scenario_id)
    
    async def list_scenarios(self, filter_by: Optional[Dict] = None) -> List[AttackScenario]:
        """Liste tous les scénarios disponibles."""
        scenarios = list(self.scenarios_db.values())
        
        if filter_by:
            filtered = []
            for scenario in scenarios:
                match = True
                
                if "chain" in filter_by and scenario.chain != filter_by["chain"]:
                    match = False
                
                if "severity" in filter_by and scenario.severity.value != filter_by["severity"]:
                    match = False
                
                if "attack_type" in filter_by and scenario.attack_type.value != filter_by["attack_type"]:
                    match = False
                
                if match:
                    filtered.append(scenario)
            
            return filtered
        
        return scenarios
    
    async def get_simulation(self, simulation_id: str) -> Optional[SimulationResult]:
        """Récupère un résultat de simulation par son ID."""
        return self.simulations_db.get(simulation_id)
    
    async def list_simulations(self, limit: int = 100, offset: int = 0) -> List[SimulationResult]:
        """Liste les simulations récentes."""
        simulations = list(self.simulations_db.values())
        simulations.sort(key=lambda x: x.start_time, reverse=True)
        
        return simulations[offset:offset + limit]
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques de sécurité globales."""
        simulations = list(self.simulations_db.values())
        
        if not simulations:
            return {
                "total_simulations": 0,
                "average_security_score": 0.0,
                "detection_rate": 0.0,
                "false_positive_rate": 0.0,
            }
        
        completed = [s for s in simulations if s.status == "completed"]
        
        total_simulations = len(simulations)
        avg_score = sum(s.security_score for s in completed) / len(completed) if completed else 0.0
        
        # Calculer les taux
        total_detected = sum(len(s.detected_threats) for s in completed)
        total_missed = sum(len(s.missed_threats) for s in completed)
        total_fp = sum(len(s.false_positives) for s in completed)
        
        detection_rate = total_detected / (total_detected + total_missed) if (total_detected + total_missed) > 0 else 0.0
        false_positive_rate = total_fp / (total_detected + total_fp) if (total_detected + total_fp) > 0 else 0.0
        
        return {
            "total_simulations": total_simulations,
            "completed_simulations": len(completed),
            "average_security_score": round(avg_score, 3),
            "detection_rate": round(detection_rate, 3),
            "false_positive_rate": round(false_positive_rate, 3),
            "total_threats_detected": total_detected,
            "total_threats_missed": total_missed,
            "total_false_positives": total_fp,
            "last_simulation": completed[0].start_time if completed else None,
        }