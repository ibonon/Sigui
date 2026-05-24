"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { DashboardTabs } from "./components/DashboardTabs";
export interface TimePoint { ts: number; allow: number; block: number; escalate: number; revenue: number; }

interface AgentInfo {
  agent_id?: string;
  status: string;
  observe_only?: boolean;
  balance_usdc?: number;
  transactions?: number;
  last_decision?: string;
}

interface TreasuryState {
  balance: number;
  balances_by_chain?: Record<string, number>;
  total_earned: number;
  total_spent: number;
  net_profit: number;
  mode?: string;
}

interface DecisionStats {
  allow: number;
  block: number;
  escalate: number;
  total: number;
  usdc_saved?: number;
  patterns_learned?: number;
}

interface ThreatRegistryState {
  total_attacks_onchain: number;
  total_usdc_protected_usdc: number;
  guaranty_fund6?: number;
}

interface LogEntry {
  agent_id: string;
  action_type: string;
  amount_usdc: number;
  decision: string;
  risk_score: number;
  arc_tx_hash?: string;
  timestamp: string;
  processing_time_ms?: number;
}

interface LivePayload {
  timestamp: string;
  treasury: TreasuryState;
  decisions: DecisionStats;
  onchain_proof?: {
    confirmed_onchain_tx_count: number;
    target_50_met: boolean;
  };
  threat_registry?: ThreatRegistryState;
  top_patterns?: { pattern_id: string; risk_weight: number }[];
  ecosystem: { running: boolean; agents: Record<string, AgentInfo> };
  policy?: {
    allow_threshold: number;
    block_threshold: number;
    latest_update?: { rationale?: string };
  };
  recent_logs?: LogEntry[];
  hogonat_history?: HogonatHistoryItem[];
  agents_tracked?: number;
}

interface HogonatHistoryItem {
  id: number;
  action_type: string;
  staker_id: string;
  amount_usdc: number;
  details: string;
  timestamp: string;
}

interface FeedItem {
  id: string;
  agentId: string;
  action: string;
  amount: number;
  decision: "ALLOW" | "BLOCK" | "ESCALATE";
  risk: number;
  hash?: string;
  ms?: number;
  ts: string;
}

interface BenchmarkPayload {
  risk_engine: {
    cpu_baseline_ms: number;
    runtime_avg_ms: number;
    target_gpu_ms: number;
    speedup_vs_cpu: number;
  };
  vision_layer: {
    baseline_ms: number;
    target_ms: number;
  };
  quality: {
    block_rate_recent: number;
    sample_size: number;
  };
  mode?: string;
}

interface HogonatPayload {
  enabled: boolean;
  mock_mode: boolean;
  total_staked_usdc: number;
  stakers_count: number;
  fee_pool_usdc: number;
  risk_weights: number[];
  allow_threshold: number;
  block_threshold: number;
  updated_at: string;
}

interface VisionGraphNode {
  id: string;
  type: string;
  label?: string;
  focus?: boolean;
}

interface VisionGraphEdge {
  source: string;
  target: string;
  kind: string;
  amount_usdc?: number;
  decision?: string;
}

interface VisionGraphPayload {
  agent_id: string;
  nodes: VisionGraphNode[];
  edges: VisionGraphEdge[];
  summary: {
    heuristic_pattern?: string;
    heuristic_confidence?: number;
    heuristic_risk_delta?: number;
    heuristic_evidence?: string;
    focus_tx_count?: number;
    focus_unique_peer_senders?: number;
    focus_destination?: string;
    chain_count?: number;
    unique_destinations?: number;
    total_amount?: number;
    chains?: string[];
  };
}

interface HogonatFormState {
  stakerId: string;
  amountUsdc: string;
}

interface VoteFormState {
  stakerId: string;
  riskWeights: [string, string, string];
  allowThreshold: string;
  blockThreshold: string;
}

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const EXPLORER = "https://testnet.arcscan.app";
const DEFAULT_FOCUS_AGENT = "agent_attacker";

const BOOT_LINES = [
  "SIGUI PROTOCOL — DePIN Security Network",
  "Initializing AMD MI300X ROCm context...",
  "Loading Qwen2-VL-7B (1,000,000 graph dataset)...",
  "Verifying ERC-8259 Identity Registry...",
  "Establishing x402 Micropayment Channels...",
  "Connecting to Arc L1 Testnet...",
  "Synchronous agent protection ACTIVE.",
];

const AGENT_LABELS: Record<string, { icon: string; title: string }> = {
  agent_payer: { icon: "🔥", title: "Danseur du Feu" },
  agent_attacker: { icon: "🦊", title: "Renard Pale" },
  agent_monitor: { icon: "👁", title: "Oeil de la Societe" },
  agent_learner: { icon: "⭐", title: "Etoile Apprenante" },
  agent_grayzone: { icon: "🌫", title: "Gray Zone" },
};

const CHAIN_META: Record<string, { label: string; icon: string }> = {
  arc: { label: "Arc", icon: "🌍" },
  ethereum: { label: "Ethereum", icon: "🔷" },
  solana: { label: "Solana", icon: "◎" },
};

const DEFAULT_BENCHMARK: BenchmarkPayload = {
  risk_engine: {
    cpu_baseline_ms: 40,
    runtime_avg_ms: 5,
    target_gpu_ms: 2,
    speedup_vs_cpu: 20,
  },
  vision_layer: {
    baseline_ms: 18,
    target_ms: 18,
  },
  quality: {
    block_rate_recent: 0,
    sample_size: 0,
  },
};

