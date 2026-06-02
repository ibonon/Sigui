"use client";

import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useWebSocket } from "./hooks/useWebSocket";
import { GraphConstellation } from "./components/GraphConstellation";
import { AttackTheaterLive } from "./components/AttackTheaterLive";

// Backend renvoie parfois "APPROVE" au lieu de "ALLOW"
function normalizeDecision(d?: string): "ALLOW" | "BLOCK" | "ESCALATE" {
  if (!d) return "ESCALATE";
  if (d === "APPROVE") return "ALLOW";
  if (d === "BLOCK" || d === "ESCALATE") return d;
  return "ALLOW";
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://127.0.0.1:8000/ws/live";

interface VerdictData {
  decision: "ALLOW" | "BLOCK" | "ESCALATE";
  risk_score: number;
  reason: string;
  action_hash: string;
  processing_time_ms: number;
  vision_confidence: number;
  raw_signals: any;
}

function shortHash(h?: string) {
  if (!h) return "—";
  return h.slice(0, 6) + "…" + h.slice(-4);
}

const AGENT_LABELS: Record<string, { title: string }> = {
  agent_payer:    { title: "Danseur du Feu" },
  agent_attacker: { title: "Renard Pâle" },
  agent_learner:  { title: "Étoile Apprenante" },
  agent_grayzone: { title: "Gray Zone" },
  agent_monitor:  { title: "Œil Société" },
};

export default function App() {
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [verdict, setVerdict] = useState<VerdictData | null>(null);
  const [activeTab, setActiveTab] = useState<"oracle" | "theater">("oracle");

  // Live WebSocket data
  const { isConnected, feed, stats, treasury, agents, graphEdges, lastTx } =
    useWebSocket(WS_URL);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearched(true);
    setScanning(true);
    setVerdict(null);

    const amountMatch = query.match(/(\d+)/);
    const amount = amountMatch ? parseFloat(amountMatch[0]) : Math.random() * 500;

    try {
      const res = await fetch(`${API}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action_type: "transfer",
          destination: query.startsWith("0x") ? query : "0x" + query,
          amount_usdc: amount,
          chain: "ethereum",
        }),
      });
      const data = await res.json();
      setTimeout(() => {
        setScanning(false);
        setVerdict(data);
      }, 1800);
    } catch {
      setTimeout(() => {
        setScanning(false);
        setVerdict({
          decision: "ESCALATE",
          risk_score: 0.5,
          reason: "Failed to reach Sigui Oracle. Fallback to ESCALATE.",
          action_hash: "0xERROR",
          processing_time_ms: 0,
          vision_confidence: 0,
          raw_signals: {},
        });
      }, 1800);
    }
  };

  return (
    <div className="app-container" style={{ overflow: "auto" }}>
      {/* ── Header ── */}
      <header className="header">
        <div className="brand">
          <div className="brand-icon">S</div>
          <div className="brand-text">SIGUI ORACLE</div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {/* Live badge */}
          <div className={`live-badge ${isConnected ? "connected" : "disconnected"}`}>
            <span className="live-dot" />
            {isConnected ? "LIVE" : "OFFLINE"}
          </div>

          {isConnected && (
            <div style={{ display: "flex", gap: "12px", fontFamily: "var(--font-mono)", fontSize: "11px" }}>
              <span style={{ color: "#10b981" }}>✅ {stats.allow}</span>
              <span style={{ color: "#f43f5e" }}>🚫 {stats.block}</span>
              <span style={{ color: "#f59e0b" }}>⚠️ {stats.escalate}</span>
            </div>
          )}

          {/* Treasury ticker */}
          {isConnected && (
            <div className="graph-status">
              💰 ${(treasury.total_earned || 0).toFixed(4)} USDC
            </div>
          )}

          {!isConnected && (
            <div className="graph-status">L1 TESTNET CONNECTING…</div>
          )}
        </div>
      </header>

      {/* ── Mode Tabs ── */}
      <div className="mode-tabs">
        <button
          className={`mode-tab ${activeTab === "oracle" ? "active" : ""}`}
          onClick={() => setActiveTab("oracle")}
        >
          ⬡ Oracle Scan
        </button>
        <button
          className={`mode-tab ${activeTab === "theater" ? "active" : ""}`}
          onClick={() => setActiveTab("theater")}
        >
          ⚡ Attack Theater
          {isConnected && <span className="tab-live-dot" />}
        </button>
      </div>

      <AnimatePresence mode="wait">
        {activeTab === "oracle" && (
          <motion.div
            key="oracle"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
            style={{ display: "flex", flexDirection: "column", flex: 1 }}
          >
            {/* ── Oracle Search ── */}
            <div className={`search-container ${searched ? "active" : ""}`}>
              <form onSubmit={handleSearch} className="omni-search">
                <input
                  type="text"
                  className="omni-input"
                  placeholder="Paste Tx Hash or 0x Address to scan…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={scanning}
                  autoFocus
                />
              </form>
            </div>

            <div className={`workspace ${searched ? "visible" : ""}`}>
              {/* Left: Graph */}
              <div className="glass-panel graph-area">
                <div className="graph-header">
                  <div className="graph-title">
                    <span style={{ color: "var(--cyan)" }}>⬡</span>{" "}
                    {searched ? "Spatio-Temporal Graph" : "Live Constellation"}
                  </div>
                  {scanning && <div className="graph-status">SCANNING…</div>}
                  {!searched && isConnected && (
                    <div className="graph-status" style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", borderColor: "rgba(16,185,129,0.3)" }}>
                      STREAMING
                    </div>
                  )}
                </div>

                <div className={`graph-content ${scanning ? "scanning" : ""}`}>
                  {scanning && (
                    <div className="scanner-beam">
                      <div className="scanner-gradient" />
                    </div>
                  )}

                  {/* Always show the live constellation */}
                  <GraphConstellation edges={searched ? [] : graphEdges} />

                  {/* Overlay the static threat graph when searched */}
                  {searched && <ThreatGraph scanning={scanning} verdict={verdict} />}
                </div>
              </div>

              {/* Right: Verdict + Live mini-feed */}
              <div className="glass-panel verdict-panel">
                <div className="graph-header">
                  <div className="graph-title">
                    <span style={{ color: "var(--violet)" }}>⚡</span>{" "}
                    Intelligence Report
                  </div>
                </div>

                <div className="verdict-content">
                  {!verdict && scanning && (
                    <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <div className="graph-status" style={{ background: "transparent", border: "none" }}>
                        AWAITING ORACLE VERDICT…
                      </div>
                    </div>
                  )}

                  {verdict && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="verdict-report"
                      style={{ display: "flex", flexDirection: "column", gap: "20px" }}
                    >
                      <div className={`verdict-box ${normalizeDecision(verdict.decision).toLowerCase()}`}>
                        <div style={{ fontSize: "12px", color: "var(--text-muted)", marginBottom: "8px", fontFamily: "var(--font-mono)" }}>
                          FINAL DECISION
                        </div>
                        <div className="verdict-title">{normalizeDecision(verdict.decision)}</div>
                        <div className="risk-meter">
                          <div
                            className="risk-fill"
                            style={{
                              width: `${(verdict.risk_score ?? 0) * 100}%`,
                              background:
                                normalizeDecision(verdict.decision) === "BLOCK"
                                  ? "var(--rose)"
                                  : normalizeDecision(verdict.decision) === "ALLOW"
                                  ? "var(--emerald)"
                                  : "var(--amber)",
                            }}
                          />
                        </div>
                        <div style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px", fontFamily: "var(--font-mono)" }}>
                          RISK SCORE: {((verdict.risk_score ?? 0) * 100).toFixed(1)}%
                        </div>
                      </div>

                      <div className="details-grid">
                        <div className="detail-row">
                          <span className="detail-label">Processing Time</span>
                          <span className="detail-value">{verdict.processing_time_ms} ms</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">Vision Confidence</span>
                          <span className="detail-value">{((verdict.vision_confidence || 0) * 100).toFixed(1)}%</span>
                        </div>
                        <div className="detail-row">
                          <span className="detail-label">Action Hash</span>
                          <span className="detail-value">{verdict.action_hash ? verdict.action_hash.slice(0, 14) : "—"}…</span>
                        </div>
                      </div>

                      {normalizeDecision(verdict.decision) !== "ALLOW" && (
                        <div className="reason-box">
                          <strong>THREAT DETECTED:</strong>
                          <br />
                          {verdict.reason}
                        </div>
                      )}
                    </motion.div>
                  )}

                  {/* Live mini-feed at bottom of verdict panel */}
                  {!searched && feed.length > 0 && (
                    <div className="mini-feed">
                      <div className="mini-feed-title">Recent decisions</div>
                      <AnimatePresence initial={false}>
                        {feed.slice(0, 6).map((item) => (
                          <motion.div
                            key={item.id}
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, height: 0, overflow: "hidden" }}
                            transition={{ duration: 0.2 }}
                            className="mini-feed-row"
                          >
                            <span className={`mini-badge ${item.decision.toLowerCase()}`}>
                              {item.decision === "BLOCK" ? "🚫" : item.decision === "ESCALATE" ? "⚠️" : "✅"}
                            </span>
                            <span className="mini-agent">{(item.agent_id || "").replace("agent_", "")}</span>
                            <span className="mini-amount">${(item.amount_usdc || 0).toFixed(0)}</span>
                            <span className="mini-ms">{item.processing_time_ms || 0}ms</span>
                          </motion.div>
                        ))}
                      </AnimatePresence>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === "theater" && (
          <motion.div
            key="theater"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.25 }}
            className="theater-tab-content"
          >
            {/* Live constellation header */}
            <div className="theater-graph-row">
              <div className="glass-panel" style={{ padding: "16px 20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                  <div className="graph-title">
                    <span style={{ color: "var(--cyan)" }}>⬡</span> Live Constellation
                  </div>
                  {isConnected && (
                    <div className="graph-status" style={{ background: "rgba(16,185,129,0.1)", color: "#10b981", borderColor: "rgba(16,185,129,0.3)" }}>
                      STREAMING {stats.total.toLocaleString()} TX
                    </div>
                  )}
                </div>
                <GraphConstellation edges={graphEdges} />
              </div>
            </div>

            {/* Attack Theater */}
            <div className="glass-panel" style={{ padding: "24px" }}>
              <div className="graph-header" style={{ marginBottom: "20px", paddingBottom: "16px", borderBottom: "1px solid rgba(148,163,184,0.1)" }}>
                <div className="graph-title">
                  <span style={{ color: "var(--violet)" }}>⚡</span> Attack Theater
                </div>
                {!isConnected && (
                  <div style={{ fontSize: "12px", color: "#f59e0b", fontFamily: "var(--font-mono)" }}>
                    ⚠️ WebSocket offline — démarrez python start_live.py
                  </div>
                )}
              </div>
              <AttackTheaterLive
                agents={agents}
                stats={stats}
                lastTx={lastTx}
                feed={feed}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Static threat graph for oracle scan mode
function ThreatGraph({
  scanning,
  verdict,
}: {
  scanning: boolean;
  verdict: VerdictData | null;
}) {
  const nodes = [
    { id: "A", x: 100, y: 150, type: "agent", label: "Source" },
    { id: "B", x: 250, y: 80, type: "mixer", label: "Mixer Node 1" },
    { id: "C", x: 250, y: 220, type: "mixer", label: "Mixer Node 2" },
    { id: "D", x: 400, y: 150, type: "dest", label: "Target" },
    { id: "E", x: 500, y: 100, type: "peer", label: "Peer 1" },
    { id: "F", x: 500, y: 200, type: "peer", label: "Peer 2" },
  ];
  const edges = [
    { source: "A", target: "B" },
    { source: "A", target: "C" },
    { source: "B", target: "D" },
    { source: "C", target: "D" },
    { source: "D", target: "E" },
    { source: "D", target: "F" },
  ];
  const isDanger = verdict?.decision === "BLOCK";
  return (
    <svg width="600" height="300" viewBox="0 0 600 300" style={{ position: "absolute" }}>
      {edges.map((e, i) => {
        const source = nodes.find((n) => n.id === e.source)!;
        const target = nodes.find((n) => n.id === e.target)!;
        return (
          <line
            key={i}
            x1={source.x} y1={source.y}
            x2={target.x} y2={target.y}
            className={`edge ${!scanning && verdict ? "active" : ""} ${isDanger ? "danger" : ""}`}
          />
        );
      })}
      {nodes.map((n) => (
        <g key={n.id} className={`node ${n.type === "dest" && !scanning && verdict ? "focus" : ""} ${isDanger && n.type === "dest" ? "danger" : ""}`}>
          <circle cx={n.x} cy={n.y} r={14} />
          <text x={n.x} y={n.y + 26} textAnchor="middle">{n.label}</text>
        </g>
      ))}
    </svg>
  );
}
