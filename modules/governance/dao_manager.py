"""
Gestionnaire de DAO multi-niveaux pour Sigui.
Gère les comités, les propositions et les décisions à différents niveaux de gouvernance.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass, field
import logging

from .governance_config import GovernanceConfig, GovernanceLevel, ProposalType
from modules.reputation.reputation_oracle import ReputationOracle
from modules.credit.credit_scoring import CreditScoringSystem

logger = logging.getLogger(__name__)


class DAOStatus(Enum):
    """Statut d'une DAO."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    UPGRADING = "upgrading"


class CommitteeMember:
    """Membre d'un comité de gouvernance."""
    
    def __init__(self, did: str, role: str, level: GovernanceLevel, 
                 reputation_score: float, voting_power: float):
        self.did = did
        self.role = role
        self.level = level
        self.reputation_score = reputation_score
        self.voting_power = voting_power
        self.joined_date = int(time.time())
        self.last_active = int(time.time())
        self.delegated_votes: Dict[str, float] = {}  # did -> voting_power
        self.voting_history: List[Dict] = []
    
    def update_activity(self):
        """Met à jour le timestamp d'activité."""
        self.last_active = int(time.time())
    
    def delegate_vote(self, delegate_did: str, voting_power: float):
        """Délègue une partie du pouvoir de vote."""
        if voting_power > self.voting_power:
            raise ValueError("Pouvoir de vote insuffisant")
        self.voting_power -= voting_power
        self.delegated_votes[delegate_did] = voting_power
    
    def revoke_delegation(self, delegate_did: str):
        """Révoque une délégation de vote."""
        if delegate_did in self.delegated_votes:
            self.voting_power += self.delegated_votes[delegate_did]
            del self.delegated_votes[delegate_did]


@dataclass
class GovernanceProposal:
    """Proposition de gouvernance."""
    proposal_id: str
    proposer_did: str
    title: str
    description: str
    proposal_type: ProposalType
    level: GovernanceLevel
    parameters: Dict[str, Any]
    created_date: int
    voting_start_date: Optional[int] = None
    voting_end_date: Optional[int] = None
    status: str = "draft"
    votes_for: float = 0.0
    votes_against: float = 0.0
    votes_abstain: float = 0.0
    total_voting_power: float = 0.0
    quorum_met: bool = False
    approved: bool = False
    execution_date: Optional[int] = None
    execution_result: Optional[Dict] = None
    discussion_thread: List[Dict] = field(default_factory=list)
    attachments: List[Dict] = field(default_factory=list)
    
    def add_discussion_message(self, author_did: str, message: str, 
                              sentiment_score: Optional[float] = None):
        """Ajoute un message à la discussion."""
        self.discussion_thread.append({
            "author_did": author_did,
            "message": message,
            "timestamp": int(time.time()),
            "sentiment_score": sentiment_score
        })
    
    def calculate_quorum(self, total_available_power: float) -> bool:
        """Calcule si le quorum est atteint."""
        if total_available_power == 0:
            return False
        participation_rate = self.total_voting_power / total_available_power
        self.quorum_met = participation_rate >= 0.3  # Seuil configurable
        return self.quorum_met
    
    def calculate_approval(self) -> bool:
        """Calcule si la proposition est approuvée."""
        if self.total_voting_power == 0:
            return False
        approval_rate = self.votes_for / (self.votes_for + self.votes_against)
        self.approved = approval_rate >= 0.6  # Seuil configurable
        return self.approved


