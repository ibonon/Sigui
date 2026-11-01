// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.20;

/**
 * @title IRiskAssessment
 * @notice Optional ERC-8259 interface for pre-execution transaction risk scoring.
 */
interface IRiskAssessment {

    struct RiskAssessment {
        bool allowed;
        uint256 riskScore;
        string reason;
        uint256 confidence;
        bytes32[] threatPatterns;
    }

    struct AssessmentRequest {
        address agent;
        uint256 amount;
        bytes32 action;
        address destination;
        bytes metadata;
    }

    function assessRisk(AssessmentRequest calldata request)
        external
        view
        returns (RiskAssessment memory);

    function batchAssessRisk(AssessmentRequest[] calldata requests)
        external
        view
        returns (RiskAssessment[] memory);

    function updateRiskParameters(
        bytes32 parameterHash,
        uint256[] calldata newValues
    ) external;
}
