"use client";

import { useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { FeedItem, LiveStats, LiveAgents } from "../hooks/useWebSocket";

const AGENT_META: Record<string, { name: string; icon: string; color: string }> = {
  agent_payer:    { name: "Danseur du Feu",  icon: "🔥", color: "#f59e0b" },
  agent_attacker: { name: "Renard Pâle",     icon: "🦊", color: "#f43f5e" },
  agent_learner:  { name: "Étoile App.",     icon: "⭐", color: "#8b5cf6" },
  agent_grayzone: { name: "Gray Zone",       icon: "🌫", color: "#64748b" },
  agent_monitor:  { name: "Œil Société",     icon: "👁", color: "#0ea5e9" },
};

const DECISION_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  ALLOW:   { bg: "rgba(16,185,129,0.15)",  color: "#10b981", label: "ALLOW" },
  APPROVE: { bg: "rgba(16,185,129,0.15)",  color: "#10b981", label: "ALLOW" },
  BLOCK:   { bg: "rgba(244,63,94,0.15)",   color: "#f43f5e", label: "BLOCK" },
  ESCALATE:{ bg: "rgba(245,158,11,0.15)",  color: "#f59e0b", label: "ESC" },
};

interface AttackTheaterLiveProps {
  agents: LiveAgents;
  stats: LiveStats;
  lastTx: FeedItem | null;
  feed: FeedItem[];
}

// Animated counter that bumps on value change
function LiveCounter({ value, color }: { value: number; color: string }) {
  const prevRef = useRef(value);
  const bumped = value !== prevRef.current;
  prevRef.current = value;

  return (
    <motion.span
      key={value}
      animate={bumped ? { scale: [1, 1.35, 1] } : {}}
      transition={{ duration: 0.3, ease: "backOut" }}
      style={{ color, fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "1.8rem" }}
    >
      {value.toLocaleString()}
    </motion.span>
  );
}

