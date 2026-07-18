"""
Sigui v3.0 — TrustGraph
Graphe de réputation spatio-temporel pour agents IA.
Utilise GNN (Graph Neural Networks) pour calculer les scores de confiance.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

import networkx as nx
import numpy as np
from loguru import logger

from config import settings


class TrustEdgeType(Enum):
    """Types de relations de confiance dans le graphe."""
    PAYMENT = "payment"
    SERVICE = "service"
    DELEGATION = "delegation"
    COLLABORATION = "collaboration"
    VERIFICATION = "verification"


@dataclass
class TrustEdge:
    """Arête dans le graphe de confiance."""
    source: str  # DID de l'agent source
    target: str  # DID de l'agent cible
    edge_type: TrustEdgeType
    weight: float  # 0.0 à 1.0
    timestamp: datetime
    metadata: Dict[str, any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, any]:
        """Convertit l'arête en dictionnaire."""
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class TrustGraph:
    """Graphe de confiance décentralisé pour agents IA."""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self.edge_history: Dict[Tuple[str, str], List[TrustEdge]] = {}
        self.node_features: Dict[str, np.ndarray] = {}
        
        # Paramètres du modèle
        self.decay_factor = 0.95  # Décroissance exponentielle
        self.min_edge_weight = 0.01
        self.max_history_length = 1000
        
        logger.info("TrustGraph initialisé")
    
    def add_agent(self, agent_did: str, features: Optional[np.ndarray] = None):
        """Ajoute un agent au graphe."""
        if agent_did not in self.graph:
            self.graph.add_node(agent_did)
            self.node_features[agent_did] = features if features is not None else np.zeros(10)
            logger.debug(f"Agent ajouté au TrustGraph: {agent_did}")
    
    def add_trust_edge(
        self,
        source_did: str,
        target_did: str,
        edge_type: TrustEdgeType,
        weight: float,
        metadata: Optional[Dict[str, any]] = None
    ) -> TrustEdge:
        """Ajoute une arête de confiance entre deux agents."""
        # S'assurer que les agents existent
        self.add_agent(source_did)
        self.add_agent(target_did)
        
        # Créer l'arête
        edge = TrustEdge(
            source=source_did,
            target=target_did,
            edge_type=edge_type,
            weight=max(self.min_edge_weight, min(1.0, weight)),
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        
        # Ajouter au graphe
        self.graph.add_edge(source_did, target_did, edge=edge)
        
        # Historiser
        key = (source_did, target_did)
        if key not in self.edge_history:
            self.edge_history[key] = []
        self.edge_history[key].append(edge)
        
        # Limiter la taille de l'historique
        if len(self.edge_history[key]) > self.max_history_length:
            self.edge_history[key] = self.edge_history[key][-self.max_history_length:]
        
        logger.debug(f"Arête de confiance ajoutée: {source_did} -> {target_did} ({edge_type.value}, weight={weight})")
        return edge
    
    def calculate_trust_score(self, agent_did: str, depth: int = 3) -> float:
        """Calcule le score de confiance d'un agent."""
        if agent_did not in self.graph:
            return 0.0
        
        # Algorithme PageRank adapté
        try:
            pagerank_scores = nx.pagerank(self.graph, alpha=0.85)
            score = pagerank_scores.get(agent_did, 0.0)
            
            # Appliquer la décroissance temporelle
            score = self._apply_temporal_decay(agent_did, score)
            
            return min(1.0, max(0.0, score))
        except Exception as e:
            logger.error(f"Erreur lors du calcul du score de confiance: {e}")
            return 0.0
    
    def _apply_temporal_decay(self, agent_did: str, base_score: float) -> float:
        """Applique la décroissance temporelle au score."""
        now = datetime.now(timezone.utc)
        total_decay = 1.0
        
        # Calculer la décroissance basée sur l'âge des arêtes entrantes
        incoming_edges = list(self.graph.in_edges(agent_did, data=True))
        
        for _, _, edge_data in incoming_edges:
            edge = edge_data.get('edge')
            if edge:
                age_hours = (now - edge.timestamp).total_seconds() / 3600
                decay = self.decay_factor ** (age_hours / 24)  # Décroissance quotidienne
                total_decay *= decay
        
        return base_score * total_decay
    
    def find_trust_paths(
        self,
        source_did: str,
        target_did: str,
        max_paths: int = 5
    ) -> List[List[Tuple[str, str, float]]]:
        """Trouve les chemins de confiance entre deux agents."""
        if source_did not in self.graph or target_did not in self.graph:
            return []
        
        try:
            paths = []
            for path in nx.all_simple_paths(self.graph, source_did, target_did, cutoff=4):
                path_edges = []
                for i in range(len(path) - 1):
                    edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                    if edge_data and 'edge' in edge_data:
                        edge = edge_data['edge']
                        path_edges.append((path[i], path[i + 1], edge.weight))
                
                if path_edges:
                    paths.append(path_edges)
                
                if len(paths) >= max_paths:
                    break
            
            return paths
        except Exception as e:
            logger.error(f"Erreur lors de la recherche de chemins de confiance: {e}")
            return []
    
    def get_trust_neighborhood(
        self,
        agent_did: str,
        radius: int = 2,
        min_trust: float = 0.1
    ) -> Dict[str, float]:
        """Récupère le voisinage de confiance d'un agent."""
        if agent_did not in self.graph:
            return {}
        
        neighborhood = {}
        
        try:
            # Utiliser BFS pour explorer le voisinage
            visited = set()
            queue = [(agent_did, 0, 1.0)]  # (node, distance, cumulative_trust)
            
            while queue:
                current, distance, cumulative_trust = queue.pop(0)
                
                if current in visited or distance > radius:
                    continue
                
                visited.add(current)
                
                if current != agent_did and cumulative_trust >= min_trust:
                    neighborhood[current] = cumulative_trust
                
                # Explorer les voisins sortants
                for neighbor in self.graph.successors(current):
                    edge_data = self.graph.get_edge_data(current, neighbor)
                    if edge_data and 'edge' in edge_data:
                        edge = edge_data['edge']
                        new_trust = cumulative_trust * edge.weight
                        queue.append((neighbor, distance + 1, new_trust))
            
            return neighborhood
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du voisinage de confiance: {e}")
            return {}
    
    def export_graph(self) -> Dict[str, any]:
        """Exporte le graphe au format JSON."""
        nodes = []
        edges = []
        
        for node in self.graph.nodes():
            nodes.append({
                "id": node,
                "trust_score": self.calculate_trust_score(node),
            })
        
        for source, target, edge_data in self.graph.edges(data=True):
            edge = edge_data.get('edge')
            if edge:
                edges.append(edge.to_dict())
        
        return {
            "nodes": nodes,
            "edges": edges,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def import_graph(self, data: Dict[str, any]):
        """Importe un graphe depuis JSON."""
        try:
            self.graph.clear()
            self.edge_history.clear()
            self.node_features.clear()
            
            # Importer les nœuds
            for node_data in data.get("nodes", []):
                node_id = node_data["id"]
                self.graph.add_node(node_id)
            
            # Importer les arêtes
            for edge_data in data.get("edges", []):
                source = edge_data["source"]
                target = edge_data["target"]
                edge_type = TrustEdgeType(edge_data["edge_type"])
                weight = edge_data["weight"]
                timestamp = datetime.fromisoformat(edge_data["timestamp"])
                metadata = edge_data.get("metadata", {})
                
                edge = TrustEdge(
                    source=source,
                    target=target,
                    edge_type=edge_type,
                    weight=weight,
                    timestamp=timestamp,
                    metadata=metadata,
                )
                
                self.graph.add_edge(source, target, edge=edge)
                
                # Historiser
                key = (source, target)
                if key not in self.edge_history:
                    self.edge_history[key] = []
                self.edge_history[key].append(edge)
            
            logger.info(f"Graphe importé avec {len(self.graph.nodes())} nœuds et {len(self.graph.edges())} arêtes")
        except Exception as e:
            logger.error(f"Erreur lors de l'importation du graphe: {e}")
            raise