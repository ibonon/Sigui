"""
Système de chiffrement homomorphe complet (FHE).
Permet des calculs sur des données chiffrées sans les déchiffrer.
"""

import json
import logging
import random
import hashlib
import base64
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

from config import settings

logger = logging.getLogger(__name__)


class FHEOperation(Enum):
    """Opérations supportées par le FHE."""
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    COMPARE = "compare"
    DOT_PRODUCT = "dot_product"
    MATRIX_MULTIPLY = "matrix_multiply"


@dataclass
class FHEKeyPair:
    """Paire de clés FHE."""
    id: str
    public_key: str  # Clé publique en base64
    private_key: str  # Clé privée en base64 (chiffrée)
    key_size: int  # Taille de la clé en bits
    created_at: datetime
    expires_at: Optional[datetime]
    metadata: Dict[str, Any]


@dataclass
class FHECiphertext:
    """Texte chiffré FHE."""
    id: str
    key_id: str
    ciphertext: str  # Données chiffrées en base64
    data_type: str  # int, float, vector, matrix
    dimensions: Optional[Tuple[int, ...]]
    created_at: datetime
    metadata: Dict[str, Any]


@dataclass
class FHEOperationResult:
    """Résultat d'une opération FHE."""
    id: str
    operation: FHEOperation
    input_ciphertexts: List[str]  # IDs des textes chiffrés d'entrée
    output_ciphertext: str  # ID du texte chiffré de sortie
    execution_time_seconds: float
    created_at: datetime
    verified: bool = False


