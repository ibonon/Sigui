import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

function normalizeConfig(rawConfig) {
  const config = rawConfig && typeof rawConfig === "object" ? rawConfig : {};

  return {
    enabled: config.enabled !== false,
    apiUrl: typeof config.apiUrl === "string" && config.apiUrl
      ? config.apiUrl.replace(/\/+$/, "")
      : "http://127.0.0.1:8765",
    apiKeyEnvVar: typeof config.apiKeyEnvVar === "string" && config.apiKeyEnvVar
      ? config.apiKeyEnvVar
      : "SIGUI_API_KEY",
    agentId: typeof config.agentId === "string" && config.agentId
      ? config.agentId
      : "openclaw_agent",
    mode: config.mode === "approval-only" ? "approval-only" : "enforce",
    blockThreshold: clampNumber(config.blockThreshold, 0.85),
    escalateThreshold: clampNumber(config.escalateThreshold, 0.55),
    autoEscalate: config.autoEscalate === true,
    failOpen: config.failOpen === true,
    timeoutMs: clampPositiveInteger(config.timeoutMs, 10000),
    watchedTools: Array.isArray(config.watchedTools)
      ? config.watchedTools.filter((value) => typeof value === "string")
      : [],
  };
}

function clampNumber(value, fallback) {
  return typeof value === "number" && value >= 0 && value <= 1 ? value : fallback;
}

function clampPositiveInteger(value, fallback) {
  return Number.isInteger(value) && value > 0 ? value : fallback;
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function getString(value) {
  return typeof value === "string" ? value : "";
}

function getNumber(value) {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string" && value.trim() !== "") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function summarizeIntent(toolName, params) {
  const loweredToolName = toolName.toLowerCase();
  const destination =
    getString(params.destination) ||
    getString(params.to) ||
    getString(params.recipient) ||
    getString(params.address);
  const action =
    getString(params.action) ||
    getString(params.actionType) ||
    inferActionFromToolName(loweredToolName);
  const chain =
    getString(params.chain) ||
    inferChainFromToolName(loweredToolName) ||
    "unknown";
  const amount =
    getNumber(params.amount) ??
    getNumber(params.value) ??
    getNumber(params.amountUsdc);
  const looksWatched =
    /transfer|approve|swap|transaction|wallet|sign|send/.test(loweredToolName) ||
    Boolean(destination) ||
    Boolean(action);

  if (!looksWatched) {
    return null;
  }

  return {
    action: action || "transaction",
    chain,
    destination,
    amount,
    rawParams: params,
  };
}

function inferActionFromToolName(toolName) {
  if (toolName.includes("approve")) {
    return "approve";
  }
  if (toolName.includes("swap")) {
    return "swap";
  }
  if (toolName.includes("transfer") || toolName.includes("send")) {
    return "transfer";
  }
  if (toolName.includes("sign")) {
    return "sign";
  }
  return "";
}

function inferChainFromToolName(toolName) {
  if (toolName.includes("aptos")) {
    return "aptos";
  }
  if (toolName.includes("starknet")) {
    return "starknet";
  }
  if (toolName.includes("evm") || toolName.includes("ethereum")) {
    return "ethereum";
  }
  return "";
}

function assessRisk(intent) {
  let risk = 0.15;
  const reasons = [];

  if (intent.action === "approve") {
    risk += 0.4;
    reasons.push("token approval detected");
  }

  if (intent.action === "sign") {
    risk += 0.3;
    reasons.push("signature request detected");
  }

  if (intent.action === "swap") {
    risk += 0.15;
    reasons.push("asset swap detected");
  }

  if (intent.amount !== null) {
    if (intent.amount >= 10000) {
      risk += 0.35;
      reasons.push("large transaction amount");
    } else if (intent.amount >= 1000) {
      risk += 0.18;
      reasons.push("moderate transaction amount");
    }
  }

  if (!intent.destination) {
    risk += 0.12;
    reasons.push("missing destination metadata");
  }

  if (intent.chain === "unknown") {
    risk += 0.08;
    reasons.push("unknown execution chain");
  }

  return {
    risk: Math.min(1, Number(risk.toFixed(2))),
    reason: reasons.length > 0 ? reasons.join(", ") : "standard transaction profile",
  };
}

function buildApprovalDescription(toolName, intent, assessment) {
  const amountText = intent.amount === null ? "unknown" : String(intent.amount);
  const destinationText = intent.destination || "unknown destination";
  return [
    `Tool: ${toolName}`,
    `Action: ${intent.action}`,
    `Chain: ${intent.chain}`,
    `Amount: ${amountText}`,
    `Destination: ${destinationText}`,
    `Risk score: ${assessment.risk}`,
    `Reason: ${assessment.reason}`,
  ].join("\n");
}

function createAbortSignal(timeoutMs) {
  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
    return AbortSignal.timeout(timeoutMs);
  }
  return undefined;
}

