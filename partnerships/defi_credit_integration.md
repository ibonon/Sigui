# 🏦 Sigui × DeFi — Agent Credit Integration Proposal

> **For: Aave, Morpho, Compound, Euler Finance**
> Version 1.0 — June 2026

---

## The Problem You Can't Solve Alone

Your protocol can lend $1B to a human with collateral. You cannot lend $1 to an AI agent —
not because the agent is untrustworthy, but because you have no way to *measure* its trustworthiness.

**The AI agent economy is already here:**
- 400,000+ ElizaOS agents deployed globally
- Virtuals Protocol: 10,000+ tokenized AI agents with real wallets
- Autonolas: 500+ autonomous on-chain services managing real funds

These agents want credit. They generate yield. They have track records.
**You cannot access this market without a trust infrastructure.**

---

## What Sigui Offers: The Agent Credit Score

Sigui's **ERC-8259 AgentRegistry** (live on Ethereum Sepolia:
`0x3806aeb76eDD2E22D3cF66A163113c4b24243b29`) generates a
**cryptographic credit score** for every registered AI agent.

### Score Components (0–1000)

```
┌────────────────────────────────────────────────────────┐
│  SIGUI AGENT CREDIT SCORE                              │
├────────────────────────────────────────────────────────┤
│  Identity Continuity    ████████████░░░░░  25%         │
│  Transaction History    ████████████████░  30%         │
│  Threat Intel Clean     ████████░░░░░░░░░  20%         │
│  Cross-chain Activity   ████░░░░░░░░░░░░░  10%         │
│  Verification Tier      ████░░░░░░░░░░░░░  10%         │
│  Insurance Coverage     ██░░░░░░░░░░░░░░░   5%         │
├────────────────────────────────────────────────────────┤
│  Example Agent Score: 950 / 1000                       │
│  Recommended Credit Limit: $5,000,000 USDC             │
│  Suggested Rate Discount:  -15 BPS                     │
└────────────────────────────────────────────────────────┘
```

### Real-Time Behavioral Verification

Unlike a static score, Sigui evaluates **every transaction** the agent initiates
using **Imina Na V2** (a Qwen2-VL-7B fine-tuned on 1,000,000 transaction graph topologies):

- `DRAIN_STAR` topology detected → Credit limit suspended, alert sent
- `MIXING_CHAIN` pattern → Risk tier downgrade, collateral ratio increase
- `COORDINATED_CLUSTER` → Immediate position freeze, liquidation protection triggered

---

## Integration Architecture

### Option A: Pre-Transaction Hook (Recommended)

```solidity
// In your lending pool contract:
interface ISiguiOracle {
    function getAgentScore(address agentDID) external view returns (uint256 score);
    function evaluateTransaction(
        address agent,
        address destination,
        uint256 amount
    ) external returns (bool allowed, uint8 riskTier);
}

// Usage:
ISiguiOracle sigui = ISiguiOracle(0x3806aeb76eDD2E22D3cF66A163113c4b24243b29);

function borrow(uint256 amount, address agent) external {
    (bool allowed, uint8 tier) = sigui.evaluateTransaction(agent, address(this), amount);
    require(allowed, "Sigui: transaction blocked");

    uint256 score = sigui.getAgentScore(agent);
    uint256 maxBorrow = calculateCreditLimit(score);  // score-based credit line
    require(amount <= maxBorrow, "Sigui: exceeds agent credit limit");

    // proceed with lending logic...
}
```

### Option B: SDK Integration (Python/TypeScript)

```python
from sigui import SiguiClient

client = SiguiClient(api_url="https://api.sigui.io")

# Before approving a loan:
evaluation = await client.evaluate_with_identity(
    amount=5_000_000,  # $5M USDC
    destination=pool_address,
    agent_did=borrowing_agent_did
)

if evaluation.decision == "ALLOW" and evaluation.score >= 800:
    approve_loan(amount=5_000_000, rate=base_rate - 15)  # preferential rate
```

---

## Revenue Share Proposal

Sigui takes a **fraction of your underwriting fee** only when:
1. The loan was granted based on a Sigui credit score ≥ 700
2. The loan was repaid successfully (success fee model)
3. Sigui's threat engine did not flag the agent during the loan period

| Loan Size | Sigui Fee | Your Risk | Example |
|---|---|---|---|
| < $100k | 2 BPS | Low | $2 for a $100k loan |
| $100k – $1M | 3 BPS | Medium | $30 for a $1M loan |
| > $1M | 5 BPS | Mitigated by Sigui | $250 for a $5M loan |

**For Aave at $15B TVL:** If 10% of loans go to AI agents via Sigui,
that's $1.5B in agent loans → **$75k-$750k/year in Sigui fees** (mostly your margin).

---

## Why Now

1. **ElizaOS has 12,000+ GitHub stars** — the agent economy is not theoretical
2. **Virtuals Protocol** agents already hold real tokens and execute real DeFi transactions
3. **First mover advantage** — No other protocol has solved agent creditworthiness
4. **Regulatory moat** — ERC-8259 is being submitted as an Ethereum Improvement Proposal

---

## Next Steps

We propose a **3-month pilot integration** on your testnet:

- Week 1-2: Smart contract integration + score feed setup
- Week 3-4: Shadow mode (score logged but not enforced)
- Week 5-8: Soft enforcement (score-based rate adjustment only)
- Week 9-12: Full enforcement + credit limits

**No cost to you during the pilot.** We take BPS only on repaid loans.

---

**Contact:**
- GitHub: [github.com/ibonon/Sigui](https://github.com/ibonon/Sigui)
- ERC-8259 Contract: `0x3806aeb76eDD2E22D3cF66A163113c4b24243b29`
- Etherscan: https://sepolia.etherscan.io/address/0x3806aeb76eDD2E22D3cF66A163113c4b24243b29

*Sigui Protocol — The Trust Infrastructure for the Autonomous Economy*
