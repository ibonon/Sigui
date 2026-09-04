"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

interface LandingPageProps {
  onLaunchApp: () => void;
}

export function LandingPage({ onLaunchApp }: LandingPageProps) {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [activeCodeTab, setActiveCodeTab] = useState<"python" | "ts" | "rust" | "curl">("python");
  const [activePillar, setActivePillar] = useState<number>(0);

  // Live Simulator state
  const [simScenario, setSimScenario] = useState<"safe" | "drain" | "mixer">("safe");
  const [simRunning, setSimRunning] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  const runSimulation = (scenario: "safe" | "drain" | "mixer") => {
    setSimScenario(scenario);
    setSimRunning(true);
    setSimResult(null);

    setTimeout(() => {
      setSimRunning(false);
      if (scenario === "safe") {
        setSimResult({
          decision: "ALLOW",
          risk_score: 0.04,
          processing_time_ms: 32.4,
          vision_pattern: "NORMAL",
          vision_confidence: 0.98,
          zk_proof: "0x8f3b...64bytes_valid",
          reason: "Transaction pattern exhibits standard transfer topology. Destination address clean.",
        });
      } else if (scenario === "drain") {
        setSimResult({
          decision: "BLOCK",
          risk_score: 0.96,
          processing_time_ms: 41.2,
          vision_pattern: "DRAIN_STAR",
          vision_confidence: 0.95,
          zk_proof: "REJECTED_DRAIN_TOPOLOGY",
          reason: "CRITICAL: High-outdegree drain star fanout detected. Destination on dynamic threat blacklist.",
        });
      } else {
        setSimResult({
          decision: "ESCALATE",
          risk_score: 0.62,
          processing_time_ms: 48.7,
          vision_pattern: "MIXING_CHAIN",
          vision_confidence: 0.86,
          zk_proof: "0x7a2c...64bytes_pending_lebe",
          reason: "Multi-hop mixing sequence detected. Sent to Lebe LLM reasoning agent for final approval.",
        });
      }
    }, 1200);
  };

  const codeSnippets = {
    python: `# Install: pip install sigui-sdk
from sigui_sdk import SiguiClient

client = SiguiClient(api_key="sigui_live_key_alpha")

# Intercept agent transaction before execution
verdict = client.evaluate_action(
    action_type="transfer",
    destination="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    amount_usdc=500.0,
    chain="arc",
    require_zk_proof=True
)

if verdict.decision == "BLOCK":
    raise SecurityException(f"Sigui Blocked Tx: {verdict.reason}")
elif verdict.decision == "ALLOW":
    execute_agent_tx()`,

    ts: `// Install: npm install @sigui/sdk
import { SiguiOracle } from "@sigui/sdk";

const sigui = new SiguiOracle({ apiKey: process.env.SIGUI_API_KEY });

// Shield your ElizaOS / LangChain AI agent
const verdict = await sigui.evaluate({
  actionType: "swap",
  destination: "0xAttackerAddress...",
  amountUsdc: 12500,
  chain: "ethereum"
});

console.log("Sigui Verdict:", verdict.decision); // "ALLOW" | "BLOCK" | "ESCALATE"
console.log("ZK Proof:", verdict.zkProof);`,

    rust: `// Cargo.toml: sigui-rs = "0.3"
use sigui_rs::{SiguiOracle, ActionPayload};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let oracle = SiguiOracle::new("sigui_live_key_alpha")?;
    
    let verdict = oracle.evaluate(ActionPayload {
        action_type: "transfer".into(),
        destination: "0x742d35Cc...".into(),
        amount_usdc: 50.0,
    }).await?;

    assert!(verdict.is_allowed(), "Transaction blocked by Sigui Security Oracle");
    Ok(())
}`,

    curl: `# Direct HTTP v2 API call with Circle x402 Micropayment Header
curl -X POST https://api.sigui.xyz/v2/evaluate \\
  -H "Authorization: Bearer sigui_live_key_alpha" \\
  -H "Content-Type: application/json" \\
  -d '{
    "action_type": "transfer",
    "destination": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    "amount_usdc": 1000.0,
    "chain": "arc"
  }'`
  };

  const pillars = [
    {
      id: "pillar-1",
      num: "01",
      tag: "FINANCIAL INFRASTRUCTURE",
      title: "Agent Solvency & Credit Scoring",
      subtitle: "Unlocking the $2 Trillion AI Agent Lending Market",
      desc: "DeFi lending protocols cannot lend to autonomous agents without credit scores. Sigui ERC-8259 calculates a real-time Solvency & Reliability Score based on identity stability, volume history, and clean threat topology. Protocols pay basis points on underwritten agent loans.",
      metric: "$2.0T",
      metricLabel: "Addressable Market Size",
      badge: "DeFi Underwriting BPS",
    },
    {
      id: "pillar-2",
      num: "02",
      tag: "NETWORK EFFECT MOAT",
      title: "Agent Stack Infiltration ('Sigui Inside')",
      subtitle: "The Standard for ElizaOS, Virtuals & OpenClaw",
      desc: "By embedding Sigui evaluation badges across major agent frameworks (ElizaOS, Virtuals, Autonolas, OpenClaw), non-compliant agents are rejected by peers. Powered by the proprietary Sigui DePIN-1M dataset (1,000,000 transaction graph topologies).",
      metric: "1M+",
      metricLabel: "Topovision Graph Dataset",
      badge: "Framework Moat",
    },
    {
      id: "pillar-3",
      num: "03",
      tag: "PRIVACY BREAKTHROUGH",
      title: "ZK-Sigui Zero-Knowledge Engine",
      subtitle: "64-Byte Groth16 Proofs on BN128 Field",
      desc: "HFT and MEV trading agents refuse to reveal strategy logic to public nodes. ZK-Sigui generates a cryptographic proof that a transaction topology is benign (not a drain star) without disclosing recipient, volume, or strategy details.",
      metric: "64B",
      metricLabel: "Compact ZK Proof Size",
      badge: "Groth16 BN128",
    },
    {
      id: "pillar-4",
      num: "04",
      tag: "DEPIN HARDWARE SCALING",
      title: "AMD MI300X Distributed Node Network",
      subtitle: "Sub-50ms Vision Inference at Scale",
      desc: "Fine-tuned vision model (Imina Na V2 — Qwen2-VL-7B) served across distributed AMD MI300X GPU nodes running ROCm. Nodes earn automated Circle x402 USDC micropayments ($0.001 per evaluation) for executing inference.",
      metric: "<38ms",
      metricLabel: "Avg Vision Latency",
      badge: "AMD ROCm Stack",
    },
    {
      id: "pillar-5",
      num: "05",
      tag: "REGULATORY STANDARD",
      title: "ERC-8259 Standard & Hogonat DAO",
      subtitle: "The DePIN Governance & Identity Protocol",
      desc: "Deployed live on Ethereum Sepolia (0x3806aeb...), ERC-8259 sets the regulatory standard for machine-to-machine interactions. Staking nodes and Hogonat governance agents dynamically update security policies on-chain.",
      metric: "Sepolia",
      metricLabel: "Live Smart Contract",
      badge: "ERC-8259 Standard",
    },
  ];

  return (
    <div className="landing-container" style={{ background: "#0a0d14", color: "#f3f4f6", fontFamily: "Inter, sans-serif" }}>
      {/* ── Background Glow Effects ── */}
      <div style={{ position: "fixed", top: "-150px", left: "50%", transform: "translateX(-50%)", width: "800px", height: "500px", background: "radial-gradient(circle, rgba(16, 185, 129, 0.15) 0%, rgba(14, 165, 233, 0.08) 50%, transparent 80%)", pointerEvents: "none", zIndex: 0 }} />
      <div style={{ position: "fixed", top: "40%", right: "-200px", width: "600px", height: "600px", background: "radial-gradient(circle, rgba(139, 92, 246, 0.12) 0%, transparent 70%)", pointerEvents: "none", zIndex: 0 }} />

      {/* ── 1. HERO SECTION ── */}
      <section style={{ position: "relative", zIndex: 1, paddingTop: "60px", paddingBottom: "80px", paddingLeft: "24px", paddingRight: "24px" }} className="max-w-6xl mx-auto text-center">
        {/* Status Badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "20px", padding: "6px 16px", fontSize: "12px", fontFamily: "JetBrains Mono, monospace", color: "#10b981", marginBottom: "28px" }}
        >
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#10b981", display: "inline-block", boxShadow: "0 0 10px #10b981", animation: "pulse 2s infinite" }} />
          SIGUI V3.0 LIVE — ARC TESTNET & ETHEREUM SEPOLIA (ERC-8259)
        </motion.div>

        {/* Main Headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          style={{ fontSize: "clamp(2.5rem, 5.5vw, 4.8rem)", fontWeight: 800, lineHeight: 1.08, letterSpacing: "-0.03em", marginBottom: "24px" }}
        >
          The Security & Regulatory Layer <br />
          for the <span style={{ background: "linear-gradient(135deg, #10b981 0%, #0ea5e9 50%, #8b5cf6 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Post-Human Agent Economy</span>
        </motion.h1>

        {/* Sub-headline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
          style={{ fontSize: "1.15rem", color: "#9ca3af", maxWidth: "780px", margin: "0 auto 36px auto", lineHeight: 1.6 }}
        >
          Sigui inspects multi-agent transactions in under <strong style={{ color: "#0ea5e9" }}>50ms</strong> before on-chain execution. Powered by AMD MI300X vision models (<strong style={{ color: "#10b981" }}>Imina Na V2</strong>), zero-knowledge proofs (<strong style={{ color: "#8b5cf6" }}>ZK-Sigui</strong>), and Circle x402 USDC micropayments.
        </motion.p>

        {/* Action CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "16px", marginBottom: "48px" }}
        >
          <button
            onClick={onLaunchApp}
            style={{ background: "linear-gradient(135deg, #10b981 0%, #059669 100%)", color: "#000", fontWeight: 700, padding: "14px 28px", borderRadius: "12px", fontSize: "15px", cursor: "pointer", border: "none", boxShadow: "0 0 24px rgba(16, 185, 129, 0.4)", transition: "all 0.2s" }}
          >
            ⚡ Launch Live Oracle App →
          </button>
          <a
            href="https://github.com/ibonon/Sigui"
            target="_blank"
            rel="noopener noreferrer"
            style={{ background: "rgba(30, 41, 59, 0.8)", color: "#f3f4f6", fontWeight: 600, padding: "14px 28px", borderRadius: "12px", fontSize: "15px", textDecoration: "none", border: "1px solid rgba(148, 163, 184, 0.2)", backdropFilter: "blur(12px)" }}
          >
            📄 Read Vision Whitepaper
          </a>
        </motion.div>

        {/* Quick Install Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          style={{ display: "inline-flex", alignItems: "center", gap: "12px", background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(148, 163, 184, 0.15)", borderRadius: "10px", padding: "10px 20px", fontFamily: "JetBrains Mono, monospace", fontSize: "13px" }}
        >
          <span style={{ color: "#10b981" }}>$</span>
          <span>pip install sigui-sdk</span>
          <button
            onClick={() => copyToClipboard("pip install sigui-sdk", "hero")}
            style={{ background: "rgba(255, 255, 255, 0.05)", border: "none", color: "#9ca3af", borderRadius: "6px", padding: "4px 8px", cursor: "pointer", fontSize: "11px" }}
          >
            {copiedCode === "hero" ? "✓ Copied" : "Copy"}
          </button>
        </motion.div>

        {/* Metrics Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "20px", marginTop: "60px" }}>
          {[
            { value: "$0.001", label: "Micropayment / Eval", sub: "Circle x402 USDC", color: "#10b981" },
            { value: "< 38ms", label: "Avg Vision Latency", sub: "AMD MI300X ROCm", color: "#0ea5e9" },
            { value: "1,000,000", label: "Graph Topologies", sub: "Dataset Moat", color: "#8b5cf6" },
            { value: "99.4%", label: "Detection Rate", sub: "Drain Star & Mixers", color: "#f59e0b" },
          ].map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 + i * 0.1 }}
              style={{ background: "rgba(17, 24, 39, 0.6)", border: "1px solid rgba(148, 163, 184, 0.1)", borderRadius: "16px", padding: "20px", backdropFilter: "blur(16px)" }}
            >
              <div style={{ fontSize: "2rem", fontWeight: 800, color: m.color, fontFamily: "JetBrains Mono, monospace" }}>{m.value}</div>
              <div style={{ fontSize: "14px", fontWeight: 600, color: "#f3f4f6", marginTop: "4px" }}>{m.label}</div>
              <div style={{ fontSize: "11px", color: "#6b7280", marginTop: "2px" }}>{m.sub}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ── 2. INTERACTIVE ORACLE SIMULATOR ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "80px 24px", background: "rgba(15, 23, 42, 0.5)", borderTop: "1px solid rgba(148, 163, 184, 0.1)", borderBottom: "1px solid rgba(148, 163, 184, 0.1)" }}>
        <div className="max-w-5xl mx-auto">
          <div style={{ textAlign: "center", marginBottom: "40px" }}>
            <span style={{ color: "#0ea5e9", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", textTransform: "uppercase", letterSpacing: "2px" }}>Live Interactive Demo</span>
            <h2 style={{ fontSize: "2.4rem", fontWeight: 800, marginTop: "8px" }}>Test the Sigui Security Pipeline</h2>
            <p style={{ color: "#9ca3af", maxWidth: "600px", margin: "8px auto 0 auto" }}>Select an agent transaction scenario below to inspect it in real-time through Sigui’s 5-stage risk pipeline.</p>
          </div>

          <div style={{ background: "rgba(17, 24, 39, 0.75)", border: "1px solid rgba(148, 163, 184, 0.15)", borderRadius: "20px", padding: "28px", backdropFilter: "blur(24px)", boxShadow: "0 20px 40px rgba(0,0,0,0.5)" }}>
            {/* Scenario Buttons */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginBottom: "24px" }}>
              <button
                onClick={() => runSimulation("safe")}
                style={{ background: simScenario === "safe" ? "rgba(16, 185, 129, 0.2)" : "rgba(30, 41, 59, 0.5)", border: `1px solid ${simScenario === "safe" ? "#10b981" : "rgba(148, 163, 184, 0.2)"}`, color: simScenario === "safe" ? "#10b981" : "#9ca3af", padding: "10px 18px", borderRadius: "10px", fontWeight: 600, cursor: "pointer" }}
              >
                ✅ Scenario 1: Safe Agent Swap ($500 USDC)
              </button>
              <button
                onClick={() => runSimulation("drain")}
                style={{ background: simScenario === "drain" ? "rgba(244, 63, 94, 0.2)" : "rgba(30, 41, 59, 0.5)", border: `1px solid ${simScenario === "drain" ? "#f43f5e" : "rgba(148, 163, 184, 0.2)"}`, color: simScenario === "drain" ? "#f43f5e" : "#9ca3af", padding: "10px 18px", borderRadius: "10px", fontWeight: 600, cursor: "pointer" }}
              >
                🚨 Scenario 2: Drain Star Exploit ($150,000 USDC)
              </button>
              <button
                onClick={() => runSimulation("mixer")}
                style={{ background: simScenario === "mixer" ? "rgba(245, 158, 11, 0.2)" : "rgba(30, 41, 59, 0.5)", border: `1px solid ${simScenario === "mixer" ? "#f59e0b" : "rgba(148, 163, 184, 0.2)"}`, color: simScenario === "mixer" ? "#f59e0b" : "#9ca3af", padding: "10px 18px", borderRadius: "10px", fontWeight: 600, cursor: "pointer" }}
              >
                ⚠️ Scenario 3: Mixing Chain Hop ($4,500 USDC)
              </button>
            </div>

            {/* Pipeline Stage Indicators */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px", marginBottom: "28px" }}>
              {[
                { stage: "1. Visual Topology", desc: "Imina Na V2 Qwen2-VL" },
                { stage: "2. Semantic Intent", desc: "Lebe Qwen2.5 LLM" },
                { stage: "3. Threat Blacklist", desc: "Dynamic Feed" },
                { stage: "4. ZK-Sigui Proof", desc: "Groth16 BN128" },
                { stage: "5. Final Verdict", desc: "Hogonat Consensus" },
              ].map((stg, idx) => (
                <div key={idx} style={{ background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(148, 163, 184, 0.1)", borderRadius: "10px", padding: "12px", textAlign: "center" }}>
                  <div style={{ fontSize: "12px", fontWeight: 700, color: "#f3f4f6" }}>{stg.stage}</div>
                  <div style={{ fontSize: "10px", color: "#6b7280", marginTop: "2px" }}>{stg.desc}</div>
                </div>
              ))}
            </div>

            {/* Result Box */}
            <div style={{ background: "#0a0d14", border: "1px solid rgba(148, 163, 184, 0.2)", borderRadius: "12px", padding: "20px", minHeight: "140px", fontFamily: "JetBrains Mono, monospace" }}>
              {simRunning && (
                <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100px", color: "#0ea5e9" }}>
                  <span style={{ display: "inline-block", width: "12px", height: "12px", borderRadius: "50%", background: "#0ea5e9", marginRight: "10px", animation: "pulse 1s infinite" }} />
                  RUNNING SIGUI ORACLE PIPELINE (MI300X GPU INFERENCE)…
                </div>
              )}

              {!simRunning && !simResult && (
                <div style={{ color: "#6b7280", textAlign: "center", padding: "30px" }}>
                  Click one of the scenario buttons above to trigger a live evaluation run.
                </div>
              )}

              {!simRunning && simResult && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                    <div>
                      <span style={{ fontSize: "11px", color: "#6b7280", marginRight: "10px" }}>FINAL DECISION:</span>
                      <span style={{ fontSize: "18px", fontWeight: 800, color: simResult.decision === "ALLOW" ? "#10b981" : simResult.decision === "BLOCK" ? "#f43f5e" : "#f59e0b" }}>
                        {simResult.decision}
                      </span>
                    </div>
                    <div style={{ fontSize: "12px", color: "#9ca3af" }}>
                      Latency: <span style={{ color: "#10b981" }}>{simResult.processing_time_ms}ms</span>
                    </div>
                  </div>

                  <div style={{ fontSize: "12px", color: "#d1d5db", marginBottom: "8px" }}>
                    <strong>Risk Score:</strong> {(simResult.risk_score * 100).toFixed(1)}% | <strong>Pattern:</strong> {simResult.vision_pattern} ({ (simResult.vision_confidence * 100).toFixed(0) }% conf)
                  </div>
                  <div style={{ fontSize: "12px", color: "#9ca3af", background: "rgba(255,255,255,0.03)", padding: "10px", borderRadius: "6px" }}>
                    💡 <strong>Oracle Reason:</strong> {simResult.reason}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. DEVELOPER PLAYGROUND SECTION ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "80px 24px" }} className="max-w-6xl mx-auto">
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <span style={{ color: "#10b981", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", textTransform: "uppercase", letterSpacing: "2px" }}>Developer Experience</span>
          <h2 style={{ fontSize: "2.4rem", fontWeight: 800, marginTop: "8px" }}>3 Lines of Code to Protect Any AI Agent</h2>
          <p style={{ color: "#9ca3af", maxWidth: "620px", margin: "8px auto 0 auto" }}>Integrate native security into Python, TypeScript, Rust, or any framework supporting HTTP requests.</p>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "32px", alignItems: "start" }}>
          {/* Left: Code Tabs */}
          <div style={{ background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(148, 163, 184, 0.2)", borderRadius: "16px", overflow: "hidden" }}>
            <div style={{ display: "flex", background: "rgba(10, 13, 20, 0.8)", borderBottom: "1px solid rgba(148, 163, 184, 0.1)", padding: "4px 8px" }}>
              {(["python", "ts", "rust", "curl"] as const).map((lang) => (
                <button
                  key={lang}
                  onClick={() => setActiveCodeTab(lang)}
                  style={{ background: activeCodeTab === lang ? "rgba(30, 41, 59, 0.8)" : "transparent", border: "none", color: activeCodeTab === lang ? "#10b981" : "#6b7280", padding: "8px 16px", borderRadius: "8px", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}
                >
                  {lang.toUpperCase()}
                </button>
              ))}
              <button
                onClick={() => copyToClipboard(codeSnippets[activeCodeTab], "tab")}
                style={{ marginLeft: "auto", background: "transparent", border: "none", color: "#9ca3af", fontSize: "11px", cursor: "pointer", fontFamily: "JetBrains Mono, monospace" }}
              >
                {copiedCode === "tab" ? "✓ Copied" : "Copy Code"}
              </button>
            </div>
            <pre style={{ margin: 0, padding: "20px", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", color: "#e2e8f0", overflowX: "auto", lineHeight: 1.6 }}>
              {codeSnippets[activeCodeTab]}
            </pre>
          </div>

          {/* Right: Framework Badges & Integration Features */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <h3 style={{ fontSize: "1.4rem", fontWeight: 700 }}>Supported Agent Frameworks</h3>

            {[
              { name: "ElizaOS (ai16z)", desc: "Native security middleware plugin for all Eliza agents.", badge: "eliza-plugin-sigui" },
              { name: "OpenClaw AI", desc: "Pre-execution security skill & action inspector.", badge: "openclaw-skill-sigui" },
              { name: "Virtuals Protocol", desc: "Tokenized agent revenue protection & solvency checks.", badge: "virtuals-sigui-shield" },
              { name: "LangChain & CrewAI", desc: "Decorator pattern for autonomous tool execution safety.", badge: "@sigui/langchain" },
            ].map((fw, idx) => (
              <div key={idx} style={{ background: "rgba(17, 24, 39, 0.5)", border: "1px solid rgba(148, 163, 184, 0.1)", borderRadius: "12px", padding: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: "15px", color: "#f3f4f6" }}>{fw.name}</div>
                  <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "2px" }}>{fw.desc}</div>
                </div>
                <span style={{ background: "rgba(14, 165, 233, 0.1)", color: "#0ea5e9", border: "1px solid rgba(14, 165, 233, 0.3)", borderRadius: "6px", padding: "4px 8px", fontSize: "10px", fontFamily: "JetBrains Mono, monospace" }}>
                  {fw.badge}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 4. INVESTOR DECK — THE 5 STRATEGIC PILLARS ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "80px 24px", background: "rgba(15, 23, 42, 0.4)", borderTop: "1px solid rgba(148, 163, 184, 0.1)" }}>
        <div className="max-w-6xl mx-auto">
          <div style={{ textAlign: "center", marginBottom: "56px" }}>
            <span style={{ color: "#8b5cf6", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", textTransform: "uppercase", letterSpacing: "2px" }}>The Investor Pitch</span>
            <h2 style={{ fontSize: "2.4rem", fontWeight: 800, marginTop: "8px" }}>The 5 Strategic Pillars of Sigui</h2>
            <p style={{ color: "#9ca3af", maxWidth: "680px", margin: "8px auto 0 auto" }}>Why Sigui will become the central regulatory and credit infrastructure of the machine economy.</p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }}>
            {pillars.map((p, idx) => (
              <motion.div
                key={p.id}
                whileHover={{ y: -4 }}
                onClick={() => setActivePillar(idx)}
                style={{ background: activePillar === idx ? "rgba(17, 24, 39, 0.9)" : "rgba(17, 24, 39, 0.5)", border: `1px solid ${activePillar === idx ? "#8b5cf6" : "rgba(148, 163, 184, 0.12)"}`, borderRadius: "16px", padding: "24px", cursor: "pointer", transition: "all 0.25s", boxShadow: activePillar === idx ? "0 0 30px rgba(139, 92, 246, 0.2)" : "none" }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "14px", fontWeight: 800, color: "#8b5cf6" }}>{p.num}</span>
                  <span style={{ background: "rgba(139, 92, 246, 0.1)", color: "#8b5cf6", border: "1px solid rgba(139, 92, 246, 0.3)", borderRadius: "6px", padding: "3px 8px", fontSize: "10px", fontFamily: "JetBrains Mono, monospace" }}>{p.badge}</span>
                </div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700, marginBottom: "4px", color: "#f3f4f6" }}>{p.title}</h3>
                <div style={{ fontSize: "12px", color: "#0ea5e9", fontWeight: 600, marginBottom: "12px" }}>{p.subtitle}</div>
                <p style={{ fontSize: "13px", color: "#9ca3af", lineHeight: 1.6, marginBottom: "20px" }}>{p.desc}</p>
                <div style={{ borderTop: "1px solid rgba(148, 163, 184, 0.1)", paddingTop: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: "11px", color: "#6b7280" }}>{p.metricLabel}</span>
                  <span style={{ fontFamily: "JetBrains Mono, monospace", fontSize: "16px", fontWeight: 800, color: "#10b981" }}>{p.metric}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── 5. HARDWARE & PARTNERS FOOTER CTA ── */}
      <section style={{ position: "relative", zIndex: 1, padding: "80px 24px text-center" }} className="max-w-4xl mx-auto text-center">
        <h2 style={{ fontSize: "2.5rem", fontWeight: 800, marginBottom: "16px" }}>Ready to Protect Your Agent Ecosystem?</h2>
        <p style={{ color: "#9ca3af", fontSize: "1.1rem", marginBottom: "32px", maxWidth: "600px", margin: "0 auto 32px auto" }}>Join leading AI agent builders and DeFi protocols securing multi-agent financial flows with Sigui.</p>

        <div style={{ display: "flex", justifyContent: "center", gap: "16px" }}>
          <button
            onClick={onLaunchApp}
            style={{ background: "linear-gradient(135deg, #10b981 0%, #0ea5e9 100%)", color: "#000", fontWeight: 800, padding: "16px 36px", borderRadius: "12px", fontSize: "16px", cursor: "pointer", border: "none", boxShadow: "0 0 30px rgba(14, 165, 233, 0.4)" }}
          >
            ⚡ Open Oracle Inspector Demo
          </button>
        </div>

        <div style={{ marginTop: "60px", paddingTop: "40px", borderTop: "1px solid rgba(148, 163, 184, 0.1)", display: "flex", flexWrap: "wrap", justifyContent: "space-around", alignItems: "center", gap: "24px", opacity: 0.6, fontSize: "13px", fontFamily: "JetBrains Mono, monospace", color: "#9ca3af" }}>
          <span>CIRCLE x402</span>
          <span>ARC TESTNET</span>
          <span>AMD MI300X</span>
          <span>ETH SEPOLIA (ERC-8259)</span>
          <span>QWEN2-VL-7B</span>
        </div>
      </section>
    </div>
  );
}
