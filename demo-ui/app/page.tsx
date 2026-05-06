"use client";

import type { FormEvent } from "react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

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
  "Loading Qwen2.5-VL and Kanaga Risk Engine...",
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
    target_gpu_ms: 5,
    speedup_vs_cpu: 8,
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
        <img src="/IMG.jpg" alt="Sigui" className="boot-logo" />
        <div className="boot-title">SIGUI</div>
        <div className="boot-subtitle">THE REGENERATION ORACLE</div>
      </div>
      <div className="boot-console">
        {lines.map((line) => (
          <div key={line} className="boot-line">
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

export default function Dashboard() {
  const [booted, setBooted] = useState(false);
  const [data, setData] = useState<LivePayload | null>(null);
  const [benchmark, setBenchmark] = useState<BenchmarkPayload>(DEFAULT_BENCHMARK);
  const [hogonat, setHogonat] = useState<HogonatPayload | null>(null);
  const [visionGraph, setVisionGraph] = useState<VisionGraphPayload | null>(null);
  const [focusAgentId, setFocusAgentId] = useState(DEFAULT_FOCUS_AGENT);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [deploying, setDeploying] = useState(false);
  const [simLabel, setSimLabel] = useState("");
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
        }
        if (hogonatRes?.status === "fulfilled" && hogonatRes.value.ok) {
          const payload = (await hogonatRes.value.json()) as HogonatPayload;
          setHogonat(payload);
        }
        if (graphRes?.status === "fulfilled" && graphRes.value.ok) {
          const payload = (await graphRes.value.json()) as VisionGraphPayload;
          setVisionGraph(payload);
        }
      } finally {
        setLoadingVision(false);
        setLoadingSidePanels(false);
      }
    },
    [focusAgentId],
  );

  useEffect(() => {
    if (!booted) return;
    const sse = new EventSource(`${API}/demo/live`);
    sse.onmessage = (event) => {
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
      } catch {
        // Ignore transient payload issues
      }
    };
    return () => sse.close();
  }, [booted]);

  useEffect(() => {
    if (!booted) return;
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
    setSimLabel("Rituel...");
    try {
      const response = await fetch(`${API}/simulate`, { method: "POST" });
      setSimLabel(response.ok ? "En cours" : "Actif");
    } catch {
      setSimLabel("Erreur");
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
      } catch {
        setStakeStatus("Erreur reseau pendant le stake.");
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
      } catch {
        setVoteStatus("Erreur reseau pendant le vote.");
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
              <img src="/IMG.jpg" alt="Sigui" className="brand-logo" />
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
            </div>

            <div className="topbar-right">
              <div className="chain-strip">
                {Object.keys(CHAIN_META).map((chain) => (
                  <ChainBadge key={chain} chain={chain} />
                ))}
              </div>
              <button className="ritual-btn" onClick={handleSimulate} disabled={deploying}>
                {simLabel || "Lancer le rituel"}
              </button>
            </div>
          </header>

          <section className="metrics-grid">
            <MetricCard
              label="Evaluations"
              value={evalsA.toLocaleString()}
              detail={`${allow} allow · ${block} block · ${escalate} escalate`}
            />
            <MetricCard
              label="Threats Blocked"
              value={blockA.toLocaleString()}
              detail={`${total > 0 ? Math.round((block / total) * 100) : 0}% des decisions`}
              accent="var(--danger)"
            />
            <MetricCard
              label="Escalations"
              value={escA.toLocaleString()}
              detail="Zone grise et dossiers ambigus"
              accent="var(--violet)"
            />
            <MetricCard
              label="USDC Proteges"
              value={formatMoney(protectedA, 2)}
              detail="Valeur sauvegardee par Sigui"
              accent="var(--success)"
            />
            <MetricCard
              label="x402 Network Revenue"
              value={formatMoney(profitA, 3)}
              detail={`${formatMoney(treasury?.total_earned ?? 0, 3)} collected · ${formatMoney(
                treasury?.total_spent ?? 0,
                3,
              )} depenses`}
              accent="var(--gold)"
            />
            <MetricCard
              label="Transactions Onchain"
              value={confirmedA.toLocaleString()}
              detail={onchain?.target_50_met ? "Objectif hackathon atteint" : "Objectif 50 en cours"}
              accent="var(--blue)"
            />
          </section>

          <section className="feature-grid">
            <div className="panel divination-panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Divination Board</div>
                  <div className="panel-caption">
                    Imina Na analyse le graphe recentre sur {focusAgentLabel}
                  </div>
                </div>
                <div className="panel-badges">
                  <label className="control-chip">
                    <span>Agent</span>
                    <select
                      value={focusAgentId}
                      onChange={(event) => setFocusAgentId(event.target.value)}
                      className="control-select"
                    >
                      {agentOptions.map((agentId) => (
                        <option key={agentId} value={agentId}>
                          {AGENT_LABELS[agentId]?.title ?? agentId}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={handleVisionRefresh}
                    disabled={loadingVision}
                  >
                    {loadingVision ? "Refresh..." : "Rafraichir"}
                  </button>
                  <span className="signal-pill">{focusPattern}</span>
                  <span className="meta-pill">{Math.round(focusConfidence * 100)}% confiance</span>
                </div>
              </div>

              <div className="divination-content">
                <div className="vision-card">
                  <GraphConstellation graph={visionGraph} />
                </div>

                <div className="vision-side">
                  <div className="vision-note">{focusEvidence}</div>

                  <div className="mini-stat-grid">
                    <div className="mini-stat">
                      <span>Focus tx</span>
                      <strong>{visionGraph?.summary?.focus_tx_count ?? 0}</strong>
                    </div>
                    <div className="mini-stat">
                      <span>Peer senders</span>
                      <strong>{visionGraph?.summary?.focus_unique_peer_senders ?? 0}</strong>
                    </div>
                    <div className="mini-stat">
                      <span>Chains</span>
                      <strong>{visionGraph?.summary?.chain_count ?? 0}</strong>
                    </div>
                    <div className="mini-stat">
                      <span>Destinations</span>
                      <strong>{visionGraph?.summary?.unique_destinations ?? 0}</strong>
                    </div>
                  </div>

                  <div className="divination-footer">
                    <div>
                      <span className="muted-label">Destination focale</span>
                      <strong>{visionGraph?.summary?.focus_destination ?? "n/a"}</strong>
                    </div>
                    <div>
                      <span className="muted-label">Flux observes</span>
                      <strong>{formatMoney(visionGraph?.summary?.total_amount ?? 0, 3)}</strong>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="panel benchmark-panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">AMD Performance</div>
                  <div className="panel-caption">CPU vs ROCm vs Imina Na</div>
                </div>
                <div className="panel-badges">
                  <span className="meta-pill">{loadingSidePanels ? "Sync..." : "Live sync"}</span>
                </div>
              </div>

              <div className="benchmark-metrics">
                <div className="benchmark-row">
                  <span>Risk Engine CPU</span>
                  <strong>{benchmark.risk_engine.cpu_baseline_ms.toFixed(1)}ms</strong>
                </div>
                <div className="benchmark-row">
                  <span>Runtime Sigui</span>
                  <strong>{benchmark.risk_engine.runtime_avg_ms.toFixed(1)}ms</strong>
                </div>
                <div className="benchmark-row">
                  <span>Speedup</span>
                  <strong>{benchmark.risk_engine.speedup_vs_cpu.toFixed(2)}x</strong>
                </div>
                <div className="benchmark-row">
                  <span>Vision Target</span>
                  <strong>{benchmark.vision_layer.target_ms.toFixed(1)}ms</strong>
                </div>
                <div className="benchmark-row">
                  <span>Recent Sample</span>
                  <strong>{benchmark.quality.sample_size}</strong>
                </div>
              </div>

              <div className="sparkline-wrap">
                <Sparkline values={benchmarkSpark} />
              </div>
              <div className="benchmark-footnote">
                Fine-tuning branche ensuite sur cette meme surface dashboard.
              </div>
            </div>
          </section>

          <section className="lower-grid">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Multi-Chain Treasury</div>
                  <div className="panel-caption">Balances consolidees du Tresor du Sigui</div>
                </div>
              </div>
              <div className="panel-body">
                <TreasuryBars balances={balancesByChain} />
                <div className="treasury-summary">
                  <div>
                    <span className="muted-label">Balance totale</span>
                    <strong>{formatMoney(treasury?.balance ?? 0, 3)}</strong>
                  </div>
                  <div>
                    <span className="muted-label">Mode</span>
                    <strong>{mode}</strong>
                  </div>
                </div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Hogonat DAO</div>
                  <div className="panel-caption">Poids Kanaga et seuils de gouvernance</div>
                </div>
              </div>
              <div className="panel-body">
                <div className="dao-topline">
                  <div>
                    <span className="muted-label">Total stake</span>
                    <strong>{formatMoney(hogonat?.total_staked_usdc ?? 0, 3)}</strong>
                  </div>
                  <div>
                    <span className="muted-label">Stakers</span>
                    <strong>{hogonat?.stakers_count ?? 0}</strong>
                  </div>
                  <div>
                    <span className="muted-label">Fee pool</span>
                    <strong>{formatMoney(hogonat?.fee_pool_usdc ?? 0, 3)}</strong>
                  </div>
                </div>

                <div className="weight-stack">
                  {(hogonat?.risk_weights ?? [0.4, 0.3, 0.3]).map((weight, index) => (
                    <div key={`${index}-${weight}`} className="weight-row">
                      <div className="weight-head">
                        <span>{["Action", "Context", "History"][index]}</span>
                        <strong>{Math.round(weight * 100)}%</strong>
                      </div>
                      <div className="bar-track">
                        <div className="bar-fill gold" style={{ width: `${weight * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>

                <div className="dao-thresholds">
                  <div>
                    <span className="muted-label">Allow threshold</span>
                    <strong>{hogonat?.allow_threshold?.toFixed(2) ?? "0.30"}</strong>
                  </div>
                  <div>
                    <span className="muted-label">Block threshold</span>
                    <strong>{hogonat?.block_threshold?.toFixed(2) ?? "0.70"}</strong>
                  </div>
                </div>

                <div className="form-section">
                  <div className="form-title">Stake Demo</div>
                  <form className="control-form" onSubmit={handleStakeSubmit}>
                    <div className="field-grid field-grid-2">
                      <label className="field">
                        <span>Staker ID</span>
                        <input
                          value={stakeForm.stakerId}
                          onChange={(event) =>
                            setStakeForm((prev) => ({ ...prev, stakerId: event.target.value }))
                          }
                          placeholder="agent_monitor"
                        />
                      </label>
                      <label className="field">
                        <span>Amount USDC</span>
                        <input
                          type="number"
                          min="0.01"
                          step="0.01"
                          value={stakeForm.amountUsdc}
                          onChange={(event) =>
                            setStakeForm((prev) => ({ ...prev, amountUsdc: event.target.value }))
                          }
                        />
                      </label>
                    </div>
                    <div className="form-actions">
                      <button type="submit" className="primary-btn" disabled={submittingStake}>
                        {submittingStake ? "Staking..." : "Stake"}
                      </button>
                      <span className="form-feedback">{stakeStatus || "Minimum 0.01 USDC"}</span>
                    </div>
                  </form>
                </div>

                <div className="form-section">
                  <div className="form-title">Vote Weights</div>
                  <form className="control-form" onSubmit={handleVoteSubmit}>
                    <div className="field-grid field-grid-2">
                      <label className="field">
                        <span>Staker ID</span>
                        <input
                          value={voteForm.stakerId}
                          onChange={(event) =>
                            setVoteForm((prev) => ({ ...prev, stakerId: event.target.value }))
                          }
                          placeholder="agent_monitor"
                        />
                      </label>
                    </div>

                    <div className="field-grid field-grid-3">
                      {(["Action", "Context", "History"] as const).map((label, index) => (
                        <label key={label} className="field">
                          <span>{label}</span>
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={voteForm.riskWeights[index]}
                            onChange={(event) =>
                              setVoteForm((prev) => {
                                const riskWeights = [...prev.riskWeights] as [
                                  string,
                                  string,
                                  string,
                                ];
                                riskWeights[index] = event.target.value;
                                return { ...prev, riskWeights };
                              })
                            }
                          />
                        </label>
                      ))}
                    </div>

                    <div className="weight-preview">
                      {draftWeights.map((weight, index) => (
                        <div key={`${index}-${weight}`} className="weight-row compact">
                          <div className="weight-head">
                            <span>{["Action", "Context", "History"][index]}</span>
                            <strong>{Math.round(weight * 100)}%</strong>
                          </div>
                          <div className="bar-track">
                            <div className="bar-fill gold" style={{ width: `${weight * 100}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="field-grid field-grid-2">
                      <label className="field">
                        <span>Allow threshold</span>
                        <input
                          type="number"
                          min="0.01"
                          max="0.98"
                          step="0.01"
                          value={voteForm.allowThreshold}
                          onChange={(event) =>
                            setVoteForm((prev) => ({ ...prev, allowThreshold: event.target.value }))
                          }
                        />
                      </label>
                      <label className="field">
                        <span>Block threshold</span>
                        <input
                          type="number"
                          min="0.02"
                          max="0.99"
                          step="0.01"
                          value={voteForm.blockThreshold}
                          onChange={(event) =>
                            setVoteForm((prev) => ({ ...prev, blockThreshold: event.target.value }))
                          }
                        />
                      </label>
                    </div>

                    <div className="form-actions">
                      <button type="submit" className="primary-btn" disabled={submittingVote}>
                        {submittingVote ? "Voting..." : "Voter"}
                      </button>
                      <button
                        type="button"
                        className="secondary-btn"
                        onClick={() =>
                          setVoteForm((prev) => ({
                            ...prev,
                            riskWeights: draftWeights.map((value) => value.toFixed(2)) as [
                              string,
                              string,
                              string,
                            ],
                          }))
                        }
                      >
                        Normaliser
                      </button>
                      <span className="form-feedback">
                        {voteStatus ||
                          `Maj ${hogonat?.updated_at?.slice(11, 19) ?? "n/a"} · ${
                            hogonat?.mock_mode ? "mock mode" : "live mode"
                          }`}
                      </span>
                    </div>
                  </form>
                </div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Ecosysteme Agents</div>
                  <div className="panel-caption">Les danseurs actifs autour de Sigui</div>
                </div>
              </div>
              <div className="panel-body agents-stack">
                {Object.entries(agents).length === 0 && (
                  <div className="empty-note">Aucun agent actif pour le moment.</div>
                )}
                {Object.entries(agents).map(([agentId, info]) => (
                  <div key={agentId} className="agent-row">
                    <div>
                      <div className="agent-title">
                        <span>{AGENT_LABELS[agentId]?.icon ?? "•"}</span>
                        {AGENT_LABELS[agentId]?.title ?? agentId}
                      </div>
                      <div className="agent-sub">{agentId}</div>
                    </div>
                    <div className="agent-meta">
                      <span className={`agent-state state-${info.status?.toLowerCase().replace(/[^a-z]/g, "-")}`}>
                        {info.status}
                      </span>
                      <span>{info.transactions ?? 0} tx</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="panel feed-panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">Live Decisions</div>
                <div className="panel-caption">ALLOW · BLOCK · ESCALATE et logs onchain</div>
              </div>
              <div className="panel-badges">
                {patterns.slice(0, 3).map((pattern) => (
                  <span key={pattern.pattern_id} className="meta-pill">
                    {pattern.pattern_id}
                  </span>
                ))}
              </div>
            </div>

            <div className="table-wrap">
              <table className="feed-table">
                <thead>
                  <tr>
                    <th>Action Hash</th>
                    <th>Agent</th>
                    <th>Action</th>
                    <th>Amount</th>
                    <th>Decision</th>
                    <th>Risk</th>
                    <th>Chain Log</th>
                    <th>Latency</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {feed.length === 0 ? (
                    <tr>
                      <td colSpan={9} className="empty-cell">
                        En attente des premieres decisions live...
                      </td>
                    </tr>
                  ) : (
                    feed.map((item) => <FeedRow key={item.id} item={item} />)
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="dashboard-grid ops-grid">
            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Ops & Business Value</div>
                  <div className="panel-caption">Metriques de performance economique</div>
                </div>
              </div>
              <div className="panel-body">
                <div className="metric-card panel">
                  <div className="metric-label">Total Value Secured (TVS)</div>
                  <div className="metric-value" style={{ color: "var(--sigui)" }}>
                    {formatMoney(protectedUsdc, 2)}
                  </div>
                  <div className="metric-detail">USDC proteges contre les attaques</div>
                </div>
                <div className="metric-card panel" style={{ marginTop: "1rem" }}>
                  <div className="metric-label">Security Protocol Cost</div>
                  <div className="metric-value" style={{ color: "var(--red)" }}>
                    {formatMoney(totalSpent, 4)}
                  </div>
                  <div className="metric-detail">Cout des evaluations (LLM, vision, onchain)</div>
                </div>
                <div className="metric-card panel" style={{ marginTop: "1rem" }}>
                  <div className="metric-label">Return on Security Investment</div>
                  <div className="metric-value" style={{ color: "var(--gold)" }}>
                    {roi}x
                  </div>
                  <div className="metric-detail">Ratio valeur protegee / cout securite</div>
                </div>
                <div className="metric-card panel" style={{ marginTop: "1rem" }}>
                  <div className="metric-label">Hogonat DAO Treasury</div>
                  <div className="metric-value" style={{ color: "var(--cyan)" }}>
                    {formatMoney(hogonat?.fee_pool_usdc ?? 0, 4)}
                  </div>
                  <div className="metric-detail">Fonds collectes par la DAO</div>
                </div>
              </div>
            </div>

            <div className="panel">
              <div className="panel-header">
                <div>
                  <div className="panel-title">Hogonat DAO Journal</div>
                  <div className="panel-caption">Historique exploitable des actions de gouvernance</div>
                </div>
              </div>
              <div className="table-wrap">
                <table className="feed-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Staker ID</th>
                      <th>Montant</th>
                      <th>Details</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hogonatHistory.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="empty-cell">
                          Aucune action DAO recente...
                        </td>
                      </tr>
                    ) : (
                      hogonatHistory.map((item) => (
                        <tr key={item.id}>
                          <td>
                            <span className={`decision-pill decision-${item.action_type.toLowerCase() === 'stake' ? 'allow' : 'escalate'}`}>
                              {item.action_type}
                            </span>
                          </td>
                          <td>{AGENT_LABELS[item.staker_id]?.title ?? item.staker_id}</td>
                          <td>{item.amount_usdc > 0 ? formatMoney(item.amount_usdc, 2) : "—"}</td>
                          <td style={{ maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={item.details}>
                            {item.details}
                          </td>
                          <td>{item.timestamp.slice(11, 19)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </section>

        </motion.main>
      )}
    </>
  );
}
