// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.24;

import {IAgentIdentityRegistry} from "./IAgentIdentityRegistry.sol";

interface VmAdversarial {
    function warp(uint256 timestamp) external;
    function prank(address sender) external;
}

interface IThreatRegistryMinimal {
    enum IncidentStatus {
        ACTIVE,
        RETRACTED,
        RESOLVED
    }

    struct AttackRecord {
        address agentAddress;
        bytes32 patternHash;
        uint256 amountUSDC6;
        uint256 riskMilli;
        uint8 layer;
        uint256 blockedAt;
        address reporter;
        IncidentStatus status;
    }

    function recordAttack(
        address agent,
        bytes32 pattern,
        uint256 amountUSDC6,
        uint256 riskMilli,
        uint8 layer
    ) external returns (uint256 incidentId);

    function retractAttack(uint256 incidentId, string calldata reason) external;
    function resolveAttack(uint256 incidentId, string calldata remediationURI) external;
    function isAttacker(address agent) external view returns (bool);
    function getIncidentSummary(address agent) external view returns (
        uint256 totalIncidents,
        uint256 activeIncidents,
        uint256 retractedIncidents,
        uint256 resolvedIncidents
    );
    function getAttackRecord(uint256 incidentId) external view returns (AttackRecord memory);
}

/// @notice Reference implementation of IThreatRegistry for adversarial testing
contract ThreatRegistryAdversarialFixture is IThreatRegistryMinimal {
    uint256 private _incidentIdCounter;
    mapping(uint256 => AttackRecord) private _attacks;
    mapping(address => uint256[]) private _agentIncidentIds;
    mapping(address => uint256) private _activeIncidentCount;
    mapping(address => uint256) private _retractedIncidentCount;
    mapping(address => uint256) private _resolvedIncidentCount;
    mapping(address => bool) private _authorizedOracles;
    address public immutable owner;

    constructor() {
        owner = msg.sender;
        _authorizedOracles[msg.sender] = true;
    }

    function addOracle(address oracle) external {
        require(msg.sender == owner, "Only owner");
        _authorizedOracles[oracle] = true;
    }

    function recordAttack(
        address agent,
        bytes32 pattern,
        uint256 amountUSDC6,
        uint256 riskMilli,
        uint8 layer
    ) external override returns (uint256 incidentId) {
        require(_authorizedOracles[msg.sender], "Unauthorized oracle");
        require(agent != address(0), "Zero address agent");

        _incidentIdCounter++;
        incidentId = _incidentIdCounter;

        _attacks[incidentId] = AttackRecord({
            agentAddress: agent,
            patternHash: pattern,
            amountUSDC6: amountUSDC6,
            riskMilli: riskMilli,
            layer: layer,
            blockedAt: block.timestamp,
            reporter: msg.sender,
            status: IncidentStatus.ACTIVE
        });

        _agentIncidentIds[agent].push(incidentId);
        _activeIncidentCount[agent]++;

        return incidentId;
    }

    function retractAttack(uint256 incidentId, string calldata) external override {
        AttackRecord storage record = _attacks[incidentId];
        require(record.blockedAt > 0, "Incident not found");
        require(record.status == IncidentStatus.ACTIVE, "Incident not active");
        require(msg.sender == record.reporter || msg.sender == owner, "Unauthorized caller");

        record.status = IncidentStatus.RETRACTED;
        _activeIncidentCount[record.agentAddress]--;
        _retractedIncidentCount[record.agentAddress]++;
    }

    function resolveAttack(uint256 incidentId, string calldata) external override {
        AttackRecord storage record = _attacks[incidentId];
        require(record.blockedAt > 0, "Incident not found");
        require(record.status == IncidentStatus.ACTIVE, "Incident not active");
        require(msg.sender != record.agentAddress, "Subject cannot self-resolve");
        require(_authorizedOracles[msg.sender] || msg.sender == record.reporter || msg.sender == owner, "Unauthorized resolver");

        record.status = IncidentStatus.RESOLVED;
        _activeIncidentCount[record.agentAddress]--;
        _resolvedIncidentCount[record.agentAddress]++;
    }

    function isAttacker(address agent) external view override returns (bool) {
        // O(1) state check: gas does not scale with incident count!
        return _activeIncidentCount[agent] > 0;
    }

    function getIncidentSummary(address agent) external view override returns (
        uint256 totalIncidents,
        uint256 activeIncidents,
        uint256 retractedIncidents,
        uint256 resolvedIncidents
    ) {
        // O(1) state lookup
        totalIncidents = _agentIncidentIds[agent].length;
        activeIncidents = _activeIncidentCount[agent];
        retractedIncidents = _retractedIncidentCount[agent];
        resolvedIncidents = _resolvedIncidentCount[agent];
    }

    function getAttackRecord(uint256 incidentId) external view override returns (AttackRecord memory) {
        return _attacks[incidentId];
    }
}

