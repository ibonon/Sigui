"""
Agent Identity Integration - Integration with existing Sigui pipeline
Connects the Agent DID system with Sigui's security evaluation pipeline
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import logging
from dataclasses import dataclass

# Import existing Sigui modules
from modules.identity.agent_did import AgentDIDGenerator, AgentIdentityManager, AgentDID
from modules.identity.reputation_engine import ReputationEngine, ReputationScore
from modules.blockchain.arc_client import ArcClient
from modules.database.memory import Memory
from modules.policy.policy_brain import PolicyBrain
from modules.threat_intel.threat_registry import ThreatRegistry


@dataclass
class AgentEvaluationResult:
    """Result of agent identity and reputation evaluation"""
    agent_did: str
    reputation_score: ReputationScore
    identity_verified: bool
    risk_factors: Dict[str, float]
    recommendation: str
    confidence: float
    evaluation_time: datetime


@dataclass
class IdentityRegistrationResult:
    """Result of agent identity registration"""
    success: bool
    agent_did: Optional[str]
    public_key: Optional[bytes]
    private_key: Optional[bytes]
    identity_document: Optional[Dict[str, Any]]
    error_message: Optional[str]
    registration_time: datetime


class AgentIdentityIntegration:
    """Integrates Agent DID system with existing Sigui pipeline"""
    
    def __init__(
        self,
        arc_client: ArcClient,
        memory: Memory,
        policy_brain: PolicyBrain,
        threat_registry: ThreatRegistry,
        chain_id: str = "arc"
    ):
        self.arc_client = arc_client
        self.memory = memory
        self.policy_brain = policy_brain
        self.threat_registry = threat_registry
        self.chain_id = chain_id
        
        # Initialize DID system
        self.did_generator = AgentDIDGenerator(chain_id=chain_id)
        self.identity_manager = AgentIdentityManager(self.did_generator)
        self.reputation_engine = ReputationEngine(device="cuda" if self._check_gpu_available() else "cpu")
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Cache for active identities
        self._identity_cache: Dict[str, AgentDID] = {}
        self._reputation_cache: Dict[str, ReputationScore] = {}
    
    def _check_gpu_available(self) -> bool:
        """Check if AMD MI300X GPU is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False
    
    async def register_agent_identity(
        self,
        agent_address: str,
        agent_type: str = "individual",
        verification_tier: int = 0,
        agent_metadata: Optional[Dict[str, Any]] = None
    ) -> IdentityRegistrationResult:
        """
        Register a new agent identity in the Sigui system
        
        Args:
            agent_address: Blockchain address of the agent
            agent_type: Type of agent (individual, organization, enterprise)
            verification_tier: Verification tier (0-4)
            agent_metadata: Optional metadata about the agent
            
        Returns:
            IdentityRegistrationResult with registration details
        """
        
        try:
            self.logger.info(f"Registering agent identity for {agent_address}")
            
            # Check if agent already has identity
            existing_identity = await self._get_existing_identity(agent_address)
            if existing_identity:
                return IdentityRegistrationResult(
                    success=False,
                    agent_did=None,
                    public_key=None,
                    private_key=None,
                    identity_document=None,
                    error_message="Agent already has registered identity",
                    registration_time=datetime.now(timezone.utc)
                )
            
            # Create new agent identity
            agent_did = await self.identity_manager.create_agent_identity(
                agent_type=agent_type,
                agent_metadata=agent_metadata,
                store_private_key=True
            )
            
            # Create identity document
            identity_doc = self.identity_manager.get_agent_identity(agent_did.did)
            
            # Register on-chain via smart contract
            registration_result = await self._register_on_chain(
                agent_address=agent_address,
                agent_did=agent_did,
                verification_tier=verification_tier
            )
            
            if not registration_result["success"]:
                return IdentityRegistrationResult(
                    success=False,
                    agent_did=None,
                    public_key=None,
                    private_key=None,
                    identity_document=None,
                    error_message=f"On-chain registration failed: {registration_result['error']}",
                    registration_time=datetime.now(timezone.utc)
                )
            
            # Cache identity
            self._identity_cache[agent_address] = agent_did
            
            # Store identity metadata in memory
            await self._store_identity_metadata(agent_address, agent_did, identity_doc)
            
            # Initialize reputation score
            initial_reputation = await self._calculate_initial_reputation(
                agent_did, verification_tier, agent_metadata
            )
            self._reputation_cache[agent_address] = initial_reputation
            
            self.logger.info(f"Successfully registered agent {agent_address} with DID {agent_did.did}")
            
            return IdentityRegistrationResult(
                success=True,
                agent_did=agent_did.did,
                public_key=agent_did.public_key,
                private_key=agent_did.private_key,
                identity_document={
                    "did": agent_did.did,
                    "public_key": agent_did.public_key.hex(),
                    "created_at": agent_did.created_at.isoformat(),
                    "verification_tier": verification_tier,
                    "agent_type": agent_type
                },
                error_message=None,
                registration_time=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error registering agent identity: {e}")
            return IdentityRegistrationResult(
                success=False,
                agent_did=None,
                public_key=None,
                private_key=None,
                identity_document=None,
                error_message=str(e),
                registration_time=datetime.now(timezone.utc)
            )
    
    async def evaluate_agent_identity(
        self,
        agent_address: str,
        transaction_data: Dict[str, Any],
        current_context: Optional[Dict[str, Any]] = None
    ) -> AgentEvaluationResult:
        """
        Evaluate agent identity and reputation for transaction security
        
        Args:
            agent_address: Blockchain address of the agent
            transaction_data: Transaction being evaluated
            current_context: Optional context information
            
        Returns:
            AgentEvaluationResult with evaluation details
        """
        
        try:
            self.logger.info(f"Evaluating agent identity for {agent_address}")
            
            # Get agent identity
            agent_did = await self._get_agent_identity(agent_address)
            if not agent_did:
                return AgentEvaluationResult(
                    agent_did="unknown",
                    reputation_score=ReputationScore(
                        base_score=0.3,
                        identity_score=0.0,
                        transaction_score=0.3,
                        verification_score=0.0,
                        cross_chain_score=0.3,
                        threat_intelligence_score=0.5,
                        insurance_score=0.0,
                        final_score=0.3,
                        confidence=0.6,
                        factors={},
                        last_updated=datetime.now(timezone.utc)
                    ),
                    identity_verified=False,
                    risk_factors={"identity_unknown": 0.8},
                    recommendation="BLOCK - Unknown agent identity",
                    confidence=0.6,
                    evaluation_time=datetime.now(timezone.utc)
                )
            
            # Get agent transaction history
            transaction_history = await self._get_agent_transaction_history(agent_address)
            
            # Get threat intelligence data
            threat_data = await self._get_agent_threat_data(agent_address)
            
            # Get insurance data
            insurance_data = await self._get_agent_insurance_data(agent_address)
            
            # Compile agent data for reputation calculation
            agent_data = await self._compile_agent_data(
                agent_did=agent_did,
                transaction_history=transaction_history,
                threat_data=threat_data,
                insurance_data=insurance_data,
                current_context=current_context
            )
            
            # Calculate reputation score
            reputation_score = self.reputation_engine.calculate_reputation_score(
                agent_did.did, agent_data
            )
            
            # Calculate risk factors
            risk_factors = await self._calculate_risk_factors(
                agent_did, reputation_score, transaction_data
            )
            
            # Generate recommendation
            recommendation = await self._generate_recommendation(
                reputation_score, risk_factors, transaction_data
            )
            
            # Update reputation in real-time
            await self._update_reputation_realtime(
                agent_address, transaction_data, reputation_score
            )
            
            # Cache results
            self._reputation_cache[agent_address] = reputation_score
            
            self.logger.info(f"Agent evaluation completed for {agent_address}: score={reputation_score.final_score:.3f}")
            
            return AgentEvaluationResult(
                agent_did=agent_did.did,
                reputation_score=reputation_score,
                identity_verified=True,
                risk_factors=risk_factors,
                recommendation=recommendation,
                confidence=reputation_score.confidence,
                evaluation_time=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            self.logger.error(f"Error evaluating agent identity: {e}")
            return AgentEvaluationResult(
                agent_did="error",
                reputation_score=ReputationScore(
                    base_score=0.0,
                    identity_score=0.0,
                    transaction_score=0.0,
                    verification_score=0.0,
                    cross_chain_score=0.0,
                    threat_intelligence_score=0.0,
                    insurance_score=0.0,
                    final_score=0.0,
                    confidence=0.0,
                    factors={},
                    last_updated=datetime.now(timezone.utc)
                ),
                identity_verified=False,
                risk_factors={"evaluation_error": 1.0},
                recommendation="ESCALATE - Evaluation error",
                confidence=0.0,
                evaluation_time=datetime.now(timezone.utc)
            )
    
    async def update_agent_reputation(
        self,
        agent_address: str,
        new_reputation_score: float,
        update_reason: str,
        update_source: str = "automated"
    ) -> bool:
        """
        Update agent reputation score
        
        Args:
            agent_address: Blockchain address of the agent
            new_reputation_score: New reputation score (0-1)
            update_reason: Reason for the update
            update_source: Source of the update
            
        Returns:
            True if update successful, False otherwise
        """
        
        try:
            self.logger.info(f"Updating reputation for {agent_address}: {new_reputation_score:.3f} - {update_reason}")
            
            # Validate inputs
            if not 0.0 <= new_reputation_score <= 1.0:
                raise ValueError("Reputation score must be between 0 and 1")
            
            # Get current reputation
            current_reputation = self._reputation_cache.get(agent_address)
            if not current_reputation:
                # Try to load from memory
                current_reputation = await self._load_reputation_from_memory(agent_address)
            
            if not current_reputation:
                raise ValueError("No existing reputation found for agent")
            
            # Update reputation on-chain
            update_result = await self._update_reputation_on_chain(
                agent_address=agent_address,
                old_score=int(current_reputation.final_score * 1000),
                new_score=int(new_reputation_score * 1000),
                update_reason=update_reason
            )
            
            if not update_result["success"]:
                raise Exception(f"On-chain update failed: {update_result['error']}")
            
            # Update local cache
            current_reputation.final_score = new_reputation_score
            current_reputation.last_updated = datetime.now(timezone.utc)
            self._reputation_cache[agent_address] = current_reputation
            
            # Store update in memory
            await self._store_reputation_update(
                agent_address=agent_address,
                old_score=current_reputation.final_score,
                new_score=new_reputation_score,
                update_reason=update_reason,
                update_source=update_source
            )
            
            self.logger.info(f"Successfully updated reputation for {agent_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating agent reputation: {e}")
            return False
    
    # Private helper methods
    
    async def _get_existing_identity(self, agent_address: str) -> Optional[AgentDID]:
        """Check if agent already has registered identity"""
        
        # Check cache first
        if agent_address in self._identity_cache:
            return self._identity_cache[agent_address]
        
        # Check memory
        identity_data = await self.memory.get_agent_identity(agent_address)
        if identity_data:
            # Reconstruct AgentDID object
            return AgentDID(
                did=identity_data["did"],
                public_key=bytes.fromhex(identity_data["public_key"]),
                private_key=None,  # Don't store private key in memory
                metadata=identity_data.get("metadata"),
                created_at=datetime.fromisoformat(identity_data["created_at"])
            )
        
        return None
    
    async def _get_agent_identity(self, agent_address: str) -> Optional[AgentDID]:
        """Get agent identity from cache or memory"""
        
        # Check cache
        if agent_address in self._identity_cache:
            return self._identity_cache[agent_address]
        
        # Load from memory
        identity_data = await self.memory.get_agent_identity(agent_address)
        if identity_data:
            return AgentDID(
                did=identity_data["did"],
                public_key=bytes.fromhex(identity_data["public_key"]),
                private_key=None,
                metadata=identity_data.get("metadata"),
                created_at=datetime.fromisoformat(identity_data["created_at"])
            )
        
        return None
    
    async def _get_agent_transaction_history(self, agent_address: str) -> List[Dict[str, Any]]:
        """Get agent's transaction history from memory"""
        
        return await self.memory.get_agent_transactions(agent_address, limit=1000)
    
    async def _get_agent_threat_data(self, agent_address: str) -> Dict[str, Any]:
        """Get threat intelligence data for agent"""
        
        threat_stats = await self.threat_registry.get_agent_threat_stats(agent_address)
        return threat_stats or {}
    
    async def _get_agent_insurance_data(self, agent_address: str) -> Dict[str, Any]:
        """Get insurance data for agent"""
        
        # This would query insurance contract
        # For now, return placeholder data
        return {
            "coverage_level": 0,
            "claims_made": 0,
            "claims_successful": 0,
            "premium_payment_consistency": 1.0
        }
    
    async def _compile_agent_data(
        self,
        agent_did: AgentDID,
        transaction_history: List[Dict[str, Any]],
        threat_data: Dict[str, Any],
        insurance_data: Dict[str, Any],
        current_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compile comprehensive agent data for reputation calculation"""
        
        # Calculate transaction statistics
        total_tx = len(transaction_history)
        successful_tx = sum(1 for tx in transaction_history if tx.get("status") == "success")
        failed_tx = total_tx - successful_tx
        
        # Calculate amounts and timing
        amounts = [tx.get("amount", 0) for tx in transaction_history]
        timestamps = [datetime.fromisoformat(tx.get("timestamp", datetime.now(timezone.utc).isoformat())) 
                     for tx in transaction_history]
        
        avg_amount = np.mean(amounts) if amounts else 0
        amount_consistency = 1.0 - (np.std(amounts) / np.mean(amounts)) if amounts and np.mean(amounts) > 0 else 0.5
        
        # Calculate timing consistency
        if len(timestamps) > 1:
            time_diffs = [(timestamps[i+1] - timestamps[i]).total_seconds() / 3600 
                         for i in range(len(timestamps)-1)]
            timing_consistency = 1.0 - (np.std(time_diffs) / np.mean(time_diffs)) if np.mean(time_diffs) > 0 else 0.5
        else:
            timing_consistency = 0.5
        
        # Calculate frequency and velocity
        if timestamps:
            time_span = (max(timestamps) - min(timestamps)).total_seconds() / 86400  # days
            transaction_frequency = total_tx / max(time_span, 1)
            transaction_velocity = total_tx / max(len(set(timestamps)), 1)
        else:
            transaction_frequency = 0
            transaction_velocity = 0
        
        # Identity features
        identity_age = (datetime.now(timezone.utc) - agent_did.created_at).total_seconds() / 86400
        
        # Extract verification tier from DID
        try:
            did_info = self.did_generator.extract_agent_info_from_did(agent_did.did)
            agent_type = did_info.get("agent_type", "unknown")
            is_organization = agent_type in ["organization", "enterprise"]
        except:
            is_organization = False
        
        # Compile comprehensive data
        return {
            # Identity features
            "identity_age_days": identity_age,
            "verification_tier": current_context.get("verification_tier", 0) if current_context else 0,
            "is_organization": is_organization,
            "has_kyc": current_context.get("has_kyc", False) if current_context else False,
            
            # Transaction features
            "total_transactions": total_tx,
            "successful_transactions": successful_tx,
            "failed_transactions": failed_tx,
            "average_transaction_amount": avg_amount,
            "transaction_frequency": transaction_frequency,
            "transaction_velocity": transaction_velocity,
            "amount_consistency": amount_consistency,
            "timing_consistency": timing_consistency,
            
            # Cross-chain features
            "chains_used": current_context.get("chains_used", 1) if current_context else 1,
            "cross_chain_consistency": current_context.get("cross_chain_consistency", 0.8) if current_context else 0.8,
            "bridge_usage_frequency": current_context.get("bridge_usage_frequency", 0) if current_context else 0,
            
            # Threat intelligence features
            "threat_patterns_matched": threat_data.get("patterns_matched", 0),
            "false_positive_rate": threat_data.get("false_positive_rate", 0.0),
            "threat_severity_average": threat_data.get("average_severity", 0.0),
            
            # Insurance features
            "insurance_coverage_level": insurance_data.get("coverage_level", 0),
            "claims_made": insurance_data.get("claims_made", 0),
            "claims_successful": insurance_data.get("claims_successful", 0),
            "premium_payment_consistency": insurance_data.get("premium_payment_consistency", 1.0),
            
            # Network features
            "trusted_connections": current_context.get("trusted_connections", 0) if current_context else 0,
            "suspicious_connections": current_context.get("suspicious_connections", 0) if current_context else 0,
            "network_centrality": current_context.get("network_centrality", 0.5) if current_context else 0.5
        }
    
    async def _calculate_risk_factors(
        self,
        agent_did: AgentDID,
        reputation_score: ReputationScore,
        transaction_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate risk factors based on identity and reputation"""
        
        risk_factors = {}
        
        # Identity risk factors
        if reputation_score.identity_score < 0.3:
            risk_factors["low_identity_score"] = 0.8
        
        if reputation_score.verification_score < 0.2:
            risk_factors["unverified_agent"] = 0.7
        
        # Transaction risk factors
        if reputation_score.transaction_score < 0.4:
            risk_factors["poor_transaction_history"] = 0.6
        
        # Cross-chain risk factors
        if reputation_score.cross_chain_score < 0.3:
            risk_factors["inconsistent_cross_chain_behavior"] = 0.5
        
        # Threat intelligence risk factors
        if reputation_score.threat_intelligence_score < 0.2:
            risk_factors["threat_intelligence_indicators"] = 0.8
        
        # Insurance risk factors
        if reputation_score.insurance_score < 0.1:
            risk_factors["no_insurance_coverage"] = 0.3
        
        # Transaction-specific risk factors
        transaction_amount = transaction_data.get("amount", 0)
        if transaction_amount > 10000:  # Large transaction
            risk_factors["large_transaction_amount"] = min(transaction_amount / 100000, 1.0)
        
        # Overall reputation risk
        if reputation_score.final_score < 0.3:
            risk_factors["low_overall_reputation"] = 0.9
        elif reputation_score.final_score < 0.5:
            risk_factors["moderate_reputation_risk"] = 0.5
        
        return risk_factors
    
    async def _generate_recommendation(
        self,
        reputation_score: ReputationScore,
        risk_factors: Dict[str, float],
        transaction_data: Dict[str, Any]
    ) -> str:
        """Generate security recommendation based on evaluation"""
        
        # Calculate overall risk level
        max_risk = max(risk_factors.values()) if risk_factors else 0.0
        
        # Decision logic
        if reputation_score.final_score >= 0.8 and max_risk < 0.3:
            return "ALLOW - High reputation, low risk"
        elif reputation_score.final_score >= 0.6 and max_risk < 0.5:
            return "ALLOW - Good reputation, acceptable risk"
        elif reputation_score.final_score >= 0.4 and max_risk < 0.7:
            return "ALLOW_WITH_MONITORING - Moderate reputation, manageable risk"
        elif max_risk >= 0.8:
            return "BLOCK - High risk factors detected"
        elif reputation_score.final_score < 0.3:
            return "BLOCK - Low agent reputation"
        else:
            return "ESCALATE - Requires manual review"
    
    async def _update_reputation_realtime(
        self,
        agent_address: str,
        transaction_data: Dict[str, Any],
        current_reputation: ReputationScore
    ) -> None:
        """Update reputation in real-time based on transaction outcome"""
        
        # This would typically be called after transaction confirmation
        # For now, just log the update
        self.logger.info(f"Real-time reputation update for {agent_address}: transaction processed")
    
    async def _register_on_chain(
        self,
        agent_address: str,
        agent_did: AgentDID,
        verification_tier: int
    ) -> Dict[str, Any]:
        """Register agent identity on-chain via smart contract"""
        
        try:
            # This would call the AgentIdentityRegistry smart contract
            # For now, return mock success
            return {
                "success": True,
                "transaction_hash": "0x1234567890abcdef",
                "gas_used": 150000,
                "registration_id": f"reg_{agent_address}_{int(datetime.now(timezone.utc).timestamp())}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_reputation_on_chain(
        self,
        agent_address: str,
        old_score: int,
        new_score: int,
        update_reason: str
    ) -> Dict[str, Any]:
        """Update agent reputation on-chain"""
        
        try:
            # This would call the AgentIdentityRegistry smart contract
            # For now, return mock success
            return {
                "success": True,
                "transaction_hash": "0xabcdef1234567890",
                "gas_used": 75000
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _store_identity_metadata(
        self,
        agent_address: str,
        agent_did: AgentDID,
        identity_doc: Dict[str, Any]
    ) -> None:
        """Store identity metadata in memory"""
        
        identity_data = {
            "agent_address": agent_address,
            "did": agent_did.did,
            "public_key": agent_did.public_key.hex(),
            "created_at": agent_did.created_at.isoformat(),
            "metadata": agent_did.metadata,
            "identity_document": identity_doc
        }
        
        await self.memory.store_agent_identity(agent_address, identity_data)
    
    async def _store_reputation_update(
        self,
        agent_address: str,
        old_score: float,
        new_score: float,
        update_reason: str,
        update_source: str
    ) -> None:
        """Store reputation update in memory"""
        
        update_data = {
            "agent_address": agent_address,
            "old_score": old_score,
            "new_score": new_score,
            "update_reason": update_reason,
            "update_source": update_source,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.memory.store_reputation_update(agent_address, update_data)
    
    async def _load_reputation_from_memory(self, agent_address: str) -> Optional[ReputationScore]:
        """Load reputation score from memory"""
        
        reputation_data = await self.memory.get_agent_reputation(agent_address)
        if reputation_data:
            return ReputationScore(
                base_score=reputation_data.get("base_score", 0.5),
                identity_score=reputation_data.get("identity_score", 0.5),
                transaction_score=reputation_data.get("transaction_score", 0.5),
                verification_score=reputation_data.get("verification_score", 0.5),
                cross_chain_score=reputation_data.get("cross_chain_score", 0.5),
                threat_intelligence_score=reputation_data.get("threat_intelligence_score", 0.5),
                insurance_score=reputation_data.get("insurance_score", 0.5),
                final_score=reputation_data.get("final_score", 0.5),
                confidence=reputation_data.get("confidence", 0.8),
                factors=reputation_data.get("factors", {}),
                last_updated=datetime.fromisoformat(reputation_data["last_updated"])
            )
        
        return None


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_identity_integration():
        """Test the identity integration system"""
        
        # Mock dependencies
        class MockArcClient:
            pass
        
        class MockMemory:
            async def get_agent_identity(self, address):
                return None
            
            async def store_agent_identity(self, address, data):
                pass
            
            async def store_reputation_update(self, address, data):
                pass
            
            async def get_agent_transactions(self, address, limit=1000):
                return []
            
            async def get_agent_reputation(self, address):
                return None
        
        class MockPolicyBrain:
            pass
        
        class MockThreatRegistry:
            async def get_agent_threat_stats(self, address):
                return {}
        
        # Create integration instance
        integration = AgentIdentityIntegration(
            arc_client=MockArcClient(),
            memory=MockMemory(),
            policy_brain=MockPolicyBrain(),
            threat_registry=MockThreatRegistry()
        )
        
        # Test agent registration
        print("Testing agent registration...")
        registration_result = await integration.register_agent_identity(
            agent_address="0x1234567890123456789012345678901234567890",
            agent_type="individual",
            verification_tier=1,
            agent_metadata={
                "name": "Test Trading Agent",
                "capabilities": ["defi", "arbitrage"],
                "service_endpoint": "https://api.test-agent.com"
            }
        )
        
        print(f"Registration Success: {registration_result.success}")
        if registration_result.success:
            print(f"Agent DID: {registration_result.agent_did}")
            print(f"Public Key: {registration_result.public_key.hex()[:20]}...")
        else:
            print(f"Error: {registration_result.error_message}")
        
        # Test agent evaluation
        print("\nTesting agent evaluation...")
        evaluation_result = await integration.evaluate_agent_identity(
            agent_address="0x1234567890123456789012345678901234567890",
            transaction_data={
                "from": "0x1234567890123456789012345678901234567890",
                "to": "0x0987654321098765432109876543210987654321",
                "amount": 1000,
                "data": "0x",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        print(f"Evaluation Result:")
        print(f"  Agent DID: {evaluation_result.agent_did}")
        print(f"  Identity Verified: {evaluation_result.identity_verified}")
        print(f"  Reputation Score: {evaluation_result.reputation_score.final_score:.3f}")
        print(f"  Confidence: {evaluation_result.confidence:.3f}")
        print(f"  Recommendation: {evaluation_result.recommendation}")
        print(f"  Risk Factors: {evaluation_result.risk_factors}")
        
        print("\nAgent Identity Integration test completed successfully!")
    
    # Run test
    asyncio.run(test_identity_integration())