async function postJson(url, body, headers, timeoutMs) {
  const response = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
    signal: createAbortSignal(timeoutMs),
  });

  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }

  if (!response.ok) {
    const detail =
      typeof payload.detail === "string"
        ? payload.detail
        : `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return payload;
}

function buildSiguiHeaders(config, intent) {
  const headers = {
    "Content-Type": "application/json",
    "X-Chain": intent.chain,
    "X-Amount": String(intent.amount ?? 0),
    "User-Agent": "openclaw-sigui-security/0.1.1",
  };

  const apiKey = process.env[config.apiKeyEnvVar];
  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  return headers;
}

function buildEvaluationPayload(config, intent, event) {
  return {
    agent_id: config.agentId,
    action_type: intent.action,
    amount_usdc: intent.amount ?? 0,
    destination: intent.destination || "unknown",
    chain: intent.chain,
    context: {
      tool_name: String(event.toolName || ""),
      tool_call_id: event.toolCallId ?? null,
      run_id: event.runId ?? event.context?.runId ?? null,
      session_id: event.context?.sessionId ?? null,
      session_key: event.context?.sessionKey ?? null,
      raw_params: intent.rawParams,
    },
    weights: {},
  };
}

function normalizeEvaluationResponse(raw, fallbackAssessment, intent) {
  const verdict = getString(raw.decision || raw.verdict || "BLOCK").toUpperCase();
  const riskScore = getNumber(raw.risk_score) ?? fallbackAssessment.risk;
  const reason = getString(raw.reason) || fallbackAssessment.reason;
  const proofUrl =
    getString(raw.onchain_proof) ||
    (getString(raw.arc_tx_log) ? `https://testnet.arcscan.app/tx/${raw.arc_tx_log}` : "");

  return {
    verdict,
    riskScore: Math.max(0, Math.min(1, riskScore)),
    reason,
    chain: getString(raw.chain) || intent.chain,
    proofUrl,
    confidence: getNumber(raw.confidence),
    raw,
  };
}

async function runSiguiEvaluation(config, intent, event) {
  const fallbackAssessment = assessRisk(intent);
  const headers = buildSiguiHeaders(config, intent);
  const evaluationPayload = buildEvaluationPayload(config, intent, event);

  const evaluationRaw = await postJson(
    `${config.apiUrl}/evaluate`,
    evaluationPayload,
    headers,
    config.timeoutMs,
  );
  const evaluation = normalizeEvaluationResponse(evaluationRaw, fallbackAssessment, intent);

  if (config.autoEscalate && evaluation.verdict === "ESCALATE") {
    const escalationRaw = await postJson(
      `${config.apiUrl}/escalate`,
      evaluationPayload,
      headers,
      config.timeoutMs,
    );

    const escalatedVerdict = getString(
      escalationRaw.escalation_result || escalationRaw.verdict || "BLOCK",
    ).toUpperCase();

    return {
      verdict: escalatedVerdict === "APPROVE" ? "ALLOW_WITH_CAP" : escalatedVerdict,
      riskScore: evaluation.riskScore,
      reason: getString(escalationRaw.reason) || evaluation.reason,
      chain: evaluation.chain,
      proofUrl: getString(escalationRaw.arc_tx_log)
        ? `https://testnet.arcscan.app/tx/${escalationRaw.arc_tx_log}`
        : evaluation.proofUrl,
      confidence: getNumber(escalationRaw.confidence) ?? evaluation.confidence,
      capAmountUsdc: getNumber(escalationRaw.cap_amount_usdc),
      analysis: getString(escalationRaw.analysis),
      raw: {
        evaluate: evaluationRaw,
        escalate: escalationRaw,
      },
    };
  }

  return evaluation;
}

