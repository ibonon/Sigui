import { IAgentRuntime, Memory, Provider, State, elizaLogger } from "@elizaos/core";
import { validateSiguiConfig } from "../environment";

export const threatProvider: Provider = {
    get: async (runtime: IAgentRuntime, message: Memory, state?: State) => {
        try {
            const config = await validateSiguiConfig(runtime);
            
            // In a real scenario, this would query a global /status or /threats endpoint.
            // For now, we simulate fetching the current global threat level from the oracle.
            // A real implementation would hit: fetch(`${config.SIGUI_API_URL}/threats/status`)
            
            const threatStatus = "NORMAL"; // Could be NORMAL, ELEVATED, CRITICAL
            const activeThreats = 0; // Number of active global threats

            return `Sigui Security Oracle Global Status: ${threatStatus}. Active network-wide threats detected: ${activeThreats}. If the status is CRITICAL, advise extreme caution for any transaction.`;
        } catch (error: any) {
            elizaLogger.error("Failed to fetch Sigui threat status in provider:", error);
            return `Sigui Security Oracle Global Status: UNKNOWN (Error: ${error.message})`;
        }
    }
};
