# Changelog

All notable changes to **sigui-sdk** are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [0.2.0] — 2026-05-24

### Added
- **OpenAI Agents SDK** native integration (`sigui.integrations.openai_agents`)
  — `create_openai_agents_tool()` returns a `FunctionTool` ready for any `Agent`.
- **AutoGen** native integration (`sigui.integrations.autogen`)
  — `create_autogen_tool()` returns an `autogen_core` `FunctionTool`.
- **smolagents** (HuggingFace) integration (`sigui.integrations.smolagents`)
  — `SiguiTool` is a proper `Tool` subclass for `CodeAgent` / `ToolCallingAgent`.
- `[openai-agents]`, `[autogen]`, `[smolagents]` optional extras in `pyproject.toml`.
- `[all]` meta-extra to install all integrations at once: `pip install "sigui-sdk[all]"`.
- GitHub Actions workflow (`publish-sdk.yml`) using PyPI Trusted Publishing (OIDC).
- `CHANGELOG.md` (this file).
- `mypy` config in `pyproject.toml`.

### Fixed
- **Critical**: `sigui.integrations.crewai` crashed at import time with `ImportError`
  when `crewai` was not installed. Fixed with a lazy availability check; the module is
  now safe to import unconditionally.
- `SiguiEvaluationTool.__init__` now raises a clear `ImportError` on instantiation
  instead of a confusing `AttributeError`.

### Changed
- Bumped version to `0.2.0` in `pyproject.toml`, `__init__.py`, and `client.py`.
- `pyproject.toml` classifiers updated: `Development Status :: 4 - Beta`.
- `integrations/__init__.py` restructured with full lazy-import documentation.

---

## [0.1.0] — 2026-05-18

### Added
- Initial release of `sigui-sdk`.
- `SiguiClient` (async) and `SiguiClientSync` (sync wrapper).
- `EvaluationResult`, `EscalationResult`, `TreasuryState` data models.
- `Verdict` enum: `ALLOW`, `BLOCK`, `ESCALATE`, `ALLOW_WITH_CAP`.
- `Chain` enum: `arc`, `ethereum`, `solana`.
- x402 automatic payment protocol handler (`X402Handler`).
- `DemoWallet` (simulation) and `CircleWallet` (production) adapters.
- `@sigui_protect` decorator for framework-agnostic function gating.
- LangChain integration: `create_langchain_tool()`.
- LangGraph integration: `create_langgraph_tool()`.
- CrewAI integration: `SiguiEvaluationTool`.
- Exception hierarchy: `SiguiError`, `SiguiBlockedError`, `SiguiPaymentError`, etc.
- Examples: `simple_agent.py`, `langchain_agent.py`, `crewai_agent.py`.
