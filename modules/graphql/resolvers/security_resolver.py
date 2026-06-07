"""
Resolvers GraphQL pour les fonctionnalités de sécurité.
Inclut les simulations d'attaque, ZK-proofs et FHE.
"""

import strawberry
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...security.attack_simulator import AttackSimulator, AttackScenario, SimulationResult
from ...security.zk_proofs import ZKProofSystem, ZKStatement, ZKProof
from ...security.fhe_system import FHESystem, FHEKeyPair, FHECiphertext, FHEOperationResult
from ..schema import (
    AttackScenario as GraphQLAttackScenario,
    SimulationResult as GraphQLSimulationResult,
    ZKStatement as GraphQLZKStatement,
    ZKProof as GraphQLZKProof,
    FHEKeyPair as GraphQLFHEKeyPair,
    FHECiphertext as GraphQLFHECiphertext,
    FHEOperationResult as GraphQLFHEOperationResult,
    AttackScenarioInput,
    SimulationInput,
    ZKStatementInput,
    ZKProofInput,
    FHEKeyPairInput,
    FHECiphertextInput,
    FHEOperationInput,
)


class SecurityResolver:
    """Resolvers pour les fonctionnalités de sécurité."""
    
    def __init__(self):
        self.attack_simulator = AttackSimulator()
        self.zk_system = ZKProofSystem()
        self.fhe_system = FHESystem()
    
    @strawberry.field
    async def attack_scenario(self, id: str) -> Optional[GraphQLAttackScenario]:
        """Récupère un scénario d'attaque par son ID."""
        scenario = await self.attack_simulator.get_scenario(id)
        
        if not scenario:
            return None
        
        return GraphQLAttackScenario(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            attack_type=scenario.attack_type.value,
            severity=scenario.severity.value,
            chain=scenario.chain,
            target=scenario.target,
            steps=scenario.steps,
            expected_outcome=scenario.expected_outcome,
            success_criteria=scenario.success_criteria,
            created_at=scenario.created_at,
            updated_at=scenario.updated_at,
        )
    
    @strawberry.field
    async def attack_scenarios(
        self,
        chain: Optional[str] = None,
        severity: Optional[str] = None,
        attack_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GraphQLAttackScenario]:
        """Liste les scénarios d'attaque disponibles."""
        filter_by = {}
        
        if chain:
            filter_by["chain"] = chain
        
        if severity:
            filter_by["severity"] = severity
        
        if attack_type:
            filter_by["attack_type"] = attack_type
        
        scenarios = await self.attack_simulator.list_scenarios(filter_by)
        
        # Convertir en format GraphQL
        graphql_scenarios = []
        for scenario in scenarios[offset:offset + limit]:
            graphql_scenarios.append(
                GraphQLAttackScenario(
                    id=scenario.id,
                    name=scenario.name,
                    description=scenario.description,
                    attack_type=scenario.attack_type.value,
                    severity=scenario.severity.value,
                    chain=scenario.chain,
                    target=scenario.target,
                    steps=scenario.steps,
                    expected_outcome=scenario.expected_outcome,
                    success_criteria=scenario.success_criteria,
                    created_at=scenario.created_at,
                    updated_at=scenario.updated_at,
                )
            )
        
        return graphql_scenarios
    
    @strawberry.field
    async def create_attack_scenario(
        self,
        input: AttackScenarioInput,
    ) -> GraphQLAttackScenario:
        """Crée un nouveau scénario d'attaque."""
        scenario_data = {
            "name": input.name,
            "description": input.description,
            "attack_type": input.attack_type,
            "severity": input.severity,
            "chain": input.chain,
            "target": input.target,
            "steps": input.steps,
            "expected_outcome": input.expected_outcome,
            "success_criteria": input.success_criteria,
        }
        
        scenario = await self.attack_simulator.create_scenario(scenario_data)
        
        return GraphQLAttackScenario(
            id=scenario.id,
            name=scenario.name,
            description=scenario.description,
            attack_type=scenario.attack_type.value,
            severity=scenario.severity.value,
            chain=scenario.chain,
            target=scenario.target,
            steps=scenario.steps,
            expected_outcome=scenario.expected_outcome,
            success_criteria=scenario.success_criteria,
            created_at=scenario.created_at,
            updated_at=scenario.updated_at,
        )
    
    @strawberry.field
    async def run_simulation(
        self,
        input: SimulationInput,
    ) -> GraphQLSimulationResult:
        """Exécute une simulation d'attaque."""
        result = await self.attack_simulator.run_simulation(
            input.scenario_id,
            input.sandbox_config,
        )
        
        return GraphQLSimulationResult(
            id=result.id,
            scenario_id=result.scenario_id,
            status=result.status,
            start_time=result.start_time,
            end_time=result.end_time,
            execution_time_seconds=result.execution_time_seconds,
            detected_threats=result.detected_threats,
            missed_threats=result.missed_threats,
            false_positives=result.false_positives,
            security_score=result.security_score,
            recommendations=result.recommendations,
            logs=result.logs,
            metadata=result.metadata,
        )
    
    @strawberry.field
    async def simulation(self, id: str) -> Optional[GraphQLSimulationResult]:
        """Récupère un résultat de simulation par son ID."""
        result = await self.attack_simulator.get_simulation(id)
        
        if not result:
            return None
        
        return GraphQLSimulationResult(
            id=result.id,
            scenario_id=result.scenario_id,
            status=result.status,
            start_time=result.start_time,
            end_time=result.end_time,
            execution_time_seconds=result.execution_time_seconds,
            detected_threats=result.detected_threats,
            missed_threats=result.missed_threats,
            false_positives=result.false_positives,
            security_score=result.security_score,
            recommendations=result.recommendations,
            logs=result.logs,
            metadata=result.metadata,
        )
    
    @strawberry.field
    async def simulations(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GraphQLSimulationResult]:
        """Liste les simulations récentes."""
        results = await self.attack_simulator.list_simulations(limit, offset)
        
        graphql_results = []
        for result in results:
            graphql_results.append(
                GraphQLSimulationResult(
                    id=result.id,
                    scenario_id=result.scenario_id,
                    status=result.status,
                    start_time=result.start_time,
                    end_time=result.end_time,
                    execution_time_seconds=result.execution_time_seconds,
                    detected_threats=result.detected_threats,
                    missed_threats=result.missed_threats,
                    false_positives=result.false_positives,
                    security_score=result.security_score,
                    recommendations=result.recommendations,
                    logs=result.logs,
                    metadata=result.metadata,
                )
            )
        
        return graphql_results
    
    @strawberry.field
    async def security_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques de sécurité globales."""
        return await self.attack_simulator.get_security_metrics()
    
    # ZK-Proofs Resolvers
    
    @strawberry.field
    async def create_zk_statement(
        self,
        input: ZKStatementInput,
    ) -> GraphQLZKStatement:
        """Crée un nouvel énoncé ZK."""
        statement_data = {
            "type": input.type,
            "description": input.description,
            "public_inputs": input.public_inputs,
            "private_inputs": input.private_inputs,
            "constraints": input.constraints,
        }
        
        statement = await self.zk_system.create_statement(statement_data)
        
        return GraphQLZKStatement(
            id=statement.id,
            type=statement.type.value,
            description=statement.description,
            public_inputs=statement.public_inputs,
            private_inputs=statement.private_inputs,
            constraints=statement.constraints,
            created_at=statement.created_at,
        )
    
    @strawberry.field
    async def generate_zk_proof(
        self,
        input: ZKProofInput,
    ) -> GraphQLZKProof:
        """Génère une preuve ZK."""
        proof = await self.zk_system.generate_proof(
            input.statement_id,
            input.witness,
        )
        
        return GraphQLZKProof(
            id=proof.id,
            statement_id=proof.statement_id,
            proof_data=proof.proof_data,
            verification_key=proof.verification_key,
            public_outputs=proof.public_outputs,
            created_at=proof.created_at,
            verified=proof.verified,
            verification_time=proof.verification_time,
        )
    
    @strawberry.field
    async def verify_zk_proof(self, proof_id: str) -> bool:
        """Vérifie une preuve ZK."""
        return await self.zk_system.verify_proof(proof_id)
    
    @strawberry.field
    async def zk_proof(self, id: str) -> Optional[GraphQLZKProof]:
        """Récupère une preuve ZK par son ID."""
        proof = await self.zk_system.get_proof(id)
        
        if not proof:
            return None
        
        return GraphQLZKProof(
            id=proof.id,
            statement_id=proof.statement_id,
            proof_data=proof.proof_data,
            verification_key=proof.verification_key,
            public_outputs=proof.public_outputs,
            created_at=proof.created_at,
            verified=proof.verified,
            verification_time=proof.verification_time,
        )
    
    @strawberry.field
    async def zk_proofs(
        self,
        type: Optional[str] = None,
        verified: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GraphQLZKProof]:
        """Liste les preuves ZK."""
        filter_by = {}
        
        if type:
            filter_by["type"] = type
        
        if verified is not None:
            filter_by["verified"] = verified
        
        proofs = await self.zk_system.list_proofs(filter_by)
        
        graphql_proofs = []
        for proof in proofs[offset:offset + limit]:
            graphql_proofs.append(
                GraphQLZKProof(
                    id=proof.id,
                    statement_id=proof.statement_id,
                    proof_data=proof.proof_data,
                    verification_key=proof.verification_key,
                    public_outputs=proof.public_outputs,
                    created_at=proof.created_at,
                    verified=proof.verified,
                    verification_time=proof.verification_time,
                )
            )
        
        return graphql_proofs
    
    @strawberry.field
    async def zk_system_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du système ZK."""
        return await self.zk_system.get_system_metrics()
    
    # FHE Resolvers
    
    @strawberry.field
    async def generate_fhe_key_pair(
        self,
        input: Optional[FHEKeyPairInput] = None,
    ) -> GraphQLFHEKeyPair:
        """Génère une nouvelle paire de clés FHE."""
        key_size = input.key_size if input else None
        
        key_pair = await self.fhe_system.generate_key_pair(key_size)
        
        return GraphQLFHEKeyPair(
            id=key_pair.id,
            public_key=key_pair.public_key,
            private_key=key_pair.private_key,
            key_size=key_pair.key_size,
            created_at=key_pair.created_at,
            expires_at=key_pair.expires_at,
            metadata=key_pair.metadata,
        )
    
    @strawberry.field
    async def encrypt_data(
        self,
        input: FHECiphertextInput,
    ) -> GraphQLFHECiphertext:
        """Chiffre des données avec FHE."""
        # Convertir les données selon le type
        data = input.data
        
        if input.data_type == "int":
            data = int(data)
        elif input.data_type == "float":
            data = float(data)
        elif input.data_type in ["vector", "matrix"]:
            data = json.loads(data)
        
        ciphertext = await self.fhe_system.encrypt(data, input.key_id)
        
        return GraphQLFHECiphertext(
            id=ciphertext.id,
            key_id=ciphertext.key_id,
            ciphertext=ciphertext.ciphertext,
            data_type=ciphertext.data_type,
            dimensions=ciphertext.dimensions,
            created_at=ciphertext.created_at,
            metadata=ciphertext.metadata,
        )
    
    @strawberry.field
    async def perform_fhe_operation(
        self,
        input: FHEOperationInput,
    ) -> GraphQLFHEOperationResult:
        """Effectue une opération sur des données chiffrées FHE."""
        result = await self.fhe_system.perform_operation(
            input.operation,
            input.ciphertext_ids,
        )
        
        return GraphQLFHEOperationResult(
            id=result.id,
            operation=result.operation.value,
            input_ciphertexts=result.input_ciphertexts,
            output_ciphertext=result.output_ciphertext,
            execution_time_seconds=result.execution_time_seconds,
            created_at=result.created_at,
            verified=result.verified,
        )
    
    @strawberry.field
    async def verify_fhe_operation(self, operation_id: str) -> bool:
        """Vérifie une opération FHE."""
        return await self.fhe_system.verify_operation(operation_id)
    
    @strawberry.field
    async def fhe_key_pair(self, id: str) -> Optional[GraphQLFHEKeyPair]:
        """Récupère une paire de clés FHE par son ID."""
        key_pair = await self.fhe_system.get_key_pair(id)
        
        if not key_pair:
            return None
        
        return GraphQLFHEKeyPair(
            id=key_pair.id,
            public_key=key_pair.public_key,
            private_key=key_pair.private_key,
            key_size=key_pair.key_size,
            created_at=key_pair.created_at,
            expires_at=key_pair.expires_at,
            metadata=key_pair.metadata,
        )
    
    @strawberry.field
    async def fhe_key_pairs(
        self,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GraphQLFHEKeyPair]:
        """Liste les paires de clés FHE disponibles."""
        key_pairs = await self.fhe_system.list_key_pairs(active_only)
        
        graphql_key_pairs = []
        for key_pair in key_pairs[offset:offset + limit]:
            graphql_key_pairs.append(
                GraphQLFHEKeyPair(
                    id=key_pair.id,
                    public_key=key_pair.public_key,
                    private_key=key_pair.private_key,
                    key_size=key_pair.key_size,
                    created_at=key_pair.created_at,
                    expires_at=key_pair.expires_at,
                    metadata=key_pair.metadata,
                )
            )
        
        return graphql_key_pairs
    
    @strawberry.field
    async def fhe_ciphertext(self, id: str) -> Optional[GraphQLFHECiphertext]:
        """Récupère un texte chiffré FHE par son ID."""
        ciphertext = await self.fhe_system.get_ciphertext(id)
        
        if not ciphertext:
            return None
        
        return GraphQLFHECiphertext(
            id=ciphertext.id,
            key_id=ciphertext.key_id,
            ciphertext=ciphertext.ciphertext,
            data_type=ciphertext.data_type,
            dimensions=ciphertext.dimensions,
            created_at=ciphertext.created_at,
            metadata=ciphertext.metadata,
        )
    
    @strawberry.field
    async def fhe_ciphertexts(
        self,
        key_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GraphQLFHECiphertext]:
        """Liste les textes chiffrés FHE."""
        ciphertexts = await self.fhe_system.list_ciphertexts(key_id)
        
        graphql_ciphertexts = []
        for ciphertext in ciphertexts[offset:offset + limit]:
            graphql_ciphertexts.append(
                GraphQLFHECiphertext(
                    id=ciphertext.id,
                    key_id=ciphertext.key_id,
                    ciphertext=ciphertext.ciphertext,
                    data_type=ciphertext.data_type,
                    dimensions=ciphertext.dimensions,
                    created_at=ciphertext.created_at,
                    metadata=ciphertext.metadata,
                )
            )
        
        return graphql_ciphertexts
    
    @strawberry.field
    async def fhe_operation_result(
        self,
        id: str,
    ) -> Optional[GraphQLFHEOperationResult]:
        """Récupère un résultat d'opération FHE par son ID."""
        result = await self.fhe_system.get_operation_result(id)
        
        if not result:
            return None
        
        return GraphQLFHEOperationResult(
            id=result.id,
            operation=result.operation.value,
            input_ciphertexts=result.input_ciphertexts,
            output_ciphertext=result.output_ciphertext,
            execution_time_seconds=result.execution_time_seconds,
            created_at=result.created_at,
            verified=result.verified,
        )
    
    @strawberry.field
    async def fhe_operations(
        self,
        verified_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[GraphQLFHEOperationResult]:
        """Liste les opérations FHE effectuées."""
        operations = await self.fhe_system.list_operations(verified_only)
        
        graphql_operations = []
        for operation in operations[offset:offset + limit]:
            graphql_operations.append(
                GraphQLFHEOperationResult(
                    id=operation.id,
                    operation=operation.operation.value,
                    input_ciphertexts=operation.input_ciphertexts,
                    output_ciphertext=operation.output_ciphertext,
                    execution_time_seconds=operation.execution_time_seconds,
                    created_at=operation.created_at,
                    verified=operation.verified,
                )
            )
        
        return graphql_operations
    
    @strawberry.field
    async def fhe_system_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du système FHE."""
        return await self.fhe_system.get_system_metrics()