/// @notice Minimal fixture double for IAgentIdentityRegistry with ERC-8259 invariants
contract AgentIdentityAdversarialFixture is IAgentIdentityRegistry {
    mapping(address => AgentIdentity) internal identities;
    mapping(string => address) internal didToAddress;
    address public immutable owner;

    constructor() {
        owner = msg.sender;
    }

    modifier authorized() {
        require(msg.sender == owner, "not authorized");
        _;
    }

    function registerAgent(
        string calldata did,
        bytes32 publicKey,
        string calldata metadataURI
    ) external payable override returns (uint256 agentId) {
        require(bytes(did).length > 0, "empty did");
        require(didToAddress[did] == address(0), "did exists");
        didToAddress[did] = msg.sender;
        identities[msg.sender] = AgentIdentity({
            did: did,
            publicKey: publicKey,
            verificationTier: 0,
            reputationScore: 500,
            registrationTime: block.timestamp,
            lastUpdate: block.timestamp,
            verificationExpiry: 0,
            metadataURI: metadataURI,
            isActive: true,
            totalTransactions: 0,
            successfulTransactions: 0
        });
        return 1;
    }

    function updateReputationScore(address agentAddress, uint16 newScore, string calldata) external override authorized {
        require(newScore <= 1000, "score out of bounds");
        identities[agentAddress].reputationScore = newScore;
        identities[agentAddress].lastUpdate = block.timestamp;
    }

    function updateVerificationTier(
        address agentAddress,
        uint8 newTier,
        uint256 validityPeriod
    ) external payable override authorized {
        require(newTier <= 4, "invalid tier");
        identities[agentAddress].verificationTier = newTier;
        identities[agentAddress].verificationExpiry = block.timestamp + validityPeriod;
        identities[agentAddress].lastUpdate = block.timestamp;
    }

    function deactivateAgent(address agent) external authorized {
        identities[agent].isActive = false;
    }

    function getEffectiveTier(address agent) public view override returns (uint8) {
        // NORMATIVE INVARIANT: MUST return 0 if !isActive OR if block.timestamp > verificationExpiry
        if (!identities[agent].isActive || block.timestamp > identities[agent].verificationExpiry) return 0;
        return identities[agent].verificationTier;
    }

    function getAgentIdentity(address agentAddress) external view override returns (AgentIdentity memory) {
        return identities[agentAddress];
    }

    function getAgentByDID(string calldata did) external view override returns (address) {
        return didToAddress[did];
    }

    function isVerified(address agent) external view override returns (bool) {
        // NORMATIVE INVARIANT: MUST return false if !isActive or getEffectiveTier <= 0
        return identities[agent].isActive && getEffectiveTier(agent) > 0;
    }

    function calculateTrustScore(address agent) external view override returns (uint16) {
        // NORMATIVE INVARIANT: MUST return 0 if !isActive
        if (!identities[agent].isActive) return 0;
        uint256 score = uint256(identities[agent].reputationScore) + uint256(getEffectiveTier(agent)) * 100;
        return uint16(score > 1000 ? 1000 : score);
    }
}

/// @notice Consumer contract implementing ERC8259Guard logic
contract MockDeFiVaultGuard {
    IThreatRegistryMinimal public immutable threatRegistry;
    IAgentIdentityRegistry public immutable identityRegistry;

    constructor(address _threatRegistry, address _identityRegistry) {
        threatRegistry = IThreatRegistryMinimal(_threatRegistry);
        identityRegistry = IAgentIdentityRegistry(_identityRegistry);
    }

    modifier onlySafeAgent() {
        require(!threatRegistry.isAttacker(msg.sender), "ERC8259Guard: caller is marked attacker");
        _;
    }

    modifier onlyVerifiedAgent() {
        require(!threatRegistry.isAttacker(msg.sender), "ERC8259Guard: caller is marked attacker");
        require(identityRegistry.isVerified(msg.sender), "ERC8259Guard: agent not verified");
        _;
    }

    function withdrawLiquidity() external onlySafeAgent returns (bool) {
        return true;
    }

    function executePrivilegedAction() external onlyVerifiedAgent returns (bool) {
        return true;
    }
}

