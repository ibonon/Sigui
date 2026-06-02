// src/actions/evaluateTransaction.ts
import {
  elizaLogger
} from "@elizaos/core";

// src/environment.ts
import { z } from "zod";
var siguiEnvSchema = z.object({
  SIGUI_API_URL: z.string().url().default("https://api.sigui.io"),
  SIGUI_API_KEY: z.string().optional()
});
async function validateSiguiConfig(runtime) {
  try {
    const config = {
      SIGUI_API_URL: runtime.getSetting("SIGUI_API_URL") || process.env.SIGUI_API_URL,
      SIGUI_API_KEY: runtime.getSetting("SIGUI_API_KEY") || process.env.SIGUI_API_KEY
    };
    return siguiEnvSchema.parse(config);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errorMessages = error.errors.map((err) => `${err.path.join(".")}: ${err.message}`).join("\n");
      throw new Error(
        `Sigui Protocol configuration validation failed:
${errorMessages}`
      );
    }
    throw error;
  }
}

// src/actions/evaluateTransaction.ts
var evaluateTransactionAction = {
  name: "EVALUATE_TRANSACTION_SECURITY",
  similes: [
    "CHECK_TRANSACTION_SAFETY",
    "AUDIT_TRANSACTION",
    "VERIFY_SMART_CONTRACT",
    "IS_THIS_SAFE"
  ],
  validate: async (runtime, message) => {
    await validateSiguiConfig(runtime);
    return true;
  },
  description: "Evaluates a blockchain transaction or address using the Sigui Protocol AI Security Oracle to detect threats like Drain Stars, Mixer Chains, or Rug Pulls before executing a transaction.",
  handler: async (runtime, message, state, options, callback) => {
    elizaLogger.log("Starting Sigui Protocol Security Evaluation");
    try {
      const config = await validateSiguiConfig(runtime);
      const text = message.content.text.toLowerCase();
      const destinationMatch = text.match(/0x[a-fA-F0-9]{40}/);
      const destination = destinationMatch ? destinationMatch[0] : "0x0000000000000000000000000000000000000000";
      const amountMatch = text.match(/(\d+(\.\d+)?)\s*(usdc|eth|apt|strk)/);
      const amount = amountMatch ? parseFloat(amountMatch[1]) : 0;
      const response = await fetch(`${config.SIGUI_API_URL}/evaluate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...config.SIGUI_API_KEY && { "Authorization": `Bearer ${config.SIGUI_API_KEY}` }
        },
        body: JSON.stringify({
          action_type: "transfer",
          destination,
          amount_usdc: amount,
          chain: "ethereum"
        })
      });
      if (!response.ok) {
        throw new Error(`Sigui API Error: ${response.statusText}`);
      }
      const result = await response.json();
      const decision = result.decision || "BLOCK";
      const riskScore = result.risk_score || 1;
      const reason = result.reason || "Unknown threat";
      let responseText = "";
      if (decision === "BLOCK") {
        responseText = `\u{1F6A8} **SIGUI SECURITY ALERT: TRANSACTION BLOCKED** \u{1F6A8}

I cannot proceed with this transaction. The Sigui AI Oracle returned a HIGH RISK score of ${riskScore.toFixed(2)}.

Reason: ${reason}`;
      } else if (decision === "ESCALATE") {
        responseText = `\u26A0\uFE0F **SIGUI SECURITY WARNING: ESCALATION REQUIRED** \u26A0\uFE0F

This transaction is ambiguous (Risk Score: ${riskScore.toFixed(2)}). It has been escalated for manual review. I will await further human instructions before proceeding.

Reason: ${reason}`;
      } else {
        responseText = `\u2705 **SIGUI SECURITY CLEARED**

The transaction has been evaluated as low risk (Score: ${riskScore.toFixed(2)}). Proceeding with execution.`;
      }
      if (callback) {
        callback({
          text: responseText,
          content: result
        });
      }
      return true;
    } catch (error) {
      elizaLogger.error("Error in Sigui evaluation:", error);
      if (callback) {
        callback({
          text: `\u274C Error connecting to Sigui Security Oracle: ${error.message}. Failing closed for safety.`,
          content: { error: error.message }
        });
      }
      return false;
    }
  },
  examples: [
    [
      {
        user: "{{user1}}",
        content: { text: "Can you send 500 USDC to 0x1234567890123456789012345678901234567890?" }
      },
      {
        user: "{{agent}}",
        content: {
          text: "Let me check with Sigui Protocol to ensure this address is safe before I send the funds.",
          action: "EVALUATE_TRANSACTION_SECURITY"
        }
      }
    ],
    [
      {
        user: "{{user1}}",
        content: { text: "Is the contract 0x000000000000000000000000000000000000dead safe to interact with?" }
      },
      {
        user: "{{agent}}",
        content: {
          text: "I am evaluating the contract via the Sigui oracle to check for honeypots or drain stars.",
          action: "EVALUATE_TRANSACTION_SECURITY"
        }
      }
    ]
  ]
};

// src/index.ts
var siguiPlugin = {
  name: "sigui",
  description: "Sigui Protocol Plugin for ElizaOS. Provides real-time AI security oracle evaluations for blockchain transactions to prevent Drain Stars, Rug Pulls, and Mixer Chains.",
  actions: [evaluateTransactionAction],
  evaluators: [],
  providers: []
};
var index_default = siguiPlugin;
export {
  index_default as default,
  siguiPlugin
};
//# sourceMappingURL=index.js.map