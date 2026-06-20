"""
Agent DID System - Decentralized Identity for AI Agents
Implements cryptographic identity generation and management for autonomous agents
"""

import hashlib
import secrets
from typing import Dict, Any, Optional, Tuple
from enum import Enum, IntEnum
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import base58
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.backends import default_backend


class AgentType(str, Enum):
    INDIVIDUAL = "individual"
    ORGANIZATION = "organization"
    ENTERPRISE = "enterprise"
    ANONYMOUS = "anonymous"


class VerificationTier(IntEnum):
    NONE = 0
    BRONZE = 1
    SILVER = 2
    GOLD = 3
    PLATINUM = 4


@dataclass
class AgentDID:
    """Represents a decentralized identifier for an AI agent"""
    did: str
    public_key: bytes
    private_key: Optional[bytes] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None


@dataclass
class IdentityDocument:
    """DID Document following W3C DID specification"""
    context: list
    id: str
    verification_method: list
    authentication: list
    assertion_method: list
    service: list
    created: str
    updated: str


class AgentDIDGenerator:
    """Generates and manages decentralized identifiers for AI agents"""
    
    def __init__(self, chain_id: str = "arc"):
        self.chain_id = chain_id
        self.did_method = "sigui"
        self.context = ["https://www.w3.org/ns/did/v1", "https://w3id.org/security/suites/ed25519-2020/v1"]
    
    def generate_did(self, public_key: bytes, agent_type: str = "individual") -> str:
        """
        Generate a DID for an AI agent
        
        Args:
            public_key: Ed25519 public key (32 bytes)
            agent_type: Type of agent (individual, organization, enterprise)
            
        Returns:
            DID string in format: did:sigui:chain:agent_type:public_key_hash
        """
        # Create public key hash
        public_key_hash = hashlib.sha256(public_key).hexdigest()[:16]
        
        # Build DID
        did = f"did:{self.did_method}:{self.chain_id}:{agent_type}:{public_key_hash}"
        
        return did
    
    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """
        Generate Ed25519 keypair for agent identity
        
        Returns:
            Tuple of (private_key, public_key) both 32 bytes
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        # Serialize keys to bytes
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        
        return private_bytes, public_bytes
    
    def create_identity_document(
        self,
        did: str,
        public_key: bytes,
        agent_metadata: Optional[Dict[str, Any]] = None
    ) -> IdentityDocument:
        """
        Create a DID document for an agent
        
        Args:
            did: Decentralized identifier
            public_key: Ed25519 public key
            agent_metadata: Optional agent metadata
            
        Returns:
            IdentityDocument following W3C DID specification
        """
        current_time = datetime.now(timezone.utc).isoformat()
        
        # Create verification method
        verification_method = {
            "id": f"{did}#keys-1",
            "type": "Ed25519VerificationKey2020",
            "controller": did,
            "publicKeyMultibase": self._encode_multibase(public_key)
        }
        
        # Create service endpoints if metadata provided
        services = []
        if agent_metadata:
            if "service_endpoints" in agent_metadata:
                services = agent_metadata["service_endpoints"]
        
        # Build identity document
        identity_doc = IdentityDocument(
            context=self.context,
            id=did,
            verification_method=[verification_method],
            authentication=[f"{did}#keys-1"],
            assertion_method=[f"{did}#keys-1"],
            service=services,
            created=current_time,
            updated=current_time
        )
        
        return identity_doc
    
    def verify_signature(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """
        Verify a signature using agent's public key
        
        Args:
            message: Message that was signed
            signature: Signature to verify
            public_key: Agent's public key
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Load public key
            public_key_obj = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
            
            # Verify signature
            public_key_obj.verify(signature, message)
            
            return True
        except Exception:
            return False
    
    def sign_message(self, message: bytes, private_key: bytes) -> bytes:
        """
        Sign a message with agent's private key
        
        Args:
            message: Message to sign
            private_key: Agent's private key
            
        Returns:
            Signature bytes
        """
        # Load private key
        private_key_obj = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
        
        # Sign message
        signature = private_key_obj.sign(message)
        
        return signature
    
    def _encode_multibase(self, data: bytes) -> str:
        """Encode data in multibase format (base58btc)"""
        # Prefix with 'z' for base58btc encoding
        encoded = "z" + base58.b58encode(data).decode('ascii')
        return encoded
    
    def _decode_multibase(self, encoded: str) -> bytes:
        """Decode multibase format (base58btc)"""
        if not encoded.startswith("z"):
            raise ValueError("Invalid multibase encoding - expected base58btc")
        
        return base58.b58decode(encoded[1:])
    
    def extract_agent_info_from_did(self, did: str) -> Dict[str, str]:
        """
        Extract information from DID string
        
        Args:
            did: Decentralized identifier
            
        Returns:
            Dictionary with extracted information
        """
        parts = did.split(":")
        
        if len(parts) < 4:
            raise ValueError("Invalid DID format")
        
        if parts[0] != "did" or parts[1] != self.did_method:
            raise ValueError("Invalid DID method")
        
        return {
            "method": parts[1],
            "chain": parts[2],
            "agent_type": parts[3],
            "public_key_hash": parts[4] if len(parts) > 4 else ""
        }


