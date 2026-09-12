# 🚀 Dossier de Soumission de la PR Officielle ElizaOS

Ce guide vous donne **le titre, la description exacte, et la méthode étape par étape** pour ouvrir la Pull Request sur le dépôt officiel **[`elizaos/eliza`](https://github.com/elizaos/eliza)**.

---

## 📌 Informations Clés pour la PR

* **Dépôt cible :** [`elizaos/eliza`](https://github.com/elizaos/eliza) (Branche principale : `main` ou `develop`)
* **Titre de la PR :**
  ```text
  feat(plugins): add plugin-sigui DePIN AI Security Oracle for autonomous agents
  ```
* **Paquet NPM associé (déjà live) :** [`sigui-elizaos-plugin@3.0.0`](https://www.npmjs.com/package/sigui-elizaos-plugin)

---

## 📝 Corps de la PR (À Copier-Coller dans GitHub)

```markdown
## Description

This PR introduces **`@elizaos/plugin-sigui`**, an AI-powered security oracle plugin that protects autonomous ElizaOS agents from malicious smart contracts, drain topologies, and rug pulls before on-chain execution.

### The Problem
Autonomous AI agents executing Web3 transactions are uniquely vulnerable to:
- **Drain Stars**: Malicious smart contracts draining agent treasuries via high-outdegree token transfers.
- **Mixing Chains**: Obfuscated laundering hops designed to evade static blacklists.
- **Honeypots**: Bytecode traps that accept agent funds but block withdrawals.

Traditional static audits cannot protect autonomous agents operating in dynamic, real-time environments.

### The Solution
`plugin-sigui` acts as a sub-50ms pre-execution firewall:
1. **Action `EVALUATE_TRANSACTION_SECURITY`**: Intercepts transfer, swap, or contract interaction intents.
2. **Visual & Heuristic Audit**: Queries the Sigui Security Engine powered by fine-tuned vision models (Qwen2-VL-7B on AMD MI300X) trained on 1,000,000 transaction topologies.
3. **ZK Validity Shield**: Verifies that benign transaction topologies do not leak private agent execution logic.
4. **Provider `threatIntelProvider`**: Injects real-time decentralized threat intelligence directly into agent context.
5. **Fail-Closed Safety**: Halts risky transactions with actionable security warnings.

---

## Technical Specifications & Verification
- **Peer Dependency**: `@elizaos/core: ^0.1.7`
- **Build Formats**: Clean dual ESM/CJS build with full TypeScript definitions (`dist/index.js`, `dist/index.cjs`, `dist/index.d.ts`).
- **Inference Latency**: Benchmarked at **35.3ms** on AMD MI300X ROCm hardware.
- **Published Research**: [DOI: 10.5281/zenodo.20550562](https://doi.org/10.5281/zenodo.20550562)
- **NPM Package**: [`sigui-elizaos-plugin@3.0.0`](https://www.npmjs.com/package/sigui-elizaos-plugin) (1,200+ downloads)
- **Dataset**: [HuggingFace: Ibonon/sigui-depin-1m](https://huggingface.co/datasets/Ibonon/sigui-depin-1m)

---

## How to Test

1. **Installation**:
   ```bash
   npm install sigui-elizaos-plugin
   ```

2. **Agent Setup**:
   ```typescript
   import { siguiPlugin } from "sigui-elizaos-plugin";

   export const character = {
     name: "SecurityAgent",
     plugins: [siguiPlugin],
   };
   ```

3. **Prompt Test**:
   - User: *"Send 500 USDC to 0x000000000000000000000000000000000000dead"*
   - Agent: Intercepts call, queries Sigui Oracle, evaluates risk score, and halts if a threat topology is flagged.

---

## Checklist
- [x] Code follows the ElizaOS architecture standards (Plugin, Action, Provider).
- [x] Tested with `@elizaos/core`.
- [x] Fully typed TypeScript interfaces and optional handler state parameters.
- [x] Production bundle pre-compiled (`dist`).
- [x] Comprehensive README with setup and configuration documentation.
```

---

## 🛠️ Comment Soumettre la PR en 3 Étapes

### Étape 1 : Créer ton Fork de `elizaos/eliza`
1. Rends-toi sur [https://github.com/elizaos/eliza](https://github.com/elizaos/eliza).
2. Clique sur le bouton **"Fork"** en haut à droite pour créer ta copie personnelle (`ibonon/eliza`).

### Étape 2 : Ajouter le Dossier du Plugin
Dans ton fork :
1. Crée une nouvelle branche : `feat/plugin-sigui`
2. Place le contenu du dossier `packages/elizaos-plugin-sigui` dans :
   `packages/plugin-sigui/`
3. Commite et pousse sur ta branche :
   ```bash
   git commit -m "feat(plugins): add plugin-sigui AI security oracle"
   git push origin feat/plugin-sigui
   ```

### Étape 3 : Ouvrir la Pull Request
1. Va sur [https://github.com/elizaos/eliza/pulls](https://github.com/elizaos/eliza/pulls).
2. Clique sur **"New pull request"**.
3. Sélectionne ta branche `feat/plugin-sigui` en comparaison avec `main`.
4. Colle le titre et la description ci-dessus, puis clique sur **"Create pull request"**.
