import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from modules.governance.dao_manager import DAOManager, CommitteeMember, GovernanceProposal
from modules.governance.governance_config import GovernanceConfig, GovernanceLevel, ProposalType
from modules.reputation.reputation_oracle import ReputationOracle
from modules.credit.credit_scoring import CreditScoringSystem

@pytest.fixture
def mock_reputation_oracle():
    oracle = AsyncMock(spec=ReputationOracle)
    oracle.calculate_composite_score.return_value = 0.85
    return oracle

@pytest.fixture
def mock_credit_scoring():
    scoring = AsyncMock(spec=CreditScoringSystem)
    class DummyRisk:
        value = "A"
    class DummyScore:
        risk_level = DummyRisk()
    scoring.calculate_credit_score.return_value = DummyScore()
    return scoring

@pytest.fixture
def dao_manager(mock_reputation_oracle, mock_credit_scoring):
    config = GovernanceConfig()
    return DAOManager(config, mock_reputation_oracle, mock_credit_scoring)

@pytest.mark.asyncio
async def test_dao_initialization(dao_manager):
    assert len(dao_manager.daos) == len(dao_manager.config.governance_levels)
    assert GovernanceLevel.TECHNICAL in dao_manager.daos
    assert dao_manager.daos[GovernanceLevel.TECHNICAL]["status"].value == "active"

@pytest.mark.asyncio
async def test_register_member(dao_manager):
    did = "did:sigui:test_member"
    success = await dao_manager.register_member(did, GovernanceLevel.TECHNICAL)
    assert success is True
    assert len(dao_manager.committees[GovernanceLevel.TECHNICAL]) == 1
    assert dao_manager.committees[GovernanceLevel.TECHNICAL][0].did == did
    assert dao_manager.committees[GovernanceLevel.TECHNICAL][0].voting_power > 0

@pytest.mark.asyncio
async def test_create_and_vote_proposal(dao_manager):
    did = "did:sigui:proposer"
    await dao_manager.register_member(did, GovernanceLevel.TECHNICAL)
    
    proposal = await dao_manager.create_proposal(
        proposer_did=did,
        title="Upgrade Core",
        description="Version 2.0 update",
        proposal_type=ProposalType.PROTOCOL_UPGRADE,
        level=GovernanceLevel.TECHNICAL,
        parameters={"version": "2.0"}
    )
    assert proposal is not None
    assert proposal.status == "draft"
    
    # Start voting
    started = await dao_manager.start_voting_period(proposal.proposal_id)
    assert started is True
    assert proposal.status == "voting"
    
    # Cast vote
    member = dao_manager.committees[GovernanceLevel.TECHNICAL][0]
    vote_power = min(10.0, member.voting_power)
    voted = await dao_manager.cast_vote(proposal.proposal_id, did, "for", vote_power)
    assert voted is True
    assert proposal.votes_for == vote_power
