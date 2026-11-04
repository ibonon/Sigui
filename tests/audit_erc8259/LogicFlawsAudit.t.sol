// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.24;

import {IAgentIdentityRegistry} from "./IAgentIdentityRegistry.sol";
import {IThreatRegistry} from "./IThreatRegistry.sol";
import {ThreatRegistryFixture} from "./IncidentLifecycle.t.sol";

interface VmCheat {
    function warp(uint256 timestamp) external;
    function prank(address sender) external;
}

/// @notice Registry implementation with Faille #3 fixed
contract SpecCompliantRegistryFixture is IAgentIdentityRegistry {
    VmCheat internal constant vm = VmCheat(address(uint160(uint256(keccak256("hevm cheat code")))));

    mapping(address => AgentIdentity) private identities;
    mapping(string => address) private didToAddress;
    address public immutable authority;
    uint256 private nextId;

    modifier onlyAuthority() {
        require(msg.sender == authority, "unauthorized verifier");
        _;
    }

    constructor() {
        authority = msg.sender;
    }

    /// @dev Per ERC-8259 spec L452: MUST revert if supplied did is empty or already registered to different address
    function registerAgent(
        string calldata did,
        bytes32 publicKey,
        string calldata metadataURI
    ) external payable override returns (uint256) {
        bytes memory didBytes = bytes(did);
        require(didBytes.length > 0, "empty did");
        require(identities[msg.sender].registrationTime == 0, "agent already registered");
        require(didToAddress[did] == address(0), "did already registered to another address");

        didToAddress[did] = msg.sender;
        AgentIdentity storage id = identities[msg.sender];
        id.did = did;
        id.publicKey = publicKey;
        id.metadataURI = metadataURI;
        id.reputationScore = 500; // Baseline neutral
        id.registrationTime = block.timestamp;
        id.lastUpdate = block.timestamp;
        id.isActive = true;
        id.verificationTier = 0;
        id.verificationExpiry = 0;

        return ++nextId;
    }

    function getAgentByDID(string calldata did) external view override returns (address) {
        return didToAddress[did];
    }

    /// @dev Admin deactivation function (simulating deactivation of rogue/compromised agent)
    function deactivateAgent(address agent) external onlyAuthority {
        require(identities[agent].registrationTime > 0, "agent not found");
        identities[agent].isActive = false;
        identities[agent].lastUpdate = block.timestamp;
    }

    function updateVerificationTier(
        address agent,
        uint8 tier,
        uint256 validityPeriod
    ) external payable override onlyAuthority {
        require(identities[agent].isActive, "inactive agent");
        require(tier <= 4, "invalid tier");
        identities[agent].verificationTier = tier;
        identities[agent].verificationExpiry = block.timestamp + validityPeriod;
        identities[agent].lastUpdate = block.timestamp;
    }

    function updateReputationScore(
        address agent,
        uint16 score,
        string calldata
    ) external override onlyAuthority {
        require(identities[agent].isActive, "inactive agent");
        require(score <= 1000, "score exceeds 1000");
        identities[agent].reputationScore = score;
        identities[agent].lastUpdate = block.timestamp;
    }

    function getAgentIdentity(address agent) external view override returns (AgentIdentity memory) {
        return identities[agent];
    }

    /// @dev CORRECTIF FAILLE #3: MUST return 0 if inactive OR expired
    function getEffectiveTier(address agent) public view override returns (uint8) {
        if (!identities[agent].isActive || block.timestamp > identities[agent].verificationExpiry) {
            return 0;
        }
        return identities[agent].verificationTier;
    }

    /// @dev CORRECTIF FAILLE #3: MUST return true only if agent is active AND effective tier > 0
    function isVerified(address agent) external view override returns (bool) {
        return identities[agent].isActive && getEffectiveTier(agent) > 0;
    }

    /// @dev CORRECTIF FAILLE #3: MUST return 0 if agent is inactive (!isActive)
    function calculateTrustScore(address agent) external view override returns (uint16) {
        if (!identities[agent].isActive) {
            return 0;
        }
        uint256 base = uint256(identities[agent].reputationScore);
        uint256 tierBoost = uint256(getEffectiveTier(agent)) * 100;
        uint256 total = base + tierBoost;
        return uint16(total > 1000 ? 1000 : total);
    }
}

