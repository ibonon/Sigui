# Sigui Security

Sigui Security is an OpenClaw code plugin that performs preflight security checks on risky blockchain tool calls before execution.

It intercepts selected tool invocations, extracts the transaction intent, sends the evaluation request to a Sigui backend, and then decides whether OpenClaw should allow, require approval for, escalate, or block the action.

The plugin is designed for agents that can move value across blockchain ecosystems and need a policy layer in front of wallet, transfer, swap, approval, and transaction tools.

## What It Does

- Screens risky blockchain tool calls before execution.
- Evaluates transaction intent across Ethereum/EVM, Starknet, and Aptos style flows.
- Calls a Sigui API for a policy decision using `/evaluate` and optionally `/escalate`.
- Supports `enforce` mode for automatic blocking and `approval-only` mode for manual review.
- Fails closed by default when the Sigui backend is unavailable.
- Adds structured approval prompts with action, chain, amount, destination, risk score, reason, and proof link when available.

## How It Works

At runtime, the plugin subscribes to the `before_tool_call` hook and inspects tool calls before they execute.

For watched tools, it attempts to infer:

- action type, such as `transfer`, `approve`, `swap`, `sign`, or generic `transaction`
- execution chain, such as `ethereum`, `starknet`, or `aptos`
- destination address
- amount or transfer value when available

It then sends a payload to the configured Sigui backend:

- `POST {apiUrl}/evaluate`
- `POST {apiUrl}/escalate` when `autoEscalate=true` and the first verdict is `ESCALATE`

The backend response is normalized into a decision that OpenClaw can enforce.

## Decision Model

Sigui Security supports the following outcomes:

| Verdict | Behavior |
| --- | --- |
| `ALLOW` | The tool call proceeds normally. |
| `ALLOW_WITH_CAP` | The tool call requires manual approval and includes the cap amount in the approval description. |
| `ESCALATE` | The tool call requires manual approval with elevated visibility into the risk context. |
| `BLOCK` | The tool call is blocked immediately in `enforce` mode. |

The plugin also maps decisions into OpenClaw approval severities:

- `critical` when the verdict is `BLOCK` or the risk score is above `blockThreshold`
- `warning` when the verdict is `ESCALATE` or the risk score is above `escalateThreshold`
- `info` otherwise

## Default Behavior

By default, the plugin:

- starts on OpenClaw startup
- runs in `enforce` mode
- blocks when `riskScore >= 0.85`
- escalates when `riskScore >= 0.55`
- times out after `10000` ms
- fails closed when the backend is unavailable
- watches the following tools:
  - `evm_send_transaction`
  - `aptos_submit_transaction`
  - `starknet_send_transaction`
  - `wallet_transfer`
  - `wallet_approve`
  - `wallet_swap`

## Installation

Install from ClawHub:

```bash
openclaw plugins install clawhub:@ibonon/openclaw-sigui-security
```

If you are developing locally, you can also work directly from the plugin folder:

```bash
cd openclaw-plugin-sigui
```

## Requirements

- OpenClaw compatible with:
  - `pluginApi >= 2026.3.24-beta.2`
  - `minGatewayVersion >= 2026.3.24-beta.2`
- Node.js 22 or newer is recommended for OpenClaw plugin development and publishing
- A reachable Sigui backend exposing the required API endpoints

## Configuration

The plugin declares the following configuration schema in `openclaw.plugin.json`.

### Config Fields

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `enabled` | `boolean` | `true` | Enables or disables the plugin. |
| `apiUrl` | `string` | `http://127.0.0.1:8765` | Base URL of the Sigui backend. Trailing slashes are trimmed. |
| `apiKeyEnvVar` | `string` | `SIGUI_API_KEY` | Name of the environment variable holding the API key. |
| `agentId` | `string` | `openclaw_agent` | Agent identifier sent to the Sigui backend. |
| `mode` | `string` | `enforce` | Either `enforce` or `approval-only`. |
| `blockThreshold` | `number` | `0.85` | Risk score threshold above which requests are blocked. |
| `escalateThreshold` | `number` | `0.55` | Risk score threshold above which requests are elevated in UI severity. |
| `autoEscalate` | `boolean` | `false` | Automatically calls `/escalate` when the first verdict is `ESCALATE`. |
| `failOpen` | `boolean` | `false` | If `true`, backend failures trigger manual approval instead of hard block. |
| `timeoutMs` | `integer` | `10000` | Timeout for backend requests. |
| `watchedTools` | `string[]` | built-in list | Explicit tool names to inspect. |

### Recommended Production Configuration

```json
{
  "enabled": true,
  "apiUrl": "https://api.sigui.example",
  "apiKeyEnvVar": "SIGUI_API_KEY",
  "agentId": "treasury-prod-agent",
  "mode": "enforce",
  "blockThreshold": 0.85,
  "escalateThreshold": 0.55,
  "autoEscalate": true,
  "failOpen": false,
  "timeoutMs": 10000,
  "watchedTools": [
    "evm_send_transaction",
    "starknet_send_transaction",
    "wallet_transfer",
    "wallet_approve",
    "wallet_swap"
  ]
}
```