class DAOManager:
    """Gestionnaire principal des DAO multi-niveaux."""
    
    def __init__(self, config: GovernanceConfig, 
                 reputation_oracle: ReputationOracle,
                 credit_scoring: CreditScoringSystem):
        self.config = config
        self.reputation_oracle = reputation_oracle
        self.credit_scoring = credit_scoring
        self.daos: Dict[GovernanceLevel, Dict[str, Any]] = {}
        self.committees: Dict[GovernanceLevel, List[CommitteeMember]] = {}
        self.proposals: Dict[str, GovernanceProposal] = {}
        self.voting_records: Dict[str, Dict[str, Dict]] = {}  # proposal_id -> voter_did -> vote
        self.delegation_chains: Dict[str, List[str]] = {}  # delegator -> [delegatees]
        self._lock = asyncio.Lock()
        
        # Initialise les DAO par niveau
        self._initialize_daos()
    
    def _initialize_daos(self):
        """Initialise les DAO pour chaque niveau de gouvernance."""
        for level in self.config.governance_levels:
            dao_id = f"dao_{level.value}_{uuid.uuid4().hex[:8]}"
            self.daos[level] = {
                "id": dao_id,
                "level": level,
                "status": DAOStatus.ACTIVE,
                "created_date": int(time.time()),
                "total_members": 0,
                "treasury_balance": 0.0,
                "active_proposals": 0,
                "executed_proposals": 0
            }
            self.committees[level] = []
            logger.info(f"DAO initialisée pour le niveau {level.value}: {dao_id}")
    
    async def register_member(self, did: str, level: GovernanceLevel) -> bool:
        """
        Enregistre un membre pour un niveau de gouvernance.
        
        Args:
            did: Identifiant décentralisé
            level: Niveau de gouvernance
            
        Returns:
            bool: True si l'enregistrement a réussi
        """
        async with self._lock:
            try:
                # Vérifie la réputation minimale
                reputation = await self.reputation_oracle.calculate_composite_score(did)
                if reputation < self.config.min_reputation_for_voting:
                    logger.warning(f"Réputation insuffisante pour {did}: {reputation}")
                    return False
                
                # Vérifie le score de crédit
                credit_score = await self.credit_scoring.calculate_credit_score(did)
                if credit_score.risk_level.value in ["D", "E", "F"]:
                    logger.warning(f"Score de crédit trop faible pour {did}: {credit_score.risk_level}")
                    return False
                
                # Calcule le pouvoir de vote initial
                voting_power = self._calculate_initial_voting_power(did, reputation, credit_score)
                
                # Crée le membre
                member = CommitteeMember(
                    did=did,
                    role="member",
                    level=level,
                    reputation_score=reputation,
                    voting_power=voting_power
                )
                
                # Ajoute au comité
                self.committees[level].append(member)
                self.daos[level]["total_members"] += 1
                
                logger.info(f"Membre enregistré: {did} pour le niveau {level.value}")
                return True
                
            except Exception as e:
                logger.error(f"Erreur enregistrement membre {did}: {e}")
                return False
    
    def _calculate_initial_voting_power(self, did: str, reputation: float, 
                                       credit_score: Any) -> float:
        """
        Calcule le pouvoir de vote initial basé sur la réputation et le crédit.
        
        Args:
            did: Identifiant décentralisé
            reputation: Score de réputation
            credit_score: Score de crédit
            
        Returns:
            float: Pouvoir de vote initial
        """
        # Facteur de réputation
        rep_factor = reputation * self.config.reputation_weight_factor
        
        # Facteur de crédit (inverse du risque)
        risk_map = {"A": 1.0, "B": 0.8, "C": 0.6, "D": 0.4, "E": 0.2, "F": 0.1}
        credit_factor = risk_map.get(credit_score.risk_level.value, 0.5)
        
        # Calcul combiné
        base_power = (rep_factor * 0.7) + (credit_factor * 0.3)
        
        # Applique le minimum
        return max(base_power, self.config.min_voting_power)
    
    async def create_proposal(self, proposer_did: str, title: str, description: str,
                            proposal_type: ProposalType, level: GovernanceLevel,
                            parameters: Dict[str, Any]) -> Optional[GovernanceProposal]:
        """
        Crée une nouvelle proposition de gouvernance.
        
        Args:
            proposer_did: DID du proposant
            title: Titre de la proposition
            description: Description détaillée
            proposal_type: Type de proposition
            level: Niveau de gouvernance
            parameters: Paramètres de la proposition
            
        Returns:
            Optional[GovernanceProposal]: Proposition créée ou None
        """
        async with self._lock:
            try:
                # Vérifie que le proposant est membre
                is_member = any(m.did == proposer_did for m in self.committees[level])
                if not is_member:
                    logger.warning(f"Proposant {proposer_did} n'est pas membre du niveau {level.value}")
                    return None
                
                # Vérifie les limites de trésorerie pour les dépenses
                if proposal_type == ProposalType.TREASURY_SPENDING:
                    amount = parameters.get("amount", 0)
                    if amount > self.config.max_treasury_spend_per_proposal:
                        logger.warning(f"Dépense trop élevée: {amount}")
                        return None
                
                # Crée la proposition
                proposal_id = f"prop_{uuid.uuid4().hex[:12]}"
                proposal = GovernanceProposal(
                    proposal_id=proposal_id,
                    proposer_did=proposer_did,
                    title=title,
                    description=description,
                    proposal_type=proposal_type,
                    level=level,
                    parameters=parameters,
                    created_date=int(time.time())
                )
                
                # Ajoute à la liste
                self.proposals[proposal_id] = proposal
                self.daos[level]["active_proposals"] += 1
                
                logger.info(f"Proposition créée: {proposal_id} par {proposer_did}")
                return proposal
                
            except Exception as e:
                logger.error(f"Erreur création proposition: {e}")
                return None
    
    async def start_voting_period(self, proposal_id: str, duration_days: Optional[int] = None) -> bool:
        """
        Démarre la période de voting pour une proposition.
        
        Args:
            proposal_id: ID de la proposition
            duration_days: Durée du voting en jours
            
        Returns:
            bool: True si le démarrage a réussi
        """
        async with self._lock:
            try:
                if proposal_id not in self.proposals:
                    logger.warning(f"Proposition non trouvée: {proposal_id}")
                    return False
                
                proposal = self.proposals[proposal_id]
                
                # Vérifie que la proposition est en draft
                if proposal.status != "draft":
                    logger.warning(f"Proposition {proposal_id} n'est pas en draft: {proposal.status}")
                    return False
                
                # Définit les dates de voting
                duration = duration_days or self.config.voting_duration_days
                proposal.voting_start_date = int(time.time())
                proposal.voting_end_date = proposal.voting_start_date + (duration * 86400)
                proposal.status = "voting"
                
                # Initialise les enregistrements de vote
                self.voting_records[proposal_id] = {}
                
                logger.info(f"Voting démarré pour {proposal_id}, durée: {duration} jours")
                return True
                
            except Exception as e:
                logger.error(f"Erreur démarrage voting: {e}")
                return False
    
    async def cast_vote(self, proposal_id: str, voter_did: str, 
                       vote_type: str, voting_power: float,
                       quadratic_cost: Optional[float] = None) -> bool:
        """
        Enregistre un vote pour une proposition.
        
        Args:
            proposal_id: ID de la proposition
            voter_did: DID du votant
            vote_type: Type de vote (for, against, abstain)
            voting_power: Puissance de vote utilisée
            quadratic_cost: Coût quadratique si applicable
            
        Returns:
            bool: True si le vote a été enregistré
        """
        async with self._lock:
            try:
                if proposal_id not in self.proposals:
                    logger.warning(f"Proposition non trouvée: {proposal_id}")
                    return False
                
                proposal = self.proposals[proposal_id]
                
                # Vérifie que le voting est actif
                if proposal.status != "voting":
                    logger.warning(f"Voting non actif pour {proposal_id}: {proposal.status}")
                    return False
                
                # Vérifie que le votant est membre
                is_member = any(m.did == voter_did for m in self.committees[proposal.level])
                if not is_member:
                    logger.warning(f"Votant {voter_did} n'est pas membre")
                    return False
                
                # Vérifie le pouvoir de vote disponible
                member = next(m for m in self.committees[proposal.level] if m.did == voter_did)
                if voting_power > member.voting_power:
                    logger.warning(f"Pouvoir de vote insuffisant: {voting_power} > {member.voting_power}")
                    return False
                
                # Applique le coût quadratique si configuré
                if self.config.voting_system.value == "quadratic_voting" and quadratic_cost:
                    actual_cost = quadratic_cost * self.config.quadratic_voting_cost_factor
                    if actual_cost > voting_power:
                        logger.warning(f"Coût quadratique trop élevé: {actual_cost}")
                        return False
                    voting_power = actual_cost
                
                # Enregistre le vote
                vote_record = {
                    "vote_type": vote_type,
                    "voting_power": voting_power,
                    "timestamp": int(time.time()),
                    "quadratic_cost": quadratic_cost
                }
                
                self.voting_records[proposal_id][voter_did] = vote_record
                
                # Met à jour les totaux
                if vote_type == "for":
                    proposal.votes_for += voting_power
                elif vote_type == "against":
                    proposal.votes_against += voting_power
                else:
                    proposal.votes_abstain += voting_power
                
                proposal.total_voting_power += voting_power
                
                # Met à jour l'historique du membre
                member.voting_history.append({
                    "proposal_id": proposal_id,
                    "vote_type": vote_type,
                    "voting_power": voting_power,
                    "timestamp": int(time.time())
                })
                member.update_activity()
                
                logger.info(f"Vote enregistré: {voter_did} -> {proposal_id} ({vote_type}: {voting_power})")
                return True
                
            except Exception as e:
                logger.error(f"Erreur enregistrement vote: {e}")
                return False
    
    async def finalize_voting(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        Finalise le voting et calcule les résultats.
        
        Args:
            proposal_id: ID de la proposition
            
        Returns:
            Optional[Dict]: Résultats du voting ou None
        """
        async with self._lock:
            try:
                if proposal_id not in self.proposals:
                    logger.warning(f"Proposition non trouvée: {proposal_id}")
                    return None
                
                proposal = self.proposals[proposal_id]
                
                # Vérifie que le voting est terminé
                if proposal.status != "voting":
                    logger.warning(f"Voting non actif pour {proposal_id}: {proposal.status}")
                    return None
                
                # Vérifie que la date de fin est passée
                if proposal.voting_end_date and proposal.voting_end_date > time.time():
                    logger.warning(f"Voting toujours actif pour {proposal_id}")
                    return None
                
                # Calcule le quorum
                total_members = len(self.committees[proposal.level])
                total_available_power = sum(m.voting_power for m in self.committees[proposal.level])
                quorum_met = proposal.calculate_quorum(total_available_power)
                
                # Calcule l'approbation
                approved = proposal.calculate_approval() if quorum_met else False
                
                # Met à jour le statut
                if approved:
                    proposal.status = "approved"
                    proposal.execution_date = int(time.time()) + (self.config.execution_delay_days * 86400)
                else:
                    proposal.status = "rejected"
                
                # Met à jour les statistiques DAO
                self.daos[proposal.level]["active_proposals"] -= 1
                if approved:
                    self.daos[proposal.level]["executed_proposals"] += 1
                
                # Prépare les résultats
                results = {
                    "proposal_id": proposal_id,
                    "title": proposal.title,
                    "level": proposal.level.value,
                    "votes_for": proposal.votes_for,
                    "votes_against": proposal.votes_against,
                    "votes_abstain": proposal.votes_abstain,
                    "total_voting_power": proposal.total_voting_power,
                    "quorum_met": quorum_met,
                    "approved": approved,
                    "participation_rate": proposal.total_voting_power / total_available_power if total_available_power > 0 else 0,
                    "approval_rate": proposal.votes_for / (proposal.votes_for + proposal.votes_against) if (proposal.votes_for + proposal.votes_against) > 0 else 0,
                    "voter_count": len(self.voting_records.get(proposal_id, {})),
                    "execution_date": proposal.execution_date
                }
                
                logger.info(f"Voting finalisé pour {proposal_id}: approved={approved}, quorum={quorum_met}")
                return results
                
            except Exception as e:
                logger.error(f"Erreur finalisation voting: {e}")
                return None
    
    async def execute_proposal(self, proposal_id: str, executor_did: str) -> Optional[Dict[str, Any]]:
        """
        Exécute une proposition approuvée.
        
        Args:
            proposal_id: ID de la proposition
            executor_did: DID de l'exécuteur
            
        Returns:
            Optional[Dict]: Résultat de l'exécution ou None
        """
        async with self._lock:
            try:
                if proposal_id not in self.proposals:
                    logger.warning(f"Proposition non trouvée: {proposal_id}")
                    return None
                
                proposal = self.proposals[proposal_id]
                
                # Vérifie que la proposition est approuvée
                if proposal.status != "approved":
                    logger.warning(f"Proposition {proposal_id} n'est pas approuvée: {proposal.status}")
                    return None
                
                # Vérifie la date d'exécution
                if proposal.execution_date and proposal.execution_date > time.time():
                    logger.warning(f"Date d'exécution non encore atteinte pour {proposal_id}")
                    return None
                
                # Vérifie que l'exécuteur est autorisé
                is_member = any(m.did == executor_did for m in self.committees[proposal.level])
                if not is_member:
                    logger.warning(f"Exécuteur {executor_did} non autorisé")
                    return None
                
                # Exécute selon le type
                execution_result = await self._execute_proposal_logic(proposal)
                
                # Met à jour la proposition
                proposal.status = "executed"
                proposal.execution_result = execution_result
                
                logger.info(f"Proposition exécutée: {proposal_id} par {executor_did}")
                return execution_result
                
            except Exception as e:
                logger.error(f"Erreur exécution proposition: {e}")
                return None
    
    async def _execute_proposal_logic(self, proposal: GovernanceProposal) -> Dict[str, Any]:
        """
        Logique d'exécution selon le type de proposition.
        
        Args:
            proposal: Proposition à exécuter
            
        Returns:
            Dict: Résultat de l'exécution
        """
        try:
            result = {
                "proposal_id": proposal.proposal_id,
                "execution_timestamp": int(time.time()),
                "success": True,
                "details": {}
            }
            
            if proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
                # Changement de paramètres système
                result["details"]["action"] = "parameter_update"
                result["details"]["parameters"] = proposal.parameters
                
            elif proposal.proposal_type == ProposalType.TREASURY_SPENDING:
                # Dépense du trésor
                amount = proposal.parameters.get("amount", 0)
                recipient = proposal.parameters.get("recipient")
                result["details"]["action"] = "treasury_spend"
                result["details"]["amount"] = amount
                result["details"]["recipient"] = recipient
                
            elif proposal.proposal_type == ProposalType.PROTOCOL_UPGRADE:
                # Mise à jour du protocole
                version = proposal.parameters.get("version")
                result["details"]["action"] = "protocol_upgrade"
                result["details"]["version"] = version
                
            elif proposal.proposal_type == ProposalType.COMMITTEE_ELECTION:
                # Élection de comité
                members = proposal.parameters.get("members", [])
                result["details"]["action"] = "committee_election"
                result["details"]["members"] = members
                
            elif proposal.proposal_type == ProposalType.EMERGENCY_ACTION:
                # Action d'urgence
                action = proposal.parameters.get("action")
                result["details"]["action"] = "emergency_action"
                result["details"]["emergency_action"] = action
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur logique exécution: {e}")
            return {
                "proposal_id": proposal.proposal_id,
                "execution_timestamp": int(time.time()),
                "success": False,
                "error": str(e)
            }
    
    def get_dao_stats(self, level: GovernanceLevel) -> Optional[Dict[str, Any]]:
        """
        Récupère les statistiques d'une DAO.
        
        Args:
            level: Niveau de gouvernance
            
        Returns:
            Optional[Dict]: Statistiques ou None
        """
        if level not in self.daos:
            return None
        
        dao = self.daos[level]
        committee = self.committees[level]
        
        # Calcule les statistiques avancées
        active_members = len([m for m in committee if time.time() - m.last_active < 86400])
        avg_reputation = sum(m.reputation_score for m in committee) / len(committee) if committee else 0
        avg_voting_power = sum(m.voting_power for m in committee) / len(committee) if committee else 0
        
        stats = {
            **dao,
            "active_members": active_members,
            "inactive_members": len(committee) - active_members,
            "avg_reputation": avg_reputation,
            "avg_voting_power": avg_voting_power,
            "total_voting_power": sum(m.voting_power for m in committee),
            "proposal_success_rate": dao["executed_proposals"] / max(dao["executed_proposals"] + (dao["active_proposals"] // 2), 1)
        }
        
        return stats
    
    def get_proposal_details(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les détails d'une proposition.
        
        Args:
            proposal_id: ID de la proposition
            
        Returns:
            Optional[Dict]: Détails ou None
        """
        if proposal_id not in self.proposals:
            return None
        
        proposal = self.proposals[proposal_id]
        votes = self.voting_records.get(proposal_id, {})
        
        details = {
            "proposal_id": proposal.proposal_id,
            "title": proposal.title,
            "description": proposal.description,
            "proposal_type": proposal.proposal_type.value,
            "level": proposal.level.value,
            "proposer_did": proposal.proposer_did,
            "status": proposal.status,
            "created_date": proposal.created_date,
            "voting_start_date": proposal.voting_start_date,
            "voting_end_date": proposal.voting_end_date,
            "parameters": proposal.parameters,
            "votes_for": proposal.votes_for,
            "votes_against": proposal.votes_against,
            "votes_abstain": proposal.votes_abstain,
            "total_voting_power": proposal.total_voting_power,
            "quorum_met": proposal.quorum_met,
            "approved": proposal.approved,
            "execution_date": proposal.execution_date,
            "execution_result": proposal.execution_result,
            "voter_count": len(votes),
            "discussion_count": len(proposal.discussion_thread),
            "attachment_count": len(proposal.attachments)
        }
        
        return details