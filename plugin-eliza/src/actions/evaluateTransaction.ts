import {
    ActionExample,
    HandlerCallback,
    IAgentRuntime,
    Memory,
    State,
    type Action,
    elizaLogger,
    composeContext,
    generateObject,
    ModelClass
} from "@elizaos/core";
import { z } from "zod";
import { validateSiguiConfig } from "../environment";

const extractionTemplate = `
Extract information about the blockchain transaction from the user's message.

User Message:
{{message.content.text}}

Extract the following information:
- action_type: The type of action (e.g., 'transfer', 'swap', 'approve', 'mint', 'interact'). Default to 'transfer' if unclear.
- destination: The destination address or contract address. If not explicitly provided, use "0x0000000000000000000000000000000000000000".
- amount: The numerical amount involved (e.g., 500). If none, use 0.
- chain: The blockchain network mentioned (e.g., 'ethereum', 'aptos', 'starknet', 'solana', 'polygon'). Default to 'ethereum' if none is mentioned.
`;

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
            
            // Update state with message if needed
            if (!state) {
                state = (await runtime.composeState(message)) as State;
            } else {
                state = await runtime.updateRecentMessageState(state);
            }

            // LLM Extraction for transaction parameters
            const context = composeContext({
                state,
                template: extractionTemplate,
            });

            const extractionObj = await generateObject({
                runtime,
                context,
                modelClass: ModelClass.SMALL,
                schema: z.object({
                    action_type: z.string(),
                    destination: z.string(),
                    amount: z.number(),
                    chain: z.string()
                })
            });
            
            const extracted = extractionObj.object as any;
            
            const destination = extracted?.destination || "0x0000000000000000000000000000000000000000";
            const amount = extracted?.amount || 0;
            const action_type = extracted?.action_type || "transfer";
            const chain = extracted?.chain || "ethereum";

            const response = await fetch(`${config.SIGUI_API_URL}/evaluate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(config.SIGUI_API_KEY && { "Authorization": `Bearer ${config.SIGUI_API_KEY}` })
                },
                body: JSON.stringify({
                    action_type: action_type,
                    destination: destination,
                    amount_usdc: amount,
                    chain: chain
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
                responseText = `🚨 **SIGUI SECURITY ALERT: TRANSACTION BLOCKED** 🚨\n\nI cannot proceed with this transaction on ${chain}. The Sigui AI Oracle returned a HIGH RISK score of ${riskScore.toFixed(2)}.\n\nReason: ${reason}`;
            } else if (decision === "ESCALATE") {
                responseText = `⚠️ **SIGUI SECURITY WARNING: ESCALATION REQUIRED** ⚠️\n\nThis ${action_type} on ${chain} is ambiguous (Risk Score: ${riskScore.toFixed(2)}). It has been escalated for manual review. I will await further human instructions before proceeding.\n\nReason: ${reason}`;
            } else {
                responseText = `✅ **SIGUI SECURITY CLEARED**\n\nThe ${action_type} to ${destination} on ${chain} has been evaluated as low risk (Score: ${riskScore.toFixed(2)}). Proceeding with execution.`;
            }

            if (callback) {
                callback({
                    text: responseText,
                    content: result,
                });
            }

            // Save the evaluation result back into memory
            const evaluationMemory: Memory = {
                id: crypto.randomUUID(),
                userId: runtime.agentId,
                agentId: runtime.agentId,
                roomId: message.roomId,
                content: {
                    text: `Evaluated transaction: ${action_type} of ${amount} to ${destination} on ${chain}. Result: ${decision}. Reason: ${reason}`,
                    action: "EVALUATE_TRANSACTION_SECURITY",
                    source: "sigui_oracle"
                },
                createdAt: Date.now()
            };
            await runtime.messageManager.createMemory(evaluationMemory);

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
