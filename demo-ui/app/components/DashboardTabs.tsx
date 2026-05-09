"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TimeSeriesPanel, DecisionDonut, BarGauge, FunnelChart, SankeyFlow } from "./Charts";

interface DashboardTabsProps {
  data: any;
  benchmark: any;
  hogonat: any;
  visionGraph: any;
  focusAgentId: string;
  feed: any[];
  deploying: boolean;
  stats: any;
  treasury: any;
  onchain: any;
  patterns: any[];
  agents: any;
  allow: number;
  block: number;
  escalate: number;
  total: number;
  protectedUsdc: number;
  profit: number;
  totalEarned: number;
  totalSpent: number;
  roi: string;
  confirmed: number;
  balancesByChain: any;
  hogonatHistory: any[];
  mode: string;
  evalsA: number;
  blockA: number;
  escA: number;
  protectedA: number;
  profitA: number;
  confirmedA: number;
  handleSimulate: () => void;
  timeSeries: any[];
  FlywheelPanel: any;
  AttackTheater: any;
  FeedRow: any;
  shortHash: (hash?: string) => string;
  AGENT_LABELS: any;
  EXPLORER: string;
}

export function DashboardTabs({
  data,
  benchmark,
  hogonat,
  visionGraph,
  focusAgentId,
  feed,
  deploying,
  stats,
  treasury,
  onchain,
  patterns,
  agents,
  allow,
  block,
  escalate,
  total,
  protectedUsdc,
  profit,
  totalEarned,
  totalSpent,
  roi,
  confirmed,
  balancesByChain,
  hogonatHistory,
  mode,
  evalsA,
  blockA,
  escA,
  protectedA,
  profitA,
  confirmedA,
  handleSimulate,
  timeSeries,
  FlywheelPanel,
  AttackTheater,
  FeedRow,
  shortHash,
  AGENT_LABELS,
  EXPLORER,
}: DashboardTabsProps) {
  const [activeTab, setActiveTab] = useState("overview");

  const formatMoney = (value: number, digits = 2) => `$${value.toFixed(digits)}`;

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "agents", label: "Agents" },
    { id: "vision", label: "Vision" },
    { id: "economics", label: "Economics" },
    { id: "analytics", label: "Analytics" },
  ];

  return (
    <div className="dashboard-tabs">
      <div className="tab-navigation">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            className={`tab-button ${activeTab === tab.id ? "active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="tab-content">
        {activeTab === "overview" && (
          <div className="overview-grid">
            <div className="metrics-row">
              <div className="metric-card panel">
                <div className="metric-label">Evaluations</div>
                <div className="metric-value">{evalsA}</div>
                <div className="metric-detail">Total processed</div>
              </div>
              <div className="metric-card panel">
                <div className="metric-label">Threats Blocked</div>
                <div className="metric-value" style={{ color: "var(--danger)" }}>{blockA}</div>
                <div className="metric-detail">Malicious transactions</div>
              </div>
              <div className="metric-card panel">
                <div className="metric-label">USDC Protected</div>
                <div className="metric-value" style={{ color: "var(--gold)" }}>{formatMoney(protectedA)}</div>
                <div className="metric-detail">Total value secured</div>
              </div>
              <div className="metric-card panel">
                <div className="metric-label">Net Profit</div>
                <div className="metric-value" style={{ color: "var(--success)" }}>{formatMoney(profitA, 3)}</div>
                <div className="metric-detail">Treasury earnings</div>
              </div>
            </div>

            <div className="charts-row">
              <div className="panel chart-panel">
                <div className="panel-header">
                  <div className="panel-title">Decision Timeline</div>
                  <div className="panel-caption">Real-time security decisions</div>
                </div>
                <TimeSeriesPanel data={timeSeries} />
              </div>

              <div className="panel chart-panel">
                <div className="panel-header">
                  <div className="panel-title">Decision Distribution</div>
                  <div className="panel-caption">Allow vs Block vs Escalate</div>
                </div>
                <DecisionDonut allow={allow} block={block} escalate={escalate} />
              </div>
            </div>

            <div className="feed-panel">
              <div className="panel-header">
                <div className="panel-title">Live Transaction Feed</div>
                <div className="panel-caption">Recent security evaluations</div>
              </div>
              <div className="feed-table-wrapper">
                <table className="feed-table">
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Agent</th>
                      <th>Action</th>
                      <th>Amount</th>
                      <th>Decision</th>
                      <th>Risk</th>
                      <th>Hash</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {feed.map((item) => (
                      <FeedRow key={item.id} item={item} />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === "agents" && (
          <div className="agents-grid">
            <AttackTheater
              agents={agents}
              stats={stats}
              deploying={deploying}
              onDeploy={handleSimulate}
            />
          </div>
        )}

        {activeTab === "vision" && (
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="vision-grid"
          >
            <div className="panel vision-panel">
              <div className="panel-header">
                <div className="panel-title">Vision Layer Analysis</div>
                <div className="panel-caption">Graph-based threat detection for {AGENT_LABELS[focusAgentId]?.title || focusAgentId}</div>
              </div>
              <div className="vision-content">
                <div className="vision-graph-container relative overflow-hidden">
                  <div className="vision-placeholder">
                    {[
                      { label: "Agent", icon: "🤖", color: "var(--primary)" },
                      { label: "Chain", icon: "🔗", color: "var(--secondary)" },
                      { label: "Destination", icon: "🏦", color: "var(--accent)" }
                    ].map((node, i) => (
                      <motion.div
                        key={node.label}
                        className="vision-node-animated"
                        animate={{
                          y: [0, -10, 0],
                          boxShadow: [
                            `0 0 10px ${node.color}40`,
                            `0 0 25px ${node.color}80`,
                            `0 0 10px ${node.color}40`
                          ]
                        }}
                        transition={{
                          duration: 3 + i,
                          repeat: Infinity,
                          ease: "easeInOut"
                        }}
                        style={{ borderColor: node.color }}
                      >
                        <span className="text-2xl mb-2">{node.icon}</span>
                        <span>{node.label}</span>
                        {i < 2 && (
                          <motion.div 
                            className="node-connector"
                            animate={{ opacity: [0.2, 0.8, 0.2] }}
                            transition={{ duration: 2, repeat: Infinity }}
                          />
                        )}
                      </motion.div>
                    ))}
                  </div>
                  {/* Floating particles for energy effect */}
                  <div className="absolute inset-0 pointer-events-none">
                    {[...Array(6)].map((_, i) => (
                      <motion.div
                        key={i}
                        className="absolute w-1 h-1 bg-gold rounded-full"
                        animate={{
                          x: [Math.random() * 400, Math.random() * 400],
                          y: [Math.random() * 200, Math.random() * 200],
                          opacity: [0, 1, 0]
                        }}
                        transition={{
                          duration: 4 + Math.random() * 4,
                          repeat: Infinity,
                          ease: "linear"
                        }}
                      />
                    ))}
                  </div>
                </div>
                <div className="vision-summary">
                  <motion.div 
                    className="vision-stat"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    <span>Pattern Detected</span>
                    <strong className={visionGraph?.summary?.heuristic_pattern !== "NORMAL" ? "text-danger" : "text-success"}>
                      {visionGraph?.summary?.heuristic_pattern || "NORMAL"}
                    </strong>
                  </motion.div>
                  <motion.div 
                    className="vision-stat"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                  >
                    <span>Confidence</span>
                    <div className="flex items-center gap-2">
                      <strong style={{ color: "var(--gold)" }}>
                        {((visionGraph?.summary?.heuristic_confidence || 0) * 100).toFixed(1)}%
                      </strong>
                      <div className="h-1.5 w-24 bg-gray-800 rounded-full overflow-hidden">
                        <motion.div 
                          className="h-full bg-gold"
                          initial={{ width: 0 }}
                          animate={{ width: `${(visionGraph?.summary?.heuristic_confidence || 0) * 100}%` }}
                          transition={{ duration: 1, ease: "easeOut" }}
                        />
                      </div>
                    </div>
                  </motion.div>
                  <motion.div 
                    className="vision-stat"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 }}
                  >
                    <span>Evidence</span>
                    <p className="evidence-text">
                      {visionGraph?.summary?.heuristic_evidence || "No visual signals detected"}
                    </p>
                  </motion.div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === "economics" && (
          <div className="economics-grid">
            <FlywheelPanel
              hogonat={hogonat}
              treasury={treasury}
              totalBlocked={block}
            />
            
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Treasury Balances</div>
                <div className="panel-caption">Multi-chain asset distribution</div>
              </div>
              <div className="treasury-bars">
                {Object.entries(balancesByChain).map(([chain, balance]) => (
                  <div key={chain} className="treasury-row">
                    <div className="treasury-row-head">
                      <span>{chain}</span>
                      <strong>{formatMoney(Number(balance) || 0, 3)}</strong>
                    </div>
                    <div className="bar-track">
                      <div 
                        className="bar-fill" 
                        style={{ 
                          width: `${Math.max(6, (Number(balance) || 0 / Math.max(...Object.values(balancesByChain).map(b => Number(b) || 0))) * 100)}%` 
                        }} 
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Economic Flow</div>
                <div className="panel-caption">Agent fees and DAO distribution</div>
              </div>
              <SankeyFlow agents={agents} />
            </div>
          </div>
        )}

        {activeTab === "analytics" && (
          <div className="analytics-grid">
            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Performance Benchmarks</div>
                <div className="panel-caption">AMD MI300X acceleration metrics</div>
              </div>
              <BarGauge
                cpuMs={benchmark.risk_engine.cpu_baseline_ms}
                amdMs={benchmark.risk_engine.runtime_avg_ms}
                visionMs={benchmark.vision_layer.target_ms}
              />
            </div>

            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Processing Pipeline</div>
                <div className="panel-caption">Transaction flow through system</div>
              </div>
              <FunnelChart
                total={total}
                evaluated={total}
                blocked={block}
                escalated={escalate}
                onchain={confirmed}
              />
            </div>

            <div className="panel">
              <div className="panel-header">
                <div className="panel-title">Security Metrics</div>
                <div className="panel-caption">Key performance indicators</div>
              </div>
              <div className="metrics-grid">
                <div className="metric-item">
                  <span className="metric-label">Block Rate</span>
                  <span className="metric-value">{total > 0 ? ((block / total) * 100).toFixed(1) : 0}%</span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">ROI</span>
                  <span className="metric-value">{roi}x</span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">On-chain Confirmed</span>
                  <span className="metric-value">{confirmedA}</span>
                </div>
                <div className="metric-item">
                  <span className="metric-label">USDC Protected</span>
                  <span className="metric-value">{formatMoney(protectedUsdc)}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .dashboard-tabs {
          padding: 24px;
        }

        .tab-navigation {
          display: flex;
          gap: 8px;
          margin-bottom: 24px;
          border-bottom: 1px solid var(--border);
        }

        .tab-button {
          padding: 12px 24px;
          background: transparent;
          border: none;
          color: var(--muted);
          font-family: var(--ui);
          font-size: 14px;
          font-weight: 500;
          cursor: pointer;
          border-bottom: 2px solid transparent;
          transition: all 0.2s ease;
        }

        .tab-button:hover {
          color: var(--text);
          background: rgba(246, 201, 14, 0.05);
        }

        .tab-button.active {
          color: var(--gold);
          border-bottom-color: var(--gold);
        }

        .overview-grid {
          display: grid;
          gap: 24px;
        }

        .metrics-row {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 16px;
        }

        .charts-row {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 16px;
        }

        .feed-panel {
          background: var(--panel);
          border: 1px solid var(--border);
          border-radius: 12px;
          overflow: hidden;
        }

        .feed-table-wrapper {
          overflow-x: auto;
        }

        .feed-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 12px;
        }

        .feed-table th,
        .feed-table td {
          padding: 8px 12px;
          text-align: left;
          border-bottom: 1px solid var(--border);
        }

        .feed-table th {
          background: var(--panel-soft);
          color: var(--muted);
          font-weight: 500;
        }

        .feed-table td {
          color: var(--text);
        }

        .agents-grid,
        .vision-grid,
        .economics-grid,
        .analytics-grid {
          display: grid;
          gap: 16px;
        }

        .vision-content {
          display: grid;
          grid-template-columns: 2fr 1fr;
          gap: 16px;
          padding: 16px;
        }

        .vision-placeholder {
          display: flex;
          justify-content: space-around;
          align-items: center;
          height: 200px;
          background: var(--panel-soft);
          border-radius: 8px;
          border: 1px solid var(--border);
        }

        .vision-node-animated {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 120px;
          height: 120px;
          background: var(--bg-2);
          border: 2px solid var(--border-strong);
          border-radius: 50%;
          color: var(--text);
          font-weight: 500;
          font-size: 13px;
          z-index: 2;
        }

        .node-connector {
          position: absolute;
          left: 120px;
          top: 50%;
          width: 60px;
          height: 2px;
          background: linear-gradient(90deg, var(--gold), transparent);
          z-index: 1;
        }

        .text-success { color: var(--success) !important; }
        .text-danger { color: var(--danger) !important; }
        .evidence-text { font-style: italic; opacity: 0.8; }

        .vision-summary {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .vision-stat {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .vision-stat span:first-child {
          color: var(--muted);
          font-size: 12px;
        }

        .vision-stat strong {
          color: var(--text);
          font-size: 16px;
        }

        .vision-stat p {
          color: var(--dim);
          font-size: 12px;
          line-height: 1.4;
          margin: 0;
        }

        .treasury-bars {
          padding: 16px;
        }

        .treasury-row {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-bottom: 12px;
        }

        .treasury-row-head {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 14px;
        }

        .treasury-row-head span {
          color: var(--muted);
        }

        .treasury-row-head strong {
          color: var(--text);
        }

        .bar-track {
          height: 8px;
          background: var(--panel-soft);
          border-radius: 4px;
          overflow: hidden;
        }

        .bar-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--gold), var(--gold-soft));
          border-radius: 4px;
          transition: width 0.3s ease;
        }

        .metrics-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
          padding: 16px;
        }

        .metric-item {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .metric-item .metric-label {
          color: var(--muted);
          font-size: 12px;
        }

        .metric-item .metric-value {
          color: var(--text);
          font-size: 18px;
          font-weight: 600;
        }

        .panel {
          background: var(--panel);
          border: 1px solid var(--border);
          border-radius: 12px;
          overflow: hidden;
        }

        .panel-header {
          padding: 16px 20px;
          border-bottom: 1px solid var(--border);
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }

        .panel-title {
          color: var(--text);
          font-size: 16px;
          font-weight: 600;
          margin-bottom: 4px;
        }

        .panel-caption {
          color: var(--muted);
          font-size: 12px;
        }

        @media (max-width: 768px) {
          .charts-row {
            grid-template-columns: 1fr;
          }
          
          .vision-content {
            grid-template-columns: 1fr;
          }
          
          .metrics-row {
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          }
        }
      `}</style>
    </div>
  );
}