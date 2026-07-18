"""
Système de voting avancé pour la gouvernance Sigui.
Supporte le voting quadratique, la pondération par réputation et la délégation.
"""

import math
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
import logging

from .governance_config import GovernanceConfig, VotingSystem
from modules.reputation.trust_graph import ReputationOracle

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Types de votes supportés."""
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class VoteWeight:
    """Poids d'un vote avec différents facteurs."""
    
    def __init__(self, base_power: float, reputation_factor: float = 1.0,
                 token_factor: float = 1.0, quadratic_cost: float = 0.0):
        self.base_power = base_power
        self.reputation_factor = reputation_factor
        self.token_factor = token_factor
        self.quadratic_cost = quadratic_cost
        self.final_weight = self._calculate_final_weight()
    
    def _calculate_final_weight(self) -> float:
        """Calcule le poids final du vote."""
        weighted = self.base_power * self.reputation_factor * self.token_factor
        # Applique le coût quadratique
        if self.quadratic_cost > 0:
            weighted = math.sqrt(weighted * self.quadratic_cost)
        return weighted
    
    def get_cost(self) -> float:
        """Calcule le coût du vote."""
        return self.base_power * self.quadratic_cost


class VotingSession:
    """Session de voting pour une proposition."""
    
    def __init__(self, proposal_id: str, level: str, 
                 voting_system: VotingSystem, config: GovernanceConfig):
        self.proposal_id = proposal_id
        self.level = level
        self.voting_system = voting_system
        self.config = config
        self.start_time = int(time.time())
        self.end_time = self.start_time + (config.voting_duration_days * 86400)
        self.votes: Dict[str, Dict[str, Any]] = {}  # voter_did -> vote_data
        self.delegated_votes: Dict[str, List[Dict]] = {}  # delegator -> [delegated_votes]
        self.total_voting_power = 0.0
        self.quorum_met = False
        self.finalized = False
        self.results: Optional[Dict[str, Any]] = None
    
    def add_vote(self, voter_did: str, vote_type: VoteType, 
                voting_power: float, quadratic_cost: Optional[float] = None,
                reputation_score: Optional[float] = None) -> bool:
        """
        Ajoute un vote à la session.
        
        Args:
            voter_did: DID du votant
            vote_type: Type de vote
            voting_power: Puissance de vote
            quadratic_cost: Coût quadratique
            reputation_score: Score de réputation
            
        Returns:
            bool: True si le vote a été ajouté
        """
        try:
            # Vérifie que le voting est actif
            if time.time() > self.end_time:
                logger.warning(f"Voting terminé pour {self.proposal_id}")
                return False
            
            # Vérifie les doublons
            if voter_did in self.votes:
                logger.warning(f"Votant {voter_did} a déjà voté")
                return False
            
            # Calcule le poids du vote
            vote_weight = self._calculate_vote_weight(
                voting_power, quadratic_cost, reputation_score
            )
            
            # Enregistre le vote
            self.votes[voter_did] = {
                "vote_type": vote_type.value,
                "voting_power": voting_power,
                "vote_weight": vote_weight.final_weight,
                "quadratic_cost": quadratic_cost,
                "reputation_score": reputation_score,
                "timestamp": int(time.time()),
                "cost": vote_weight.get_cost()
            }
            
            # Met à jour le total
            self.total_voting_power += vote_weight.final_weight
            
            logger.info(f"Vote ajouté: {voter_did} -> {vote_type.value} (poids: {vote_weight.final_weight})")
            return True
            
        except Exception as e:
            logger.error(f"Erreur ajout vote: {e}")
            return False
    
    def _calculate_vote_weight(self, base_power: float, 
                              quadratic_cost: Optional[float],
                              reputation_score: Optional[float]) -> VoteWeight:
        """
        Calcule le poids d'un vote selon le système configuré.
        
        Args:
            base_power: Puissance de vote de base
            quadratic_cost: Coût quadratique
            reputation_score: Score de réputation
            
        Returns:
            VoteWeight: Poids calculé
        """
        # Facteurs par défaut
        rep_factor = 1.0
        token_factor = 1.0
        q_cost = quadratic_cost or 0.0
        
        # Applique la pondération par réputation si configurée
        if self.voting_system == VotingSystem.REPUTATION_WEIGHTED and reputation_score:
            rep_factor = reputation_score * self.config.reputation_weight_factor
        
        # Applique la pondération par tokens si configurée
        if self.voting_system == VotingSystem.TOKEN_WEIGHTED:
            # Simule un facteur basé sur les tokens détenus
            token_factor = self.config.token_weight_factor
        
        # Pour le voting quadratique
        if self.voting_system == VotingSystem.QUADRATIC_VOTING:
            if quadratic_cost is None:
                q_cost = base_power * self.config.quadratic_voting_cost_factor
        
        return VoteWeight(
            base_power=base_power,
            reputation_factor=rep_factor,
            token_factor=token_factor,
            quadratic_cost=q_cost
        )
    
    def add_delegated_vote(self, delegator_did: str, delegatee_did: str,
                          voting_power: float, vote_type: VoteType) -> bool:
        """
        Ajoute un vote délégué.
        
        Args:
            delegator_did: DID du délégant
            delegatee_did: DID du délégué
            voting_power: Puissance de vote déléguée
            vote_type: Type de vote
            
        Returns:
            bool: True si la délégation a été ajoutée
        """
        try:
            # Vérifie la profondeur de délégation
            if self._check_delegation_depth(delegator_did) > self.config.max_delegation_depth:
                logger.warning(f"Profondeur de délégation excessive pour {delegator_did}")
                return False
            
            # Enregistre la délégation
            if delegator_did not in self.delegated_votes:
                self.delegated_votes[delegator_did] = []
            
            delegation = {
                "delegatee_did": delegatee_did,
                "voting_power": voting_power,
                "vote_type": vote_type.value,
                "timestamp": int(time.time())
            }
            
            self.delegated_votes[delegator_did].append(delegation)
            
            # Le délégué doit aussi voter
            if delegatee_did not in self.votes:
                # Le délégué vote avec le pouvoir combiné
                existing_power = sum(d["voting_power"] for d in self.delegated_votes.get(delegatee_did, []))
                total_power = existing_power + voting_power
                
                # Ajoute le vote du délégué
                self.add_vote(
                    voter_did=delegatee_did,
                    vote_type=vote_type,
                    voting_power=total_power
                )
            
            logger.info(f"Délégation ajoutée: {delegator_did} -> {delegatee_did} ({voting_power})")
            return True
            
        except Exception as e:
            logger.error(f"Erreur ajout délégation: {e}")
            return False
    
    def _check_delegation_depth(self, delegator_did: str, current_depth: int = 0) -> int:
        """
        Vérifie la profondeur de la chaîne de délégation.
        
        Args:
            delegator_did: DID du délégant
            current_depth: Profondeur actuelle
            
        Returns:
            int: Profondeur maximale
        """
        if delegator_did not in self.delegated_votes:
            return current_depth
        
        max_depth = current_depth
        for delegation in self.delegated_votes[delegator_did]:
            depth = self._check_delegation_depth(
                delegation["delegatee_did"],
                current_depth + 1
            )
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def calculate_quorum(self, total_available_power: float) -> bool:
        """
        Calcule si le quorum est atteint.
        
        Args:
            total_available_power: Puissance de vote totale disponible
            
        Returns:
            bool: True si le quorum est atteint
        """
        if total_available_power == 0:
            self.quorum_met = False
            return False
        
        participation_rate = self.total_voting_power / total_available_power
        self.quorum_met = participation_rate >= self.config.quorum_threshold
        return self.quorum_met
    
    def calculate_results(self) -> Dict[str, Any]:
        """
        Calcule les résultats du voting.
        
        Returns:
            Dict: Résultats détaillés
        """
        try:
            # Agrège les votes
            votes_for = 0.0
            votes_against = 0.0
            votes_abstain = 0.0
            
            for vote_data in self.votes.values():
                weight = vote_data["vote_weight"]
                if vote_data["vote_type"] == VoteType.FOR.value:
                    votes_for += weight
                elif vote_data["vote_type"] == VoteType.AGAINST.value:
                    votes_against += weight
                else:
                    votes_abstain += weight
            
            total_votes = votes_for + votes_against + votes_abstain
            
            # Calcule les pourcentages
            if total_votes > 0:
                for_pct = (votes_for / total_votes) * 100
                against_pct = (votes_against / total_votes) * 100
                abstain_pct = (votes_abstain / total_votes) * 100
            else:
                for_pct = against_pct = abstain_pct = 0.0
            
            # Détermine si approuvé
            approved = False
            if self.quorum_met and total_votes > 0:
                approval_rate = votes_for / (votes_for + votes_against)
                approved = approval_rate >= self.config.approval_threshold
            
            # Statistiques avancées
            voter_count = len(self.votes)
            avg_vote_weight = self.total_voting_power / voter_count if voter_count > 0 else 0
            
            # Analyse des délégations
            delegation_count = sum(len(votes) for votes in self.delegated_votes.values())
            avg_delegation_power = 0.0
            if delegation_count > 0:
                total_delegated_power = sum(
                    d["voting_power"] 
                    for delegations in self.delegated_votes.values() 
                    for d in delegations
                )
                avg_delegation_power = total_delegated_power / delegation_count
            
            self.results = {
                "proposal_id": self.proposal_id,
                "level": self.level,
                "voting_system": self.voting_system.value,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "votes_for": votes_for,
                "votes_against": votes_against,
                "votes_abstain": votes_abstain,
                "total_votes": total_votes,
                "for_percentage": for_pct,
                "against_percentage": against_pct,
                "abstain_percentage": abstain_pct,
                "total_voting_power": self.total_voting_power,
                "quorum_met": self.quorum_met,
                "approved": approved,
                "voter_count": voter_count,
                "avg_vote_weight": avg_vote_weight,
                "delegation_count": delegation_count,
                "avg_delegation_power": avg_delegation_power,
                "participation_rate": (self.total_voting_power / total_available_power) * 100 if hasattr(self, 'total_available_power') else 0,
                "timestamp": int(time.time())
            }
            
            self.finalized = True
            logger.info(f"Résultats calculés pour {self.proposal_id}: approved={approved}")
            return self.results
            
        except Exception as e:
            logger.error(f"Erreur calcul résultats: {e}")
            return {
                "proposal_id": self.proposal_id,
                "error": str(e),
                "timestamp": int(time.time())
            }
    
    def get_vote_breakdown(self) -> Dict[str, Any]:
        """
        Récupère la répartition détaillée des votes.
        
        Returns:
            Dict: Répartition des votes
        """
        if not self.finalized:
            logger.warning(f"Voting non finalisé pour {self.proposal_id}")
            return {}
        
        # Analyse par type de votant
        member_votes = []
        delegated_votes = []
        
        for voter_did, vote_data in self.votes.items():
            # Vérifie si c'est un vote délégué
            is_delegated = False
            for delegations in self.delegated_votes.values():
                for d in delegations:
                    if d["delegatee_did"] == voter_did:
                        is_delegated = True
                        break
                if is_delegated:
                    break
            
            vote_info = {
                "voter_did": voter_did,
                "vote_type": vote_data["vote_type"],
                "vote_weight": vote_data["vote_weight"],
                "voting_power": vote_data["voting_power"],
                "quadratic_cost": vote_data["quadratic_cost"],
                "reputation_score": vote_data["reputation_score"],
                "timestamp": vote_data["timestamp"]
            }
            
            if is_delegated:
                delegated_votes.append(vote_info)
            else:
                member_votes.append(vote_info)
        
        # Analyse des délégations
        delegation_analysis = []
        for delegator_did, delegations in self.delegated_votes.items():
            total_delegated = sum(d["voting_power"] for d in delegations)
            delegation_analysis.append({
                "delegator_did": delegator_did,
                "delegation_count": len(delegations),
                "total_delegated_power": total_delegated,
                "delegations": delegations
            })
        
        return {
            "member_votes": member_votes,
            "delegated_votes": delegated_votes,
            "delegation_analysis": delegation_analysis,
            "total_voters": len(self.votes),
            "total_delegators": len(self.delegated_votes)
        }


