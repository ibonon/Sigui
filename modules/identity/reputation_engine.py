"""
Agent Reputation Engine - AI-powered reputation scoring for autonomous agents
Optimized for AMD MI300X GPUs using PyTorch
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import asyncio
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import IsolationForest
import joblib


@dataclass
class ReputationScore:
    """Complete reputation score with factors"""
    base_score: float
    identity_score: float
    transaction_score: float
    verification_score: float
    cross_chain_score: float
    threat_intelligence_score: float
    insurance_score: float
    final_score: float
    confidence: float
    factors: Dict[str, float]
    last_updated: datetime


@dataclass
class AgentFeatures:
    """Feature vector for reputation calculation"""
    # Identity features
    identity_age_days: float
    verification_tier: int
    is_organization: bool
    has_kyc: bool
    
    # Transaction features
    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    average_transaction_amount: float
    transaction_frequency: float
    transaction_velocity: float
    amount_consistency: float
    timing_consistency: float
    
    # Cross-chain features
    chains_used: int
    cross_chain_consistency: float
    bridge_usage_frequency: float
    
    # Threat intelligence features
    threat_patterns_matched: int
    false_positive_rate: float
    threat_severity_average: float
    
    # Insurance features
    insurance_coverage_level: int
    claims_made: int
    claims_successful: int
    premium_payment_consistency: float
    
    # Network features
    trusted_connections: int
    suspicious_connections: int
    network_centrality: float


class ReputationScoringModel(nn.Module):
    """PyTorch neural network for reputation scoring - optimized for AMD MI300X"""
    
    def __init__(self, input_dim: int = 128, hidden_dim: int = 256, dropout_rate: float = 0.2):
        super().__init__()
        
        # Feature extraction layers
        self.feature_extractor = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.BatchNorm1d(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.BatchNorm1d(hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim // 2, hidden_dim // 4),
            nn.BatchNorm1d(hidden_dim // 4),
            nn.ReLU(),
            nn.Dropout(dropout_rate),
            
            nn.Linear(hidden_dim // 4, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(dropout_rate)
        )
        
        # Individual scoring heads
        self.identity_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.transaction_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.verification_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.cross_chain_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.threat_intel_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        self.insurance_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
        
        # Final aggregation head
        self.final_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        
        # Confidence estimation
        self.confidence_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """Forward pass through the network"""
        # Ensure tensor is on GPU (AMD MI300X)
        if torch.cuda.is_available() and not x.is_cuda:
            x = x.to('cuda')
        
        # Extract features
        features = self.feature_extractor(x)
        
        # Calculate individual scores
        identity_score = self.identity_head(features)
        transaction_score = self.transaction_head(features)
        verification_score = self.verification_head(features)
        cross_chain_score = self.cross_chain_head(features)
        threat_intel_score = self.threat_intel_head(features)
        insurance_score = self.insurance_head(features)
        
        # Calculate final score
        final_score = self.final_head(features)
        
        # Calculate confidence
        confidence = self.confidence_head(features)
        
        return {
            "identity_score": identity_score,
            "transaction_score": transaction_score,
            "verification_score": verification_score,
            "cross_chain_score": cross_chain_score,
            "threat_intel_score": threat_intel_score,
            "insurance_score": insurance_score,
            "final_score": final_score,
            "confidence": confidence,
            "features": features
        }


class AgentReputationDataset(Dataset):
    """Dataset for training reputation scoring model"""
    
    def __init__(self, features: np.ndarray, labels: np.ndarray):
        self.features = torch.FloatTensor(features)
        self.labels = torch.FloatTensor(labels)
    
    def __len__(self):
        return len(self.features)
    
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx]


class ReputationEngine:
    """Main reputation engine with AMD MI300X optimization"""
    
    def __init__(self, model_path: Optional[str] = None, device: str = "cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = None
        self.scalers = {}
        self.feature_importance = {}
        self.anomaly_detector = None
        
        # Feature weights for different reputation factors
        self.feature_weights = {
            "identity": 0.25,      # Identity verification and age
            "transaction": 0.30,   # Transaction patterns and behavior
            "verification": 0.20, # Verification tier and KYC status
            "cross_chain": 0.10, # Cross-chain activity consistency
            "threat_intel": 0.10, # Threat intelligence indicators
            "insurance": 0.05    # Insurance history and claims
        }
        
        # Load model if path provided
        if model_path:
            self.load_model(model_path)
        else:
            self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the reputation scoring model"""
        self.model = ReputationScoringModel(input_dim=128, hidden_dim=256)
        
        # Move to GPU if available
        if self.device == "cuda":
            self.model = self.model.to('cuda')
            print(f"Model initialized on AMD MI300X GPU")
        else:
            print(f"Model initialized on CPU")
    
    def extract_features(self, agent_data: Dict[str, Any]) -> np.ndarray:
        """Extract feature vector from agent data"""
        
        features = []
        
        # Identity features
        features.extend([
            agent_data.get("identity_age_days", 0) / 365.0,  # Normalized age
            agent_data.get("verification_tier", 0) / 4.0,   # Normalized tier
            1.0 if agent_data.get("is_organization", False) else 0.0,
            1.0 if agent_data.get("has_kyc", False) else 0.0
        ])
        
        # Transaction features
        total_tx = agent_data.get("total_transactions", 0)
        successful_tx = agent_data.get("successful_transactions", 0)
        failed_tx = agent_data.get("failed_transactions", 0)
        
        success_rate = successful_tx / max(total_tx, 1)
        failure_rate = failed_tx / max(total_tx, 1)
        
        features.extend([
            np.log1p(total_tx),  # Log scale for transaction count
            success_rate,
            failure_rate,
            agent_data.get("average_transaction_amount", 0) / 10000.0,  # Normalized amount
            agent_data.get("transaction_frequency", 0) / 100.0,         # Normalized frequency
            agent_data.get("transaction_velocity", 0) / 50.0,          # Normalized velocity
            agent_data.get("amount_consistency", 0.5),                     # 0-1 consistency
            agent_data.get("timing_consistency", 0.5)                      # 0-1 consistency
        ])
        
        # Cross-chain features
        features.extend([
            agent_data.get("chains_used", 0) / 10.0,                      # Normalized chains
            agent_data.get("cross_chain_consistency", 0.5),               # 0-1 consistency
            agent_data.get("bridge_usage_frequency", 0) / 10.0             # Normalized bridge usage
        ])
        
        # Threat intelligence features
        features.extend([
            agent_data.get("threat_patterns_matched", 0) / 10.0,          # Normalized patterns
            agent_data.get("false_positive_rate", 0.0),                   # 0-1 rate
            agent_data.get("threat_severity_average", 0) / 10.0           # Normalized severity
        ])
        
        # Insurance features
        features.extend([
            agent_data.get("insurance_coverage_level", 0) / 4.0,        # Normalized coverage
            agent_data.get("claims_made", 0) / 5.0,                        # Normalized claims
            agent_data.get("claims_successful", 0) / max(agent_data.get("claims_made", 1), 1),
            agent_data.get("premium_payment_consistency", 0.5)             # 0-1 consistency
        ])
        
        # Network features
        features.extend([
            agent_data.get("trusted_connections", 0) / 100.0,            # Normalized connections
            agent_data.get("suspicious_connections", 0) / 10.0,             # Normalized suspicious
            agent_data.get("network_centrality", 0.5)                      # 0-1 centrality
        ])
        
        # Pad to 128 features if necessary
        while len(features) < 128:
            features.append(0.0)
        
        return np.array(features[:128], dtype=np.float32)
    
    def calculate_reputation_score(self, agent_did: str, agent_data: Dict[str, Any]) -> ReputationScore:
        """Calculate comprehensive reputation score for an agent"""
        
        try:
            # Extract features
            features = self.extract_features(agent_data)
            
            # Scale features
            features_scaled = self._scale_features(features)
            
            # Convert to tensor
            features_tensor = torch.FloatTensor(features_scaled).unsqueeze(0)
            
            # Move to GPU if available
            if self.device == "cuda":
                features_tensor = features_tensor.to('cuda')
            
            # Get model predictions
            with torch.no_grad():
                predictions = self.model(features_tensor)
            
            # Extract individual scores
            identity_score = predictions["identity_score"].item()
            transaction_score = predictions["transaction_score"].item()
            verification_score = predictions["verification_score"].item()
            cross_chain_score = predictions["cross_chain_score"].item()
            threat_intel_score = predictions["threat_intel_score"].item()
            insurance_score = predictions["insurance_score"].item()
            final_score = predictions["final_score"].item()
            confidence = predictions["confidence"].item()
            
            # Apply feature weights to create weighted final score
            weighted_score = (
                identity_score * self.feature_weights["identity"] +
                transaction_score * self.feature_weights["transaction"] +
                verification_score * self.feature_weights["verification"] +
                cross_chain_score * self.feature_weights["cross_chain"] +
                threat_intel_score * self.feature_weights["threat_intel"] +
                insurance_score * self.feature_weights["insurance"]
            )
            
            # Detect anomalies
            anomaly_score = self._detect_anomalies(features_scaled)
            
            # Adjust score based on anomalies
            if anomaly_score > 0.7:  # High anomaly score
                weighted_score *= 0.5  # Reduce reputation significantly
                confidence *= 0.7      # Reduce confidence
            
            # Ensure score is between 0 and 1
            final_weighted_score = max(0.0, min(1.0, weighted_score))
            
            return ReputationScore(
                base_score=final_score,
                identity_score=identity_score,
                transaction_score=transaction_score,
                verification_score=verification_score,
                cross_chain_score=cross_chain_score,
                threat_intelligence_score=threat_intel_score,
                insurance_score=insurance_score,
                final_score=final_weighted_score,
                confidence=confidence,
                factors=self.feature_weights,
                last_updated=datetime.now(timezone.utc)
            )
            
        except Exception as e:
            print(f"Error calculating reputation for {agent_did}: {e}")
            # Return neutral score with low confidence on error
            return ReputationScore(
                base_score=0.5,
                identity_score=0.5,
                transaction_score=0.5,
                verification_score=0.5,
                cross_chain_score=0.5,
                threat_intelligence_score=0.5,
                insurance_score=0.5,
                final_score=0.5,
                confidence=0.1,
                factors=self.feature_weights,
                last_updated=datetime.now(timezone.utc)
            )
    
    def _scale_features(self, features: np.ndarray) -> np.ndarray:
        """Scale features using trained scalers"""
        
        if hasattr(self, 'feature_scaler'):
            return self.feature_scaler.transform(features.reshape(1, -1)).flatten()
        else:
            # Use simple min-max scaling if no trained scaler
            return (features - features.min()) / (features.max() - features.min() + 1e-8)
    
    def _detect_anomalies(self, features: np.ndarray) -> float:
        """Detect anomalies in agent behavior"""
        
        if self.anomaly_detector is not None:
            anomaly_score = self.anomaly_detector.decision_function(features.reshape(1, -1))[0]
            # Convert to 0-1 scale where 1 is most anomalous
            return max(0.0, min(1.0, (anomaly_score + 1) / 2))
        else:
            return 0.0  # No anomaly detection available
    
    def train_model(
        self,
        training_data: List[Dict[str, Any]],
        labels: List[float],
        epochs: int = 100,
        batch_size: int = 32,
        learning_rate: float = 0.001
    ) -> Dict[str, float]:
        """Train the reputation scoring model on AMD MI300X"""
        
        print(f"Training model on {self.device}...")
        
        # Extract features
        features = []
        for agent_data in training_data:
            features.append(self.extract_features(agent_data))
        
        features = np.array(features)
        labels = np.array(labels)
        
        # Fit scalers
        self.feature_scaler = StandardScaler()
        features_scaled = self.fit_scalers(features)
        
        # Train anomaly detector
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.anomaly_detector.fit(features_scaled)
        
        # Create dataset
        dataset = AgentReputationDataset(features_scaled, labels)
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        # Setup optimizer and loss
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.MSELoss()
        
        # Training loop
        self.model.train()
        training_history = []
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            
            for batch_features, batch_labels in dataloader:
                # Move to GPU if available
                if self.device == "cuda":
                    batch_features = batch_features.to('cuda')
                    batch_labels = batch_labels.to('cuda')
                
                # Forward pass
                predictions = self.model(batch_features)
                
                # Calculate loss on final score
                loss = criterion(predictions["final_score"].squeeze(), batch_labels)
                
                # Backward pass
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
            
            avg_loss = epoch_loss / len(dataloader)
            training_history.append(avg_loss)
            
            if epoch % 10 == 0:
                print(f"Epoch {epoch}/{epochs}, Loss: {avg_loss:.6f}")
        
        # Calculate training metrics
        final_loss = training_history[-1]
        
        print(f"Training completed. Final loss: {final_loss:.6f}")
        
        return {
            "final_loss": final_loss,
            "epochs_trained": epochs,
            "device_used": self.device
        }
    
    def fit_scalers(self, features: np.ndarray) -> np.ndarray:
        """Fit feature scalers and return scaled features"""
        
        self.feature_scaler = StandardScaler()
        scaled_features = self.feature_scaler.fit_transform(features)
        
        return scaled_features
    
    def save_model(self, path: str):
        """Save trained model and scalers"""
        
        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "feature_scaler": self.feature_scaler,
            "anomaly_detector": self.anomaly_detector,
            "feature_weights": self.feature_weights,
            "device": self.device
        }
        
        torch.save(checkpoint, path)
        print(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load trained model and scalers"""
        
        checkpoint = torch.load(path, map_location=self.device)
        
        # Initialize model if not already done
        if self.model is None:
            self._initialize_model()
        
        # Load model state
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.eval()
        
        # Load scalers
        self.feature_scaler = checkpoint["feature_scaler"]
        self.anomaly_detector = checkpoint["anomaly_detector"]
        
        # Load feature weights
        if "feature_weights" in checkpoint:
            self.feature_weights = checkpoint["feature_weights"]
        
        print(f"Model loaded from {path}")
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance for interpretability"""
        
        # This would typically use SHAP or similar techniques
        # For now, return the feature weights
        return self.feature_weights.copy()
    
    def update_reputation_realtime(
        self,
        agent_did: str,
        new_transaction: Dict[str, Any],
        current_reputation: float
    ) -> Tuple[float, float]:
        """Update reputation in real-time based on new transaction"""
        
        # Extract transaction features
        tx_amount = new_transaction.get("amount", 0)
        tx_success = new_transaction.get("success", True)
        tx_timestamp = new_transaction.get("timestamp", datetime.now(timezone.utc))
        
        # Calculate reputation delta
        reputation_delta = 0.0
        
        if tx_success:
            # Successful transaction increases reputation
            amount_factor = min(tx_amount / 1000.0, 1.0)  # Cap at 1000 USD equivalent
            reputation_delta = 0.01 * amount_factor  # Small positive delta
        else:
            # Failed transaction decreases reputation
            reputation_delta = -0.02  # Small negative delta
        
        # Apply time decay
        time_decay = self._calculate_time_decay(tx_timestamp)
        reputation_delta *= time_decay
        
        # Update reputation with bounds
        new_reputation = current_reputation + reputation_delta
        new_reputation = max(0.0, min(1.0, new_reputation))
        
        # Calculate confidence based on transaction history
        confidence = self._calculate_confidence_from_transactions(agent_did)
        
        return new_reputation, confidence
    
    def _calculate_time_decay(self, transaction_time: datetime) -> float:
        """Calculate time decay factor for reputation updates"""
        
        now = datetime.now(timezone.utc)
        time_diff = (now - transaction_time).total_seconds() / 86400  # Days
        
        # Exponential decay with 30-day half-life
        decay_factor = np.exp(-time_diff / 30.0)
        
        return max(0.1, decay_factor)  # Minimum 10% weight
    
    def _calculate_confidence_from_transactions(self, agent_did: str) -> float:
        """Calculate confidence based on transaction history"""
        
        # This would query transaction history
        # For now, return placeholder
        return 0.8  # 80% confidence with sufficient history


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_reputation_engine():
        """Test the reputation engine"""
        
        # Initialize reputation engine
        engine = ReputationEngine(device="cuda" if torch.cuda.is_available() else "cpu")
        
        # Create sample agent data
        agent_data = {
            "identity_age_days": 365,
            "verification_tier": 3,  # Gold tier
            "is_organization": True,
            "has_kyc": True,
            
            "total_transactions": 1000,
            "successful_transactions": 980,
            "failed_transactions": 20,
            "average_transaction_amount": 500,
            "transaction_frequency": 10,
            "transaction_velocity": 5,
            "amount_consistency": 0.85,
            "timing_consistency": 0.90,
            
            "chains_used": 5,
            "cross_chain_consistency": 0.95,
            "bridge_usage_frequency": 2,
            
            "threat_patterns_matched": 0,
            "false_positive_rate": 0.02,
            "threat_severity_average": 0,
            
            "insurance_coverage_level": 3,  # Enterprise level
            "claims_made": 1,
            "claims_successful": 1,
            "premium_payment_consistency": 1.0,
            
            "trusted_connections": 50,
            "suspicious_connections": 2,
            "network_centrality": 0.7
        }
        
        # Calculate reputation score
        reputation_score = engine.calculate_reputation_score("did:sigui:arc:individual:abc123", agent_data)
        
        print(f"Agent Reputation Score:")
        print(f"  Final Score: {reputation_score.final_score:.3f}")
        print(f"  Confidence: {reputation_score.confidence:.3f}")
        print(f"  Identity Score: {reputation_score.identity_score:.3f}")
        print(f"  Transaction Score: {reputation_score.transaction_score:.3f}")
        print(f"  Verification Score: {reputation_score.verification_score:.3f}")
        print(f"  Cross-chain Score: {reputation_score.cross_chain_score:.3f}")
        print(f"  Threat Intel Score: {reputation_score.threat_intelligence_score:.3f}")
        print(f"  Insurance Score: {reputation_score.insurance_score:.3f}")
        print(f"  Last Updated: {reputation_score.last_updated}")
        
        # Test real-time update
        new_transaction = {
            "amount": 1000,
            "success": True,
            "timestamp": datetime.now(timezone.utc)
        }
        
        new_score, confidence = engine.update_reputation_realtime(
            "did:sigui:arc:individual:abc123",
            new_transaction,
            reputation_score.final_score
        )
        
        print(f"\nAfter new transaction:")
        print(f"  New Score: {new_score:.3f}")
        print(f"  Confidence: {confidence:.3f}")
        
        # Test feature extraction
        features = engine.extract_features(agent_data)
        print(f"\nFeature Vector Shape: {features.shape}")
        print(f"Feature Vector Sample: {features[:10]}")
        
        # Test anomaly detection
        features_scaled = engine._scale_features(features)
        anomaly_score = engine._detect_anomalies(features_scaled)
        print(f"\nAnomaly Score: {anomaly_score:.3f}")
    
    # Run test
    asyncio.run(test_reputation_engine())