import {
    ActionExample,
    HandlerCallback,
    IAgentRuntime,
    Memory,
    State,
    type Action,
    elizaLogger,
} from "@elizaos/core";
import { validateSiguiConfig } from "../environment";

export const evaluateTransactionAction: Action = {
    name: "EVALUATE_TRANSACTION_SECURITY",
    similes: [
        "CHECK_TRANSACTION_SAFETY",
        "AUDIT_TRANSACTION",
        "VERIFY_SMART_CONTRACT",
        "IS_THIS_SAFE"
    ],
    validate: async (runtime: IAgentRuntime, message: Memory) => {
        await validateSiguiConfig(runtime);
        return true;
    },
    description: "Evaluates a blockchain transaction or address using the Sigui Protocol AI Security Oracle to detect threats like Drain Stars, Mixer Chains, or Rug Pulls before executing a transaction.",
    handler: async (
        runtime: IAgentRuntime,
        message: Memory,
        state: State,
        options: any,
        callback?: HandlerCallback
    ): Promise<boolean> => {
        elizaLogger.log("Starting Sigui Protocol Security Evaluation");

        try {
            const config = await validateSiguiConfig(runtime);
            
            // Simplified extraction for the demo. In production, Eliza providers would use LLM extraction.
            const text = message.content.text.toLowerCase();
            const destinationMatch = text.match(/0x[a-fA-F0-9]{40}/);
            const destination = destinationMatch ? destinationMatch[0] : "0x0000000000000000000000000000000000000000";
            
            const amountMatch = text.match(/(\d+(\.\d+)?)\s*(usdc|eth|apt|strk)/);
            const amount = amountMatch ? parseFloat(amountMatch[1]) : 0;

            const response = await fetch(`${config.SIGUI_API_URL}/evaluate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(config.SIGUI_API_KEY && { "Authorization": `Bearer ${config.SIGUI_API_KEY}` })
                },
                body: JSON.stringify({
                    action_type: "transfer",
                    destination: destination,
                    amount_usdc: amount,
                    chain: "ethereum"
                })
            });

            if (!response.ok) {
                throw new Error(`Sigui API Error: ${response.statusText}`);
            }

            const result = await response.json();
            
            const decision = result.decision || "BLOCK";
            const riskScore = result.risk_score || 1.0;
            const reason = result.reason || "Unknown threat";

            let responseText = "";
            if (decision === "BLOCK") {
                responseText = `🚨 **SIGUI SECURITY ALERT: TRANSACTION BLOCKED** 🚨\n\nI cannot proceed with this transaction. The Sigui AI Oracle returned a HIGH RISK score of ${riskScore.toFixed(2)}.\n\nReason: ${reason}`;
            } else if (decision === "ESCALATE") {
                responseText = `⚠️ **SIGUI SECURITY WARNING: ESCALATION REQUIRED** ⚠️\n\nThis transaction is ambiguous (Risk Score: ${riskScore.toFixed(2)}). It has been escalated for manual review. I will await further human instructions before proceeding.\n\nReason: ${reason}`;
            } else {
                responseText = `✅ **SIGUI SECURITY CLEARED**\n\nThe transaction has been evaluated as low risk (Score: ${riskScore.toFixed(2)}). Proceeding with execution.`;
            }

            if (callback) {
                callback({
                    text: responseText,
                    content: result,
                });
            }

            // Return true if action successfully evaluated (even if the verdict is BLOCK, the action of *evaluating* succeeded)
            return true;
        } catch (error: any) {
            elizaLogger.error("Error in Sigui evaluation:", error);
            if (callback) {
                callback({
                    text: `❌ Error connecting to Sigui Security Oracle: ${error.message}. Failing closed for safety.`,
                    content: { error: error.message },
                });
            }
            return false;
        }
    },
    examples: [
        [
            {
                user: "{{user1}}",
                content: { text: "Can you send 500 USDC to 0x1234567890123456789012345678901234567890?" },
            },
            {
                user: "{{agent}}",
                content: {
                    text: "Let me check with Sigui Protocol to ensure this address is safe before I send the funds.",
                    action: "EVALUATE_TRANSACTION_SECURITY",
                },
            },
        ],
        [
            {
                user: "{{user1}}",
                content: { text: "Is the contract 0x000000000000000000000000000000000000dead safe to interact with?" },
            },
            {
                user: "{{agent}}",
                content: {
                    text: "I am evaluating the contract via the Sigui oracle to check for honeypots or drain stars.",
                    action: "EVALUATE_TRANSACTION_SECURITY",
                },
            },
        ],
    ] as ActionExample[][],
};
