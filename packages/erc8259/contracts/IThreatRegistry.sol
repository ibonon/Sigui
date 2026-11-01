// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.20;

/**
 * @title IThreatRegistry
 * @notice Standard interface for sharing malicious agent patterns and incident reports (ERC-8259).
 */
interface IThreatRegistry {

    struct AttackRecord {
        address agentAddress;
        bytes32 patternHash;
        uint256 amountUSDC6;
        uint256 riskMilli;
        uint8 layer;
        uint256 blockedAt;
    }

    event AttackBlocked(
        uint256 indexed idx,
        address indexed agent,
        bytes32 indexed pattern,
        uint256 amountUSDC6,
        uint256 riskMilli,
        uint8 layer
    );

    event ThreatPatternShared(
        bytes32 indexed pattern,
        address indexed reporter,
        uint256 riskScore,
        string description
    );

    function recordAttack(
        address agent,
        bytes32 pattern,
        uint256 amountUSDC6,
        uint256 riskMilli,
        uint8 layer
    ) external;

    function shareThreatPattern(
        bytes32 pattern,
        uint256 riskScore,
        string calldata description
    ) external;

    function isKnownAttacker(address agent)
        external
        view
        returns (bool);

    function getAgentAttackHistory(address agent)
        external
        view
        returns (uint256 attackCount, uint256 totalBlocked);

    function assessTransactionRisk(
        address agent,
        uint256 amount,
        bytes32 action
    ) external view returns (uint256);
}
