# 🤝 Contributing to Sigui Protocol

First off — **thank you** for taking the time to contribute. Sigui is building the trust infrastructure for the autonomous economy, and every contribution makes AI agents safer for everyone.

Whether you're fixing a typo, adding a new framework wrapper, or proposing a novel detection pattern, **you belong here**.

---

## 📋 Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Environment Setup](#development-environment-setup)
4. [Good First Issues](#-good-first-issues)
5. [Contributing New Detection Patterns (Yurugu Layer)](#-contributing-new-detection-patterns-yurugu-layer)
6. [Pull Request Guidelines](#pull-request-guidelines)
7. [Commit Message Convention](#commit-message-convention)
8. [Reporting Bugs](#reporting-bugs)

---

## Code of Conduct

This project follows a simple rule: **be excellent to each other**. We are a global, open-source community. Discrimination of any kind will not be tolerated. Please be constructive, patient, and kind.

---

## Getting Started

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/<your-username>/Sigui.git
   cd Sigui
   ```
3. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```

---

## Development Environment Setup

### Option A: pip + venv (recommended for quick start)

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\activate        # Windows PowerShell

# Install all dependencies
pip install -r requirements.txt

# Install the SDK in editable mode (optional, for SDK development)
pip install -e sdk/python/

# Run the gateway locally
uvicorn main:app --port 8000 --reload
```

### Option B: Poetry (for dependency management)

```bash
pip install poetry
poetry install
poetry run uvicorn main:app --port 8000 --reload
```

### Option C: Docker (full NexusMind stack)

The full stack — including the NexusMind P2P mesh, the Sigui Gateway, and the Next.js Dashboard — can be launched with a single command:

```bash
docker compose up --build
```

This will start:
| Service | URL |
|---|---|
| Sigui Gateway (FastAPI) | http://localhost:8000 |
| NexusMind P2P Tracker | ws://localhost:8000/ws/nexus |
| Demo Dashboard (Next.js) | http://localhost:3000 |

> **AMD MI300X users**: See `requirements_amd.txt` and `record_amd_demo.sh` for the ROCm-optimized setup.

### Running Tests

```bash
pytest tests/ -v
```

---

## 🌱 Good First Issues

New to the project? Here are concrete, well-scoped tasks that are perfect starting points:

### 🌍 Translations
The Sigui Protocol aims to be accessible globally. Help us translate documentation and in-code comments into:
- French (`fr`)
- Arabic (`ar`)
- Portuguese (`pt`)
- Swahili (`sw`)

Start by adding your language to the `docs/` folder or translating the top-level `README.md`.

### 🤖 Agent Framework Wrappers

The SDK currently supports LangChain, CrewAI, ElizaOS, and smolagents. We'd love community-built wrappers for:

| Framework | Effort | Notes |
|---|---|---|
| **smolagents** (HuggingFace) | Medium | See `sdk/python/sigui/integrations/smolagents.py` as reference |
| **AutoGen** (Microsoft) | Medium | `AgentChat` pattern — wrap `SiguiClient.evaluate()` as a tool |
| **Semantic Kernel** (Microsoft) | Medium | Use the `KernelFunction` decorator pattern |
| **Atomic Agents** | Low | Thin wrapper around `SiguiClient` |
| **LlamaIndex** | Low | Agent tool integration |

Each wrapper should live in `sdk/python/sigui/integrations/<framework_name>.py` and follow the pattern established in `sdk/python/sigui/integrations/langchain.py`.

### 📊 Dataset & Benchmark Contributions
- Add new simulated transaction graph topologies to `datasets/dogon/` with their corresponding annotations.
- Improve benchmark scripts in `modules/benchmark.py`.

### 🐛 Small Bug Fixes & Improvements
- Check open [GitHub Issues](https://github.com/Ibonon/Sigui/issues) labeled `good first issue`.

---

## 🔍 Contributing New Detection Patterns (Yurugu Layer)

The **Yurugu layer** is Sigui's detection logic for novel on-chain attack patterns. If you've identified a new DeFi attack topology that isn't currently detected, here's how to propose it:

### Step 1: Document the Pattern

Create a Markdown file in `docs/patterns/` following this template:

```markdown
# Pattern: <PATTERN_NAME>

## Description
A concise explanation of the attack.

## On-Chain Signature
- Transaction graph shape (e.g., one-to-many fan-out followed by aggregation)
- Typical USDC amounts and timing
- Known smart contract functions involved (ABI selectors)

## Detection Heuristics
- Proposed rules for `modules/security_engine.py`
- Suggested visual signature for Imina-Na training

## Real-World Example
- Transaction hash(es) or simulated scenario

## Proposed Risk Delta
- Suggested `risk_delta` value (0.0 to 0.7)
```

### Step 2: Implement the Heuristic

Add your detection logic to `modules/security_engine.py`. Follow the existing pattern:

```python
# In SecurityEngine._compute_risk_score()
if <your_condition>:
    flags.append(RiskFlag(
        name="YOUR_PATTERN_NAME",
        description="Human-readable description.",
        risk_delta=0.XX,
        layer="yurugu",
    ))
```

### Step 3: Add Tests

Add unit tests to `tests/` verifying both true positive (attack detected) and true negative (legitimate transaction not flagged) cases.

### Step 4: Open a Pull Request

Reference your pattern documentation in the PR description and tag it with the `detection-pattern` label.

---

## Pull Request Guidelines

- **One PR per logical change** — don't bundle unrelated fixes together.
- **Write tests** for new features and bug fixes.
- **Update documentation** if your change affects the public API or user-facing behavior.
- **Keep PRs small** — large PRs are harder to review and slower to merge.
- Ensure `pytest tests/ -v` passes locally before submitting.

### PR Title Format

```
<type>(<scope>): <short description>

Examples:
feat(sdk): add AutoGen integration wrapper
fix(security_engine): correct DRAIN_STAR threshold for low-value transactions
docs(contributing): add Semantic Kernel example
```

---

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

| Prefix | When to use |
|---|---|
| `feat:` | A new feature |
| `fix:` | A bug fix |
| `docs:` | Documentation changes only |
| `refactor:` | Code restructure without behavior change |
| `test:` | Adding or fixing tests |
| `chore:` | Build, deps, CI/CD changes |

---

## Reporting Bugs

Please open a GitHub Issue with:

1. **What you expected** to happen.
2. **What actually happened** (include the full error traceback).
3. **Reproduction steps** (minimal code example if possible).
4. **Environment**: Python version, OS, `pip freeze` output.

---

## Questions?

Open a [GitHub Discussion](https://github.com/Ibonon/Sigui/discussions) — we monitor it actively and are happy to guide you.

---

*Thank you for helping make the agentic economy safer. 🛡️*