### Safer Rollout Configuration

If you want to evaluate behavior before enforcing blocks:

```json
{
  "enabled": true,
  "mode": "approval-only",
  "autoEscalate": true,
  "failOpen": true
}
```

This mode is useful for pilots, audits, internal testing, and staged deployment.

## Environment Variables

If your Sigui backend requires authentication, set the configured API key environment variable before running OpenClaw.

Example:

```bash
export SIGUI_API_KEY="your_sigui_api_key"
```

The plugin automatically sends:

- `Authorization: Bearer <value>` when the environment variable is present
- `X-Chain`
- `X-Amount`
- `User-Agent: openclaw-sigui-security/0.1.1`

## API Contract

The plugin expects a Sigui backend that supports the following endpoints.

### `POST /evaluate`

Request body:

```json
{
  "agent_id": "openclaw_agent",
  "action_type": "transfer",
  "amount_usdc": 1500,
  "destination": "0xabc...",
  "chain": "ethereum",
  "context": {
    "tool_name": "wallet_transfer",
    "tool_call_id": "tool-call-id",
    "run_id": "run-id",
    "session_id": "session-id",
    "session_key": "session-key",
    "raw_params": {
      "to": "0xabc...",
      "amount": 1500
    }
  },
  "weights": {}
}
```

Typical response fields consumed by the plugin:

```json
{
  "decision": "ESCALATE",
  "risk_score": 0.74,
  "reason": "Suspicious approval pattern",
  "chain": "ethereum",
  "confidence": 0.93,
  "onchain_proof": "https://example.com/proof/123"
}
```

### `POST /escalate`

This endpoint is only used when:

- `autoEscalate=true`
- the initial verdict is `ESCALATE`

Typical response fields consumed by the plugin:

```json
{
  "escalation_result": "APPROVE",
  "reason": "Approved with spend cap",
  "confidence": 0.91,
  "cap_amount_usdc": 500,
  "analysis": "Counterparty risk acceptable for limited spend",
  "arc_tx_log": "0xdeadbeef"
}
```

When `escalation_result` is `APPROVE`, the plugin converts it into `ALLOW_WITH_CAP`.

## Approval and Blocking UX

When manual review is required, the plugin generates an approval dialog containing:

- tool name
- action type
- chain
- amount
- destination
- verdict
- risk score
- reason
- cap amount when present
- proof URL when present

When blocking is enforced, the plugin returns a compact block reason such as:

```text
Sigui blocked approve on ethereum: token approval detected, large transaction amount (risk 0.91).
```

## Fallback and Failure Handling

By default, the plugin fails closed:

- if the backend cannot be reached
- if the backend returns an invalid response
- if the request times out

In that case, the tool call is blocked.

If `failOpen=true`, backend failures become a manual approval gate instead of an automatic block. This is useful for development or partial outage tolerance, but it is less strict from a security standpoint.

## Local Development

Install dependencies in the host OpenClaw environment as needed, then test the plugin with a reachable Sigui API.

A minimal local workflow:

```bash
cd openclaw-plugin-sigui
openclaw plugins inspect sigui-security --runtime --json
```

To install the published package after release:

```bash
openclaw plugins install clawhub:@ibonon/openclaw-sigui-security
```

## Repository Files

```text
openclaw-plugin-sigui/
├── index.js               # Plugin runtime and policy logic
├── openclaw.plugin.json   # Plugin manifest and config schema
├── package.json           # Package metadata and OpenClaw compatibility
└── README.md              # Plugin documentation
```

## Security Notes

- The plugin does not execute blockchain transactions itself. It intercepts existing tool calls and applies policy before execution.
- Security quality depends on both intent extraction and the correctness of the Sigui backend verdicts.
- Tools with names outside `watchedTools` can still be reviewed when their parameters look like a transaction intent, but explicit listing is recommended for predictable coverage.
- If intent cannot be reliably classified for a watched tool, the plugin requests manual approval instead of allowing the call blindly.

## Example Use Cases

- Review wallet transfer requests before an agent moves funds
- Block suspicious token approval calls
- Escalate high-value swaps for human approval
- Add a policy gate in front of Starknet or Aptos transaction tools
- Enforce treasury controls for autonomous or semi-autonomous agents

## Publishing

ClawHub documentation recommends publishing plugins with the `clawhub` CLI. A dry run is the safest first step:

```bash
clawhub package publish ./openclaw-plugin-sigui --dry-run
```

Then publish:

```bash
clawhub package publish ./openclaw-plugin-sigui
```

After publishing, users can install the plugin with:

```bash
openclaw plugins install clawhub:@ibonon/openclaw-sigui-security
```

## Version

Current local package version:

- `0.1.2`

## License

MIT
