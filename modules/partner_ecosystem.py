"""
Partner Ecosystem Integration - Compound, Aave, MakerDAO integrations
Real DeFi protocol integrations with business value filtering
"""

import asyncio
import json
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import logging
from dataclasses import dataclass
from decimal import Decimal

# Import existing Sigui modules
from modules.vision_integration import VisionIntegrationEngine, AutonomousEconomyContext
from modules.identity.agent_did import AgentType, VerificationTier
from modules.blockchain.arc_client import ArcClient
from modules.database.memory import Memory
from modules.policy.policy_brain import PolicyBrain
from modules.threat_intel.threat_registry import ThreatRegistry
from modules.governance.hogonat_dao import HogonatDAO
from modules.treasury import Treasury


@dataclass
class PartnerProtocol:
    """Partner DeFi protocol configuration"""
    name: str
    chain: str
    tvl_usd: float
    min_transaction_value: float  # Minimum value for business relevance
    revenue_share_percentage: float
    integration_status: str
    threat_patterns: List[str]
    agent_categories: List[str]


@dataclass
class BusinessValueFilter:
    """Business value filtering for transactions"""
    min_transaction_value_usd: float = 100.0  # Minimum $100 for real business
    max_processing_cost_ratio: float = 0.1    # Max 10% of transaction value
    required_verification_tier: int = 1      # Silver minimum
    min_reputation_score: float = 600.0      # Minimum reputation


