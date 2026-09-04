# @elizaos-plugins/plugin-sigui

Sigui Security Oracle plugin for **ElizaOS** agents. Pre-evaluates transactions against fine-tuned vision models (Qwen2-VL-7B on AMD MI300X), ZK proofs (Groth16 BN128), and dynamic threat blacklists.

## Installation

```bash
npm install @elizaos-plugins/plugin-sigui
```

## Usage

```typescript
import { siguiPlugin } from "@elizaos-plugins/plugin-sigui";

export default {
  plugins: [siguiPlugin],
};
```
