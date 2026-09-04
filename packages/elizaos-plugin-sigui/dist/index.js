// @elizaos-plugins/plugin-sigui v3.0.0 (CommonJS)
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

var index_exports = {};
__export(index_exports, {
  default: () => siguiPlugin,
  evaluateTransactionAction: () => evaluateTransactionAction,
  siguiPlugin: () => siguiPlugin,
  threatIntelProvider: () => threatIntelProvider,
  validateSiguiConfig: () => validateSiguiConfig
});
module.exports = __toCommonJS(index_exports);

async function validateSiguiConfig(runtime) {
  const url = runtime.getSetting("SIGUI_API_URL") || process.env.SIGUI_API_URL || "http://127.0.0.1:8000";
  const key = runtime.getSetting("SIGUI_API_KEY") || process.env.SIGUI_API_KEY;
  const requireZk = (runtime.getSetting("SIGUI_REQUIRE_ZK") || process.env.SIGUI_REQUIRE_ZK || "false") === "true";
  const failClosed = (runtime.getSetting("SIGUI_FAIL_CLOSED") || process.env.SIGUI_FAIL_CLOSED || "true") === "true";
  return { SIGUI_API_URL: url, SIGUI_API_KEY: key, SIGUI_REQUIRE_ZK: requireZk, SIGUI_FAIL_CLOSED: failClosed };
}

async function callSiguiApi(config, payload) {
  const zkParam = config.SIGUI_REQUIRE_ZK ? "?zk=true" : "";
  const endpoint = `${config.SIGUI_API_URL}/v2/evaluate${zkParam}`;
  const response = await fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(config.SIGUI_API_KEY && { Authorization: `Bearer ${config.SIGUI_API_KEY}` })
    },
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    throw new Error(`Sigui API returned ${response.status}: ${response.statusText}`);
  }
  return response.json();
}

const evaluateTransactionAction = {
  name: "EVALUATE_TRANSACTION_SECURITY",
  similes: ["CHECK_TRANSACTION_SAFETY", "AUDIT_TRANSACTION", "VERIFY_SMART_CONTRACT", "IS_THIS_SAFE", "SIGUI_CHECK"],
  description: "Evaluates a blockchain transaction or address using the Sigui Protocol AI Security Oracle (AMD MI300X + ZK proofs) to detect Drain Stars, Mixer Chains, and Rug Pulls before execution.",
  validate: async (runtime, _message) => {
    await validateSiguiConfig(runtime);
    return true;
  },
  handler: async (runtime, message, state, _options, callback) => {
    const config = await validateSiguiConfig(runtime);
    const text = message.content?.text || "";
    const addressMatch = text.match(/0x[a-fA-F0-9]{40}/);
    const amountMatch = text.match(/(\d+(?:\.\d+)?)\s*(?:USDC|ETH|BTC|SOL|APT)/i);
    const payload = {
      action_type: "transfer",
      destination: addressMatch ? addressMatch[0] : "0x0000000000000000000000000000000000000000",
      amount_usdc: amountMatch ? parseFloat(amountMatch[1]) : 0,
      chain: "ethereum"
    };
    try {
      const result = await callSiguiApi(config, payload);
      const decision = result.decision || "BLOCK";
      const riskScore = result.risk_score || 1.0;
      const reason = result.reason || "Threat detected by Sigui AI Oracle";
      const pattern = result.pattern || "UNKNOWN";
      const zkProof = !!result.zk_proof?.verified;
      const zkBadge = zkProof ? " [ZK-Verified \u2713]" : "";
      let responseText;
      if (decision === "BLOCK") {
        responseText = `\u{1F6A8} **SIGUI SECURITY ALERT \u2014 BLOCKED**${zkBadge}\n\nPattern: **${pattern}** | Risk: **${(riskScore * 100).toFixed(0)}%**\n\n${reason}\n\nThis transaction has been blocked by Sigui AI Oracle.`;
      } else if (decision === "ESCALATE") {
        responseText = `\u26A0\uFE0F **SIGUI WARNING \u2014 ESCALATION REQUIRED**${zkBadge}\n\nPattern: **${pattern}** | Risk: **${(riskScore * 100).toFixed(0)}%**\n\nAwaiting human review before proceeding.`;
      } else {
        responseText = `\u2705 **SIGUI CLEARED**${zkBadge}\n\nPattern: **${pattern}** | Risk: **${(riskScore * 100).toFixed(0)}%**\n\nTransaction to ${payload.destination.slice(0, 10)}\u2026 is safe to execute.`;
      }
      if (callback) callback({ text: responseText, content: result });
      if (decision === "BLOCK" && config.SIGUI_FAIL_CLOSED) return false;
      return true;
    } catch (error) {
      if (callback) {
        callback({
          text: `\u274C Sigui Oracle unreachable: ${error.message}. ${config.SIGUI_FAIL_CLOSED ? "Failing closed for safety." : "Proceeding with caution."}`,
          content: { error: error.message }
        });
      }
      return !config.SIGUI_FAIL_CLOSED;
    }
  },
  examples: [
    [
      { user: "{{user1}}", content: { text: "Send 500 USDC to 0x1234567890123456789012345678901234567890" } },
      { user: "{{agent}}", content: { text: "Let me verify this address with the Sigui AI Oracle before sending.", action: "EVALUATE_TRANSACTION_SECURITY" } }
    ]
  ]
};

const threatIntelProvider = {
  get: async (runtime, _message, _state) => {
    try {
      const config = await validateSiguiConfig(runtime);
      const resp = await fetch(`${config.SIGUI_API_URL}/api/threat-intel`, {
        headers: config.SIGUI_API_KEY ? { Authorization: `Bearer ${config.SIGUI_API_KEY}` } : {}
      });
      if (!resp.ok) return "Sigui threat intel unavailable.";
      const data = await resp.json();
      const patterns = (data.patterns || []).slice(0, 5);
      if (patterns.length === 0) return "No active threats detected by Sigui.";
      const lines = patterns.map(
        (p) => `\u2022 ${p.destination?.slice(0, 12)}\u2026 \u2014 ${p.pattern} (conf: ${(p.confidence * 100).toFixed(0)}%)`
      );
      return `**Sigui Live Threat Intel (last ${patterns.length} learned):**\n${lines.join("\n")}`;
    } catch {
      return "Sigui threat intel unavailable (oracle offline).";
    }
  }
};

const siguiPlugin = {
  name: "sigui",
  description: "Sigui Protocol \u2014 DePIN AI Security Oracle for ElizaOS. Detects Drain Stars, Mixer Chains & Rug Pulls using Qwen2-VL-7B on AMD MI300X + Groth16 ZK proofs.",
  actions: [evaluateTransactionAction],
  evaluators: [],
  providers: [threatIntelProvider]
};
