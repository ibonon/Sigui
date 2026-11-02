// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.20;

/**
 * @title IThreatRegistry
 * @notice Standard interface for sharing malicious agent patterns and incident reports (ERC-8259).
 */
interface IThreatRegistry {

    enum IncidentStatus {
        ACTIVE,      // Active confirmed threat posing immediate risk
        RETRACTED,   // False positive or reporting error formally retracted
        RESOLVED     // Remediated historical exploit with verified resolution
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

    event AttackBlocked(
        uint256 indexed idx,
        address indexed agent,
        bytes32 indexed pattern,
        uint256 amountUSDC6,
        uint256 riskMilli,
        uint8 layer
    );

    event AttackRetracted(
        uint256 indexed incidentId,
        address indexed agent,
        address indexed reporter,
        string reason
    );

    event AttackResolved(
        uint256 indexed incidentId,
        address indexed agent,
        address indexed resolver,
        string remediationURI
    );

    event ThreatPatternShared(
        bytes32 indexed pattern,
        address indexed reporter,
        uint256 riskScore,
        string description
    );

    /**
     * @notice Records an intercepted attack or unauthorized exploit attempt.
     * @dev MUST revert if called by an unauthorized address. Emits AttackBlocked.
     * @param agent Malicious agent address.
     * @param pattern Behavioral pattern hash.
     * @param amountUSDC6 Associated transaction volume in 6-decimal units.
     * @param riskMilli Calculated risk score scaled by 1000 (0-1000).
     * @param layer Identified attack vector category (1-4).
     * @return incidentId Unique identifier assigned to this incident.
     */
    function recordAttack(
        address agent,
        bytes32 pattern,
        uint256 amountUSDC6,
        uint256 riskMilli,
        uint8 layer
    ) external returns (uint256 incidentId);

    /**
     * @notice Retracts an erroneous report (false positive).
     * @dev MUST only be callable by original reporter or governance. Emits AttackRetracted.
     * @param incidentId ID of the incident to retract.
     * @param reason Explanation for the retraction.
     */
    function retractAttack(
        uint256 incidentId,
        string calldata reason
    ) external;

    /**
     * @notice Marks an attack as resolved following verified remediation or restitution.
     * @dev MUST NOT be callable by the subject agent. Emits AttackResolved.
     * @param incidentId ID of the incident resolved.
     * @param remediationURI Attestation URI or audit proof of remediation.
     */
    function resolveAttack(
        uint256 incidentId,
        string calldata remediationURI
    ) external;

    /**
     * @notice Publishes a recognized threat pattern for cross-protocol intelligence sharing.
     * @param pattern Cryptographic hash of the observed threat topology.
     * @param riskScore Associated severity rating (0-1000).
     * @param description Brief description of the threat vector.
     */
    function shareThreatPattern(
        bytes32 pattern,
        uint256 riskScore,
        string calldata description
    ) external;

    /**
     * @notice Checks whether an address has active, un-remediated threat incidents.
     * @param agent Address to check.
     * @return True if at least one ACTIVE incident exists for this address.
     */
    function isKnownAttacker(address agent)
        external
        view
        returns (bool);

    /**
     * @notice Queries whether an address has active threat incidents (alias for isKnownAttacker).
     * @param agent Address to check.
     * @return True if at least one ACTIVE incident exists for this address.
     */
    function hasActiveThreat(address agent)
        external
        view
        returns (bool);

    /**
     * @notice Returns the full attack record for a given incident ID.
     * @param incidentId ID of the incident to query.
     * @return AttackRecord struct containing stored incident data.
     */
    function getAttackRecord(uint256 incidentId)
        external
        view
        returns (AttackRecord memory);

    /**
     * @notice Retrieves the historical attack frequency and blocked volume for an agent.
     * @param agent Address to query.
     * @return attackCount Total number of recorded attack events across all states.
     * @return totalBlocked Cumulative value blocked across incidents.
     */
    function getAgentAttackHistory(address agent)
        external
        view
        returns (uint256 attackCount, uint256 totalBlocked);

    /**
     * @notice Returns detailed incident breakdown by lifecycle status.
     * @param agent Address to query.
     * @return active Count of active, un-remediated incidents.
     * @return resolved Count of confirmed but remediated incidents.
     * @return retracted Count of retracted false-positive reports.
     */
    function getIncidentSummary(address agent)
        external
        view
        returns (uint256 active, uint256 resolved, uint256 retracted);

    /**
     * @notice Evaluates potential transaction risk against recorded threat patterns.
     * @param agent Address initiating the transaction.
     * @param amount Transaction amount.
     * @param action Identifier of the attempted interaction.
     * @return Computed threat risk score (0-1000).
     */
    function assessTransactionRisk(
        address agent,
        uint256 amount,
        bytes32 action
    ) external view returns (uint256);
}