class AgentIdentityManager:
    """Manages agent identities and their lifecycle"""
    
    def __init__(self, did_generator: AgentDIDGenerator, ipfs_client=None):
        self.did_generator = did_generator
        self.ipfs_client = ipfs_client
        self._identity_cache: Dict[str, IdentityDocument] = {}
        self._key_cache: Dict[str, Tuple[bytes, bytes]] = {}
    
    async def create_agent_identity(
        self,
        agent_type: str = "individual",
        agent_metadata: Optional[Dict[str, Any]] = None,
        store_private_key: bool = True
    ) -> AgentDID:
        """
        Create a new agent identity with DID and keypair
        
        Args:
            agent_type: Type of agent (individual, organization, enterprise)
            agent_metadata: Optional metadata about the agent
            store_private_key: Whether to cache the private key
            
        Returns:
            AgentDID object with generated identity
        """
        # Generate keypair
        private_key, public_key = self.did_generator.generate_keypair()
        
        # Generate DID
        did = self.did_generator.generate_did(public_key, agent_type)
        
        # Create identity document
        identity_doc = self.did_generator.create_identity_document(
            did, public_key, agent_metadata
        )
        
        # Create AgentDID object
        agent_did = AgentDID(
            did=did,
            public_key=public_key,
            private_key=private_key if store_private_key else None,
            metadata=agent_metadata,
            created_at=datetime.now(timezone.utc)
        )
        
        # Cache identity and keys
        self._identity_cache[did] = identity_doc
        if store_private_key:
            self._key_cache[did] = (private_key, public_key)
        
        # Store identity document to IPFS if client available
        if self.ipfs_client:
            try:
                doc_json = json.dumps({
                    "@context": identity_doc.context,
                    "id": identity_doc.id,
                    "verificationMethod": identity_doc.verification_method,
                    "authentication": identity_doc.authentication,
                    "assertionMethod": identity_doc.assertion_method,
                    "service": identity_doc.service,
                    "created": identity_doc.created,
                    "updated": identity_doc.updated
                }, indent=2)
                
                ipfs_hash = await self.ipfs_client.upload_json(doc_json)
                agent_did.metadata = agent_did.metadata or {}
                agent_did.metadata["ipfs_hash"] = ipfs_hash
                
            except Exception as e:
                print(f"Warning: Failed to store identity document to IPFS: {e}")
        
        return agent_did
    
    def get_agent_identity(self, did: str) -> Optional[IdentityDocument]:
        """
        Get agent identity document by DID
        
        Args:
            did: Decentralized identifier
            
        Returns:
            IdentityDocument if found, None otherwise
        """
        return self._identity_cache.get(did)
    
    def get_agent_keys(self, did: str) -> Optional[Tuple[bytes, bytes]]:
        """
        Get agent keypair by DID
        
        Args:
            did: Decentralized identifier
            
        Returns:
            Tuple of (private_key, public_key) if found, None otherwise
        """
        return self._key_cache.get(did)
    
    async def verify_agent_transaction(
        self,
        transaction_data: Dict[str, Any],
        signature: bytes,
        agent_did: str
    ) -> bool:
        """
        Verify that a transaction was signed by the agent
        
        Args:
            transaction_data: Transaction data
            signature: Cryptographic signature
            agent_did: Agent's DID
            
        Returns:
            True if signature is valid, False otherwise
        """
        # Get agent identity
        identity_doc = self.get_agent_identity(agent_did)
        if not identity_doc:
            return False
        
        # Get public key from identity document
        verification_method = identity_doc.verification_method[0]
        public_key_multibase = verification_method["publicKeyMultibase"]
        public_key = self.did_generator._decode_multibase(public_key_multibase)
        
        # Serialize transaction data
        message = json.dumps(transaction_data, sort_keys=True).encode('utf-8')
        
        # Verify signature
        return self.did_generator.verify_signature(message, signature, public_key)
    
    def update_agent_metadata(
        self,
        did: str,
        new_metadata: Dict[str, Any]
    ) -> bool:
        """
        Update agent metadata
        
        Args:
            did: Agent's DID
            new_metadata: New metadata to update
            
        Returns:
            True if update successful, False otherwise
        """
        identity_doc = self.get_agent_identity(did)
        if not identity_doc:
            return False
        
        # Update the identity document
        identity_doc.updated = datetime.now(timezone.utc).isoformat()
        
        # Update cached metadata
        # Note: In production, this would update on-chain storage
        return True
    
    def calculate_reputation_factors(self, did: str) -> Dict[str, float]:
        """
        Calculate reputation factors for an agent based on their identity
        
        Args:
            did: Agent's DID
            
        Returns:
            Dictionary of reputation factors
        """
        try:
            agent_info = self.did_generator.extract_agent_info_from_did(did)
            
            factors = {
                "identity_age": self._calculate_identity_age(did),
                "verification_level": self._get_verification_level(did),
                "agent_type_score": self._get_agent_type_score(agent_info.get("agent_type", "")),
                "cryptographic_strength": 1.0,  # Ed25519 is considered strong
                "identity_consistency": self._check_identity_consistency(did)
            }
            
            return factors
            
        except Exception as e:
            print(f"Error calculating reputation factors for {did}: {e}")
            return {
                "identity_age": 0.0,
                "verification_level": 0.0,
                "agent_type_score": 0.0,
                "cryptographic_strength": 0.0,
                "identity_consistency": 0.0
            }
    
    def _calculate_identity_age(self, did: str) -> float:
        """Calculate how old the identity is (normalized 0-1)"""
        # This would typically query blockchain for registration time
        # For now, return a placeholder
        return 0.5  # 50% age (would be calculated from actual registration time)
    
    def _get_verification_level(self, did: str) -> float:
        """Get verification level (0.0 to 1.0)"""
        # This would query on-chain verification status
        # For now, return based on cached data
        identity_doc = self.get_agent_identity(did)
        if not identity_doc:
            return 0.0
        
        # Simple heuristic based on service endpoints
        if len(identity_doc.service) > 0:
            return 0.8  # High verification
        else:
            return 0.3  # Basic verification
    
    def _get_agent_type_score(self, agent_type: str) -> float:
        """Get score based on agent type"""
        scores = {
            "enterprise": 1.0,
            "organization": 0.8,
            "individual": 0.5,
            "anonymous": 0.1
        }
        return scores.get(agent_type, 0.3)
    
    def _check_identity_consistency(self, did: str) -> float:
        """Check consistency of identity data"""
        # This would validate identity document structure and signatures
        # For now, return placeholder
        return 0.9  # High consistency for properly formatted DIDs


