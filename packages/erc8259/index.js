/**
 * @sigui/erc8259
 * Standard Solidity interfaces and Guard for ERC-8259 (AI Agent Identity & Threat Registry).
 */
module.exports = {
  ERC8259Guard: require.resolve("./contracts/ERC8259Guard.sol"),
  IAgentIdentityRegistry: require.resolve("./contracts/IAgentIdentityRegistry.sol"),
  IThreatRegistry: require.resolve("./contracts/IThreatRegistry.sol"),
  IRiskAssessment: require.resolve("./contracts/IRiskAssessment.sol"),
};
