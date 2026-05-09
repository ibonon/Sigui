"""
Agent Identity Integration with existing Sigui pipeline
Integrates the Agent DID system with Sigui's security evaluation pipeline
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import logging
from dataclasses import dataclass

# Import existing Sigui modules
from modules.identity.identity_integration import AgentIdentityIntegration, AgentEvaluationResult
from modules.blockchain.arc_client import ArcClient
from modules.database.memory import Memory
from modules.policy.policy_brain import PolicyBrain
from modules.threat_intel.threat_registry import ThreatRegistry
from modules.governance.hogonat_dao import HogonatDAO


@dataclass
class EnhancedEvaluationRequest:
    """Enhanced evaluation request with identity information"""
    agent_address: str
    destination_address: str
    amount: int
    data: bytes
    agent_did: Optional[str] = None
    reputation_score: Optional[float] = None
    identity_verified: bool = False
    verification_tier: int = 0


@dataclass
class EnhancedEvaluationResponse:
    """Enhanced evaluation response with identity context"""
    decision: str  # ALLOW, BLOCK, ESCALATE
    risk_score: float
    confidence: float
    reason: str
    agent_identity_context: Dict[str, Any]
    reputation_factors: Dict[str, float]
    identity_recommendation: str
    processing_time_ms: int
    timestamp: datetime


class SiguiIdentityPipeline:
    """Enhanced Sigui pipeline with Agent Identity integration"""
    
    def __init__(
        self,
        arc_client: ArcClient,
        memory: Memory,
        policy_brain: PolicyBrain,
        threat_registry: ThreatRegistry,
        hogonat_dao: HogonatDAO,
        chain_id: str = "arc"
    ):
        self.arc_client = arc_client
        self.memory = memory
        self.policy_brain = policy_brain
        self.threat_registry = threat_registry
        self.hogonat_dao = hogonat_dao
        self.chain_id = chain_id
        
        # Initialize identity integration
        self.identity_integration = AgentIdentityIntegration(
            arc_client=arc_client,
            memory=memory,
            policy_brain=policy_brain,
            threat_registry=threat_registry,
            chain_id=chain_id
        )
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
        
        # Performance metrics
        self.evaluation_count = 0
        self.identity_evaluation_count = 0
        self.average_processing_time = 0.0
    
    async def evaluate_transaction_with_identity(
        self,
        agent_address: str,
        destination_address: str,
        amount: int,
        transaction_data: bytes,
        skip_identity: bool = False
    ) -> EnhancedEvaluationResponse:
        """
        Evaluate transaction with enhanced identity verification
        
        Args:
            agent_address: Blockchain address of the agent
            destination_address: Transaction destination
            amount: Transaction amount
            transaction_data: Transaction calldata
            skip_identity: Whether to skip identity evaluation
            
        Returns:
            Enhanced evaluation response
        """
        
        start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Evaluating transaction for agent {agent_address}")
            
            # Step 1: Agent Identity Evaluation
            identity_context = await self._evaluate_agent_identity(
                agent_address=agent_address,
                transaction_data={
                    "from": agent_address,
                    "to": destination_address,
                    "amount": amount,
                    "data": transaction_data.hex()
                },
                skip_identity=skip_identity
            )
            
            # Step 2: Traditional Sigui Evaluation
            base_evaluation = await self._perform_base_evaluation(
                agent_address=agent_address,
                destination_address=destination_address,
                amount=amount,
                transaction_data=transaction_data,
                identity_context=identity_context
            )
            
            # Step 3: Identity-Enhanced Decision Making
            final_decision = await self._make_identity_enhanced_decision(
                base_evaluation=base_evaluation,
                identity_context=identity_context
            )
            
            # Step 4: Update Agent Reputation
            await self._update_agent_reputation_post_evaluation(
                agent_address=agent_address,
                evaluation_result=final_decision,
                transaction_data={
                    "from": agent_address,
                    "to": destination_address,
                    "amount": amount,
                    "data": transaction_data.hex(),
                    "success": final_decision.decision == "ALLOW",
                    "timestamp": start_time.isoformat()
                }
            )
            
            # Calculate processing time
            processing_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Update metrics
            self.evaluation_count += 1
            if not skip_identity:
                self.identity_evaluation_count += 1
            
            # Update average processing time
            self.average_processing_time = (
                (self.average_processing_time * (self.evaluation_count - 1) + processing_time_ms) 
                / self.evaluation_count
            )
            
            self.logger.info(f"Transaction evaluation completed for {agent_address}: {final_decision.decision}")
            
            return EnhancedEvaluationResponse(
                decision=final_decision.decision,
                risk_score=final_decision.risk_score,
                confidence=final_decision.confidence,
                reason=final_decision.reason,
                agent_identity_context=identity_context,
                reputation_factors=final_decision.reputation_factors,
                identity_recommendation=identity_context.get("recommendation", "No identity context"),
                processing_time_ms=processing_time_ms,
                timestamp=start_time
            )
            
        except Exception as e:
            self.logger.error(f"Error in identity-enhanced evaluation: {e}")
            
            # Fallback to basic evaluation
            processing_time_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            return EnhancedEvaluationResponse(
                decision="ESCALATE",
                risk_score=0.8,
                confidence=0.5,
                reason=f"Identity evaluation error: {str(e)}",
                agent_identity_context={"error": str(e)},
                reputation_factors={},
                identity_recommendation="ESCALATE - System error",
                processing_time_ms=processing_time_ms,
                timestamp=start_time
            )
    
    async def register_agent_identity(
        self,
        agent_address: str,
        agent_type: str = "individual",
        verification_tier: int = 0,
        agent_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register a new agent identity in the Sigui system
        
        Args:
            agent_address: Blockchain address of the agent
            agent_type: Type of agent (individual, organization, enterprise)
            verification_tier: Verification tier (0-4)
            agent_metadata: Optional metadata about the agent
            
        Returns:
            Registration result
        """
        
        try:
            self.logger.info(f"Registering agent identity for {agent_address}")
            
            # Register identity through integration module
            result = await self.identity_integration.register_agent_identity(
                agent_address=agent_address,
                agent_type=agent_type,
                verification_tier=verification_tier,
                agent_metadata=agent_metadata
            )
            
            if result.success:
                self.logger.info(f"Successfully registered agent {agent_address}")
                
                # Store registration in memory
                await self.memory.store_agent_registration({
                    "agent_address": agent_address,
                    "agent_did": result.agent_did,
                    "agent_type": agent_type,
                    "verification_tier": verification_tier,
                    "registration_time": result.registration_time.isoformat(),
                    "metadata": agent_metadata
                })
                
                # Update governance metrics
                await self.hogonat_dao.record_agent_registration(
                    agent_address=agent_address,
                    verification_tier=verification_tier
                )
                
                return {
                    "success": True,
                    "agent_did": result.agent_did,
                    "public_key": result.public_key.hex() if result.public_key else None,
                    "private_key": result.private_key.hex() if result.private_key else None,
                    "identity_document": result.identity_document,
                    "registration_time": result.registration_time.isoformat()
                }
            else:
                self.logger.error(f"Failed to register agent {agent_address}: {result.error_message}")
                return {
                    "success": False,
                    "error": result.error_message
                }
                
        except Exception as e:
            self.logger.error(f"Error registering agent identity: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_agent_identity_info(self, agent_address: str) -> Dict[str, Any]:
        """Get comprehensive agent identity information"""
        
        try:
            # Get from memory first
            identity_data = await self.memory.get_agent_identity(agent_address)
            if not identity_data:
                return {"error": "Agent identity not found"}
            
            # Get reputation score
            reputation_data = await self.memory.get_agent_reputation(agent_address)
            
            # Get recent transaction statistics
            recent_transactions = await self.memory.get_agent_transactions(agent_address, limit=100)
            
            # Calculate statistics
            total_tx = len(recent_transactions)
            successful_tx = sum(1 for tx in recent_transactions if tx.get("status") == "success")
            blocked_tx = sum(1 for tx in recent_transactions if tx.get("status") == "blocked")
            
            return {
                "agent_address": agent_address,
                "agent_did": identity_data.get("agent_did"),
                "agent_type": identity_data.get("agent_type", "unknown"),
                "verification_tier": identity_data.get("verification_tier", 0),
                "registration_time": identity_data.get("registration_time"),
                "reputation_score": reputation_data.get("final_score", 0.5) if reputation_data else 0.5,
                "transaction_statistics": {
                    "total": total_tx,
                    "successful": successful_tx,
                    "blocked": blocked_tx,
                    "success_rate": successful_tx / max(total_tx, 1)
                },
                "identity_verified": identity_data.get("verification_tier", 0) > 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting agent identity info: {e}")
            return {"error": str(e)}
    
    async def get_identity_pipeline_statistics(self) -> Dict[str, Any]:
        """Get statistics about the identity pipeline"""
        
        try:
            # Get from memory
            stats = await self.memory.get_identity_statistics()
            
            return {
                "total_agents": stats.get("total_agents", 0),
                "verified_agents": stats.get("verified_agents", 0),
                "identity_evaluations": self.identity_evaluation_count,
                "total_evaluations": self.evaluation_count,
                "average_processing_time_ms": self.average_processing_time,
                "verification_tiers": {
                    "platinum": stats.get("platinum_agents", 0),
                    "gold": stats.get("gold_agents", 0),
                    "silver": stats.get("silver_agents", 0),
                    "bronze": stats.get("bronze_agents", 0),
                    "none": stats.get("unverified_agents", 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error getting identity pipeline statistics: {e}")
            return {"error": str(e)}
    
    # Private helper methods
    
    async def _evaluate_agent_identity(
        self,
        agent_address: str,
        transaction_data: Dict[str, Any],
        skip_identity: bool = False
    ) -> Dict[str, Any]:
        """Evaluate agent identity and reputation"""
        
        if skip_identity:
            return {
                "agent_did": None,
                "reputation_score": None,
                "identity_verified": False,
                "verification_tier": 0,
                "recommendation": "Identity evaluation skipped",
                "risk_factors": {}
            }
        
        # Evaluate agent identity
        identity_result = await self.identity_integration.evaluate_agent_identity(
            agent_address=agent_address,
            transaction_data=transaction_data
        )
        
        return {
            "agent_did": identity_result.agent_did,
            "reputation_score": identity_result.reputation_score.final_score,
            "identity_verified": identity_result.identity_verified,
            "verification_tier": identity_result.reputation_score.verification_score,
            "recommendation": identity_result.recommendation,
            "risk_factors": identity_result.risk_factors,
            "reputation_factors": {
                "identity": identity_result.reputation_score.identity_score,
                "transaction": identity_result.reputation_score.transaction_score,
                "verification": identity_result.reputation_score.verification_score,
                "cross_chain": identity_result.reputation_score.cross_chain_score,
                "threat_intel": identity_result.reputation_score.threat_intelligence_score,
                "insurance": identity_result.reputation_score.insurance_score
            }
        }
    
    async def _perform_base_evaluation(
        self,
        agent_address: str,
        destination_address: str,
        amount: int,
        transaction_data: bytes,
        identity_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform traditional Sigui evaluation"""
        
        # Get existing evaluation from policy brain
        base_decision = await self.policy_brain.evaluate_transaction(
            agent_address=agent_address,
            destination_address=destination_address,
            amount=amount,
            data=transaction_data
        )
        
        return {
            "decision": base_decision.get("decision", "ESCALATE"),
            "risk_score": base_decision.get("risk_score", 0.5),
            "confidence": base_decision.get("confidence", 0.5),
            "reason": base_decision.get("reason", "Base evaluation"),
            "reputation_factors": {}
        }
    
    async def _make_identity_enhanced_decision(
        self,
        base_evaluation: Dict[str, Any],
        identity_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make final decision incorporating identity context"""
        
        base_decision = base_evaluation["decision"]
        base_risk_score = base_evaluation["risk_score"]
        base_confidence = base_evaluation["confidence"]
        
        # Extract identity factors
        reputation_score = identity_context.get("reputation_score", 0.5)
        identity_verified = identity_context.get("identity_verified", False)
        verification_tier = identity_context.get("verification_tier", 0)
        identity_recommendation = identity_context.get("recommendation", "")
        risk_factors = identity_context.get("risk_factors", {})
        reputation_factors = identity_context.get("reputation_factors", {})
        
        # Apply identity-based adjustments
        adjusted_risk_score = base_risk_score
        adjusted_confidence = base_confidence
        final_reason = base_evaluation["reason"]
        
        # High reputation agents get risk reduction
        if reputation_score >= 0.8 and identity_verified:
            adjusted_risk_score *= 0.7  # 30% risk reduction
            adjusted_confidence *= 1.2   # 20% confidence boost
            final_reason += " - High reputation agent"
        
        # Unverified agents get risk increase
        elif not identity_verified:
            adjusted_risk_score *= 1.5   # 50% risk increase
            adjusted_confidence *= 0.8   # 20% confidence reduction
            final_reason += " - Unverified agent"
        
        # Verification tier adjustments
        if verification_tier >= 3:  # Gold or Platinum
            adjusted_risk_score *= 0.8   # 20% risk reduction
            final_reason += " - Verified organization"
        
        # Risk factor adjustments
        if "high_reputation_agent" in risk_factors:
            adjusted_risk_score *= 0.9
        
        if "unverified_agent" in risk_factors:
            adjusted_risk_score *= 1.3
        
        # Final decision logic
        if adjusted_risk_score >= 0.8:
            final_decision = "BLOCK"
        elif adjusted_risk_score >= 0.6:
            final_decision = "ESCALATE"
        else:
            final_decision = "ALLOW"
        
        # Ensure confidence stays within bounds
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        return {
            "decision": final_decision,
            "risk_score": adjusted_risk_score,
            "confidence": adjusted_confidence,
            "reason": final_reason,
            "reputation_factors": reputation_factors
        }
    
    async def _update_agent_reputation_post_evaluation(
        self,
        agent_address: str,
        evaluation_result: Dict[str, Any],
        transaction_data: Dict[str, Any]
    ) -> None:
        """Update agent reputation based on evaluation outcome"""
        
        try:
            # Only update if agent has identity
            identity_data = await self.memory.get_agent_identity(agent_address)
            if not identity_data:
                return
            
            # Determine if transaction was successful
            transaction_success = evaluation_result["decision"] == "ALLOW"
            
            # Update reputation in real-time
            await self.identity_integration.update_agent_reputation(
                agent_address=agent_address,
                new_reputation_score=evaluation_result["confidence"],
                update_reason=f"Transaction evaluation: {evaluation_result['decision']}",
                update_source="sigui_pipeline"
            )
            
            # Store transaction in memory
            transaction_data["status"] = "success" if transaction_success else "blocked"
            transaction_data["evaluation_decision"] = evaluation_result["decision"]
            transaction_data["risk_score"] = evaluation_result["risk_score"]
            transaction_data["confidence"] = evaluation_result["confidence"]
            
            await self.memory.store_transaction(transaction_data)
            
        except Exception as e:
            self.logger.error(f"Error updating agent reputation: {e}")


# Integration with existing gateway
async def setup_identity_enhanced_pipeline(app, arc_client, memory, policy_brain, threat_registry, hogonat_dao):
    """Setup identity-enhanced pipeline in the gateway"""
    
    # Create identity pipeline
    identity_pipeline = SiguiIdentityPipeline(
        arc_client=arc_client,
        memory=memory,
        policy_brain=policy_brain,
        threat_registry=threat_registry,
        hogonat_dao=hogonat_dao
    )
    
    # Add new endpoints
    
    @app.post("/identity/register", tags=["Identity"])
    async def register_agent_identity(request: Dict[str, Any]):
        """Register a new agent identity"""
        
        agent_address = request.get("agent_address")
        agent_type = request.get("agent_type", "individual")
        verification_tier = request.get("verification_tier", 0)
        agent_metadata = request.get("agent_metadata", {})
        
        if not agent_address:
            return {"success": False, "error": "agent_address is required"}
        
        result = await identity_pipeline.register_agent_identity(
            agent_address=agent_address,
            agent_type=agent_type,
            verification_tier=verification_tier,
            agent_metadata=agent_metadata
        )
        
        return result
    
    @app.get("/identity/{agent_address}", tags=["Identity"])
    async def get_agent_identity_info(agent_address: str):
        """Get comprehensive agent identity information"""
        
        return await identity_pipeline.get_agent_identity_info(agent_address)
    
    @app.post("/identity/evaluate", tags=["Identity"])
    async def evaluate_with_identity(request: Dict[str, Any]):
        """Evaluate transaction with identity verification"""
        
        agent_address = request.get("agent_address")
        destination_address = request.get("destination_address")
        amount = request.get("amount", 0)
        data = request.get("data", "0x")
        skip_identity = request.get("skip_identity", False)
        
        if not agent_address or not destination_address:
            return {"success": False, "error": "agent_address and destination_address are required"}
        
        # Convert hex data to bytes
        if data.startswith("0x"):
            data = bytes.fromhex(data[2:])
        else:
            data = data.encode()
        
        result = await identity_pipeline.evaluate_transaction_with_identity(
            agent_address=agent_address,
            destination_address=destination_address,
            amount=amount,
            transaction_data=data,
            skip_identity=skip_identity
        )
        
        # Convert datetime to string for JSON serialization
        response = {
            "decision": result.decision,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "reason": result.reason,
            "agent_identity_context": result.agent_identity_context,
            "reputation_factors": result.reputation_factors,
            "identity_recommendation": result.identity_recommendation,
            "processing_time_ms": result.processing_time_ms,
            "timestamp": result.timestamp.isoformat()
        }
        
        return response
    
    @app.get("/identity/statistics", tags=["Identity"])
    async def get_identity_statistics():
        """Get identity pipeline statistics"""
        
        return await identity_pipeline.get_identity_pipeline_statistics()
    
    # Enhanced demo endpoint with identity information
    @app.get("/demo/enhanced", tags=["Demo"])
    async def enhanced_demo_report():
        """Enhanced demo report with identity statistics"""
        
        # Get base demo data
        base_stats = await memory.get_stats()
        identity_stats = await identity_pipeline.get_identity_pipeline_statistics()
        
        # Combine statistics
        enhanced_report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "base_statistics": base_stats,
            "identity_statistics": identity_stats,
            "pipeline_performance": {
                "average_processing_time_ms": identity_pipeline.average_processing_time,
                "total_evaluations": identity_pipeline.evaluation_count,
                "identity_evaluations": identity_pipeline.identity_evaluation_count
            }
        }
        
        return enhanced_report
    
    return identity_pipeline


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_identity_pipeline():
        """Test the identity-enhanced pipeline"""
        
        # Mock dependencies
        class MockArcClient:
            pass
        
        class MockMemory:
            async def get_agent_identity(self, address):
                return None
            
            async def store_agent_identity(self, address, data):
                pass
            
            async def get_agent_reputation(self, address):
                return None
            
            async def get_agent_transactions(self, address, limit=100):
                return []
            
            async def get_stats(self):
                return {"total_evaluations": 100}
        
        class MockPolicyBrain:
            async def evaluate_transaction(self, **kwargs):
                return {"decision": "ALLOW", "risk_score": 0.3, "confidence": 0.8, "reason": "Mock evaluation"}
        
        class MockThreatRegistry:
            async def get_agent_threat_stats(self, address):
                return {}
        
        class MockHogonatDAO:
            async def record_agent_registration(self, **kwargs):
                pass
        
        # Create pipeline
        pipeline = SiguiIdentityPipeline(
            arc_client=MockArcClient(),
            memory=MockMemory(),
            policy_brain=MockPolicyBrain(),
            threat_registry=MockThreatRegistry(),
            hogonat_dao=MockHogonatDAO()
        )
        
        # Test agent registration
        print("Testing agent registration...")
        registration_result = await pipeline.register_agent_identity(
            agent_address="0x1234567890123456789012345678901234567890",
            agent_type="individual",
            verification_tier=1
        )
        
        print(f"Registration result: {registration_result}")
        
        # Test identity evaluation
        print("\nTesting identity evaluation...")
        evaluation_result = await pipeline.evaluate_transaction_with_identity(
            agent_address="0x1234567890123456789012345678901234567890",
            destination_address="0x0987654321098765432109876543210987654321",
            amount=1000,
            transaction_data=b"test_transaction_data"
        )
        
        print(f"Evaluation decision: {evaluation_result.decision}")
        print(f"Risk score: {evaluation_result.risk_score}")
        print(f"Identity verified: {evaluation_result.agent_identity_context.get('identity_verified', False)}")
        
        # Test statistics
        print("\nTesting statistics...")
        stats = await pipeline.get_identity_pipeline_statistics()
        print(f"Statistics: {stats}")
        
        print("\nIdentity pipeline test completed successfully!")
    
    # Run test
    asyncio.run(test_identity_pipeline())