class PartnerEcosystemIntegration:
    """
    Integration with major DeFi protocols focusing on business value
    Filters out low-value transactions that don't generate revenue
    """
    
    def __init__(
        self,
        vision_engine: VisionIntegrationEngine,
        arc_client: ArcClient,
        memory: Memory,
        policy_brain: PolicyBrain,
        threat_registry: ThreatRegistry,
        hogonat_dao: HogonatDAO,
        treasury: Treasury
    ):
        self.vision_engine = vision_engine
        self.arc_client = arc_client
        self.memory = memory
        self.policy_brain = policy_brain
        self.threat_registry = threat_registry
        self.hogonat_dao = hogonat_dao
        self.treasury = treasury
        
        self.logger = logging.getLogger(__name__)
        
        # Business value filter
        self.business_filter = BusinessValueFilter()
        
        # Partner protocols with real TVL and business metrics
        self.partner_protocols = {
            "compound": PartnerProtocol(
                name="Compound Finance",
                chain="ethereum",
                tvl_usd=2.1e9,  # $2.1B TVL
                min_transaction_value=1000.0,  # $1K minimum
                revenue_share_percentage=20.0,
                integration_status="active",
                threat_patterns=["reentrancy", "flash_loan_attack", "oracle_manipulation"],
                agent_categories=["lending_bot", "yield_optimizer", "arbitrageur"]
            ),
            "aave": PartnerProtocol(
                name="Aave Protocol",
                chain="ethereum",
                tvl_usd=6.8e9,  # $6.8B TVL
                min_transaction_value=5000.0,  # $5K minimum
                revenue_share_percentage=25.0,
                integration_status="active",
                threat_patterns=["flash_loan_attack", "liquidation_attack", "governance_attack"],
                agent_categories=["borrowing_agent", "leverage_trader", "yield_farmer"]
            ),
            "makerdao": PartnerProtocol(
                name="MakerDAO",
                chain="ethereum",
                tvl_usd=7.2e9,  # $7.2B TVL (DAI supply)
                min_transaction_value=10000.0,  # $10K minimum
                revenue_share_percentage=30.0,
                integration_status="integration_pending",
                threat_patterns=["oracle_manipulation", "governance_attack", "collateral_attack"],
                agent_categories=["cdp_manager", "stablecoin_arbitrageur", "vault_optimizer"]
            ),
            "uniswap": PartnerProtocol(
                name="Uniswap",
                chain="ethereum",
                tvl_usd=4.5e9,  # $4.5B TVL
                min_transaction_value=2000.0,  # $2K minimum
                revenue_share_percentage=15.0,
                integration_status="active",
                threat_patterns=["sandwich_attack", "mempool_manipulation", "price_manipulation"],
                agent_categories=["amm_lp_bot", "arbitrageur", "mempool_reader"]
            ),
            "synthetix": PartnerProtocol(
                name="Synthetix",
                chain="ethereum",
                tvl_usd=1.8e9,  # $1.8B TVL
                min_transaction_value=3000.0,  # $3K minimum
                revenue_share_percentage=18.0,
                integration_status="active",
                threat_patterns=["oracle_manipulation", "synth_manipulation", "front_running"],
                agent_categories=["synth_trader", "staking_optimizer", "debt_manager"]
            )
        }
        
        # Revenue tracking
        self.revenue_by_protocol: Dict[str, float] = {}
        self.protected_value_by_protocol: Dict[str, float] = {}
        self.business_metrics: Dict[str, Any] = {
            "total_revenue_generated": 0.0,
            "total_value_protected": 0.0,
            "high_value_transactions": 0,
            "low_value_transactions_filtered": 0,
            "average_transaction_value": 0.0,
            "revenue_per_transaction": 0.0
        }
    
    async def evaluate_partner_transaction(
        self,
        protocol_name: str,
        agent_address: str,
        transaction_value: float,
        transaction_data: bytes,
        agent_type: AgentType = AgentType.ORGANIZATION
    ) -> Dict[str, Any]:
        """
        Evaluate transaction for partner protocol with business value filtering
        
        Args:
            protocol_name: Name of partner protocol
            agent_address: Agent blockchain address
            transaction_value: Transaction value in USD
            transaction_data: Transaction data
            agent_type: Type of agent (default: ORGANIZATION for business transactions)
            
        Returns:
            Evaluation result with business metrics
        """
        
        start_time = datetime.now(timezone.utc)
        
        # Get partner protocol
        protocol = self.partner_protocols.get(protocol_name.lower())
        if not protocol:
            return {
                "decision": "BLOCK",
                "reason": f"Unknown protocol: {protocol_name}",
                "business_relevant": False,
                "error": True,
                "processing_time_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            }
        
        # Business value filtering
        business_check = await self._check_business_value(
            transaction_value=transaction_value,
            protocol=protocol,
            agent_address=agent_address
        )
        
        if not business_check["is_business_relevant"]:
            # Log but don't process low-value transactions
            self.business_metrics["low_value_transactions_filtered"] += 1
            self.logger.info(
                f"Filtered low-value transaction: ${transaction_value} from {agent_address} "
                f"for {protocol.name} (min: ${protocol.min_transaction_value})"
            )
            return {
                "decision": "BLOCK",
                "reason": business_check["reason"],
                "business_relevant": False,
                "transaction_value": transaction_value,
                "min_required": protocol.min_transaction_value,
                "processing_time_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            }
        
        # High-value transaction - proceed with full evaluation
        self.logger.info(
            f"Processing high-value transaction: ${transaction_value} from {agent_address} "
            f"for {protocol.name}"
        )
        
        # Use vision integration engine for comprehensive evaluation
        evaluation_result = await self.vision_engine.evaluate_autonomous_transaction(
            agent_address=agent_address,
            destination_address=protocol_name,  # Protocol as destination
            transaction_value=transaction_value,
            transaction_data=transaction_data,
            agent_type=agent_type
        )
        
        # Calculate business impact
        business_result = await self._calculate_business_impact(
            evaluation_result=evaluation_result,
            protocol=protocol,
            transaction_value=transaction_value
        )
        
        # Update business metrics
        await self._update_business_metrics(
            protocol_name=protocol_name,
            transaction_value=transaction_value,
            business_result=business_result,
            evaluation_result=evaluation_result
        )
        
        return {
            **evaluation_result,
            "business_relevant": True,
            "protocol_name": protocol_name,
            "revenue_generated": business_result["revenue_generated"],
            "value_protected": business_result["value_protected"],
            "business_metrics": self.business_metrics,
            "processing_time_ms": (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        }
    
    async def _check_business_value(
        self,
        transaction_value: float,
        protocol: PartnerProtocol,
        agent_address: str
    ) -> Dict[str, Any]:
        """Check if transaction meets business value criteria"""
        
        # Check minimum transaction value
        if transaction_value < protocol.min_transaction_value:
            return {
                "is_business_relevant": False,
                "reason": f"Transaction value ${transaction_value} below minimum ${protocol.min_transaction_value} for {protocol.name}",
                "transaction_value": transaction_value,
                "min_required": protocol.min_transaction_value
            }
        
        # Check processing cost ratio
        processing_cost = 0.001  # $0.001 per evaluation
        cost_ratio = processing_cost / transaction_value
        if cost_ratio > self.business_filter.max_processing_cost_ratio:
            return {
                "is_business_relevant": False,
                "reason": f"Processing cost ratio {cost_ratio:.1%} exceeds maximum {self.business_filter.max_processing_cost_ratio:.1%}",
                "transaction_value": transaction_value,
                "processing_cost": processing_cost,
                "cost_ratio": cost_ratio
            }
        
        # Get agent identity for verification checks
        agent_identity = await self.vision_engine.identity_integration.get_agent_identity(agent_address)
        if not agent_identity:
            return {
                "is_business_relevant": False,
                "reason": "Agent not registered - identity verification required for high-value transactions",
                "transaction_value": transaction_value
            }
        
        # Check verification tier
        if agent_identity.verification_tier < self.business_filter.required_verification_tier:
            return {
                "is_business_relevant": False,
                "reason": f"Agent verification tier {agent_identity.verification_tier} below required {self.business_filter.required_verification_tier}",
                "current_tier": agent_identity.verification_tier,
                "required_tier": self.business_filter.required_verification_tier
            }
        
        # Check reputation score
        reputation_result = await self.vision_engine.identity_integration.evaluate_agent_reputation(agent_address)
        if reputation_result.overall_score < self.business_filter.min_reputation_score:
            return {
                "is_business_relevant": False,
                "reason": f"Agent reputation {reputation_result.overall_score} below minimum {self.business_filter.min_reputation_score}",
                "current_reputation": reputation_result.overall_score,
                "required_reputation": self.business_filter.min_reputation_score
            }
        
        return {
            "is_business_relevant": True,
            "reason": "Transaction meets all business value criteria",
            "agent_verification_tier": agent_identity.verification_tier,
            "agent_reputation": reputation_result.overall_score
        }
    
    async def _calculate_business_impact(
        self,
        evaluation_result: Dict[str, Any],
        protocol: PartnerProtocol,
        transaction_value: float
    ) -> Dict[str, Any]:
        """Calculate business impact metrics"""
        
        decision = evaluation_result.get("decision", "BLOCK")
        confidence = evaluation_result.get("confidence", 0.0)
        
        # Revenue calculation based on decision and protocol
        if decision == "ALLOW":
            # Successful transaction generates revenue share
            revenue_generated = 0.001  # Base $0.001 fee
            if protocol.revenue_share_percentage > 0:
                # Additional revenue share from protocol
                revenue_generated += (transaction_value * protocol.revenue_share_percentage / 10000)  # Basis points
            value_protected = transaction_value  # Full value protected
            
        elif decision == "ESCALATE":
            # Escalated transaction - higher fee for human review
            revenue_generated = 0.003  # $0.003 escalation fee
            value_protected = transaction_value * confidence  # Partial protection
            
        else:  # BLOCK
            # Blocked transaction - revenue from threat prevention
            revenue_generated = 0.001  # Base fee
            # Estimate value saved (would need threat severity for accurate calculation)
            estimated_loss_rate = 0.1  # Assume 10% loss if threat succeeded
            value_protected = transaction_value * estimated_loss_rate * confidence
        
        return {
            "revenue_generated": revenue_generated,
            "value_protected": value_protected,
            "protocol_name": protocol.name,
            "protocol_tvl": protocol.tvl_usd,
            "decision": decision,
            "confidence": confidence,
            "transaction_value": transaction_value
        }
    
    async def _update_business_metrics(
        self,
        protocol_name: str,
        transaction_value: float,
        business_result: Dict[str, Any],
        evaluation_result: Dict[str, Any]
    ) -> None:
        """Update business metrics"""
        
        # Update protocol-specific metrics
        if protocol_name not in self.revenue_by_protocol:
            self.revenue_by_protocol[protocol_name] = 0.0
            self.protected_value_by_protocol[protocol_name] = 0.0
        
        self.revenue_by_protocol[protocol_name] += business_result["revenue_generated"]
        self.protected_value_by_protocol[protocol_name] += business_result["value_protected"]
        
        # Update global metrics
        self.business_metrics["total_revenue_generated"] += business_result["revenue_generated"]
        self.business_metrics["total_value_protected"] += business_result["value_protected"]
        self.business_metrics["high_value_transactions"] += 1
        
        # Calculate averages
        total_transactions = self.business_metrics["high_value_transactions"]
        self.business_metrics["average_transaction_value"] = (
            self.business_metrics["total_value_protected"] / total_transactions
        ) if total_transactions > 0 else 0.0
        
        self.business_metrics["revenue_per_transaction"] = (
            self.business_metrics["total_revenue_generated"] / total_transactions
        ) if total_transactions > 0 else 0.0
        
        self.logger.info(
            f"Business metrics updated - Protocol: {protocol_name}, "
            f"Revenue: ${business_result['revenue_generated']:.4f}, "
            f"Protected: ${business_result['value_protected']:.2f}, "
            f"Total Revenue: ${self.business_metrics['total_revenue_generated']:.4f}"
        )
    
    async def get_partner_revenue_report(self) -> Dict[str, Any]:
        """Generate revenue report by partner protocol"""
        
        return {
            "revenue_by_protocol": self.revenue_by_protocol,
            "protected_value_by_protocol": self.protected_value_by_protocol,
            "business_metrics": self.business_metrics,
            "partner_protocols": {
                name: {
                    "name": protocol.name,
                    "tvl_usd": protocol.tvl_usd,
                    "min_transaction_value": protocol.min_transaction_value,
                    "revenue_share_percentage": protocol.revenue_share_percentage,
                    "integration_status": protocol.integration_status,
                    "current_revenue": self.revenue_by_protocol.get(name, 0.0),
                    "current_protected_value": self.protected_value_by_protocol.get(name, 0.0)
                }
                for name, protocol in self.partner_protocols.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def simulate_business_growth(self, target_tvl: float = 50e9) -> Dict[str, Any]:
        """Simulate business growth to target TVL"""
        
        current_total_tvl = sum(protocol.tvl_usd for protocol in self.partner_protocols.values())
        growth_multiple = target_tvl / current_total_tvl if current_total_tvl > 0 else 1.0
        
        # Project revenue based on TVL growth
        projected_revenue = {}
        projected_protected_value = {}
        
        for protocol_name, protocol in self.partner_protocols.items():
            # Assume 0.1% of TVL generates evaluation revenue
            projected_tvl = protocol.tvl_usd * growth_multiple
            annual_evaluations = projected_tvl * 0.001  # 0.1% of TVL in evaluations
            
            # Revenue projection
            avg_transaction_value = 10000.0  # $10K average
            evaluation_fees = annual_evaluations / avg_transaction_value * 0.001  # $0.001 per evaluation
            revenue_share = annual_evaluations * protocol.revenue_share_percentage / 10000
            
            projected_revenue[protocol_name] = evaluation_fees + revenue_share
            projected_protected_value[protocol_name] = annual_evaluations
        
        return {
            "current_tvl": current_total_tvl,
            "target_tvl": target_tvl,
            "growth_multiple": growth_multiple,
            "projected_revenue_by_protocol": projected_revenue,
            "projected_protected_value_by_protocol": projected_protected_value,
            "total_projected_revenue": sum(projected_revenue.values()),
            "total_projected_protected_value": sum(projected_protected_value.values()),
            "assumptions": {
                "evaluation_fee_per_transaction": 0.001,
                "average_transaction_value": 10000.0,
                "evaluation_rate": 0.001  # 0.1% of TVL
            }
        }


# Integration adapters for specific protocols
class CompoundAdapter:
    """Compound Finance specific integration"""
    
    @staticmethod
    async def evaluate_compound_transaction(
        agent_address: str,
        action: str,  # "supply", "borrow", "withdraw"
        asset: str,   # "USDC", "ETH", etc.
        amount: float,
        partner_integration: PartnerEcosystemIntegration
    ) -> Dict[str, Any]:
        """Evaluate Compound-specific transaction"""
        
        # Compound-specific threat patterns
        compound_threats = {
            "supply": ["reentrancy", "oracle_manipulation"],
            "borrow": ["flash_loan_attack", "collateral_manipulation"],
            "withdraw": ["reentrancy", "accounting_attack"]
        }
        
        # Create transaction data
        transaction_data = json.dumps({
            "protocol": "compound",
            "action": action,
            "asset": asset,
            "amount": amount,
            "threat_patterns": compound_threats.get(action, [])
        }).encode()
        
        return await partner_integration.evaluate_partner_transaction(
            protocol_name="compound",
            agent_address=agent_address,
            transaction_value=amount,
            transaction_data=transaction_data,
            agent_type=AgentType.ORGANIZATION
        )


class AaveAdapter:
    """Aave Protocol specific integration"""
    
    @staticmethod
    async def evaluate_aave_transaction(
        agent_address: str,
        action: str,  # "supply", "borrow", "repay", "withdraw"
        asset: str,
        amount: float,
        partner_integration: PartnerEcosystemIntegration
    ) -> Dict[str, Any]:
        """Evaluate Aave-specific transaction"""
        
        # Aave-specific threat patterns
        aave_threats = {
            "supply": ["flash_loan_attack", "oracle_manipulation"],
            "borrow": ["flash_loan_attack", "collateral_manipulation"],
            "repay": ["accounting_attack", "oracle_manipulation"],
            "withdraw": ["reentrancy", "accounting_attack"]
        }
        
        # Create transaction data
        transaction_data = json.dumps({
            "protocol": "aave",
            "action": action,
            "asset": asset,
            "amount": amount,
            "threat_patterns": aave_threats.get(action, [])
        }).encode()
        
        return await partner_integration.evaluate_partner_transaction(
            protocol_name="aave",
            agent_address=agent_address,
            transaction_value=amount,
            transaction_data=transaction_data,
            agent_type=AgentType.ORGANIZATION
        )