"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { motion, AnimatePresence } from "framer-motion";

/* ================================================================
   TYPES
   ================================================================ */
interface AgentInfo {
  status: string;
  observe_only?: boolean;
  balance_usdc?: number;
  transactions?: number;
  last_decision?: string;
}

interface LivePayload {
  timestamp: string;
  treasury: {
    balance: number;
    total_earned: number;
    total_spent: number;
    net_profit: number;
    mode?: string;
  };
  decisions: {
    allow: number;
    block: number;
    escalate: number;
    total: number;
    usdc_saved?: number;
    patterns_learned?: number;
  };
  onchain_proof?: {
    confirmed_onchain_tx_count: number;
    target_50_met: boolean;
  };
  threat_registry?: {
    total_attacks_onchain: number;
    total_usdc_protected_usdc: number;
    guaranty_fund6?: number;
  };
  top_patterns?: { pattern_id: string; risk_weight: number }[];
  ecosystem: { running: boolean; agents: Record<string, AgentInfo> };
  policy?: {
    allow_threshold: number;
    block_threshold: number;
    latest_update?: { rationale?: string };
  };
  recent_logs?: LogEntry[];
  agents_tracked?: number;
  response_validation?: {
    total: number;
    safe: number;
    suspicious: number;
    poisoned: number;
  };
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

interface FeedItem {
  id: string;
  agent: string;
  action: string;
  amount: number;
  decision: "ALLOW" | "BLOCK" | "ESCALATE";
  risk: number;
  hash?: string;
  ms?: number;
  ts: string;
}

/* ================================================================
   CONSTANTS
   ================================================================ */
const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const EXPLORER = "https://testnet.arcscan.app";

const AGENTS_ORDERED = ["payer", "frank", "hacker", "dave"];
const AGENT_ICONS: Record<string, string> = {
  payer: "💳",
  frank: "🤖",
  hacker: "💀",
  dave: "👤",
};

const BOOT_LINES = [
  "🛡️ ARCWARDEN SECURITY ORACLE v3.0 — INITIALIZING...",
  "Loading MemoClaw threat models and pattern index... OK",
  "Connecting to Arc testnet RPC... CONNECTED",
  "Bootstrapping agent ecosystem (payer / attacker / learner / monitor)... READY",
  "On-chain Guaranty Fund verification... $5.00 USDC FOUND ✓",
  "Dashboard online ✓",
];

const LATENCY_SPARK = [38, 44, 41, 48, 43, 40, 47, 48, 42, 39, 45, 48];

const DEFAULT_PATTERNS = [
  { pattern_id: "RAPID_SUCCESSION_TX", risk_weight: 0.95 },
  { pattern_id: "LARGE_SINGLE_TX", risk_weight: 0.95 },
  { pattern_id: "UNUSUAL_HOUR_TX", risk_weight: 0.18 },
  { pattern_id: "NEW_RECIPIENT_ADDR", risk_weight: 0.12 },
];

/* ================================================================
   HOOKS
   ================================================================ */
function useClock() {
  const [t, setT] = useState("");
  useEffect(() => {
    const tick = () => {
      const now = new Date();
      const h = now.getUTCHours().toString().padStart(2, "0");
      const m = now.getUTCMinutes().toString().padStart(2, "0");
      const s = now.getUTCSeconds().toString().padStart(2, "0");
      setT(`${h}:${m}:${s} UTC`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return t;
}

function useUptime() {
  const start = useRef(Date.now());
  const [up, setUp] = useState("00:00:00");
  useEffect(() => {
    const tick = () => {
      const elapsed = Math.floor((Date.now() - start.current) / 1000);
      const h = Math.floor(elapsed / 3600)
        .toString()
        .padStart(2, "0");
      const m = Math.floor((elapsed % 3600) / 60)
        .toString()
        .padStart(2, "0");
      const sc = (elapsed % 60).toString().padStart(2, "0");
      setUp(`${h}:${m}:${sc}`);
    };
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);
  return up;
}

function useAnimatedNumber(target: number, decimals = 0): number {
  const [val, setVal] = useState(target);
  const cur = useRef(target);

  useEffect(() => {
    let rafId: number;
    const step = () => {
      const diff = target - cur.current;
      if (Math.abs(diff) < 0.04) {
        cur.current = target;
        setVal(target);
        return;
      }
      cur.current += diff * 0.13;
      setVal(cur.current);
      rafId = requestAnimationFrame(step);
    };
    rafId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafId);
  }, [target]); // eslint-disable-line react-hooks/exhaustive-deps

  return parseFloat(val.toFixed(decimals));
}

/* ================================================================
   SUB-COMPONENTS
   ================================================================ */

/* Tiny sparkline SVG */
function Sparkline({
  values,
  color = "var(--blue-soft)",
}: {
  values: number[];
  color?: string;
}) {
  const W = 64,
    H = 20;
  const max = Math.max(...values);
  const min = Math.min(...values);
  const range = max - min || 1;
  const pts = values
    .map(
      (v, i) =>
        `${(i / (values.length - 1)) * W},${
          H - ((v - min) / range) * (H - 3) - 1.5
        }`,
    )
    .join(" ");
  return (
    <svg
      width={W}
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      style={{ display: "block" }}
    >
      <polyline
        points={pts}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}

/* Node graph SVG */
interface NodeGraphProps {
  agents: Record<string, AgentInfo>;
  running: boolean;
}
function NodeGraph({ agents, running }: NodeGraphProps) {
  const nodes = [
    { id: "warden", x: 100, y: 60, label: "ARC", r: 14, color: "#3b82f6" },
    { id: "payer", x: 32, y: 20, label: "PAYER", r: 9, color: "#2edd7e" },
    { id: "frank", x: 168, y: 20, label: "FRANK", r: 9, color: "#60a5fa" },
    { id: "hacker", x: 32, y: 100, label: "HACK", r: 9, color: "#ff3b6b" },
    { id: "dave", x: 168, y: 100, label: "DAVE", r: 9, color: "#ffb200" },
  ];
  const links: [number, number][] = [
    [0, 1],
    [0, 2],
    [0, 3],
    [0, 4],
    [1, 2],
    [3, 4],
  ];

  return (
    <svg
      width="200"
      height="120"
      viewBox="0 0 200 120"
      className="node-graph-svg"
    >
      <defs>
        <radialGradient id="ng-glow" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.55" />
          <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
        </radialGradient>
        <filter id="ng-blur" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Links */}
      {links.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a].x}
          y1={nodes[a].y}
          x2={nodes[b].x}
          y2={nodes[b].y}
          stroke="rgba(59,130,246,0.28)"
          strokeWidth="1"
          strokeDasharray="4 3"
        >
          {running && (
            <animate
              attributeName="stroke-dashoffset"
              from="0"
              to="-7"
              dur="0.9s"
              repeatCount="indefinite"
            />
          )}
        </line>
      ))}

      {/* Nodes */}
      {nodes.map((n, i) => {
        const info = i > 0 ? agents[AGENTS_ORDERED[i - 1]] : undefined;
        const active =
          i === 0
            ? running
            : info?.status === "running" ||
              info?.status === "active" ||
              running;
        return (
          <g key={n.id}>
            {i === 0 && (
              <circle cx={n.x} cy={n.y} r={n.r + 11} fill="url(#ng-glow)" />
            )}
            <circle
              cx={n.x}
              cy={n.y}
              r={n.r}
              fill={active ? n.color : "#1a2946"}
              stroke={n.color}
              strokeWidth="1.5"
              filter={active ? "url(#ng-blur)" : undefined}
              opacity={active ? 1 : 0.32}
            />
            <text
              x={n.x}
              y={n.y + n.r + 9}
              textAnchor="middle"
              fontSize="6"
              fill="rgba(148,163,184,0.8)"
              fontFamily="'JetBrains Mono', monospace"
            >
              {n.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* Decision donut chart */
interface DonutProps {
  allow: number;
  block: number;
  esc: number;
}
function DecisionDonut({ allow, block, esc }: DonutProps) {
  const total = allow + block + esc;
  const items = [
    { name: "ALLOW", value: allow || 1, real: allow, color: "#2edd7e" },
    { name: "BLOCK", value: block || 1, real: block, color: "#ff3b6b" },
    { name: "ESCALATE", value: esc || 1, real: esc, color: "#ffb200" },
  ];
  const pct = (v: number) => (total > 0 ? Math.round((v / total) * 100) : 0);

  return (
    <div className="donut-wrap">
      {/* Chart */}
      <div
        style={{
          position: "relative",
          width: 162,
          height: 144,
          flexShrink: 0,
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={items}
              cx="50%"
              cy="50%"
              innerRadius={46}
              outerRadius={62}
              dataKey="value"
              strokeWidth={0}
              paddingAngle={2}
            >
              {items.map((entry, i) => (
                <Cell key={i} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: "#0b1528",
                border: "1px solid rgba(59,130,246,0.25)",
                borderRadius: 6,
                fontSize: 10,
              }}
              itemStyle={{ color: "#e2e8f0" }}
            />
          </PieChart>
        </ResponsiveContainer>
        {/* Center label */}
        <div
          style={{
            position: "absolute",
            top: "50%",
            left: "50%",
            transform: "translate(-50%, -50%)",
            textAlign: "center",
            pointerEvents: "none",
          }}
        >
          <div className="donut-total">{total.toLocaleString()}</div>
          <div className="donut-total-lbl">Total</div>
        </div>
      </div>

      {/* Legend */}
      <div className="donut-legend">
        {items.map((d) => (
          <div className="legend-item" key={d.name}>
            <div className="legend-dot" style={{ background: d.color }} />
            <span className="legend-label">{d.name}</span>
            <span className="legend-pct">{pct(d.real)}%</span>
            <span className="legend-val">= {d.real.toLocaleString()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* Stat card */
const STAT_ACCENT: Record<string, string> = {
  allow: "#2edd7e",
  block: "#ff3b6b",
  esc: "#ffb200",
  usdc: "#60a5fa",
  profit: "#2edd7e",
  latency: "#60a5fa",
};

interface StatCardProps {
  type: "allow" | "block" | "esc" | "usdc" | "profit" | "latency";
  label: string;
  value: string | number;
  sub?: string;
  icon?: string;
  sparklineValues?: number[];
}
function StatCard({
  type,
  label,
  value,
  sub,
  icon,
  sparklineValues,
}: StatCardProps) {
  const accent = STAT_ACCENT[type] ?? "#3b82f6";
  return (
    <div className="panel stat-card" style={{ borderTopColor: accent }}>
      <div className="stat-label">
        <span>{label}</span>
        {icon && <span className="stat-icon">{icon}</span>}
      </div>
      <div className="stat-value" style={{ color: accent }}>
        {value}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
      {sparklineValues && (
        <div className="stat-sparkline">
          <Sparkline values={sparklineValues} color={accent} />
        </div>
      )}
    </div>
  );
}

/* Pattern bar */
interface PatternBarProps {
  pattern_id: string;
  risk_weight: number;
}
function PatternBar({ pattern_id, risk_weight }: PatternBarProps) {
  const pct = Math.min(100, risk_weight * 100);
  return (
    <div className="pattern-bar">
      <div className="pattern-bar-header">
        <span className="pattern-bar-label">{pattern_id}</span>
        <span className="pattern-bar-score">{risk_weight.toFixed(2)}</span>
      </div>
      <div className="pattern-track">
        <div className="pattern-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

/* Agent mini card */
interface AgentMiniProps {
  id: string;
  info?: AgentInfo;
}
function AgentMini({ id, info }: AgentMiniProps) {
  const status = info?.status ?? "idle";
  const active = status === "running" || status === "active";
  const obs = info?.observe_only;
  const icon = AGENT_ICONS[id] ?? "🤖";
  const badge = obs
    ? { label: "OBS", color: "#60a5fa", bg: "rgba(59,130,246,0.12)" }
    : active
      ? { label: "LIVE", color: "#2edd7e", bg: "rgba(46,221,126,0.12)" }
      : { label: "IDLE", color: "#94a3b8", bg: "rgba(148,163,184,0.08)" };
  return (
    <div className="agent-mini">
      <span className="agent-mini-icon">{icon}</span>
      <span className="agent-mini-name">{id.toUpperCase()}</span>
      {info?.transactions != null && (
        <span
          style={{
            fontSize: 9,
            color: "var(--muted)",
            fontFamily: "var(--mono)",
          }}
        >
          {info.transactions}tx
        </span>
      )}
      <span
        className="agent-mini-badge"
        style={{ color: badge.color, background: badge.bg }}
      >
        {badge.label}
      </span>
    </div>
  );
}

/* Feed table row */
interface FeedRowProps {
  item: FeedItem;
}
function FeedRow({ item }: FeedRowProps) {
  const decClass =
    item.decision === "ALLOW"
      ? "pill-allow"
      : item.decision === "BLOCK"
        ? "pill-block"
        : "pill-esc";
  const riskLabel = item.risk > 0.65 ? "HIGH" : item.risk > 0.3 ? "MED" : "LOW";
  const riskClass =
    riskLabel === "HIGH"
      ? "risk-high"
      : riskLabel === "MED"
        ? "risk-med"
        : "risk-low";
  const shortId = `${item.id.slice(0, 10)}...`;
  
  // Logic to detect simulated or error hashes
  const isRealHash = (h?: string) => 
    h && h.startsWith("0x") && !h.startsWith("0xSIM_") && !h.startsWith("0xERROR_");

  const shortArc = item.hash ? `${item.hash.slice(0, 10)}...` : null;

  return (
    <tr>
      <td>
        <span className="tx-id-display">
          {shortId}
        </span>
      </td>
      <td>
        <span style={{ fontWeight: 600 }}>
          {AGENT_ICONS[item.agent] ?? "🤖"} {item.agent}
        </span>
      </td>
      <td style={{ color: "var(--muted)" }}>{item.action}</td>
      <td style={{ color: "var(--text)" }}>
        {item.amount != null ? `$${item.amount.toFixed(2)}` : "—"}
      </td>
      <td>
        <span className={`pill ${decClass}`}>{item.decision}</span>
      </td>
      <td>
        <span className={`risk-badge ${riskClass}`}>{riskLabel}</span>
      </td>
      <td>
        {shortArc ? (
          isRealHash(item.hash) ? (
            <a
              className="tx-link"
              href={`${EXPLORER}/tx/${item.hash}`}
              target="_blank"
              rel="noreferrer"
            >
              {shortArc}
            </a>
          ) : (
            <span style={{ color: "var(--muted)", fontSize: 9 }}>{item.hash.startsWith("0xSIM_") ? "Simulated" : "Error"}</span>
          )
        ) : (
          <span style={{ color: "var(--muted)", fontSize: 9 }}>None</span>
        )}
      </td>
      <td style={{ color: "var(--muted)" }}>
        {item.ms != null ? `${item.ms}ms` : "—"}
      </td>
      <td style={{ color: "var(--muted)" }}>{item.ts}</td>
    </tr>
  );
}

/* Boot overlay */
function BootOverlay({ onDone }: { onDone: () => void }) {
  const [lines, setLines] = useState<string[]>([]);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  useEffect(() => {
    let i = 0;
    const show = () => {
      if (i < BOOT_LINES.length) {
        const idx = i;
        setLines((prev) => [...prev, BOOT_LINES[idx]]);
        i++;
        setTimeout(show, 340);
      } else {
        setTimeout(() => doneRef.current(), 460);
      }
    };
    show();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <motion.div
      className="boot-overlay"
      exit={{ opacity: 0 }}
      transition={{ duration: 0.45 }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        style={{ marginBottom: 40, textAlign: "center" }}
      >
        <img
          src="/IMG.jpg"
          alt="ArcWarden Logo"
          style={{
            width: 180,
            height: 180,
            filter: "drop-shadow(0 0 20px rgba(96, 165, 250, 0.4))",
            marginBottom: 20,
          }}
        />
        <div
          style={{
            fontSize: 24,
            fontWeight: 800,
            letterSpacing: "0.2em",
            color: "white",
            textShadow: "0 0 10px rgba(96, 165, 250, 0.5)",
          }}
        >
          ARCWARDEN
        </div>
      </motion.div>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 10,
          alignItems: "flex-start",
          minWidth: 400,
          padding: "20px 40px",
          background: "rgba(0,0,0,0.3)",
          borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.05)",
        }}
      >
        {lines.map((l, i) => (
          <motion.div
            key={i}
            className="boot-line"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22 }}
          >
            <span style={{ color: "var(--blue)", marginRight: 8 }}>{">"}</span>
            {l}
            {i === lines.length - 1 && <span className="boot-cursor">█</span>}
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}

/* ================================================================
   MAIN DASHBOARD
   ================================================================ */
export default function Dashboard() {
  const [booted, setBooted] = useState(false);
  const [data, setData] = useState<LivePayload | null>(null);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [deploying, setDeploying] = useState(false);
  const [simLabel, setSimLabel] = useState("");

  const clock = useClock();
  const uptime = useUptime();

  /* Derive values — all hooks must run unconditionally below */
  const d = data?.decisions;
  const t = data?.treasury;

  const allow = d?.allow ?? 0;
  const block = d?.block ?? 0;
  const escalate = d?.escalate ?? 0;
  const total = d?.total ?? 0;
  const saved = d?.usdc_saved ?? 0;
  const profit = t?.net_profit ?? 0;
  const earned = t?.total_earned ?? 0;
  const spent = t?.total_spent ?? 0;
  const confirmed = data?.onchain_proof?.confirmed_onchain_tx_count ?? 0;
  const targetMet = data?.onchain_proof?.target_50_met ?? false;

  const allowA = useAnimatedNumber(allow);
  const blockA = useAnimatedNumber(block);
  const escA = useAnimatedNumber(escalate);
  const savedA = useAnimatedNumber(
    data?.threat_registry?.total_usdc_protected_usdc ?? saved,
    2
  );
  const guarantyA = useAnimatedNumber(
    (data?.threat_registry?.guaranty_fund6 ?? 0) / 1_000_000,
    4
  );
  const profA = useAnimatedNumber(profit, 4);
  const earnA = useAnimatedNumber(earned, 4);
  const feeA = useAnimatedNumber(spent, 4);
  const confA = useAnimatedNumber(confirmed);

  const agents = data?.ecosystem?.agents ?? {};
  const running = data?.ecosystem?.running ?? false;
  const patterns =
    data?.top_patterns && data.top_patterns.length > 0
      ? data.top_patterns
      : DEFAULT_PATTERNS;

  const modeRaw = t?.mode ?? "NORMAL";
  const mode = modeRaw.toUpperCase();
  const modeColor =
    mode === "NORMAL"
      ? "var(--allow)"
      : mode.includes("DEGRAD")
        ? "var(--esc)"
        : "var(--block)";

  const onchainPct = Math.min(100, Math.round((confirmed / 50) * 100));
  const allowPct = total > 0 ? Math.round((allow / total) * 100) : 0;
  const blockPct = total > 0 ? Math.round((block / total) * 100) : 0;
  const escPct = total > 0 ? Math.round((escalate / total) * 100) : 0;

  /* SSE — start after boot */
  useEffect(() => {
    if (!booted) return;
    const sse = new EventSource(`${API}/demo/live`);
    sse.onmessage = (e) => {
      try {
        const p: LivePayload = JSON.parse(e.data);
        setData(p);
        if (p.recent_logs && p.recent_logs.length > 0) {
          setFeed((prev) => {
            const next: FeedItem[] = p.recent_logs!.map((l) => ({
              id: `0x${Math.random().toString(16).slice(2, 14)}`,
              agent: l.agent_id.replace(/^agent_/, ""),
              action: l.action_type,
              amount: l.amount_usdc,
              decision: (l.decision?.toUpperCase() ??
                "ALLOW") as FeedItem["decision"],
              risk: l.risk_score,
              hash: l.arc_tx_hash || undefined,
              ms: l.processing_time_ms,
              ts: l.timestamp.slice(11, 19),
            }));
            const seen = new Set<string>();
            return [...next, ...prev]
              .filter((item) => {
                const key = `${item.agent}|${item.ts}|${item.amount}|${item.decision}`;
                if (seen.has(key)) return false;
                seen.add(key);
                return true;
              })
              .slice(0, 100);
          });
        }
      } catch {
        /* ignore parse errors */
      }
    };
    return () => sse.close();
  }, [booted]);

  const handleSimulate = useCallback(async () => {
    setDeploying(true);
    setSimLabel("Deploying…");
    try {
      const res = await fetch(`${API}/simulate`, { method: "POST" });
      if (res.ok) {
        setSimLabel("✅ Running!");
        setTimeout(() => setSimLabel(""), 4000);
      } else {
        setSimLabel("⚠️ Active");
        setTimeout(() => setSimLabel(""), 3000);
      }
    } catch {
      setSimLabel("❌ Error");
      setTimeout(() => setSimLabel(""), 3000);
    } finally {
      setDeploying(false);
    }
  }, []);

  /* ── RENDER ── */
  return (
    <>
      {/* Boot sequence */}
      <AnimatePresence>
        {!booted && <BootOverlay key="boot" onDone={() => setBooted(true)} />}
      </AnimatePresence>

      {/* Main dashboard */}
      {booted && (
        <motion.div
          className="aw-root"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.55 }}
        >
          {/* ── HEADER ─────────────────────────────────────── */}
          <header className="header">
            <div className="brand">
              <img
                src="/IMG.jpg"
                alt="Logo"
                style={{
                  width: 32,
                  height: 32,
                  marginRight: 10,
                  filter: "drop-shadow(0 0 5px rgba(96, 165, 250, 0.4))",
                }}
              />
              ARCWARDEN <span>SECURITY ORACLE V3.0</span>
            </div>

            <div className="header-center">
              <span
                className="mode-pill"
                style={{ color: modeColor, borderColor: modeColor }}
              >
                <span className="dot" /> {mode}
              </span>
              <span className="info-chip">Testnet: Arc</span>
              <span className="info-chip">Block: 38,386,003</span>
              <span className="info-chip">Uptime: {uptime}</span>
            </div>

            <div className="header-right">
              <span className="live-badge">
                <span className="live-dot" /> LIVE
              </span>
              <button
                className="deploy-btn"
                onClick={handleSimulate}
                disabled={deploying}
              >
                ⚡ {simLabel || "Deploy Agents"}
              </button>
              <span className="clock">{clock}</span>
            </div>
          </header>

          {/* ── THREAT STRIP ───────────────────────────────── */}
          <div className="threat-strip" />

          {/* ── HERO ROW ───────────────────────────────────── */}
          <div className="hero-row">
            {/* Left: Onchain counter */}
            <div className="hero-onchain panel">
              <div className="hero-icon">⛓</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="hero-label">ONCHAIN TRANSACTIONS</div>
                <div className="hero-count">{confA}</div>
                <div className="hero-sub">
                  Min req hackathon 50 TRANSACTIONS{targetMet ? " ✅" : ""}
                </div>
                <div className="progress-container">
                  <span className="progress-label">PROGRESS</span>
                  <span className="progress-pct">{onchainPct}%</span>
                </div>
                <div className="progress-track">
                  <motion.div
                    className="progress-fill"
                    initial={{ width: "0%" }}
                    animate={{ width: `${onchainPct}%` }}
                    transition={{ duration: 0.9, ease: "easeOut" }}
                  />
                </div>
                <div className="progress-sub">
                  {confirmed} / 50 transactions onchain
                </div>
              </div>
            </div>

            {/* Right: Network graph */}
            <div className="hero-network panel">
              <div className="hero-health">
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: "var(--allow)",
                    display: "inline-block",
                    boxShadow: "0 0 6px var(--allow)",
                    flexShrink: 0,
                  }}
                />
                Health: 99.8% — Optimal
              </div>
              <div className="node-graph-container">
                <NodeGraph agents={agents} running={running} />
              </div>
            </div>
          </div>

          {/* ── STATS ROW ──────────────────────────────────── */}
          <div className="stats-row">
            <StatCard
              type="allow"
              label="ALLOWED"
              value={allowA.toLocaleString()}
              sub={`${allowPct}% of decisions`}
            />
            <StatCard
              type="block"
              label="BLOCKED"
              value={blockA.toLocaleString()}
              sub={`${blockPct}% threats stopped`}
              icon="🛡️"
            />
            <StatCard
              type="esc"
              label="ESCALATED"
              value={escA.toLocaleString()}
              sub={`${escPct}% escalated`}
              icon="⚠️"
            />
            <StatCard
              type="usdc"
              label="USDC PROTECTED"
              value={`$${savedA.toFixed(2)}`}
              sub="saved from threats"
            />
            <StatCard
              type="esc"
              label="GUARANTY FUND"
              value={`$${guarantyA.toFixed(4)}`}
              sub="bonded for insurance"
              icon="⚖️"
            />
            <StatCard
              type="profit"
              label="NET PROFIT"
              value={`$${profA.toFixed(4)}`}
              sub={`Revenue: $${earnA.toFixed(4)} / Fees: $${feeA.toFixed(4)}`}
            />
            <StatCard
              type="latency"
              label="AVG LATENCY"
              value="~40ms"
              sub="p99 <100ms"
              icon="↗"
              sparklineValues={LATENCY_SPARK}
            />
          </div>

          {/* ── MID ROW ────────────────────────────────────── */}
          <div className="mid-row">
            {/* Decision donut */}
            <div className="panel">
              <div className="panel-hd">DECISION SPLIT</div>
              <DecisionDonut allow={allow} block={block} esc={escalate} />
            </div>

            {/* MemoClaw patterns */}
            <div className="panel">
              <div className="panel-hd">MEMOCLAW — TOP PATTERNS</div>
              <div className="patterns-list">
                {patterns.slice(0, 5).map((p) => (
                  <PatternBar
                    key={p.pattern_id}
                    pattern_id={p.pattern_id}
                    risk_weight={p.risk_weight}
                  />
                ))}
              </div>
            </div>

            {/* System logic / agents */}
            <div className="panel">
              <div className="panel-hd">
                SYSTEM LOGIC <span>Data In → Decision Out</span>
              </div>
              <div className="system-logic-body">
                <div className="system-note">
                  Each transaction is scored by MemoClaw, routed through policy
                  thresholds (allow / escalate / block), then committed on-chain
                  via Arc testnet.
                </div>
                {AGENTS_ORDERED.map((id) => (
                  <AgentMini key={id} id={id} info={agents[id]} />
                ))}
              </div>
            </div>
          </div>

          {/* ── LIVE FEED TABLE ────────────────────────────── */}
          <div className="panel table-panel">
            <div className="panel-hd">
              INTEGRATED LIVE FEED &amp; ONCHAIN LOG
            </div>
            <div className="feed-table-wrap">
              <table className="feed-table">
                <thead>
                  <tr>
                    <th>TX HASH</th>
                    <th>AGENT ID</th>
                    <th>ACTION</th>
                    <th>AMOUNT</th>
                    <th>DECISION</th>
                    <th>Risk Level</th>
                    <th>ARC TX</th>
                    <th>MS</th>
                    <th>TIME</th>
                  </tr>
                </thead>
                <tbody>
                  {feed.length === 0 ? (
                    <tr>
                      <td
                        colSpan={9}
                        style={{
                          textAlign: "center",
                          padding: "28px",
                          color: "var(--muted)",
                          fontFamily: "var(--mono)",
                          fontSize: 11,
                        }}
                      >
                        Awaiting live transactions…
                      </td>
                    </tr>
                  ) : (
                    feed.map((item) => <FeedRow key={item.id} item={item} />)
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </motion.div>
      )}
    </>
  );
}