// Mock data for when backend is not available
const MOCK_DATA: LivePayload = {
  timestamp: new Date().toISOString(),
  treasury: {
    balance: 1250.50,
    balances_by_chain: { arc: 500.25, ethereum: 450.75, solana: 299.50 },
    total_earned: 2100.00,
    total_spent: 850.50,
    net_profit: 1249.50,
    mode: "NORMAL",
  },
  decisions: {
    allow: 1420,
    block: 340,
    escalate: 85,
    total: 1845,
    usdc_saved: 12500.00,
    patterns_learned: 23,
  },
  onchain_proof: {
    confirmed_onchain_tx_count: 1245,
    target_50_met: true,
  },
  threat_registry: {
    total_attacks_onchain: 340,
    total_usdc_protected_usdc: 12500.00,
    guaranty_fund6: 5000.00,
  },
  top_patterns: [
    { pattern_id: "DRAIN_STAR", risk_weight: 0.85 },
    { pattern_id: "MIXING_CHAIN", risk_weight: 0.72 },
    { pattern_id: "COORDINATED_CLUSTER", risk_weight: 0.68 },
  ],
  ecosystem: {
    running: true,
    agents: {
      agent_payer: { status: "active", transactions: 450, last_decision: "ALLOW" },
      agent_attacker: { status: "active", transactions: 320, last_decision: "BLOCK" },
      agent_learner: { status: "active", transactions: 280, last_decision: "ALLOW" },
      agent_grayzone: { status: "active", transactions: 180, last_decision: "ESCALATE" },
      agent_monitor: { status: "active", transactions: 615, last_decision: "ALLOW" },
    },
  },
  policy: {
    allow_threshold: 0.30,
    block_threshold: 0.70,
  },
  recent_logs: [
    {
      agent_id: "agent_attacker",
      action_type: "transfer",
      amount_usdc: 125.50,
      decision: "BLOCK",
      risk_score: 0.82,
      arc_tx_hash: "0x1234...abcd",
      timestamp: new Date().toISOString(),
      processing_time_ms: 45,
    },
    {
      agent_id: "agent_payer",
      action_type: "transfer",
      amount_usdc: 85.25,
      decision: "ALLOW",
      risk_score: 0.15,
      arc_tx_hash: "0x5678...efgh",
      timestamp: new Date().toISOString(),
      processing_time_ms: 38,
    },
  ],
  hogonat_history: [],
  agents_tracked: 5,
};

