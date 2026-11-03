# Changelog — `erc-8259`

All notable changes to the `erc-8259` NPM package are documented here.

---

## [1.2.1] - 2026-11-03

### Security Notice & Critical Desynchronization Resolution
> ⚠️ **CRITICAL UPGRADE NOTICE FOR USERS OF v1.0.x / v1.1.0**:
> Package versions `1.0.0`, `1.0.1`, and `1.1.0` contained an out-of-date version of `IAgentIdentityRegistry.sol` that did NOT match the official Ethereum ERC-8259 specification.
> 
> Specifically, versions prior to 1.2.0:
> 1. **Missing `verificationExpiry`**: The `AgentIdentity` struct lacked the `uint256 verificationExpiry` field, preventing verification decay.
> 2. **Missing `getEffectiveTier`**: The interface lacked the `getEffectiveTier(address)` function, making it impossible to evaluate expiration dynamically.
> 3. **Critical Privilege Escalation Vector**: `registerAgent()` still accepted `uint8 verificationTier`, allowing newly registered agents to self-assign their verification tier upon registration.
>
> In v1.2.0+, `registerAgent(string did, bytes32 publicKey, string metadataURI)` strictly enforces the Tier 0 (UNVERIFIED) initialization invariant as ratified by the Ethereum community in PR #2137. Verification tier upgrades require an explicit authorized call to `updateVerificationTier(agent, newTier, validityPeriod)`.
>
> Any project using `erc-8259` v1.1.0 or lower MUST upgrade to v1.2.1 immediately.

### Fixed
- **NatSpec Parsing Error**: Resolved docstring tag parsing errors in `ERC8259Guard.sol` under strict `solc` compilers.
- **Spec Parity**: Verified complete parity between `packages/erc8259/contracts/` and `ERCS/erc-8259.md` (upstream ERC-8259).

---

## [1.2.0] - 2026-11-03

### Changed
- Reconciled `IAgentIdentityRegistry.sol` with upstream ERC-8259 (PR #2137, PR #2139).
- Removed `verificationTier` parameter from `registerAgent()`.
- Added `verificationExpiry` and `getEffectiveTier()`.
- Added explicit normative requirement for `calculateTrustScore()` to use `getEffectiveTier()`.
- Fixed NatSpec comment syntax in `ERC8259Guard.sol`.

---

## [1.1.0] - 2026-11-02

### Added
- Added incident lifecycle support in `IThreatRegistry.sol` (`IncidentStatus` enum, `retractAttack`, `resolveAttack`, `getIncidentSummary`) as ratified in PR #2138.

---

## [1.0.1] - 2026-11-01

### Initial Release
- Initial published release of `erc-8259` interfaces and `ERC8259Guard.sol`.
