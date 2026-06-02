# @sigui/plugin-eliza

The official Sigui Protocol security plugin for ElizaOS.

This plugin equips your autonomous Eliza agents with the Sigui AI Security Oracle. Before your agent signs a transaction or interacts with a smart contract, this plugin evaluates the destination address and transaction amount against the Sigui Trustformer model to detect threats like Drain Stars, Rug Pulls, and Mixer Chains.

If a threat is detected, the plugin forces a `BLOCK` and prevents the agent from losing funds, adhering to a fail-closed security policy.

## Installation

```bash
npm install @sigui/plugin-eliza
```

## Configuration

Set the following environment variables in your `.env` file:

```env
SIGUI_API_URL=https://api.sigui.io
SIGUI_API_KEY=your_api_key_here  # Optional
```

*Note: For testing, you can use the Sigui local mock server endpoint `http://localhost:8000`.*

## Usage

Register the plugin with your ElizaOS agent runtime:

```typescript
import { AgentRuntime } from "@elizaos/core";
import { siguiPlugin } from "@sigui/plugin-eliza";

const runtime = new AgentRuntime({
    // ... your agent config ...
    plugins: [siguiPlugin],
});
```

The plugin automatically registers the `EVALUATE_TRANSACTION_SECURITY` action. When the agent detects an intent to transfer funds, it will trigger this action, call the Sigui API, and append the security verdict (ALLOW/BLOCK/ESCALATE) to its memory context.

## Security Model

- **ALLOW:** Proceed normally.
- **BLOCK:** The transaction is highly dangerous. The action injects a hard stop into the agent's context.
- **ESCALATE:** Ambiguous risk. The agent is instructed to ask a human operator for explicit confirmation before proceeding.

## License
MIT