function describeSiguiDecision(toolName, intent, decision) {
  const amountText = intent.amount === null ? "unknown" : String(intent.amount);
  const destinationText = intent.destination || "unknown destination";
  const lines = [
    `Tool: ${toolName}`,
    `Action: ${intent.action}`,
    `Chain: ${decision.chain || intent.chain}`,
    `Amount: ${amountText}`,
    `Destination: ${destinationText}`,
    `Verdict: ${decision.verdict}`,
    `Risk score: ${decision.riskScore}`,
    `Reason: ${decision.reason}`,
  ];

  if (decision.capAmountUsdc !== null && decision.capAmountUsdc !== undefined) {
    lines.push(`Cap amount (USDC): ${decision.capAmountUsdc}`);
  }
  if (decision.analysis) {
    lines.push(`Analysis: ${decision.analysis}`);
  }
  if (decision.proofUrl) {
    lines.push(`Proof: ${decision.proofUrl}`);
  }

  return lines.join("\n");
}

function classifySeverity(config, decision) {
  if (decision.verdict === "BLOCK" || decision.riskScore >= config.blockThreshold) {
    return "critical";
  }
  if (decision.verdict === "ESCALATE" || decision.riskScore >= config.escalateThreshold) {
    return "warning";
  }
  return "info";
}

function buildFailureDecision(config, toolName, intent, error) {
  const message = `Sigui API error for ${toolName}: ${error instanceof Error ? error.message : String(error)}`;
  if (config.failOpen) {
    return {
      requireApproval: {
        title: "Sigui unavailable",
        description: [
          message,
          `Action: ${intent.action}`,
          `Chain: ${intent.chain}`,
          `Destination: ${intent.destination || "unknown"}`,
        ].join("\n"),
        severity: "warning",
        timeoutMs: 60000,
        timeoutBehavior: "deny",
      },
    };
  }

  return {
    block: true,
    blockReason: `${message}. Failing closed because failOpen=false.`,
  };
}

export default definePluginEntry({
  id: "sigui-security",
  name: "Sigui Security",
  description: "Preflight policy checks for risky blockchain tool calls.",
  register(api) {
    api.on(
      "before_tool_call",
      async (event) => {
        const config = normalizeConfig(event.context?.pluginConfig);
        if (!config.enabled || !isObject(event.params)) {
          return;
        }

        const toolName = String(event.toolName || "");
        const watchedByName =
          config.watchedTools.length === 0 ||
          config.watchedTools.some((entry) => entry === toolName);
        const intent = summarizeIntent(toolName, event.params);

        if (!watchedByName && !intent) {
          return;
        }

        if (!intent) {
          return {
            requireApproval: {
              title: "Sigui review required",
              description: `Sigui could not fully classify tool ${toolName}. Manual approval required.`,
              severity: "warning",
              timeoutMs: 60000,
              timeoutBehavior: "deny",
            },
          };
        }

        let decision;
        try {
          decision = await runSiguiEvaluation(config, intent, event);
        } catch (error) {
          return buildFailureDecision(config, toolName, intent, error);
        }

        const description = describeSiguiDecision(toolName, intent, decision);
        const severity = classifySeverity(config, decision);

        if (config.mode === "approval-only" || decision.verdict === "ESCALATE") {
          return {
            requireApproval: {
              title: decision.verdict === "ESCALATE" ? "Sigui escalation" : "Sigui security approval",
              description,
              severity,
              timeoutMs: 60000,
              timeoutBehavior: "deny",
            },
          };
        }

        if (decision.verdict === "BLOCK" || decision.riskScore >= config.blockThreshold) {
          return {
            block: true,
            blockReason: `Sigui blocked ${intent.action} on ${decision.chain}: ${decision.reason} (risk ${decision.riskScore}).`,
          };
        }

        if (decision.verdict === "ALLOW_WITH_CAP") {
          return {
            requireApproval: {
              title: "Sigui capped approval",
              description,
              severity,
              timeoutMs: 60000,
              timeoutBehavior: "deny",
            },
          };
        }

        return;
      },
      { priority: 80, timeoutMs: 10000 },
    );
  },
});
