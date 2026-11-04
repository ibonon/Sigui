// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.24;

import {IThreatRegistry} from "./IThreatRegistry.sol";

interface VmIncident {
    function prank(address sender) external;
    function expectRevert(bytes calldata) external;
}

/// Minimal test double for IThreatRegistry to verify T7 and lifecycle transitions.
contract ThreatRegistryFixture is IThreatRegistry {
    address public immutable governance;
    uint256 private nextIncidentId = 1;

    mapping(uint256 => AttackRecord) private _records;
    mapping(address => uint256) private _activeCount;
    mapping(address => uint256) private _resolvedCount;
    mapping(address => uint256) private _retractedCount;

    constructor() {
        governance = msg.sender;
    }

    function recordAttack(
        address agent,
        bytes32 pattern,
        uint256 amountUSDC6,
        uint256 riskMilli,
        uint8 layer
    ) external override returns (uint256 incidentId) {
        incidentId = nextIncidentId++;
        _records[incidentId] = AttackRecord({
            agentAddress: agent,
            patternHash: pattern,
            amountUSDC6: amountUSDC6,
            riskMilli: riskMilli,
            layer: layer,
            blockedAt: block.timestamp,
            reporter: msg.sender,
            status: IncidentStatus.ACTIVE
        });
        _activeCount[agent]++;
        emit AttackBlocked(incidentId, agent, pattern, amountUSDC6, riskMilli, layer);
    }

    function retractAttack(uint256 incidentId, string calldata reason) external override {
        AttackRecord storage rec = _records[incidentId];
        require(rec.blockedAt > 0, "incident not found");
        require(rec.status == IncidentStatus.ACTIVE, "incident not active");
        require(msg.sender == rec.reporter || msg.sender == governance, "unauthorized reporter");

        rec.status = IncidentStatus.RETRACTED;
        _activeCount[rec.agentAddress]--;
        _retractedCount[rec.agentAddress]++;
        emit AttackRetracted(incidentId, rec.agentAddress, rec.reporter, reason);
    }

    function resolveAttack(uint256 incidentId, string calldata remediationURI) external override {
        AttackRecord storage rec = _records[incidentId];
        require(rec.blockedAt > 0, "incident not found");
        require(rec.status == IncidentStatus.ACTIVE, "incident not active");
        require(msg.sender != rec.agentAddress, "subject agent cannot self-resolve");

        rec.status = IncidentStatus.RESOLVED;
        _activeCount[rec.agentAddress]--;
        _resolvedCount[rec.agentAddress]++;
        emit AttackResolved(incidentId, rec.agentAddress, msg.sender, remediationURI);
    }

    function isKnownAttacker(address agent) external view override returns (bool) {
        return _activeCount[agent] > 0;
    }

    function hasActiveThreat(address agent) external view override returns (bool) {
        return _activeCount[agent] > 0;
    }

    function getAttackRecord(uint256 incidentId) external view override returns (AttackRecord memory) {
        return _records[incidentId];
    }

    function shareThreatPattern(
        bytes32,
        uint256,
        string calldata
    ) external override {}

    function getAgentAttackHistory(address) external pure override returns (uint256, uint256) {
        return (0, 0);
    }

    function getIncidentSummary(address agent) external view override returns (uint256 active, uint256 resolved, uint256 retracted) {
        return (_activeCount[agent], _resolvedCount[agent], _retractedCount[agent]);
    }

    function assessTransactionRisk(address, uint256, bytes32) external pure override returns (uint256) {
        return 0;
    }
}

contract IncidentLifecycleTest {
    VmIncident internal constant vm = VmIncident(address(uint160(uint256(keccak256("hevm cheat code")))));

    ThreatRegistryFixture internal registry;
    address internal constant ORACLE = address(0x8259A1);
    address internal constant AUDITOR = address(0x8259A2);
    address internal constant MALICIOUS_AGENT = address(0x8259BA);
    bytes32 internal constant PATTERN = keccak256("reentrancy_drain");

    function setUp() public {
        registry = new ThreatRegistryFixture();
    }

    function test_T7_independentIncidentResolutionMaintainsBlock() public {
        vm.prank(ORACLE);
        uint256 incA = registry.recordAttack(MALICIOUS_AGENT, PATTERN, 1000000, 900, 1);
        vm.prank(ORACLE);
        uint256 incB = registry.recordAttack(MALICIOUS_AGENT, PATTERN, 500000, 800, 1);

        require(registry.isKnownAttacker(MALICIOUS_AGENT), "must be known attacker");
        require(registry.hasActiveThreat(MALICIOUS_AGENT), "must have active threat");

        // Resolve incA by auditor
        vm.prank(AUDITOR);
        registry.resolveAttack(incA, "ipfs://remediation-report-A");

        // T7 INVARIANT: Resolving incA MUST NOT clear attacker flag while incB is ACTIVE
        require(registry.isKnownAttacker(MALICIOUS_AGENT), "T7 violation: incB is still active");
        require(registry.hasActiveThreat(MALICIOUS_AGENT), "T7 violation: hasActiveThreat should be true");

        // Resolve incB by auditor
        vm.prank(AUDITOR);
        registry.resolveAttack(incB, "ipfs://remediation-report-B");

        // Now both incidents are resolved
        require(!registry.isKnownAttacker(MALICIOUS_AGENT), "must be cleared after all resolved");
        require(!registry.hasActiveThreat(MALICIOUS_AGENT), "hasActiveThreat must be false");

        (uint256 active, uint256 resolved, uint256 retracted) = registry.getIncidentSummary(MALICIOUS_AGENT);
        require(active == 0, "active count mismatch");
        require(resolved == 2, "resolved count mismatch");
        require(retracted == 0, "retracted count mismatch");
    }

    function test_retractAttack_clearsFalsePositive() public {
        vm.prank(ORACLE);
        uint256 inc = registry.recordAttack(MALICIOUS_AGENT, PATTERN, 1000000, 900, 1);
        require(registry.isKnownAttacker(MALICIOUS_AGENT), "must be flagged");

        // False positive retracted by the original reporter
        vm.prank(ORACLE);
        registry.retractAttack(inc, "False positive confirmed");

        require(!registry.isKnownAttacker(MALICIOUS_AGENT), "flag must clear after retraction");
        (uint256 active, uint256 resolved, uint256 retracted) = registry.getIncidentSummary(MALICIOUS_AGENT);
        require(active == 0 && resolved == 0 && retracted == 1, "summary mismatch");
    }

    function test_subjectAgentCannotSelfResolveAttack() public {
        vm.prank(ORACLE);
        uint256 inc = registry.recordAttack(MALICIOUS_AGENT, PATTERN, 1000000, 900, 1);

        // Subject agent attempts to self-resolve
        vm.prank(MALICIOUS_AGENT);
        vm.expectRevert("subject agent cannot self-resolve");
        registry.resolveAttack(inc, "ipfs://fake-report");
    }

    function test_unauthorizedCallerCannotRetract() public {
        vm.prank(ORACLE);
        uint256 inc = registry.recordAttack(MALICIOUS_AGENT, PATTERN, 1000000, 900, 1);

        // Random address tries to retract
        vm.prank(address(0x9999));
        vm.expectRevert("unauthorized reporter");
        registry.retractAttack(inc, "unauthorized attempt");
    }
}