/// @notice Conformance and logic flaw verification suite
contract LogicFlawsAuditTest {
    VmCheat internal constant vm = VmCheat(address(uint160(uint256(keccak256("hevm cheat code")))));

    SpecCompliantRegistryFixture internal registry;
    ThreatRegistryFixture internal threatRegistry;

    address internal constant ALICE = address(0xA11CE);
    address internal constant MALLORY = address(0xBAD);

    function setUp() public {
        registry = new SpecCompliantRegistryFixture();
        threatRegistry = new ThreatRegistryFixture();
    }

    // ─────────────────────────────────────────────────────────────
    // FAILLE #2 : Front-running de DID
    // ─────────────────────────────────────────────────────────────
    function test_Faille2_DIDFrontRunningVulnerability() public {
        string memory aliceDID = "did:agent:1:0x00000000000000000000000000000000000a11ce";

        // Mallory sees Alice's intended DID in the mempool or intent network.
        // Mallory calls registerAgent with Alice's DID from Mallory's address.
        vm.prank(MALLORY);
        uint256 malloryAgentId = registry.registerAgent(aliceDID, keccak256("malloryKey"), "ipfs://mallory");
        require(malloryAgentId > 0, "Mallory registration succeeded");

        // Mallory is now recorded as the owner of Alice's DID!
        address registeredOwner = registry.getAgentByDID(aliceDID);
        require(registeredOwner == MALLORY, "Mallory hijacked Alice DID");

        // Alice now attempts to register her own legitimate DID from her own address.
        // It reverts because the spec only checks `didToAddress[did] == 0`.
        vm.prank(ALICE);
        try registry.registerAgent(aliceDID, keccak256("aliceKey"), "ipfs://alice") {
            revert("Alice should have been blocked due to front-running");
        } catch Error(string memory reason) {
            // Expected revert: Alice is locked out of her own DID!
            require(
                keccak256(bytes(reason)) == keccak256(bytes("did already registered to another address")),
                "Revert reason mismatch"
            );
        }
    }

    // ─────────────────────────────────────────────────────────────
    // FAILLE #3 (CORRIGÉE) : isActive vérifié dans isVerified(), getEffectiveTier() et calculateTrustScore()
    // ─────────────────────────────────────────────────────────────
    function test_Faille3_DeactivatedAgentIsCorrectlyRejected() public {
        // Alice registers
        vm.prank(ALICE);
        registry.registerAgent("did:agent:1:0x00000000000000000000000000000000000a11ce", keccak256("k"), "ipfs://a");

        // Verifier promotes Alice to Tier 2 (Silver) for 30 days
        registry.updateVerificationTier(ALICE, 2, 30 days);
        require(registry.isVerified(ALICE), "Alice initially verified");
        require(registry.getEffectiveTier(ALICE) == 2, "Alice tier 2");
        require(registry.calculateTrustScore(ALICE) == 700, "Trust score: 500 + 200 = 700");

        // Now Alice's agent goes rogue or is compromised. Governance deactivates Alice!
        registry.deactivateAgent(ALICE);

        // Verification of state: isActive is indeed false
        IAgentIdentityRegistry.AgentIdentity memory aliceState = registry.getAgentIdentity(ALICE);
        require(aliceState.isActive == false, "Alice is deactivated");

        // VERIFICATION DE LA CORRECTION :
        // 1. isVerified(ALICE) renvoie FALSE !
        bool stillVerified = registry.isVerified(ALICE);
        require(stillVerified == false, "FIXED: Deactivated agent MUST NOT be verified");

        // 2. getEffectiveTier(ALICE) renvoie 0 !
        uint8 effectiveTier = registry.getEffectiveTier(ALICE);
        require(effectiveTier == 0, "FIXED: Deactivated agent effective tier MUST be 0");

        // 3. calculateTrustScore(ALICE) renvoie 0 !
        uint16 trustScore = registry.calculateTrustScore(ALICE);
        require(trustScore == 0, "FIXED: Deactivated agent trust score MUST be 0");
    }

    // ─────────────────────────────────────────────────────────────
    // FAILLE #5 : Taxonomie ThreatLayer non standardisée (uint8 opaque)
    // ─────────────────────────────────────────────────────────────
    function test_Faille5_ThreatLayerOpaqueUint8AcceptsArbitraryValues() public {
        // In IThreatRegistry.sol, layer is uint8 with no enum type.
        // A reporter can submit nonsense values like 99, 250, 0 because no ThreatLayer enum exists.
        uint8 nonsenseLayer = 250;
        uint256 incidentId = threatRegistry.recordAttack(
            ALICE,
            keccak256("pattern"),
            1000 * 1e6,
            850,
            nonsenseLayer
        );

        IThreatRegistry.AttackRecord memory record = threatRegistry.getAttackRecord(incidentId);
        require(record.layer == 250, "Registry accepted arbitrary layer 250");
    }
}
