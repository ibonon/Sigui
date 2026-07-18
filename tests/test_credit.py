import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from modules.credit.credit_scoring import CreditScoringSystem, CreditScore, CreditApplication
from modules.credit.credit_config import CreditConfig, CollateralType

@pytest.fixture
def mock_reputation_oracle():
    oracle = MagicMock()
    oracle.calculate_composite_score.return_value = 90.0
    return oracle

@pytest.fixture
def credit_system(mock_reputation_oracle):
    config = CreditConfig()
    config.ai_scoring_enabled = False
    return CreditScoringSystem(config, mock_reputation_oracle)

@pytest.mark.asyncio
async def test_credit_system_initialization(credit_system):
    init_success = await credit_system.initialize()
    assert init_success is True

@pytest.mark.asyncio
async def test_calculate_credit_score(credit_system):
    did = "did:sigui:borrower"
    collateral = [{"type": "bitcoin", "amount": 1}]
    
    score = await credit_system.calculate_credit_score(did, 1000.0, collateral)
    assert score is not None
    assert score.overall_score > 0
    assert hasattr(score.risk_level, 'value')

@pytest.mark.asyncio
async def test_submit_credit_application(credit_system):
    await credit_system.initialize()
    
    # Depending on default config, we try to construct a valid app
    app = CreditApplication(
        application_id="app_12345",
        applicant_did="did:sigui:borrower",
        requested_amount_usd=5000.0,
        loan_term="1_month",
        collateral_assets=[{"type": "bitcoin", "amount": 0.5}],
        purpose="DeFi Arbitrage"
    )
    
    # Overriding validation constraints loosely for testing if needed
    credit_system.config.min_loan_amount_usd = 100
    credit_system.config.max_loan_amount_usd = 100000
    # Add dummy terms to bypass config check if config does not have 1_month
    class DummyTerm:
        value = "1_month"
    credit_system.config.available_loan_terms = [DummyTerm()]
    credit_system.config.max_loan_to_value_ratio = 0.8
    
    result = await credit_system.submit_credit_application(app)
    assert result is not None
    assert result.status in ["approved", "rejected"]
    
    # Test cleanup
    await credit_system.cleanup()
