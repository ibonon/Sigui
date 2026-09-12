import { Plugin, Action, Provider, IAgentRuntime } from '@elizaos/core';

/**
 * @elizaos-plugins/plugin-sigui
 *
 * Sigui DePIN AI Security Oracle — ElizaOS Plugin
 *
 * Intercepts transaction calls from ElizaOS agents and evaluates them
 * in real-time using the Sigui Protocol API v2:
 *   - Vision inference (Qwen2-VL-7B on AMD MI300X GPU)
 *   - ZK-Sigui proofs (Groth16 BN128 simulation)
 *   - Dynamic threat blacklist (feedback loop)
 *
 * @module @elizaos-plugins/plugin-sigui
 * @version 3.0.0
 * @license MIT
 */

interface SiguiConfig {
    SIGUI_API_URL: string;
    SIGUI_API_KEY?: string;
    SIGUI_REQUIRE_ZK?: boolean;
    SIGUI_FAIL_CLOSED?: boolean;
}
declare function validateSiguiConfig(runtime: IAgentRuntime): Promise<SiguiConfig>;
declare const evaluateTransactionAction: Action;
declare const threatIntelProvider: Provider;
declare const siguiPlugin: Plugin;

export { type SiguiConfig, siguiPlugin as default, evaluateTransactionAction, siguiPlugin, threatIntelProvider, validateSiguiConfig };