class AdvancedVotingSystem:
    """Système de voting avancé avec support multiple."""
    
    def __init__(self, config: GovernanceConfig, reputation_oracle: ReputationOracle):
        self.config = config
        self.reputation_oracle = reputation_oracle
        self.sessions: Dict[str, VotingSession] = {}
        self.voter_registry: Dict[str, Dict[str, Any]] = {}  # voter_did -> voter_data
        self.delegation_registry: Dict[str, List[str]] = {}  # delegator -> [delegatees]
        self._lock = asyncio.Lock()
    
    async def create_voting_session(self, proposal_id: str, level: str) -> Optional[VotingSession]:
        """
        Crée une nouvelle session de voting.
        
        Args:
            proposal_id: ID de la proposition
            level: Niveau de gouvernance
            
        Returns:
            Optional[VotingSession]: Session créée ou None
        """
        async with self._lock:
            try:
                if proposal_id in self.sessions:
                    logger.warning(f"Session existante pour {proposal_id}")
                    return self.sessions[proposal_id]
                
                # Détermine le système de voting
                voting_system = self.config.voting_system
                
                # Crée la session
                session = VotingSession(
                    proposal_id=proposal_id,
                    level=level,
                    voting_system=voting_system,
                    config=self.config
                )
                
                self.sessions[proposal_id] = session
                logger.info(f"Session de voting créée: {proposal_id} ({voting_system.value})")
                return session
                
            except Exception as e:
                logger.error(f"Erreur création session: {e}")
                return None
    
    async def register_voter(self, voter_did: str, level: str, 
                           reputation_score: Optional[float] = None,
                           token_balance: Optional[float] = None) -> bool:
        """
        Enregistre un votant pour le système.
        
        Args:
            voter_did: DID du votant
            level: Niveau de gouvernance
            reputation_score: Score de réputation
            token_balance: Balance de tokens
            
        Returns:
            bool: True si l'enregistrement a réussi
        """
        async with self._lock:
            try:
                if voter_did in self.voter_registry:
                    logger.warning(f"Votant déjà enregistré: {voter_did}")
                    return False
                
                # Récupère le score de réputation si non fourni
                if reputation_score is None:
                    reputation_score = self.reputation_oracle.get_trust_score(voter_did)
                
                # Calcule le pouvoir de vote initial
                voting_power = self._calculate_voting_power(
                    reputation_score, token_balance
                )
                
                # Enregistre le votant
                self.voter_registry[voter_did] = {
                    "did": voter_did,
                    "level": level,
                    "reputation_score": reputation_score,
                    "token_balance": token_balance or 0.0,
                    "voting_power": voting_power,
                    "registered_date": int(time.time()),
                    "last_vote_date": None,
                    "total_votes_cast": 0,
                    "delegation_count": 0,
                    "is_active": True
                }
                
                logger.info(f"Votant enregistré: {voter_did} (pouvoir: {voting_power})")
                return True
                
            except Exception as e:
                logger.error(f"Erreur enregistrement votant: {e}")
                return False
    
    def _calculate_voting_power(self, reputation_score: float, 
                               token_balance: Optional[float]) -> float:
        """
        Calcule le pouvoir de vote d'un votant.
        
        Args:
            reputation_score: Score de réputation
            token_balance: Balance de tokens
            
        Returns:
            float: Pouvoir de vote calculé
        """
        # Facteur de réputation
        rep_factor = reputation_score * self.config.reputation_weight_factor
        
        # Facteur de tokens
        token_factor = 0.0
        if token_balance and token_balance > 0:
            # Normalise le balance de tokens
            normalized_tokens = min(token_balance / 1000.0, 1.0)  # Max 1000 tokens = facteur 1.0
            token_factor = normalized_tokens * self.config.token_weight_factor
        
        # Calcul combiné
        base_power = rep_factor + token_factor
        
        # Applique le minimum
        return max(base_power, self.config.min_voting_power)
    
    async def cast_vote(self, proposal_id: str, voter_did: str, 
                       vote_type: VoteType, voting_power: float,
                       quadratic_cost: Optional[float] = None) -> bool:
        """
        Enregistre un vote pour une proposition.
        
        Args:
            proposal_id: ID de la proposition
            voter_did: DID du votant
            vote_type: Type de vote
            voting_power: Puissance de vote
            quadratic_cost: Coût quadratique
            
        Returns:
            bool: True si le vote a été enregistré
        """
        async with self._lock:
            try:
                # Vérifie la session
                if proposal_id not in self.sessions:
                    logger.warning(f"Session non trouvée: {proposal_id}")
                    return False
                
                session = self.sessions[proposal_id]
                
                # Vérifie le votant
                if voter_did not in self.voter_registry:
                    logger.warning(f"Votant non enregistré: {voter_did}")
                    return False
                
                voter = self.voter_registry[voter_did]
                
                # Vérifie le niveau
                if voter["level"] != session.level:
                    logger.warning(f"Niveau incompatible: {voter['level']} != {session.level}")
                    return False
                
                # Vérifie le pouvoir de vote disponible
                if voting_power > voter["voting_power"]:
                    logger.warning(f"Pouvoir de vote insuffisant: {voting_power} > {voter['voting_power']}")
                    return False
                
                # Récupère le score de réputation
                reputation_score = voter["reputation_score"]
                
                # Ajoute le vote
                success = session.add_vote(
                    voter_did=voter_did,
                    vote_type=vote_type,
                    voting_power=voting_power,
                    quadratic_cost=quadratic_cost,
                    reputation_score=reputation_score
                )
                
                if success:
                    # Met à jour le registre du votant
                    voter["last_vote_date"] = int(time.time())
                    voter["total_votes_cast"] += 1
                    # Réduit le pouvoir de vote utilisé
                    voter["voting_power"] -= voting_power
                
                return success
                
            except Exception as e:
                logger.error(f"Erreur cast vote: {e}")
                return False
    
    async delegate_vote(self, proposal_id: str, delegator_did: str, 
                       delegatee_did: str, voting_power: float,
                       vote_type: VoteType) -> bool:
        """
        Délègue un vote à un autre votant.
        
        Args:
            proposal_id: ID de la proposition
            delegator_did: DID du délégant
            delegatee_did: DID du délégué
            voting_power: Puissance de vote déléguée
            vote_type: Type de vote
            
        Returns:
            bool: True si la délégation a réussi
        """
        async with self._lock:
            try:
                # Vérifie la session
                if proposal_id not in self.sessions:
                    logger.warning(f"Session non trouvée: {proposal_id}")
                    return False
                
                session = self.sessions[proposal_id]
                
                # Vérifie les votants
                if delegator_did not in self.voter_registry:
                    logger.warning(f"Délégant non enregistré: {delegator_did}")
                    return False
                
                if delegatee_did not in self.voter_registry:
                    logger.warning(f"Délégué non enregistré: {delegatee_did}")
                    return False
                
                delegator = self.voter_registry[delegator_did]
                delegatee = self.voter_registry[delegatee_did]
                
                # Vérifie les niveaux
                if delegator["level"] != session.level or delegatee["level"] != session.level:
                    logger.warning(f"Niveaux incompatibles")
                    return False
                
                # Vérifie le pouvoir de vote disponible
                if voting_power > delegator["voting_power"]:
                    logger.warning(f"Pouvoir de vote insuffisant: {voting_power}")
                    return False
                
                # Ajoute la délégation
                success = session.add_delegated_vote(
                    delegator_did=delegator_did,
                    delegatee_did=delegatee_did,
                    voting_power=voting_power,
                    vote_type=vote_type
                )
                
                if success:
                    # Met à jour le registre
                    delegator["voting_power"] -= voting_power
                    delegator["delegation_count"] += 1
                    
                    # Enregistre la chaîne de délégation
                    if delegator_did not in self.delegation_registry:
                        self.delegation_registry[delegator_did] = []
                    self.delegation_registry[delegator_did].append(delegatee_did)
                
                return success
                
            except Exception as e:
                logger.error(f"Erreur délégation vote: {e}")
                return False
    
    async def finalize_voting(self, proposal_id: str, 
                            total_available_power: float) -> Optional[Dict[str, Any]]:
        """
        Finalise une session de voting et calcule les résultats.
        
        Args:
            proposal_id: ID de la proposition
            total_available_power: Puissance de vote totale disponible
            
        Returns:
            Optional[Dict]: Résultats ou None
        """
        async with self._lock:
            try:
                if proposal_id not in self.sessions:
                    logger.warning(f"Session non trouvée: {proposal_id}")
                    return None
                
                session = self.sessions[proposal_id]
                
                # Vérifie que le voting est terminé
                if time.time() < session.end_time:
                    logger.warning(f"Voting toujours actif pour {proposal_id}")
                    return None
                
                # Calcule le quorum
                session.calculate_quorum(total_available_power)
                
                # Calcule les résultats
                results = session.calculate_results()
                
                logger.info(f"Voting finalisé pour {proposal_id}")
                return results
                
            except Exception as e:
                logger.error(f"Erreur finalisation voting: {e}")
                return None
    
    def get_voter_stats(self, voter_did: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les statistiques d'un votant.
        
        Args:
            voter_did: DID du votant
            
        Returns:
            Optional[Dict]: Statistiques ou None
        """
        if voter_did not in self.voter_registry:
            return None
        
        voter = self.voter_registry[voter_did]
        
        # Calcule l'activité
        days_since_last_vote = None
        if voter["last_vote_date"]:
            days_since_last_vote = (time.time() - voter["last_vote_date"]) / 86400
        
        # Calcule l'efficacité de vote
        vote_efficiency = 0.0
        if voter["total_votes_cast"] > 0:
            # Simule une efficacité basée sur la réputation et l'activité
            vote_efficiency = voter["reputation_score"] * 0.7
            if days_since_last_vote and days_since_last_vote < 30:
                vote_efficiency += 0.3
        
        stats = {
            **voter,
            "days_since_last_vote": days_since_last_vote,
            "vote_efficiency": vote_efficiency,
            "delegation_chain": self.delegation_registry.get(voter_did, []),
            "is_delegator": voter_did in self.delegation_registry,
            "delegatee_count": len(self.delegation_registry.get(voter_did, []))
        }
        
        return stats
    
    def get_session_analytics(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les analyses détaillées d'une session.
        
        Args:
            proposal_id: ID de la proposition
            
        Returns:
            Optional[Dict]: Analyses ou None
        """
        if proposal_id not in self.sessions:
            return None
        
        session = self.sessions[proposal_id]
        
        if not session.finalized:
            logger.warning(f"Session non finalisée: {proposal_id}")
            return None
        
        # Récupère la répartition des votes
        breakdown = session.get_vote_breakdown()
        
        # Analyse des tendances
        time_analysis = self._analyze_voting_timeline(session)
        
        # Analyse des clusters de vote
        cluster_analysis = self._analyze_vote_clusters(session)
        
        analytics = {
            "session_id": proposal_id,
            "level": session.level,
            "voting_system": session.voting_system.value,
            "total_voters": len(session.votes),
            "total_delegators": len(session.delegated_votes),
            "quorum_met": session.quorum_met,
            "approved": session.results.get("approved", False) if session.results else False,
            "participation_rate": session.results.get("participation_rate", 0) if session.results else 0,
            "vote_breakdown": breakdown,
            "time_analysis": time_analysis,
            "cluster_analysis": cluster_analysis,
            "timestamp": int(time.time())
        }
        
        return analytics
    
    def _analyze_voting_timeline(self, session: VotingSession) -> Dict[str, Any]:
        """Analyse la timeline des votes."""
        votes_by_hour = {}
        for vote_data in session.votes.values():
            hour = time.strftime('%H', time.localtime(vote_data["timestamp"]))
            votes_by_hour[hour] = votes_by_hour.get(hour, 0) + 1
        
        # Calcule les pics d'activité
        peak_hours = sorted(votes_by_hour.items(), key=lambda x: x[1], reverse=True)[:3]
        
        return {
            "votes_by_hour": votes_by_hour,
            "peak_hours": peak_hours,
            "total_hours": len(votes_by_hour),
            "avg_votes_per_hour": len(session.votes) / max(len(votes_by_hour), 1)
        }
    
    def _analyze_vote_clusters(self, session: VotingSession) -> Dict[str, Any]:
        """Analyse les clusters de votes par réputation."""
        clusters = {
            "high_reputation": {"for": 0, "against": 0, "abstain": 0, "count": 0},
            "medium_reputation": {"for": 0, "against": 0, "abstain": 0, "count": 0},
            "low_reputation": {"for": 0, "against": 0, "abstain": 0, "count": 0}
        }
        
        for vote_data in session.votes.values():
            rep_score = vote_data.get("reputation_score", 0.5)
            vote_type = vote_data["vote_type"]
            
            if rep_score >= 0.7:
                cluster = clusters["high_reputation"]
            elif rep_score >= 0.4:
                cluster = clusters["medium_reputation"]
            else:
                cluster = clusters["low_reputation"]
            
            cluster[vote_type] += 1
            cluster["count"] += 1
        
        # Calcule les pourcentages
        for cluster_name, cluster_data in clusters.items():
            total = cluster_data["count"]
            if total > 0:
                cluster_data["for_pct"] = (cluster_data["for"] / total) * 100
                cluster_data["against_pct"] = (cluster_data["against"] / total) * 100
                cluster_data["abstain_pct"] = (cluster_data["abstain"] / total) * 100
        
        return clusters