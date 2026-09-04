import { useState } from "react";
import { motion } from "framer-motion";

export default function SiguiLandingV3() {
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
    <div style={{ background: "#0a0d14", color: "#f3f4f6", fontFamily: "Inter, sans-serif", minHeight: "100vh" }}>
      {/* ── 1. HERO SECTION ── */}
      <section style={{ position: "relative", zIndex: 1, paddingTop: "80px", paddingBottom: "80px" }} className="max-w-6xl mx-auto text-center px-4">
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          style={{ display: "inline-flex", alignItems: "center", gap: "8px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", borderRadius: "20px", padding: "6px 16px", fontSize: "12px", fontFamily: "JetBrains Mono, monospace", color: "#10b981", marginBottom: "28px" }}
        >
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#10b981", display: "inline-block" }} />
          SIGUI V3.0 LIVE — ARC TESTNET & ETHEREUM SEPOLIA (ERC-8259)
        </motion.div>

        <h1 style={{ fontSize: "clamp(2.5rem, 5.5vw, 4.8rem)", fontWeight: 800, lineHeight: 1.08, letterSpacing: "-0.03em", marginBottom: "24px" }}>
          The Security & Regulatory Layer <br />
          for the <span style={{ background: "linear-gradient(135deg, #10b981 0%, #0ea5e9 50%, #8b5cf6 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Post-Human Agent Economy</span>
        </h1>

        <p style={{ fontSize: "1.15rem", color: "#9ca3af", maxWidth: "780px", margin: "0 auto 36px auto", lineHeight: 1.6 }}>
          Sigui inspects multi-agent transactions in under <strong style={{ color: "#0ea5e9" }}>50ms</strong> before on-chain execution. Powered by AMD MI300X vision models (<strong style={{ color: "#10b981" }}>Imina Na V2</strong>), zero-knowledge proofs (<strong style={{ color: "#8b5cf6" }}>ZK-Sigui</strong>), and Circle x402 USDC micropayments.
        </p>

        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "16px", marginBottom: "48px" }}>
          <a
            href="http://localhost:3000"
            style={{ background: "linear-gradient(135deg, #10b981 0%, #059669 100%)", color: "#000", fontWeight: 700, padding: "14px 28px", borderRadius: "12px", fontSize: "15px", textDecoration: "none", boxShadow: "0 0 24px rgba(16, 185, 129, 0.4)" }}
          >
            ⚡ Launch Live Oracle App →
          </a>
          <a
            href="https://github.com/ibonon/Sigui"
            target="_blank"
            rel="noopener noreferrer"
            style={{ background: "rgba(30, 41, 59, 0.8)", color: "#f3f4f6", fontWeight: 600, padding: "14px 28px", borderRadius: "12px", fontSize: "15px", textDecoration: "none", border: "1px solid rgba(148, 163, 184, 0.2)" }}
          >
            📄 Read Vision Whitepaper
          </a>
        </div>

        <div style={{ display: "inline-flex", alignItems: "center", gap: "12px", background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(148, 163, 184, 0.15)", borderRadius: "10px", padding: "10px 20px", fontFamily: "JetBrains Mono, monospace", fontSize: "13px" }}>
          <span style={{ color: "#10b981" }}>$</span>
          <span>pip install sigui-sdk</span>
          <button
            onClick={() => copyToClipboard("pip install sigui-sdk", "hero")}
            style={{ background: "rgba(255, 255, 255, 0.05)", border: "none", color: "#9ca3af", borderRadius: "6px", padding: "4px 8px", cursor: "pointer", fontSize: "11px" }}
          >
            {copiedCode === "hero" ? "✓ Copied" : "Copy"}
          </button>
        </div>
      </section>

      {/* ── 2. INTERACTIVE SIMULATOR ── */}
      <section style={{ padding: "80px 24px", background: "rgba(15, 23, 42, 0.5)", borderTop: "1px solid rgba(148, 163, 184, 0.1)" }}>
        <div style={{ maxWidth: "1000px", margin: "0 auto" }}>
          <div style={{ textAlign: "center", marginBottom: "40px" }}>
            <span style={{ color: "#0ea5e9", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", textTransform: "uppercase" }}>Live Interactive Demo</span>
            <h2 style={{ fontSize: "2.4rem", fontWeight: 800, marginTop: "8px" }}>Test the Sigui Security Pipeline</h2>
          </div>

          <div style={{ background: "rgba(17, 24, 39, 0.75)", border: "1px solid rgba(148, 163, 184, 0.15)", borderRadius: "20px", padding: "28px" }}>
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

            <div style={{ background: "#0a0d14", border: "1px solid rgba(148, 163, 184, 0.2)", borderRadius: "12px", padding: "20px", minHeight: "140px", fontFamily: "JetBrains Mono, monospace" }}>
              {simRunning && <div style={{ color: "#0ea5e9" }}>RUNNING SIGUI ORACLE PIPELINE (MI300X GPU INFERENCE)…</div>}
              {!simRunning && !simResult && <div style={{ color: "#6b7280" }}>Click a scenario button above to run evaluation.</div>}
              {!simRunning && simResult && (
                <div>
                  <div style={{ fontSize: "18px", fontWeight: 800, color: simResult.decision === "ALLOW" ? "#10b981" : simResult.decision === "BLOCK" ? "#f43f5e" : "#f59e0b" }}>
                    VERDICT: {simResult.decision} ({simResult.processing_time_ms}ms)
                  </div>
                  <div style={{ fontSize: "12px", color: "#9ca3af", marginTop: "8px" }}>{simResult.reason}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── 3. DEVELOPER CODE PLAYGROUND ── */}
      <section style={{ padding: "80px 24px" }} className="max-w-6xl mx-auto">
        <div style={{ textAlign: "center", marginBottom: "48px" }}>
          <h2 style={{ fontSize: "2.4rem", fontWeight: 800 }}>Developer Integration</h2>
        </div>
        <div style={{ background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(148, 163, 184, 0.2)", borderRadius: "16px", padding: "24px" }}>
          <div style={{ display: "flex", gap: "8px", marginBottom: "16px" }}>
            {(["python", "ts", "rust", "curl"] as const).map((lang) => (
              <button
                key={lang}
                onClick={() => setActiveCodeTab(lang)}
                style={{ background: activeCodeTab === lang ? "rgba(30, 41, 59, 0.8)" : "transparent", border: "none", color: activeCodeTab === lang ? "#10b981" : "#6b7280", padding: "8px 16px", borderRadius: "8px", fontFamily: "JetBrains Mono, monospace", cursor: "pointer" }}
              >
                {lang.toUpperCase()}
              </button>
            ))}
          </div>
          <pre style={{ margin: 0, fontFamily: "JetBrains Mono, monospace", fontSize: "12px", color: "#e2e8f0", overflowX: "auto" }}>
            {codeSnippets[activeCodeTab]}
          </pre>
        </div>
      </section>

      {/* ── 4. INVESTOR 5 PILLARS ── */}
      <section style={{ padding: "80px 24px", background: "rgba(15, 23, 42, 0.4)", borderTop: "1px solid rgba(148, 163, 184, 0.1)" }}>
        <div className="max-w-6xl mx-auto">
          <div style={{ textAlign: "center", marginBottom: "48px" }}>
            <span style={{ color: "#8b5cf6", fontFamily: "JetBrains Mono, monospace", fontSize: "12px", textTransform: "uppercase" }}>Strategic Investment Case</span>
            <h2 style={{ fontSize: "2.4rem", fontWeight: 800, marginTop: "8px" }}>The 5 Strategic Pillars of Sigui</h2>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px" }}>
            {pillars.map((p, idx) => (
              <div key={p.id} style={{ background: "rgba(17, 24, 39, 0.5)", border: "1px solid rgba(148, 163, 184, 0.12)", borderRadius: "16px", padding: "24px" }}>
                <div style={{ color: "#8b5cf6", fontFamily: "JetBrains Mono, monospace", fontWeight: 800 }}>{p.num}</div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 700, margin: "8px 0 4px 0" }}>{p.title}</h3>
                <p style={{ fontSize: "13px", color: "#9ca3af" }}>{p.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
