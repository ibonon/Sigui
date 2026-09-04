import type { Plugin, IAgentRuntime, Memory, State, Action, Provider } from "@elizaos/core";

export interface SiguiConfig {
    SIGUI_API_URL: string;
    SIGUI_API_KEY?: string;
    SIGUI_REQUIRE_ZK?: boolean;
    SIGUI_FAIL_CLOSED?: boolean;
}

export declare function validateSiguiConfig(runtime: IAgentRuntime): Promise<SiguiConfig>;
export declare const evaluateTransactionAction: Action;
export declare const threatIntelProvider: Provider;
export declare const siguiPlugin: Plugin;
export default siguiPlugin;
