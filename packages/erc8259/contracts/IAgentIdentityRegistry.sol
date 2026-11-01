// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.20;

/**
 * @title IAgentIdentityRegistry
 * @notice Standard interface for AI agent decentralized identity and reputation management (ERC-8259).
 */
interface IAgentIdentityRegistry {
    
    struct AgentIdentity {
        string did;
        bytes32 publicKey;
        uint8 verificationTier;
        uint16 reputationScore;
        uint256 registrationTime;
        uint256 lastUpdate;
        string metadataURI;
        bool isActive;
        uint256 totalTransactions;
        uint256 successfulTransactions;
    }

    struct VerificationTier {
        string name;
        string requirements;
        uint16 trustMultiplier;
        uint256 verificationFee;
        uint256 validityPeriod;
    }

    event AgentRegistered(
        string indexed did,
        address indexed agentAddress,
        uint8 verificationTier,
        uint16 reputationScore,
        uint256 registrationTime
    );

    event AgentUpdated(
        string indexed did,
        uint16 reputationScore,
        uint8 verificationTier,
        uint256 lastUpdate
    );

    event ReputationScoreUpdated(
        string indexed did,
        uint16 oldScore,
        uint16 newScore,
        string updateReason
    );

    function registerAgent(
        string calldata did,
        bytes32 publicKey,
        uint8 verificationTier,
        string calldata metadataURI
    ) external payable returns (uint256 agentId);

    function updateReputationScore(
        address agentAddress,
        uint16 newScore,
        string calldata updateReason
    ) external;

    function updateVerificationTier(
        address agentAddress,
        uint8 newTier
    ) external payable;

    function getAgentIdentity(address agentAddress)
        external
        view
        returns (AgentIdentity memory);

    function getAgentByDID(string calldata did)
        external
        view
        returns (address);

    function isVerified(address agentAddress)
        external
        view
        returns (bool);

    function calculateTrustScore(address agentAddress)
        external
        view
        returns (uint16);
}