function formatMoney(value: number, digits = 2) {
  return `$${value.toFixed(digits)}`;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function normalizeWeights(weights: number[]) {
  const safe = weights.map((value) => (Number.isFinite(value) && value > 0 ? value : 0));
  const total = safe.reduce((sum, value) => sum + value, 0);
  if (total <= 0) return [0.4, 0.3, 0.3];
  return safe.map((value) => Number((value / total).toFixed(4)));
}

function shortHash(value?: string) {
  if (!value) return "none";
  if (value.length <= 14) return value;
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function useClock() {
  const [time, setTime] = useState("");
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        `${now.getUTCHours().toString().padStart(2, "0")}:${now
          .getUTCMinutes()
          .toString()
          .padStart(2, "0")}:${now
          .getUTCSeconds()
          .toString()
          .padStart(2, "0")} UTC`,
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return time;
}

function useUptime() {
  const start = useRef(Date.now());
  const [value, setValue] = useState("00:00:00");
  useEffect(() => {
    const tick = () => {
      const elapsed = Math.floor((Date.now() - start.current) / 1000);
      const h = Math.floor(elapsed / 3600)
        .toString()
        .padStart(2, "0");
      const m = Math.floor((elapsed % 3600) / 60)
        .toString()
        .padStart(2, "0");
      const s = (elapsed % 60).toString().padStart(2, "0");
      setValue(`${h}:${m}:${s}`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return value;
}

function useAnimatedNumber(target: number, decimals = 0) {
  const [value, setValue] = useState(target);
  const current = useRef(target);

  useEffect(() => {
    let rafId = 0;
    const step = () => {
      const diff = target - current.current;
      if (Math.abs(diff) < 0.04) {
        current.current = target;
        setValue(target);
        return;
      }
      current.current += diff * 0.16;
      setValue(current.current);
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [target]);

  return Number(value.toFixed(decimals));
}

function Sparkline({
  values,
  color = "var(--gold)",
}: {
  values: number[];
  color?: string;
}) {
  const width = 96;
  const height = 28;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const points = values
    .map(
      (v, i) =>
        `${(i / Math.max(1, values.length - 1)) * width},${
          height - ((v - min) / range) * (height - 4) - 2
        }`,
    )
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MetricCard({
  label,
  value,
  detail,
  accent = "var(--gold)",
}: {
  label: string;
  value: string;
  detail: string;
  accent?: string;
}) {
  return (
    <div className="metric-card panel">
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color: accent }}>
        {value}
      </div>
      <div className="metric-detail">{detail}</div>
    </div>
  );
}

function ChainBadge({ chain }: { chain: string }) {
  const meta = CHAIN_META[chain] ?? { label: chain, icon: "•" };
  return (
    <span className="chain-badge">
      <span>{meta.icon}</span>
      {meta.label}
    </span>
  );
}

function BootOverlay({ onDone }: { onDone: () => void }) {
  const [lines, setLines] = useState<string[]>([]);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  useEffect(() => {
    let idx = 0;
    const pump = () => {
      if (idx < BOOT_LINES.length) {
        setLines((prev) => [...prev, BOOT_LINES[idx]]);
        idx += 1;
        setTimeout(pump, 320);
        return;
      }
      setTimeout(() => doneRef.current(), 520);
    };
    pump();
  }, []);

  return (
    <motion.div className="boot-overlay" exit={{ opacity: 0 }}>
      <div className="boot-logo-wrap">
        <img src="/logo.png" alt="Sigui" className="boot-logo rounded-full shadow-[0_0_15px_rgba(255,165,0,0.5)]" />
        <div className="boot-title">SIGUI</div>
        <div className="boot-subtitle">THE REGENERATION ORACLE</div>
      </div>
      <div className="boot-console">
        {lines.map((line, index) => (
          <div key={`${line}-${index}`} className="boot-line">
            <span className="boot-prefix">{">"}</span>
            {line}
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function GraphConstellation({ graph }: { graph: VisionGraphPayload | null }) {
  const width = 520;
  const height = 260;

  const layout = useMemo(() => {
    if (!graph) {
      return { nodes: [], edges: [] as Array<{ x1: number; y1: number; x2: number; y2: number; kind: string }> };
    }

    const columns: Record<string, number> = {
      agent: 70,
      peer_agent: 70,
      chain: 210,
      destination: 400,
    };
    const grouped: Record<string, VisionGraphNode[]> = {
      agent: [],
      peer_agent: [],
      chain: [],
      destination: [],
    };

    graph.nodes.forEach((node) => {
      if (!grouped[node.type]) grouped[node.type] = [];
      grouped[node.type].push(node);
    });

    const positions = new Map<string, { x: number; y: number; node: VisionGraphNode }>();

    Object.entries(grouped).forEach(([type, nodes]) => {
      const sorted = [...nodes].sort((a, b) => Number(Boolean(b.focus)) - Number(Boolean(a.focus)));
      const count = Math.max(sorted.length, 1);
      sorted.forEach((node, index) => {
        const y = ((index + 1) / (count + 1)) * (height - 30) + 15;
        const x = columns[type] ?? 260;
        positions.set(node.id, { x, y, node });
      });
    });

    const edges = graph.edges
      .map((edge) => {
        const source = positions.get(edge.source);
        const target = positions.get(edge.target);
        if (!source || !target) return null;
        return {
          x1: source.x,
          y1: source.y,
          x2: target.x,
          y2: target.y,
          kind: edge.kind,
        };
      })
      .filter(Boolean) as Array<{ x1: number; y1: number; x2: number; y2: number; kind: string }>;

    return {
      nodes: Array.from(positions.values()),
      edges,
    };
  }, [graph]);

  return (
    <svg className="vision-svg" viewBox={`0 0 ${width} ${height}`}>
      <defs>
        <radialGradient id="sigui-focus" cx="50%" cy="50%" r="60%">
          <stop offset="0%" stopColor="rgba(246,201,14,0.75)" />
          <stop offset="100%" stopColor="rgba(246,201,14,0)" />
        </radialGradient>
      </defs>
      {layout.edges.map((edge, index) => (
        <line
          key={`${edge.kind}-${index}`}
          x1={edge.x1}
          y1={edge.y1}
          x2={edge.x2}
          y2={edge.y2}
          className={`vision-edge vision-edge-${edge.kind}`}
        />
      ))}
      {layout.nodes.map(({ x, y, node }) => {
        const radius =
          node.type === "chain" ? 12 : node.focus ? 13 : node.type === "agent" ? 10 : 8;
        return (
          <g key={node.id}>
            {node.focus && <circle cx={x} cy={y} r={26} fill="url(#sigui-focus)" />}
            <circle
              cx={x}
              cy={y}
              r={radius}
              className={`vision-node vision-node-${node.type} ${node.focus ? "focus" : ""}`}
            />
            <text x={x} y={y + radius + 14} textAnchor="middle" className="vision-label">
              {(node.label || node.id).slice(0, 14)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function TreasuryBars({ balances }: { balances: Record<string, number> }) {
  const max = Math.max(...Object.values(balances), 0.001);
  return (
    <div className="treasury-bars">
      {Object.entries(CHAIN_META).map(([chain, meta]) => {
        const value = balances[chain] ?? 0;
        const pct = Math.max(6, (value / max) * 100);
        return (
          <div key={chain} className="treasury-row">
            <div className="treasury-row-head">
              <span>
                {meta.icon} {meta.label}
              </span>
              <strong>{formatMoney(value, 3)}</strong>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function FlywheelPanel({
  hogonat,
  treasury,
  totalBlocked,
}: {
  hogonat: HogonatPayload | null;
  treasury: TreasuryState | null;
  totalBlocked: number;
}) {
  const feePool = hogonat?.fee_pool_usdc ?? 0;
  const staked = hogonat?.total_staked_usdc ?? 0;
  const earned = treasury?.total_earned ?? 0;
  const spent = treasury?.total_spent ?? 0;
  const roi = spent > 0 ? (((treasury?.net_profit ?? 0) + spent) / spent).toFixed(1) : "∞";

  return (
    <div className="panel flywheel-panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">⚙️ Economic Flywheel</div>
          <div className="panel-caption">Agent → x402 → Treasury → DAO → Stakers → PolicyBrain · Autonomous loop</div>
        </div>
        <span className="meta-pill">Zero human intervention</span>
      </div>
      <div className="flywheel-body">
        <div className="flywheel-nodes">
          <div className="fw-node">
            <div className="fw-icon">🤖</div>
            <div className="fw-label">AI Agent</div>
            <div className="fw-value">$0.001 / call</div>
          </div>
          <div className="fw-connector">
            <div className="fw-arrow">→</div>
            <div className="fw-pct">x402</div>
          </div>
          <div className="fw-node">
            <div className="fw-icon">🛡️</div>
            <div className="fw-label">Sigui Oracle</div>
            <div className="fw-value">{formatMoney(earned, 4)} earned</div>
          </div>
          <div className="fw-connector">
            <div className="fw-arrow">→</div>
            <div className="fw-pct">20%</div>
          </div>
          <div className="fw-node">
            <div className="fw-icon">🏛️</div>
            <div className="fw-label">Hogonat DAO</div>
            <div className="fw-value">{formatMoney(feePool, 4)} pool</div>
          </div>
          <div className="fw-connector">
            <div className="fw-arrow">→</div>
            <div className="fw-pct">rewards</div>
          </div>
          <div className="fw-node">
            <div className="fw-icon">💎</div>
            <div className="fw-label">Stakers</div>
            <div className="fw-value">{formatMoney(staked, 4)} staked</div>
          </div>
          <div className="fw-connector">
            <div className="fw-arrow">→</div>
            <div className="fw-pct">vote</div>
          </div>
          <div className="fw-node">
            <div className="fw-icon">🧠</div>
            <div className="fw-label">PolicyBrain</div>
            <div className="fw-value">thresholds</div>
          </div>
          <div className="fw-connector">
            <div className="fw-arrow">↺</div>
            <div className="fw-pct">loop</div>
          </div>
        </div>
        <div className="fw-summary">
          <div className="fw-stat">
            <span>Total earned</span>
            <strong>{formatMoney(earned, 4)}</strong>
          </div>
          <div className="fw-stat">
            <span>Threats blocked</span>
            <strong>{totalBlocked}</strong>
          </div>
          <div className="fw-stat">
            <span>DAO fee pool</span>
            <strong>{formatMoney(feePool, 4)}</strong>
          </div>
          <div className="fw-stat">
            <span>Security ROI</span>
            <strong>{roi}x</strong>
          </div>
        </div>
      </div>
    </div>
  );
}

function AttackTheater({
  agents,
  stats,
  deploying,
  onDeploy,
}: {
  agents: Record<string, AgentInfo>;
  stats: DecisionStats | undefined;
  deploying: boolean;
  onDeploy: () => void;
}) {
  const block = stats?.block ?? 0;
  const allow = stats?.allow ?? 0;
  const escalate = stats?.escalate ?? 0;
  const blockRate = stats?.total ? Math.round((block / stats.total) * 100) : 0;

  const THEATER_AGENTS = [
    { id: "agent_payer", icon: "🔥", name: "Danseur du Feu", role: "Legitimate" },
    { id: "agent_attacker", icon: "🦊", name: "Renard Pâle", role: "Adversarial" },
    { id: "agent_learner", icon: "⭐", name: "Étoile App.", role: "Learning" },
    { id: "agent_grayzone", icon: "🌫", name: "Gray Zone", role: "Ambiguous" },
    { id: "agent_monitor", icon: "👁", name: "Œil Société", role: "Monitor" },
  ];

  return (
    <div className="panel theater-panel">
      <div className="panel-header">
        <div className="theater-header-row">
          <div className="live-dot" />
          <div>
            <div className="panel-title">⚔️ Attack Theater — Live</div>
            <div className="panel-caption">5 autonomous agents · Payer · Attacker · Learner · GrayZone · Monitor</div>
          </div>
        </div>
        <div className="panel-badges">
          <span className="amd-chip">⬛ AMD MI300X</span>
          <button className="ritual-btn" onClick={onDeploy} disabled={deploying}>
            {deploying ? "Déploiement..." : "⚡ Déployer les agents"}
          </button>
        </div>
      </div>

      <div className="theater-stats">
        <div className="theater-stat">
          <div className="theater-stat-label">Threats Blocked</div>
          <div className="theater-stat-value" style={{ color: "var(--danger)" }}>{block}</div>
        </div>
        <div className="theater-stat">
          <div className="theater-stat-label">Vision Samples (AMD MI300X)</div>
          <div className="theater-stat-value" style={{ color: "var(--violet)" }}>1,000,000</div>
        </div>
        <div className="theater-stat">
          <div className="theater-stat-label">Transactions Allowed</div>
          <div className="theater-stat-value" style={{ color: "var(--success)" }}>{allow}</div>
        </div>
        <div className="theater-stat">
          <div className="theater-stat-label">Block Rate</div>
          <div className="theater-stat-value" style={{ color: blockRate > 40 ? "var(--danger)" : "var(--gold)" }}>{blockRate}%</div>
        </div>
      </div>

      <div className="theater-agents">
        {THEATER_AGENTS.map((ta) => {
          const info = agents[ta.id];
          const isActive = info?.status === "active";
          const isBlocked = info?.last_decision === "BLOCK";
          return (
            <div
              key={ta.id}
              className={`theater-agent ${isBlocked ? "is-blocked" : isActive ? "is-active" : ""}`}
            >
              <div className="theater-agent-icon">{ta.icon}</div>
              <div className="theater-agent-name">{ta.name}</div>
              <div className="theater-agent-sub">{ta.role}</div>
              <div className="theater-agent-tx">{info?.transactions ?? 0} tx</div>
              {info?.last_decision && (
                <span className={`theater-agent-decision decision-pill decision-${(info.last_decision ?? "").toLowerCase()}`}>
                  {info.last_decision}
                </span>
              )}
              {!info && (
                <span className="theater-agent-decision" style={{ color: "var(--dim)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: "999px" }}>idle</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function FeedRow({ item }: { item: FeedItem }) {
  const isRealHash =
    item.hash &&
    item.hash.startsWith("0x") &&
    !item.hash.startsWith("0xSIM_") &&
    !item.hash.startsWith("0xERROR_");

  return (
    <tr>
      <td>{shortHash(item.id)}</td>
      <td>{AGENT_LABELS[item.agentId]?.title ?? item.agentId}</td>
      <td>{item.action}</td>
      <td>{formatMoney(item.amount, 2)}</td>
      <td>
        <span className={`decision-pill decision-${item.decision.toLowerCase()}`}>
          {item.decision}
        </span>
      </td>
      <td>{item.risk.toFixed(3)}</td>
      <td>
        {isRealHash ? (
          <a
            className="tx-link"
            href={`${EXPLORER}/tx/${item.hash}`}
            target="_blank"
            rel="noreferrer"
          >
            {shortHash(item.hash)}
          </a>
        ) : (
          <span className="muted-text">{shortHash(item.hash)}</span>
        )}
      </td>
      <td>{item.ms ? `${item.ms}ms` : "—"}</td>
      <td>{item.ts}</td>
    </tr>
  );
}

// ── DEMO SIMULATION ENGINE ────────────────────────────────────────────────────
// Generates realistic live data when backend is offline
const DEMO_AGENTS = ["agent_payer", "agent_attacker", "agent_learner", "agent_grayzone", "agent_monitor"];
const DEMO_ACTIONS = ["transfer", "swap", "borrow", "stake", "withdraw", "bridge"];
const DEMO_DECISIONS: FeedItem["decision"][] = ["ALLOW", "ALLOW", "ALLOW", "BLOCK", "ESCALATE"];

function makeDemoFeedItem(): FeedItem {
  const agentId = DEMO_AGENTS[Math.floor(Math.random() * DEMO_AGENTS.length)];
  const decision = DEMO_DECISIONS[Math.floor(Math.random() * DEMO_DECISIONS.length)];
  const amount = parseFloat((Math.random() * 980 + 20).toFixed(2));
  const risk = decision === "BLOCK" ? 0.72 + Math.random() * 0.28
    : decision === "ESCALATE" ? 0.45 + Math.random() * 0.25
    : Math.random() * 0.28;
  const hash = decision !== "ALLOW" ? undefined : `0x${Math.random().toString(16).slice(2, 10)}...${Math.random().toString(16).slice(2, 6)}`;
  return {
    id: `${agentId}-${Date.now()}-${Math.random()}`,
    agentId,
    action: DEMO_ACTIONS[Math.floor(Math.random() * DEMO_ACTIONS.length)],
    amount,
    decision,
    risk: parseFloat(risk.toFixed(3)),
    hash,
    ms: Math.floor(Math.random() * 30 + 8),
    ts: new Date().toISOString().slice(11, 19),
  };
}

export default function Dashboard() {
  const [booted, setBooted] = useState(false);
  const [data, setData] = useState<LivePayload | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkPayload>(DEFAULT_BENCHMARK);
  const [hogonat, setHogonat] = useState<HogonatPayload | null>(null);
  const [visionGraph, setVisionGraph] = useState<VisionGraphPayload | null>(null);
  const [focusAgentId, setFocusAgentId] = useState(DEFAULT_FOCUS_AGENT);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [timeSeries, setTimeSeries] = useState<TimePoint[]>([]);
  const [deploying, setDeploying] = useState(false);
  const [simLabel, setSimLabel] = useState("");
  const [backendOnline, setBackendOnline] = useState(false);
  const [stakeForm, setStakeForm] = useState<HogonatFormState>({
    stakerId: "agent_monitor",
    amountUsdc: "0.01",
  });
  const [voteForm, setVoteForm] = useState<VoteFormState>({
    stakerId: "agent_monitor",
    riskWeights: ["0.40", "0.30", "0.30"],
    allowThreshold: "0.30",
    blockThreshold: "0.70",
  });
  const [stakeStatus, setStakeStatus] = useState<string>("");
  const [voteStatus, setVoteStatus] = useState<string>("");
  const [submittingStake, setSubmittingStake] = useState(false);
  const [submittingVote, setSubmittingVote] = useState(false);
  const [loadingVision, setLoadingVision] = useState(false);
  const [loadingSidePanels, setLoadingSidePanels] = useState(false);
  // Simulation counters (used when backend is offline)
  const simCounters = useRef({ allow: 1420, block: 340, escalate: 85, earned: 2.1842, protected: 12500, confirmed: 1245 });
  const voteFormInitialized = useRef(false);

  const clock = useClock();
  const uptime = useUptime();

  const stats = data?.decisions;
  const treasury = data?.treasury;
  const onchain = data?.onchain_proof;
  const patterns = data?.top_patterns ?? [];
  const agents = data?.ecosystem?.agents ?? {};

  const allow = stats?.allow ?? 0;
  const block = stats?.block ?? 0;
  const escalate = stats?.escalate ?? 0;
  const total = stats?.total ?? 0;
  const protectedUsdc = data?.threat_registry?.total_usdc_protected_usdc ?? stats?.usdc_saved ?? 0;
  const profit = treasury?.net_profit ?? 0;
  const totalEarned = treasury?.total_earned ?? 0;
  const totalSpent = treasury?.total_spent ?? 0;
  const roi = totalSpent > 0 ? (protectedUsdc / totalSpent).toFixed(2) : "0.00";
  const confirmed = onchain?.confirmed_onchain_tx_count ?? 0;
  const balancesByChain = treasury?.balances_by_chain ?? { arc: 0, ethereum: 0, solana: 0 };
  const hogonatHistory = data?.hogonat_history ?? [];
  const mode = (treasury?.mode ?? "NORMAL").toUpperCase();
  const modeClass =
    mode === "NORMAL" ? "mode-normal" : mode.includes("DEGRAD") ? "mode-degraded" : "mode-emergency";

  const evalsA = useAnimatedNumber(total);
  const blockA = useAnimatedNumber(block);
  const escA = useAnimatedNumber(escalate);
  const protectedA = useAnimatedNumber(protectedUsdc, 2);
  const profitA = useAnimatedNumber(profit, 3);
  const confirmedA = useAnimatedNumber(confirmed);

  const agentOptions = useMemo(() => {
    const keys = new Set<string>([DEFAULT_FOCUS_AGENT]);
    Object.keys(agents).forEach((key) => keys.add(key));
    feed.forEach((item) => keys.add(item.agentId));
    return Array.from(keys);
  }, [agents, feed]);

  const refreshDashboardData = useCallback(
    async (options?: { visionOnly?: boolean }) => {
      const visionOnly = options?.visionOnly ?? false;

      if (visionOnly) {
        setLoadingVision(true);
      } else {
        setLoadingSidePanels(true);
      }

      try {
        const requests = visionOnly
          ? [fetch(`${API}/vision/graph/${encodeURIComponent(focusAgentId)}`)]
          : [
              fetch(`${API}/benchmark`),
              fetch(`${API}/hogonat/state`),
              fetch(`${API}/vision/graph/${encodeURIComponent(focusAgentId)}`),
            ];

        const results = await Promise.allSettled(requests);

        if (visionOnly) {
          const graphRes = results[0];
          if (graphRes.status === "fulfilled" && graphRes.value.ok) {
            const payload = (await graphRes.value.json()) as VisionGraphPayload;
            setVisionGraph(payload);
          }
          return;
        }

        const [benchmarkRes, hogonatRes, graphRes] = results;
        if (benchmarkRes?.status === "fulfilled" && benchmarkRes.value.ok) {
          const payload = (await benchmarkRes.value.json()) as BenchmarkPayload;
          setBenchmark(payload);
        } else if (benchmarkRes?.status === "rejected") {
          console.warn("Failed to fetch benchmark data:", benchmarkRes.reason);
        }
        if (hogonatRes?.status === "fulfilled" && hogonatRes.value.ok) {
          const payload = (await hogonatRes.value.json()) as HogonatPayload;
          setHogonat(payload);
        } else if (hogonatRes?.status === "rejected") {
          console.warn("Failed to fetch hogonat data:", hogonatRes.reason);
        }
        if (graphRes?.status === "fulfilled" && graphRes.value.ok) {
          const payload = (await graphRes.value.json()) as VisionGraphPayload;
          setVisionGraph(payload);
        } else if (graphRes?.status === "rejected") {
          console.warn("Failed to fetch vision graph data:", graphRes.reason);
        }
      } catch (error) {
        console.warn("Failed to refresh dashboard data:", error);
      } finally {
        setLoadingVision(false);
        setLoadingSidePanels(false);
      }
    },
    [focusAgentId],
  );

  // ── Live data from backend SSE ────────────────────────────────────────────
  useEffect(() => {
    if (!booted) return;

    let sse: EventSource | null = null;
    let sseConnected = false;

    const connect = () => {
      try {
        sse = new EventSource(`${API}/demo/live`);

        sse.onopen = () => {
          sseConnected = true;
          setBackendOnline(true);
        };

        sse.onmessage = (event) => {
          sseConnected = true;
          setBackendOnline(true);
          try {
            const payload: LivePayload = JSON.parse(event.data);
            setData(payload);
            if (payload.recent_logs?.length) {
              setFocusAgentId(payload.recent_logs[0].agent_id || DEFAULT_FOCUS_AGENT);
              setFeed((prev) => {
                const next = payload.recent_logs!.map((row) => ({
                  id: `${row.agent_id}-${row.timestamp}-${row.decision}-${row.amount_usdc}`,
                  agentId: row.agent_id,
                  action: row.action_type,
                  amount: row.amount_usdc,
                  decision: (row.decision?.toUpperCase() ?? "ALLOW") as FeedItem["decision"],
                  risk: row.risk_score,
                  hash: row.arc_tx_hash,
                  ms: row.processing_time_ms,
                  ts: row.timestamp.slice(11, 19),
                }));
                const seen = new Set<string>();
                return [...next, ...prev].filter((item) => {
                  if (seen.has(item.id)) return false;
                  seen.add(item.id);
                  return true;
                }).slice(0, 18);
              });
            }
            if (payload.decisions) {
              setTimeSeries((prev) => {
                const newPt = {
                  ts: Date.now(),
                  allow: payload.decisions.allow || 0,
                  block: payload.decisions.block || 0,
                  escalate: payload.decisions.escalate || 0,
                  revenue: payload.treasury?.net_profit || 0,
                };
                return [...prev, newPt].slice(-50);
              });
            }
          } catch { /* ignore */ }
        };

        sse.onerror = () => {
          if (!sseConnected) setBackendOnline(false);
        };
      } catch { /* ignore */ }
    };

    connect();
    return () => sse?.close();
  }, [booted]);

  // ── Autonomous demo simulation (kicks in when backend is offline) ─────────
  useEffect(() => {
    if (!booted) return;

    const tick = () => {
      if (backendOnline) return; // let real SSE drive the UI

      const c = simCounters.current;
      // randomly pick decision outcome
      const roll = Math.random();
      const isBlock = roll > 0.82;
      const isEsc = !isBlock && roll > 0.77;
      const isAllow = !isBlock && !isEsc;

      if (isAllow) c.allow++;
      if (isBlock) { c.block++; }
      if (isEsc) c.escalate++;
      c.earned += 0.001;
      c.protected += isBlock ? Math.random() * 800 + 200 : 0;
      if (isAllow && Math.random() > 0.7) c.confirmed++;

      const newItem = makeDemoFeedItem();

      setFeed((prev) => [newItem, ...prev].slice(0, 18));

      setTimeSeries((prev) => [
        ...prev,
        { ts: Date.now(), allow: c.allow, block: c.block, escalate: c.escalate, revenue: c.earned },
      ].slice(-50));

      // Build synthetic LivePayload
      const syntheticData: LivePayload = {
        ...MOCK_DATA,
        timestamp: new Date().toISOString(),
        treasury: {
          balance: c.earned * 0.8,
          balances_by_chain: { arc: c.earned * 0.4, ethereum: c.earned * 0.25, solana: c.earned * 0.15 },
          total_earned: c.earned,
          total_spent: c.earned * 0.12,
          net_profit: c.earned * 0.88,
          mode: "NORMAL",
        },
        decisions: { allow: c.allow, block: c.block, escalate: c.escalate, total: c.allow + c.block + c.escalate, usdc_saved: c.protected, patterns_learned: 23 },
        onchain_proof: { confirmed_onchain_tx_count: c.confirmed, target_50_met: c.confirmed >= 50 },
        threat_registry: { total_attacks_onchain: c.block, total_usdc_protected_usdc: c.protected, guaranty_fund6: c.protected * 0.4 },
        ecosystem: {
          running: true,
          agents: {
            agent_payer: { status: "active", transactions: Math.floor(c.allow * 0.32), last_decision: "ALLOW" },
            agent_attacker: { status: "active", transactions: Math.floor(c.block * 0.85), last_decision: "BLOCK" },
            agent_learner: { status: "active", transactions: Math.floor(c.allow * 0.18), last_decision: "ALLOW" },
            agent_grayzone: { status: "active", transactions: Math.floor(c.escalate * 0.9), last_decision: "ESCALATE" },
            agent_monitor: { status: "active", transactions: Math.floor((c.allow + c.block) * 0.4), last_decision: "ALLOW" },
          },
        },
      };
      setData(syntheticData);
    };

    const id = setInterval(tick, 1200);
    return () => clearInterval(id);
  }, [booted, backendOnline]);

  useEffect(() => {
    if (!booted) return;
    
    // Fetch real data from backend with Imina Na model
    refreshDashboardData();
    
    const id = setInterval(() => {
      void refreshDashboardData();
    }, 4500);
    return () => {
      clearInterval(id);
    };
  }, [booted, refreshDashboardData]);

  useEffect(() => {
    if (!hogonat || voteFormInitialized.current) return;
    voteFormInitialized.current = true;
    setVoteForm({
      stakerId: "agent_monitor",
      riskWeights: hogonat.risk_weights.map((value) => value.toFixed(2)) as [
        string,
        string,
        string,
      ],
      allowThreshold: hogonat.allow_threshold.toFixed(2),
      blockThreshold: hogonat.block_threshold.toFixed(2),
    });
  }, [hogonat]);

  const handleSimulate = useCallback(async () => {
    setDeploying(true);
    setSimLabel("Initializing...");
    try {
      const response = await fetch(`${API}/simulate`, { method: "POST" });
      setSimLabel(response.ok ? "Running..." : "Active");
    } catch (error) {
      console.warn("Simulate API call failed:", error);
      setSimLabel("Error");
    } finally {
      setTimeout(() => setSimLabel(""), 2600);
      setDeploying(false);
    }
  }, []);

  const handleVisionRefresh = useCallback(async () => {
    await refreshDashboardData({ visionOnly: true });
  }, [refreshDashboardData]);

  const handleStakeSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setStakeStatus("");

      const stakerId = stakeForm.stakerId.trim();
      const amountUsdc = Number(stakeForm.amountUsdc);

      if (!stakerId) {
        setStakeStatus("Renseigne un staker_id valide.");
        return;
      }
      if (!Number.isFinite(amountUsdc) || amountUsdc <= 0) {
        setStakeStatus("Le montant de stake doit etre positif.");
        return;
      }

      setSubmittingStake(true);
      try {
        const response = await fetch(`${API}/hogonat/stake`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            staker_id: stakerId,
            amount_usdc: Number(amountUsdc.toFixed(6)),
          }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          setStakeStatus(String(payload.detail || "Echec du stake."));
          return;
        }
        setStakeStatus(
          `Stake enregistre pour ${stakerId}: ${formatMoney(
            payload.amount_staked_usdc ?? amountUsdc,
            3,
          )}`,
        );
        await refreshDashboardData();
      } catch (error) {
        console.warn("Stake API call failed:", error);
        setStakeStatus("Erreur réseau pendant le stake.");
      } finally {
        setSubmittingStake(false);
      }
    },
    [refreshDashboardData, stakeForm],
  );

  const handleVoteSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setVoteStatus("");

      const stakerId = voteForm.stakerId.trim();
      const parsedWeights = voteForm.riskWeights.map((value) => Number(value));
      const weights = normalizeWeights(parsedWeights);
      const allowThreshold = clamp(Number(voteForm.allowThreshold), 0.01, 0.98);
      const blockThreshold = clamp(Number(voteForm.blockThreshold), 0.02, 0.99);

      if (!stakerId) {
        setVoteStatus("Renseigne un staker_id pour voter.");
        return;
      }
      if (weights.some((value) => !Number.isFinite(value))) {
        setVoteStatus("Les poids doivent etre numeriques.");
        return;
      }
      if (!Number.isFinite(allowThreshold) || !Number.isFinite(blockThreshold)) {
        setVoteStatus("Les seuils doivent etre numeriques.");
        return;
      }
      if (allowThreshold >= blockThreshold) {
        setVoteStatus("Le seuil allow doit rester inferieur au seuil block.");
        return;
      }

      setSubmittingVote(true);
      try {
        const response = await fetch(`${API}/hogonat/vote`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            staker_id: stakerId,
            risk_weights: weights,
            allow_threshold: Number(allowThreshold.toFixed(4)),
            block_threshold: Number(blockThreshold.toFixed(4)),
          }),
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) {
          setVoteStatus(String(payload.detail || "Vote refuse."));
          return;
        }
        setVoteStatus("Vote applique et etat Hogonat rafraichi.");
        voteFormInitialized.current = false;
        await refreshDashboardData();
      } catch (error) {
        console.warn("Vote API call failed:", error);
        setVoteStatus("Erreur réseau pendant le vote.");
      } finally {
        setSubmittingVote(false);
      }
    },
    [refreshDashboardData, voteForm],
  );

  const focusPattern = visionGraph?.summary?.heuristic_pattern ?? "NORMAL";
  const focusConfidence = visionGraph?.summary?.heuristic_confidence ?? 0.72;
  const focusEvidence =
    visionGraph?.summary?.heuristic_evidence ?? "Aucun signal visuel dominant pour le moment.";
  const focusAgentLabel = AGENT_LABELS[focusAgentId]?.title ?? focusAgentId;
  const benchmarkSpark = [
    benchmark.risk_engine.cpu_baseline_ms,
    benchmark.risk_engine.runtime_avg_ms + 6,
    benchmark.risk_engine.runtime_avg_ms + 3,
    benchmark.risk_engine.runtime_avg_ms,
    benchmark.vision_layer.target_ms,
  ];
  const draftWeights = normalizeWeights(voteForm.riskWeights.map((value) => Number(value)));

  return (
    <>
      <AnimatePresence>
        {!booted && <BootOverlay key="boot" onDone={() => setBooted(true)} />}
      </AnimatePresence>

      {booted && (
        <motion.main
          className="dashboard-root"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.45 }}
        >
          <header className="topbar">
            <div className="brand-block">
              <img src="/logo.png" alt="Sigui" className="brand-logo rounded-full shadow-[0_0_15px_rgba(255,165,0,0.5)]" />
              <div>
                <div className="brand-title">SIGUI DePIN NETWORK</div>
                <div className="brand-subtitle">Synchronous Security Oracle powered by AMD MI300X</div>
              </div>
            </div>

            <div className="topbar-center">
              <span className={`mode-pill ${modeClass}`}>{mode}</span>
              <span className="meta-pill">AMD MI300X</span>
              <span className="meta-pill">x402</span>
              <span className="meta-pill">Uptime {uptime}</span>
              <span className="meta-pill">{clock}</span>
              {!backendOnline && (
                <span className="mode-pill demo-mode">⚡ DEMO SIMULATION</span>
              )}
              {backendOnline && (
                <span className="mode-pill mode-normal">🟢 LIVE</span>
              )}
            </div>

            <div className="topbar-right">
              <div className="chain-strip">
                {Object.keys(CHAIN_META).map((chain) => (
                  <ChainBadge key={chain} chain={chain} />
                ))}
              </div>
              <button className="ritual-btn" onClick={handleSimulate} disabled={deploying}>
                {simLabel || "Deploy Agents"}
              </button>
            </div>
          </header>


          <DashboardTabs 
            data={data}
            benchmark={benchmark}
            hogonat={hogonat}
            visionGraph={visionGraph}
            focusAgentId={focusAgentId}
            feed={feed}
            deploying={deploying}
            stats={stats}
            treasury={treasury}
            onchain={onchain}
            patterns={patterns}
            agents={agents}
            allow={allow}
            block={block}
            escalate={escalate}
            total={total}
            protectedUsdc={protectedUsdc}
            profit={profit}
            totalEarned={totalEarned}
            totalSpent={totalSpent}
            roi={roi}
            confirmed={confirmed}
            balancesByChain={balancesByChain}
            hogonatHistory={hogonatHistory}
            mode={mode}
            evalsA={evalsA}
            blockA={blockA}
            escA={escA}
            protectedA={protectedA}
            profitA={profitA}
            confirmedA={confirmedA}
            handleSimulate={handleSimulate}
            timeSeries={timeSeries}
            FlywheelPanel={FlywheelPanel}
            AttackTheater={AttackTheater}
            FeedRow={FeedRow}
            shortHash={shortHash}
            AGENT_LABELS={AGENT_LABELS}
            EXPLORER={EXPLORER}
          />
        </motion.main>
      )}
    </>
  );
}