// Scrolling ticker row
function TickerRow({ item }: { item: FeedItem }) {
  const meta = AGENT_META[item.agent_id] ?? { name: item.agent_id, icon: "🤖", color: "#94a3b8" };
  const ds = DECISION_STYLE[item.decision] ?? DECISION_STYLE["ALLOW"];
  const hash = (item.arc_tx_hash || "").slice(0, 10) + "…";

  return (
    <motion.div
      initial={{ opacity: 0, x: -24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="ticker-row"
    >
      <span className="ticker-agent" style={{ color: meta.color }}>
        {meta.icon} {meta.name}
      </span>
      <span className="ticker-amount">
        ${(item.amount_usdc || 0).toFixed(0)} USDC
      </span>
      <span className="ticker-decision" style={{ background: ds.bg, color: ds.color }}>
        {ds.label}
      </span>
      <span className="ticker-risk" style={{ color: (item.risk_score || 0) > 0.6 ? "#f43f5e" : "#94a3b8" }}>
        {((item.risk_score || 0) * 100).toFixed(0)}%
      </span>
      <span className="ticker-hash">{hash}</span>
      <span className="ticker-ms">{item.processing_time_ms || 0}ms</span>
    </motion.div>
  );
}

export function AttackTheaterLive({ agents, stats, lastTx, feed }: AttackTheaterLiveProps) {
  const usdcSaved = stats.usdc_saved ?? 0;
  const blockRate = stats.total > 0 ? ((stats.block / stats.total) * 100).toFixed(1) : "0.0";

  return (
    <div className="theater-wrapper">
      {/* Top KPI strip — ticking counters */}
      <div className="theater-kpis">
        <div className="kpi-card">
          <div className="kpi-label">✅ ALLOW</div>
          <LiveCounter value={stats.allow} color="#10b981" />
        </div>
        <div className="kpi-card">
          <div className="kpi-label">🚫 BLOCK</div>
          <LiveCounter value={stats.block} color="#f43f5e" />
        </div>
        <div className="kpi-card">
          <div className="kpi-label">⚠️ ESCALATE</div>
          <LiveCounter value={stats.escalate} color="#f59e0b" />
        </div>
        <div className="kpi-card">
          <div className="kpi-label">💰 USDC Saved</div>
          <motion.span
            key={Math.floor(usdcSaved)}
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 0.3 }}
            style={{ color: "#f6c90e", fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "1.8rem" }}
          >
            ${usdcSaved.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </motion.span>
        </div>
        <div className="kpi-card">
          <div className="kpi-label">🎯 Block Rate</div>
          <span style={{ color: "#f43f5e", fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: "1.8rem" }}>
            {blockRate}%
          </span>
        </div>
      </div>

      {/* Agent status grid */}
      <div className="theater-agents">
        {Object.entries(AGENT_META).map(([id, meta]) => {
          const agent = agents[id];
          const isActive = agent?.status === "active";
          const txCount = agent?.transactions ?? 0;
          return (
            <div key={id} className="agent-card">
              <div className="agent-header">
                <span className="agent-icon">{meta.icon}</span>
                <div>
                  <div className="agent-name" style={{ color: meta.color }}>{meta.name}</div>
                  <div className="agent-id">{id}</div>
                </div>
                <div className={`agent-status-dot ${isActive ? "active" : "idle"}`} />
              </div>
              <div className="agent-tx">
                <span className="agent-tx-label">Transactions</span>
                <motion.span
                  key={txCount}
                  animate={{ scale: [1, 1.2, 1] }}
                  transition={{ duration: 0.25 }}
                  className="agent-tx-count"
                  style={{ color: meta.color }}
                >
                  {txCount.toLocaleString()}
                </motion.span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Live transaction ticker */}
      <div className="theater-ticker-header">
        <span>⚡ LIVE TRANSACTION FEED</span>
        <span className="ticker-total">{stats.total.toLocaleString()} total</span>
      </div>
      <div className="theater-ticker">
        <div className="ticker-head-row">
          <span>Agent</span>
          <span>Amount</span>
          <span>Decision</span>
          <span>Risk</span>
          <span>Hash</span>
          <span>Latency</span>
        </div>
        <div className="ticker-body">
          <AnimatePresence initial={false}>
            {feed.slice(0, 12).map((item) => (
              <TickerRow key={item.id} item={item} />
            ))}
          </AnimatePresence>
        </div>
      </div>

      <style>{`
        .theater-wrapper {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }

        .theater-kpis {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 12px;
        }

        .kpi-card {
          background: rgba(17,24,39,0.7);
          border: 1px solid rgba(148,163,184,0.1);
          border-radius: 12px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .kpi-label {
          font-size: 11px;
          color: #94a3b8;
          font-family: var(--font-mono);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .theater-agents {
          display: grid;
          grid-template-columns: repeat(5, 1fr);
          gap: 10px;
        }

        .agent-card {
          background: rgba(17,24,39,0.6);
          border: 1px solid rgba(148,163,184,0.08);
          border-radius: 10px;
          padding: 12px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .agent-header {
          display: flex;
          align-items: flex-start;
          gap: 8px;
        }

        .agent-icon { font-size: 20px; }

        .agent-name {
          font-size: 12px;
          font-weight: 600;
        }

        .agent-id {
          font-size: 10px;
          color: #475569;
          font-family: var(--font-mono);
        }

        .agent-status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          margin-left: auto;
          margin-top: 2px;
          flex-shrink: 0;
        }

        .agent-status-dot.active {
          background: #10b981;
          box-shadow: 0 0 6px #10b981;
          animation: pulse-dot 2s infinite;
        }

        .agent-status-dot.idle {
          background: #475569;
        }

        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.4; }
        }

        .agent-tx {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .agent-tx-label {
          font-size: 10px;
          color: #475569;
          font-family: var(--font-mono);
        }

        .agent-tx-count {
          font-size: 16px;
          font-weight: 700;
          font-family: var(--font-mono);
        }

        .theater-ticker-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-family: var(--font-mono);
          font-size: 11px;
          color: #94a3b8;
          text-transform: uppercase;
          letter-spacing: 0.08em;
          padding: 0 4px;
        }

        .ticker-total {
          color: #475569;
        }

        .theater-ticker {
          background: rgba(17,24,39,0.7);
          border: 1px solid rgba(148,163,184,0.08);
          border-radius: 12px;
          overflow: hidden;
        }

        .ticker-head-row {
          display: grid;
          grid-template-columns: 2fr 1fr 0.8fr 0.6fr 1.2fr 0.7fr;
          padding: 8px 14px;
          background: rgba(255,255,255,0.03);
          border-bottom: 1px solid rgba(148,163,184,0.06);
          font-size: 10px;
          color: #475569;
          font-family: var(--font-mono);
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }

        .ticker-body {
          max-height: 280px;
          overflow: hidden;
        }

        .ticker-row {
          display: grid;
          grid-template-columns: 2fr 1fr 0.8fr 0.6fr 1.2fr 0.7fr;
          padding: 8px 14px;
          border-bottom: 1px solid rgba(148,163,184,0.04);
          align-items: center;
          font-size: 12px;
        }

        .ticker-row:hover {
          background: rgba(255,255,255,0.02);
        }

        .ticker-agent {
          font-weight: 500;
          font-size: 11px;
        }

        .ticker-amount {
          color: #f8fafc;
          font-family: var(--font-mono);
          font-size: 11px;
        }

        .ticker-decision {
          padding: 2px 8px;
          border-radius: 4px;
          font-family: var(--font-mono);
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-align: center;
        }

        .ticker-risk {
          font-family: var(--font-mono);
          font-size: 11px;
        }

        .ticker-hash {
          font-family: var(--font-mono);
          font-size: 10px;
          color: #475569;
        }

        .ticker-ms {
          font-family: var(--font-mono);
          font-size: 11px;
          color: #94a3b8;
          text-align: right;
        }

        @media (max-width: 1024px) {
          .theater-kpis,
          .theater-agents {
            grid-template-columns: repeat(3, 1fr);
          }
        }
      `}</style>
    </div>
  );
}