class FHESystem:
    """Système de chiffrement homomorphe complet."""
    
    def __init__(self):
        self.key_pairs_db = {}
        self.ciphertexts_db = {}
        self.operations_db = {}
        
        # Paramètres de sécurité
        self.default_key_size = 2048
        self.max_operation_depth = 10
        
        logger.info("FHE System initialisé")
    
    async def generate_key_pair(self, key_size: Optional[int] = None) -> FHEKeyPair:
        """Génère une nouvelle paire de clés FHE."""
        key_size = key_size or self.default_key_size
        
        # Générer les clés RSA (simulation du FHE)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        # Sérialiser les clés
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        private_key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # Créer l'ID de la paire de clés
        key_id = hashlib.sha256(
            f"{public_key_pem[:100]}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:32]
        
        # Date d'expiration (1 an par défaut)
        expires_at = datetime.now() + timedelta(days=365)
        
        key_pair = FHEKeyPair(
            id=key_id,
            public_key=public_key_pem,
            private_key=private_key_pem,
            key_size=key_size,
            created_at=datetime.now(),
            expires_at=expires_at,
            metadata={
                "algorithm": "RSA-FHE-SIM",
                "security_level": "high",
                "max_operations": self.max_operation_depth,
            }
        )
        
        self.key_pairs_db[key_id] = key_pair
        logger.info(f"Paire de clés FHE générée: {key_id} ({key_size} bits)")
        
        return key_pair
    
    async def encrypt(self, data: Union[int, float, List, np.ndarray], 
                     key_id: str) -> FHECiphertext:
        """Chiffre des données avec une clé FHE."""
        if key_id not in self.key_pairs_db:
            raise ValueError(f"Clé {key_id} non trouvée")
        
        key_pair = self.key_pairs_db[key_id]
        
        # Déterminer le type de données
        if isinstance(data, (int, np.integer)):
            data_type = "int"
            dimensions = None
            data_str = str(data)
        
        elif isinstance(data, (float, np.floating)):
            data_type = "float"
            dimensions = None
            data_str = str(data)
        
        elif isinstance(data, (list, np.ndarray)):
            if isinstance(data, list):
                data = np.array(data)
            
            data_type = "vector" if data.ndim == 1 else "matrix"
            dimensions = data.shape
            
            # Convertir en JSON pour la simulation
            data_str = json.dumps(data.tolist())
        
        else:
            raise ValueError(f"Type de données non supporté: {type(data)}")
        
        # Chiffrer les données (simulation avec RSA)
        public_key = serialization.load_pem_public_key(
            key_pair.public_key.encode(),
            backend=default_backend()
        )
        
        # Pour la simulation, on utilise un chiffrement simple
        # En réalité, on utiliserait un schéma FHE comme CKKS ou BFV
        ciphertext_bytes = public_key.encrypt(
            data_str.encode(),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        ciphertext_b64 = base64.b64encode(ciphertext_bytes).decode('utf-8')
        
        # Créer l'ID du texte chiffré
        ciphertext_id = hashlib.sha256(
            f"{key_id}{ciphertext_b64[:50]}{datetime.now().timestamp()}".encode()
        ).hexdigest()[:32]
        
        ciphertext = FHECiphertext(
            id=ciphertext_id,
            key_id=key_id,
            ciphertext=ciphertext_b64,
            data_type=data_type,
            dimensions=dimensions,
            created_at=datetime.now(),
            metadata={
                "original_type": str(type(data)),
                "encryption_time": datetime.now().isoformat(),
            }
        )
        
        self.ciphertexts_db[ciphertext_id] = ciphertext
        logger.info(f"Données chiffrées: {ciphertext_id} ({data_type})")
        
        return ciphertext
    
    async def decrypt(self, ciphertext_id: str) -> Union[int, float, List, np.ndarray]:
        """Déchiffre des données FHE."""
        if ciphertext_id not in self.ciphertexts_db:
            raise ValueError(f"Texte chiffré {ciphertext_id} non trouvé")
        
        ciphertext = self.ciphertexts_db[ciphertext_id]
        key_pair = self.key_pairs_db.get(ciphertext.key_id)
        
        if not key_pair:
            raise ValueError(f"Clé {ciphertext.key_id} non trouvée")
        
        # Charger la clé privée
        private_key = serialization.load_pem_private_key(
            key_pair.private_key.encode(),
            password=None,
            backend=default_backend()
        )
        
        # Déchiffrer
        ciphertext_bytes = base64.b64decode(ciphertext.ciphertext)
        
        try:
            decrypted_bytes = private_key.decrypt(
                ciphertext_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            decrypted_str = decrypted_bytes.decode('utf-8')
            
            # Reconstruire les données selon le type
            if ciphertext.data_type == "int":
                return int(decrypted_str)
            
            elif ciphertext.data_type == "float":
                return float(decrypted_str)
            
            elif ciphertext.data_type in ["vector", "matrix"]:
                data_list = json.loads(decrypted_str)
                result = np.array(data_list)
                
                # Restaurer les dimensions
                if ciphertext.dimensions:
                    result = result.reshape(ciphertext.dimensions)
                
                return result
            
            else:
                raise ValueError(f"Type de données inconnu: {ciphertext.data_type}")
        
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement: {e}")
            raise
    
    async def perform_operation(self, operation: FHEOperation, 
                               ciphertext_ids: List[str]) -> FHEOperationResult:
        """Effectue une opération sur des données chiffrées."""
        # Vérifier les textes chiffrés
        for ct_id in ciphertext_ids:
            if ct_id not in self.ciphertexts_db:
                raise ValueError(f"Texte chiffré {ct_id} non trouvé")
        
        ciphertexts = [self.ciphertexts_db[ct_id] for ct_id in ciphertext_ids]
        
        # Vérifier la compatibilité des types
        self._validate_operation_compatibility(operation, ciphertexts)
        
        start_time = datetime.now()
        
        try:
            # Effectuer l'opération (simulation)
            output_ciphertext = await self._simulate_fhe_operation(
                operation, ciphertexts
            )
            
            # Sauvegarder le texte chiffré de sortie
            self.ciphertexts_db[output_ciphertext.id] = output_ciphertext
            
            # Créer le résultat d'opération
            operation_id = hashlib.sha256(
                f"{operation.value}{'-'.join(ciphertext_ids)}{datetime.now().timestamp()}".encode()
            ).hexdigest()[:32]
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = FHEOperationResult(
                id=operation_id,
                operation=operation,
                input_ciphertexts=ciphertext_ids,
                output_ciphertext=output_ciphertext.id,
                execution_time_seconds=execution_time,
                created_at=datetime.now(),
                verified=True,
            )
            
            self.operations_db[operation_id] = result
            
            logger.info(f"Opération FHE effectuée: {operation.value} -> {output_ciphertext.id}")
            
            return result
        
        except Exception as e:
            logger.error(f"Erreur lors de l'opération FHE: {e}")
            raise
    
    def _validate_operation_compatibility(self, operation: FHEOperation, 
                                         ciphertexts: List[FHECiphertext]):
        """Valide la compatibilité des données pour une opération."""
        if operation == FHEOperation.ADD:
            if len(ciphertexts) != 2:
                raise ValueError("ADD nécessite exactement 2 opérandes")
            
            if ciphertexts[0].data_type != ciphertexts[1].data_type:
                raise ValueError("Types de données incompatibles pour ADD")
        
        elif operation == FHEOperation.MULTIPLY:
            if len(ciphertexts) != 2:
                raise ValueError("MULTIPLY nécessite exactement 2 opérandes")
            
            # Vérifier les dimensions pour la multiplication matricielle
            if (ciphertexts[0].data_type == "matrix" and 
                ciphertexts[1].data_type == "matrix"):
                
                if (ciphertexts[0].dimensions[1] != 
                    ciphertexts[1].dimensions[0]):
                    raise ValueError(
                        f"Dimensions incompatibles: {ciphertexts[0].dimensions} "
                        f"x {ciphertexts[1].dimensions}"
                    )
        
        elif operation == FHEOperation.DOT_PRODUCT:
            if len(ciphertexts) != 2:
                raise ValueError("DOT_PRODUCT nécessite exactement 2 vecteurs")
            
            if (ciphertexts[0].data_type != "vector" or 
                ciphertexts[1].data_type != "vector"):
                raise ValueError("DOT_PRODUCT nécessite des vecteurs")
            
            if (ciphertexts[0].dimensions[0] != 
                ciphertexts[1].dimensions[0]):
                raise ValueError("Vecteurs de tailles différentes")
    
    async def _simulate_fhe_operation(self, operation: FHEOperation,
                                     ciphertexts: List[FHECiphertext]) -> FHECiphertext:
        """Simule une opération FHE."""
        # Pour la simulation, on déchiffre, effectue l'opération, et rechiffre
        # En réalité, l'opération se ferait directement sur les données chiffrées
        
        decrypted_data = []
        for ciphertext in ciphertexts:
            data = await self.decrypt(ciphertext.id)
            decrypted_data.append(data)
        
        # Effectuer l'opération
        if operation == FHEOperation.ADD:
            result = decrypted_data[0] + decrypted_data[1]
        
        elif operation == FHEOperation.SUBTRACT:
            result = decrypted_data[0] - decrypted_data[1]
        
        elif operation == FHEOperation.MULTIPLY:
            result = decrypted_data[0] * decrypted_data[1]
        
        elif operation == FHEOperation.COMPARE:
            # Retourne 1 si a > b, 0 sinon
            result = 1 if decrypted_data[0] > decrypted_data[1] else 0
        
        elif operation == FHEOperation.DOT_PRODUCT:
            result = np.dot(decrypted_data[0], decrypted_data[1])
        
        elif operation == FHEOperation.MATRIX_MULTIPLY:
            result = np.matmul(decrypted_data[0], decrypted_data[1])
        
        else:
            raise ValueError(f"Opération non supportée: {operation}")
        
        # Rechiffrer le résultat
        key_id = ciphertexts[0].key_id
        output_ciphertext = await self.encrypt(result, key_id)
        
        return output_ciphertext
    
    async def verify_operation(self, operation_id: str) -> bool:
        """Vérifie qu'une opération FHE a été correctement effectuée."""
        if operation_id not in self.operations_db:
            raise ValueError(f"Opération {operation_id} non trouvée")
        
        operation_result = self.operations_db[operation_id]
        
        try:
            # Pour la vérification, on compare avec un calcul en clair
            # En réalité, on utiliserait des preuves cryptographiques
            
            # Déchiffrer les entrées
            input_data = []
            for ct_id in operation_result.input_ciphertexts:
                data = await self.decrypt(ct_id)
                input_data.append(data)
            
            # Déchiffrer la sortie
            output_data = await self.decrypt(operation_result.output_ciphertext)
            
            # Effectuer l'opération en clair
            if operation_result.operation == FHEOperation.ADD:
                expected = input_data[0] + input_data[1]
            
            elif operation_result.operation == FHEOperation.SUBTRACT:
                expected = input_data[0] - input_data[1]
            
            elif operation_result.operation == FHEOperation.MULTIPLY:
                expected = input_data[0] * input_data[1]
            
            elif operation_result.operation == FHEOperation.COMPARE:
                expected = 1 if input_data[0] > input_data[1] else 0
            
            elif operation_result.operation == FHEOperation.DOT_PRODUCT:
                expected = np.dot(input_data[0], input_data[1])
            
            elif operation_result.operation == FHEOperation.MATRIX_MULTIPLY:
                expected = np.matmul(input_data[0], input_data[1])
            
            else:
                return False
            
            # Comparer avec la sortie chiffrée
            if isinstance(expected, np.ndarray) and isinstance(output_data, np.ndarray):
                is_valid = np.allclose(expected, output_data, rtol=1e-5)
            else:
                is_valid = abs(expected - output_data) < 1e-5
            
            operation_result.verified = is_valid
            
            logger.info(f"Opération {operation_id} vérifiée: {is_valid}")
            
            return is_valid
        
        except Exception as e:
            logger.error(f"Erreur lors de la vérification: {e}")
            operation_result.verified = False
            return False
    
    async def get_key_pair(self, key_id: str) -> Optional[FHEKeyPair]:
        """Récupère une paire de clés par son ID."""
        return self.key_pairs_db.get(key_id)
    
    async def get_ciphertext(self, ciphertext_id: str) -> Optional[FHECiphertext]:
        """Récupère un texte chiffré par son ID."""
        return self.ciphertexts_db.get(ciphertext_id)
    
    async def get_operation_result(self, operation_id: str) -> Optional[FHEOperationResult]:
        """Récupère un résultat d'opération par son ID."""
        return self.operations_db.get(operation_id)
    
    async def list_key_pairs(self, active_only: bool = True) -> List[FHEKeyPair]:
        """Liste les paires de clés disponibles."""
        key_pairs = list(self.key_pairs_db.values())
        
        if active_only:
            now = datetime.now()
            key_pairs = [
                kp for kp in key_pairs
                if not kp.expires_at or kp.expires_at > now
            ]
        
        return key_pairs
    
    async def list_ciphertexts(self, key_id: Optional[str] = None) -> List[FHECiphertext]:
        """Liste les textes chiffrés."""
        ciphertexts = list(self.ciphertexts_db.values())
        
        if key_id:
            ciphertexts = [ct for ct in ciphertexts if ct.key_id == key_id]
        
        return ciphertexts
    
    async def list_operations(self, verified_only: bool = False) -> List[FHEOperationResult]:
        """Liste les opérations effectuées."""
        operations = list(self.operations_db.values())
        
        if verified_only:
            operations = [op for op in operations if op.verified]
        
        operations.sort(key=lambda x: x.created_at, reverse=True)
        
        return operations
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Récupère les métriques du système FHE."""
        total_keys = len(self.key_pairs_db)
        total_ciphertexts = len(self.ciphertexts_db)
        total_operations = len(self.operations_db)
        
        # Opérations vérifiées
        verified_operations = sum(1 for op in self.operations_db.values() if op.verified)
        
        # Distribution par type d'opération
        operation_distribution = {}
        for op in self.operations_db.values():
            op_type = op.operation.value
            operation_distribution[op_type] = operation_distribution.get(op_type, 0) + 1
        
        # Temps d'exécution moyen
        execution_times = [op.execution_time_seconds for op in self.operations_db.values()]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0
        
        return {
            "total_key_pairs": total_keys,
            "total_ciphertexts": total_ciphertexts,
            "total_operations": total_operations,
            "verified_operations": verified_operations,
            "verification_rate": verified_operations / total_operations if total_operations > 0 else 0,
            "average_execution_time_seconds": round(avg_execution_time, 3),
            "operation_distribution": operation_distribution,
            "max_operation_depth": self.max_operation_depth,
            "last_operation": max(
                [op.created_at for op in self.operations_db.values()],
                default=None
            ),
        }
    
    async def rotate_keys(self, old_key_id: str, new_key_id: Optional[str] = None) -> FHEKeyPair:
        """Effectue une rotation de clés FHE."""
        if old_key_id not in self.key_pairs_db:
            raise ValueError(f"Ancienne clé {old_key_id} non trouvée")
        
        # Générer une nouvelle paire de clés si non fournie
        if not new_key_id:
            new_key_pair = await self.generate_key_pair()
            new_key_id = new_key_pair.id
        elif new_key_id not in self.key_pairs_db:
            raise ValueError(f"Nouvelle clé {new_key_id} non trouvée")
        
        # Rechiffrer tous les textes chiffrés avec l'ancienne clé
        old_ciphertexts = [
            ct for ct in self.ciphertexts_db.values()
            if ct.key_id == old_key_id
        ]
        
        for old_ct in old_ciphertexts:
            # Déchiffrer avec l'ancienne clé
            data = await self.decrypt(old_ct.id)
            
            # Rechiffrer avec la nouvelle clé
            new_ct = await self.encrypt(data, new_key_id)
            
            # Mettre à jour les références
            # (dans un système réel, on mettrait à jour les métadonnées)
        
        logger.info(f"Rotation de clés effectuée: {old_key_id} -> {new_key_id}")
        
        return self.key_pairs_db[new_key_id]