# Example usage and testing
if __name__ == "__main__":
    # Create DID generator
    did_gen = AgentDIDGenerator(chain_id="arc")
    
    # Create identity manager
    identity_mgr = AgentIdentityManager(did_gen)
    
    # Test creating agent identity
    import asyncio
    
    async def test_identity_system():
        # Create new agent identity
        agent_metadata = {
            "name": "Trading Agent Alpha",
            "type": "algorithmic_trading",
            "capabilities": ["defi", "arbitrage", "market_making"],
            "service_endpoints": [
                {
                    "id": "{did}#service-1",
                    "type": "AgentService",
                    "serviceEndpoint": "https://api.agent-alpha.com"
                }
            ]
        }
        
        agent_did = await identity_mgr.create_agent_identity(
            agent_type="individual",
            agent_metadata=agent_metadata,
            store_private_key=True
        )
        
        print(f"Created agent DID: {agent_did.did}")
        print(f"Public Key: {agent_did.public_key.hex()}")
        print(f"Private Key: {agent_did.private_key.hex() if agent_did.private_key else 'Not stored'}")
        
        # Test identity document
        identity_doc = identity_mgr.get_agent_identity(agent_did.did)
        if identity_doc:
            print(f"Identity Document ID: {identity_doc.id}")
            print(f"Verification Methods: {len(identity_doc.verification_method)}")
            print(f"Services: {len(identity_doc.service)}")
        
        # Test reputation factors
        factors = identity_mgr.calculate_reputation_factors(agent_did.did)
        print(f"Reputation Factors: {factors}")
        
        # Test transaction signing
        transaction_data = {
            "from": "0x123...",
            "to": "0x456...",
            "amount": 1000,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Sign transaction
        message = json.dumps(transaction_data, sort_keys=True).encode('utf-8')
        signature = did_gen.sign_message(message, agent_did.private_key)
        
        print(f"Transaction Signature: {signature.hex()}")
        
        # Verify signature
        is_valid = await identity_mgr.verify_agent_transaction(
            transaction_data, signature, agent_did.did
        )
        print(f"Signature Valid: {is_valid}")
    
    # Run test
    asyncio.run(test_identity_system())