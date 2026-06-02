# Sigui Autonomous Ecosystem

This module runs 4 real autonomous agents in-process with Sigui:

- `agent_payer`: normal payment behavior, pays `/evaluate`, reacts to `ALLOW/BLOCK/ESCALATE`
- `agent_attacker`: rotates attack strategies and replays blocked patterns
- `agent_monitor`: polls Sigui endpoints and writes `metrics.json`
- `agent_learner`: warms up with normal behavior, then mimics attacker pattern and tracks detection latency

## 1) Configure wallets

Set these variables in `.env`:

- `SIGUI_WALLET_ID`
- `SIGUI_WALLET_ADDRESS`
- `PAYER_WALLET_ID`
- `ATTACKER_WALLET_ID`
- `MONITOR_WALLET_ID`
- `LEARNER_WALLET_ID`
- `CIRCLE_API_KEY`
- `ARC_RPC_URL`
- `ARC_CHAIN_ID`

## 2) Get Arc testnet USDC

1. Create or import your Circle Developer-Controlled wallets in Circle Console.
2. Fund each wallet on Arc testnet via faucet/USDC distribution used by the hackathon.
3. Confirm balances before starting:
   - Payer, Attacker, Learner need spendable USDC.
   - Monitor can run with 0 USDC (observe-only).

If a wallet has no balance, the corresponding agent enters `observe-only` mode automatically.

## 3) Run Sigui + ecosystem

```bash
uvicorn main:app --reload --port 8000
```

Ecosystem runs automatically in FastAPI lifespan startup.

## 4) Observe runtime state

- API: `GET /ecosystem/status`
- Submission report: `GET /demo/report` (also writes `ecosystem/demo_report.json`)
- Monitor output: `ecosystem/metrics.json`
- Dashboard: `streamlit run dashboard/app.py`