/// @title AdversarialAttacksTest
/// @notice Hostile environment adversarial test suite for ERC-8259
contract AdversarialAttacksTest {
    VmAdversarial internal constant vm = VmAdversarial(address(uint160(uint256(keccak256("hevm cheat code")))));

    ThreatRegistryAdversarialFixture internal threatRegistry;
    AgentIdentityAdversarialFixture internal identityRegistry;
    MockDeFiVaultGuard internal vault;

    address internal constant ORACLE_ALICE = address(0xAA01);
    address internal constant ATTACKER_BOB = address(0xBB02);
    address internal constant SYBIL_1 = address(0xCC01);
    address internal constant SYBIL_2 = address(0xCC02);
    address internal constant SYBIL_3 = address(0xCC03);
    address internal constant HONEST_CHARLIE = address(0xDD01);

    function setUp() public {
        vm.warp(1_800_000_000);

        threatRegistry = new ThreatRegistryAdversarialFixture();
        identityRegistry = new AgentIdentityAdversarialFixture();
        vault = new MockDeFiVaultGuard(address(threatRegistry), address(identityRegistry));

        // Authorize Oracle Alice
        threatRegistry.addOracle(ORACLE_ALICE);

        // Register Bob, Charlie, and Sybils
        vm.prank(ATTACKER_BOB);
        identityRegistry.registerAgent("did:agent:1:bob", keccak256("bobKey"), "ipfs://bob");

        vm.prank(HONEST_CHARLIE);
        identityRegistry.registerAgent("did:agent:1:charlie", keccak256("charlieKey"), "ipfs://charlie");

        vm.prank(SYBIL_1);
        identityRegistry.registerAgent("did:agent:1:sybil1", keccak256("s1"), "ipfs://s1");
        vm.prank(SYBIL_2);
        identityRegistry.registerAgent("did:agent:1:sybil2", keccak256("s2"), "ipfs://s2");
        vm.prank(SYBIL_3);
        identityRegistry.registerAgent("did:agent:1:sybil3", keccak256("s3"), "ipfs://s3");
    }

    /// ------------------------------------------------------------------------
    /// SCENARIO 1: Sybil Retraction Attack
    /// ------------------------------------------------------------------------
    function test_adversarial_sybil_cannot_retract_or_resolve() public {
        // Step 1: Alice records legitimate attack against Bob
        vm.prank(ORACLE_ALICE);
        uint256 incidentId = threatRegistry.recordAttack(
            ATTACKER_BOB,
            keccak256("DRAIN_STAR"),
            100_000_000, // 100 USDC
            950,         // 95% risk
            1            // Layer 1
        );

        // Bob is marked attacker, vault withdraw reverts
        require(threatRegistry.isAttacker(ATTACKER_BOB), "Bob must be flagged");
        vm.prank(ATTACKER_BOB);
        try vault.withdrawLiquidity() {
            revert("Vulnerability: Flagged attacker was able to withdraw!");
        } catch {}

        // Step 2: Bob attempts to self-retract the attack
        vm.prank(ATTACKER_BOB);
        try threatRegistry.retractAttack(incidentId, "I am innocent") {
            revert("Vulnerability: Subject agent was able to self-retract attack!");
        } catch {}

        // Step 3: Bob attempts to self-resolve the attack
        vm.prank(ATTACKER_BOB);
        try threatRegistry.resolveAttack(incidentId, "ipfs://fake-remediation") {
            revert("Vulnerability: Subject agent was able to self-resolve attack!");
        } catch {}

        // Step 4: Bob's Sybil addresses attempt to retract or resolve
        address[3] memory sybils = [SYBIL_1, SYBIL_2, SYBIL_3];
        for (uint256 i = 0; i < sybils.length; i++) {
            vm.prank(sybils[i]);
            try threatRegistry.retractAttack(incidentId, "Sybil retract") {
                revert("Vulnerability: Sybil address was able to retract attack!");
            } catch {}

            vm.prank(sybils[i]);
            try threatRegistry.resolveAttack(incidentId, "ipfs://sybil-resolve") {
                revert("Vulnerability: Sybil address was able to resolve attack!");
            } catch {}
        }

        // Bob remains an attacker
        require(threatRegistry.isAttacker(ATTACKER_BOB), "Bob must still be flagged");

        // Step 5: Legitimate reporter Alice retracts (false positive resolution)
        vm.prank(ORACLE_ALICE);
        threatRegistry.retractAttack(incidentId, "Formal false positive retraction");

        // Bob is no longer flagged as an attacker
        require(!threatRegistry.isAttacker(ATTACKER_BOB), "Bob should no longer be attacker");
        
        // Bob can now interact with vault safely
        vm.prank(ATTACKER_BOB);
        bool success = vault.withdrawLiquidity();
        require(success, "Bob should now be allowed to withdraw");
    }

    /// ------------------------------------------------------------------------
    /// SCENARIO 2: Zero or Boundary Verification Expiry Attack
    /// ------------------------------------------------------------------------
    function test_adversarial_zero_and_boundary_expiry() public {
        uint256 start = block.timestamp;

        // Subcase A: Verifier assigns Tier 3 with validityPeriod = 0 (Immediate expiry)
        identityRegistry.updateVerificationTier(HONEST_CHARLIE, 3, 0);

        // At exact start block: verificationExpiry == start.
        // As soon as block.timestamp > verificationExpiry (even 1 second later):
        vm.warp(start + 1);
        require(identityRegistry.getEffectiveTier(HONEST_CHARLIE) == 0, "Zero-period must expire immediately");
        require(!identityRegistry.isVerified(HONEST_CHARLIE), "Zero-period must not be verified");
        require(identityRegistry.calculateTrustScore(HONEST_CHARLIE) == 500, "Must have zero tier boost");

        // Privileged vault action MUST revert
        vm.prank(HONEST_CHARLIE);
        try vault.executePrivilegedAction() {
            revert("Vulnerability: Agent with zero-period tier passed onlyVerifiedAgent!");
        } catch {}

        // Subcase B: Boundary testing with validityPeriod = 100 seconds
        identityRegistry.updateVerificationTier(HONEST_CHARLIE, 2, 100);
        uint256 end = start + 1 + 100;

        // At exact boundary (end): valid (block.timestamp <= expiry)
        vm.warp(end);
        require(identityRegistry.getEffectiveTier(HONEST_CHARLIE) == 2, "Must be valid at boundary");
        require(identityRegistry.isVerified(HONEST_CHARLIE), "Must be verified at boundary");
        vm.prank(HONEST_CHARLIE);
        require(vault.executePrivilegedAction(), "Must pass at boundary");

        // At boundary + 1 second: strictly expired (block.timestamp > expiry)
        vm.warp(end + 1);
        require(identityRegistry.getEffectiveTier(HONEST_CHARLIE) == 0, "Must be expired at boundary + 1");
        require(!identityRegistry.isVerified(HONEST_CHARLIE), "Must not be verified at boundary + 1");

        vm.prank(HONEST_CHARLIE);
        try vault.executePrivilegedAction() {
            revert("Vulnerability: Expired agent at boundary + 1 passed onlyVerifiedAgent!");
        } catch {}

        // Subcase C: Attempting to extend expiration via updateReputationScore
        identityRegistry.updateReputationScore(HONEST_CHARLIE, 950, "Top contributor");
        require(identityRegistry.getEffectiveTier(HONEST_CHARLIE) == 0, "Reputation update must NOT extend expiry");
        require(!identityRegistry.isVerified(HONEST_CHARLIE), "Reputation update must NOT verify expired agent");
    }

    /// ------------------------------------------------------------------------
    /// SCENARIO 3: Incident Spamming & Gas Exhaustion Attack
    /// ------------------------------------------------------------------------
    function test_adversarial_incident_spam_bounded_gas() public {
        // Step 1: Measure baseline gas of isAttacker on clean agent
        uint256 gasBefore1 = gasleft();
        bool isAtkClean = threatRegistry.isAttacker(HONEST_CHARLIE);
        uint256 gasUsedClean = gasBefore1 - gasleft();
        require(!isAtkClean, "Charlie should not be attacker");

        // Step 2: Spam 50 incidents against Attacker Bob
        for (uint256 i = 0; i < 50; i++) {
            vm.prank(ORACLE_ALICE);
            threatRegistry.recordAttack(
                ATTACKER_BOB,
                keccak256(abi.encodePacked("SPAM_PATTERN_", i)),
                1000 * (i + 1),
                800,
                1
            );
        }

        // Verify counts
        (
            uint256 totalIncidents,
            uint256 activeIncidents,
            uint256 retractedIncidents,
            uint256 resolvedIncidents
        ) = threatRegistry.getIncidentSummary(ATTACKER_BOB);

        require(totalIncidents == 50, "Total must be 50");
        require(activeIncidents == 50, "Active must be 50");
        require(retractedIncidents == 0, "Retracted must be 0");
        require(resolvedIncidents == 0, "Resolved must be 0");

        // Step 3: Measure gas of isAttacker on heavily spammed agent
        uint256 gasBeforeSpammed = gasleft();
        bool isAtkSpammed = threatRegistry.isAttacker(ATTACKER_BOB);
        uint256 gasUsedSpammed = gasBeforeSpammed - gasleft();
        require(isAtkSpammed, "Bob must be flagged attacker");

        // Invariant: Evaluation gas must remain strictly bounded O(1)
        // If an implementation iterated over all 50 incidents, gas would increase by > 50,000!
        require(gasUsedClean < 10_000, "Clean isAttacker must be sub-10k gas");
        require(gasUsedSpammed < 10_000, "Spammed isAttacker must remain sub-10k gas");

        // Step 4: Vault modifier gas test under spam (standard cold call bound < 50k)
        vm.prank(HONEST_CHARLIE);
        uint256 gasBeforeVault = gasleft();
        vault.withdrawLiquidity();
        uint256 gasUsedVault = gasBeforeVault - gasleft();
        require(gasUsedVault < 50_000, "Vault execution must remain low gas despite global spam");
    }
}
