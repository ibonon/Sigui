// SPDX-License-Identifier: CC0-1.0
pragma solidity ^0.8.20;

import {IThreatRegistry} from "./IThreatRegistry.sol";
import {IAgentIdentityRegistry} from "./IAgentIdentityRegistry.sol";

/**
 * @title ERC8259Guard
 * @notice Plug-and-play security guard for DeFi protocols and smart contracts.
 * @dev Add 2 lines of code to protect your protocol from malicious AI agents network-wide.
 * 
 * Example usage:
 * 
 *   import "@sigui/erc8259/ERC8259Guard.sol";
 * 
 *   contract MyDeFiVault is ERC8259Guard {
 *       constructor(address _threatRegistry) 
 *           ERC8259Guard(_threatRegistry, address(0)) {}
 * 
 *       function executeTrade(uint256 amount) external onlySafeAgent {
 *           // Protected DeFi execution logic
 *       }
 *   }
 */
abstract contract ERC8259Guard {

    /// @notice Standard ERC-8259 Threat Registry endpoint
    IThreatRegistry public immutable threatRegistry;
    
    /// @notice Standard ERC-8259 Agent Identity Registry endpoint (optional)
    IAgentIdentityRegistry public immutable identityRegistry;

    error ERC8259BlockedMaliciousAgent(address agent);
    error ERC8259UnverifiedAgent(address agent);
    error ERC8259LowTrustScore(address agent, uint16 score, uint16 requiredScore);

    /**
     * @param _threatRegistry Address of conformant ERC-8259 ThreatRegistry
     * @param _identityRegistry Address of conformant ERC-8259 IdentityRegistry (can be address(0))
     */
    constructor(address _threatRegistry, address _identityRegistry) {
        threatRegistry = IThreatRegistry(_threatRegistry);
        identityRegistry = IAgentIdentityRegistry(_identityRegistry);
    }

    /**
     * @notice Reverts if the caller is flagged as a malicious attacker in the global registry.
     */
    modifier onlySafeAgent() {
        if (address(threatRegistry) != address(0) && threatRegistry.isKnownAttacker(msg.sender)) {
            revert ERC8259BlockedMaliciousAgent(msg.sender);
        }
        _;
    }

    /**
     * @notice Reverts if the caller is not verified (Tier > 0) in the identity registry.
     */
    modifier onlyVerifiedAgent() {
        if (address(threatRegistry) != address(0) && threatRegistry.isKnownAttacker(msg.sender)) {
            revert ERC8259BlockedMaliciousAgent(msg.sender);
        }
        if (address(identityRegistry) != address(0) && !identityRegistry.isVerified(msg.sender)) {
            revert ERC8259UnverifiedAgent(msg.sender);
        }
        _;
    }

    /**
     * @notice Enforces a minimum trust score threshold (0-1000 basis points).
     */
    modifier minTrustScore(uint16 threshold) {
        if (address(threatRegistry) != address(0) && threatRegistry.isKnownAttacker(msg.sender)) {
            revert ERC8259BlockedMaliciousAgent(msg.sender);
        }
        if (address(identityRegistry) != address(0)) {
            uint16 score = identityRegistry.calculateTrustScore(msg.sender);
            if (score < threshold) {
                revert ERC8259LowTrustScore(msg.sender, score, threshold);
            }
        }
        _;
    }
}
