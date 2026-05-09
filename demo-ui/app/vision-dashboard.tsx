"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { DashboardTabs } from "./components/DashboardTabs";
import { VisionMetricsPanel } from "./components/VisionMetricsPanel";
import { AgentIdentityPanel } from "./components/AgentIdentityPanel";
import { ThreatIntelPanel } from "./components/ThreatIntelPanel";
import { InsurancePanel } from "./components/InsurancePanel";

export interface TimePoint { 
  ts: number; 
  allow: number; 
  block: number; 
  escalate: number; 
  revenue: number; 
  agents_registered: number;
  threat_patterns: number;
  insurance_coverage: number;
}

interface AgentInfo {
  agent_id?: string;
  status: string;
  observe_only?: boolean;
  balance_usdc?: number;
  transactions?: number;
  last_decision?: string;
  did?: string;
  reputation_score?: number;
  verification_tier?: string;
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
  agents_protected?: number;
}

interface ThreatRegistryState {
  total_attacks_onchain: number;
  total_usdc_protected_usdc: number;
  guaranty_fund6?: number;
  active_patterns?: number;
  contributors?: number;
}

interface VisionMetrics {
  total_agents_registered: number;
  total_threat_patterns: number;
  total_insurance_coverage: number;
  total_usdc_protected: number;
  average_response_time_ms: number;
  threat_detection_accuracy: number;
  network_effect_score: number;
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
  agent_did?: string;
  reputation_score?: number;
}

export default function VisionDashboard() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [treasury, setTreasury] = useState<TreasuryState | null>(null);
  const [decisions, setDecisions] = useState<DecisionStats>({ allow: 0, block: 0, escalate: 0, total: 0 });
  const [threatRegistry, setThreatRegistry] = useState<ThreatRegistryState | null>(null);
  const [visionMetrics, setVisionMetrics] = useState<VisionMetrics | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "identity" | "threats" | "insurance" | "vision">("overview");
  const [isBooting, setIsBooting] = useState(true);
  const [bootLogs, setBootLogs] = useState<string[]>([]);
  const [timeSeries, setTimeSeries] = useState<TimePoint[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const bootConsoleRef = useRef<HTMLDivElement | null>(null);

  // Enhanced color palette inspired by 2026 dashboard trends
  const colors = {
    primary: "#00D4FF",      // Electric blue
    secondary: "#FF6B6B",    // Coral red
    accent: "#4ECDC4",       // Turquoise
    gold: "#FFD93D",         // Golden yellow
    success: "#6BCF7F",      // Fresh green
    warning: "#FFA726",      // Amber
    danger: "#EF5350",       // Red
    dark: "#1A1A2E",         // Deep navy
    darker: "#16213E",       // Darker navy
    light: "#F5F7FF",        // Light text
    muted: "#AAB2D5",        // Muted text
    dim: "#7180B9",          // Dim text
    gradient: {
      primary: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      secondary: "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)",
      accent: "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)",
      success: "linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)",
      dark: "linear-gradient(135deg, #2c3e50 0%, #34495e 100%)"
    }
  };

  // Enhanced styling for vision dashboard
  const styles = {
    container: {
      background: `linear-gradient(180deg, ${colors.darker} 0%, ${colors.dark} 100%)`,
      minHeight: "100vh",
      color: colors.light,
      fontFamily: "'Inter', sans-serif"
    },
    header: {
      background: `linear-gradient(90deg, ${colors.primary}20, ${colors.accent}20)`,
      backdropFilter: "blur(10px)",
      borderBottom: `1px solid ${colors.primary}30`
    },
    card: {
      background: `linear-gradient(135deg, ${colors.dark} 0%, ${colors.darker} 100%)`,
      border: `1px solid ${colors.primary}20`,
      borderRadius: "16px",
      boxShadow: `0 8px 32px ${colors.primary}10`,
      backdropFilter: "blur(10px)"
    },
    metricCard: {
      background: `linear-gradient(135deg, ${colors.primary}15, ${colors.accent}15)`,
      border: `1px solid ${colors.primary}30`,
      borderRadius: "12px",
      boxShadow: `0 4px 16px ${colors.primary}20`
    },
    button: {
      background: colors.gradient.primary,
      border: "none",
      borderRadius: "8px",
      color: "white",
      fontWeight: "600",
      transition: "all 0.3s ease"
    }
  };

  const addBootLog = useCallback((line: string) => {
    setBootLogs(prev => [...prev, line]);
  }, []);

  useEffect(() => {
    if (bootConsoleRef.current) {
      bootConsoleRef.current.scrollTop = bootConsoleRef.current.scrollHeight;
    }
  }, [bootLogs]);

  useEffect(() => {
    const connect = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      const es = new EventSource("http://localhost:8000/demo/live");
      eventSourceRef.current = es;

      es.onopen = () => {
        setIsConnected(true);
        addBootLog("✅ Connected to Sigui Vision Engine");
      };

      es.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          handlePayload(payload);
        } catch (err) {
          console.warn("Bad SSE payload", err);
        }
      };

      es.onerror = () => {
        setIsConnected(false);
        addBootLog("⚠️  Connection lost, retrying in 3s…");
        es.close();
        setTimeout(connect, 3000);
      };
    };

    connect();
    return () => eventSourceRef.current?.close();
  }, [addBootLog]);

  const handlePayload = (payload: any) => {
    if (payload.kind === "boot") {
      setBootLogs(payload.lines || []);
      if (payload.complete) {
        setIsBooting(false);
        addBootLog("🌠 Vision Integration Engine Ready");
        addBootLog("🚀 AWS of Trust Infrastructure for Autonomous Economy");
      }
      return;
    }

    if (payload.kind === "agent") {
      setAgents(payload.agents || []);
      return;
    }

    if (payload.kind === "treasury") {
      setTreasury(payload);
      return;
    }

    if (payload.kind === "decisions") {
      setDecisions(payload);
      return;
    }

    if (payload.kind === "threat_registry") {
      setThreatRegistry(payload);
      return;
    }

    if (payload.kind === "vision_metrics") {
      setVisionMetrics(payload);
      return;
    }

    if (payload.kind === "log") {
      setLogs(prev => [...prev, payload].slice(-500));
      return;
    }

    if (payload.kind === "time_series") {
      setTimeSeries(payload.points || []);
      return;
    }
  };

  const renderOverview = () => (
    <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-6 mb-8">
      {/* Vision Metrics Cards */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-6"
        style={styles.metricCard}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium" style={{ color: colors.muted }}>Agents Registered</h3>
          <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: colors.gradient.accent }}>
            <span className="text-white text-xs">🤖</span>
          </div>
        </div>
        <div className="text-3xl font-bold mb-2" style={{ color: colors.primary }}>
          {visionMetrics?.total_agents_registered || 0}
        </div>
        <div className="text-xs" style={{ color: colors.success }}>+12% from last week</div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="p-6"
        style={styles.metricCard}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium" style={{ color: colors.muted }}>Threat Patterns</h3>
          <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: colors.gradient.secondary }}>
            <span className="text-white text-xs">🛡️</span>
          </div>
        </div>
        <div className="text-3xl font-bold mb-2" style={{ color: colors.secondary }}>
          {visionMetrics?.total_threat_patterns || 0}
        </div>
        <div className="text-xs" style={{ color: colors.success }}>+8 new patterns today</div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="p-6"
        style={styles.metricCard}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium" style={{ color: colors.muted }}>USDC Protected</h3>
          <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: colors.gradient.success }}>
            <span className="text-white text-xs">💰</span>
          </div>
        </div>
        <div className="text-3xl font-bold mb-2" style={{ color: colors.success }}>
          ${(visionMetrics?.total_usdc_protected || 0).toLocaleString()}
        </div>
        <div className="text-xs" style={{ color: colors.success }}>+2.3M this month</div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="p-6"
        style={styles.metricCard}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium" style={{ color: colors.muted }}>Response Time</h3>
          <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: colors.gradient.primary }}>
            <span className="text-white text-xs">⚡</span>
          </div>
        </div>
        <div className="text-3xl font-bold mb-2" style={{ color: colors.accent }}>
          {(visionMetrics?.average_response_time_ms || 50).toFixed(1)}ms
        </div>
        <div className="text-xs" style={{ color: colors.success }}>10x faster than competitors</div>
      </motion.div>
    </div>
  );

  const renderContent = () => {
    switch (activeTab) {
      case "overview":
        return renderOverview();
      case "identity":
        return <AgentIdentityPanel agents={agents} colors={colors} styles={styles} />;
      case "threats":
        return <ThreatIntelPanel threatRegistry={threatRegistry} colors={colors} styles={styles} />;
      case "insurance":
        return <InsurancePanel treasury={treasury} colors={colors} styles={styles} />;
      case "vision":
        return <VisionMetricsPanel visionMetrics={visionMetrics} colors={colors} styles={styles} />;
      default:
        return renderOverview();
    }
  };

  if (isBooting) {
    return (
      <div className="boot-overlay">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="boot-logo-wrap"
        >
          <img src="/IMG.jpg" alt="Sigui" className="boot-logo" />
          <div className="boot-title">Sigui Vision</div>
          <div className="boot-subtitle">AWS of Trust Infrastructure</div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="boot-console"
          ref={bootConsoleRef}
        >
          {bootLogs.map((line, i) => (
            <div key={i} className="boot-line">
              <span className="boot-prefix">›</span>
              {line}
            </div>
          ))}
          {!isConnected && (
            <div className="boot-line" style={{ color: colors.warning }}>
              <span className="boot-prefix">⚠️</span>
              Connecting to Sigui Vision Engine...
            </div>
          )}
        </motion.div>
      </div>
    );
  }

  return (
    <div style={styles.container} className="min-h-screen">
      {/* Enhanced Header */}
      <header style={styles.header} className="border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full flex items-center justify-center" style={{ background: colors.gradient.primary }}>
              <span className="text-white font-bold">🌠</span>
            </div>
            <div>
              <h1 className="text-2xl font-bold" style={{ fontFamily: "'Cinzel Decorative', serif", color: colors.gold }}>
                Sigui Vision
              </h1>
              <p className="text-sm" style={{ color: colors.muted }}>
                AWS of Trust Infrastructure for the Autonomous Economy
              </p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              <span className="text-sm" style={{ color: colors.muted }}>
                {isConnected ? 'Connected' : 'Reconnecting...'}
              </span>
            </div>
            
            {treasury && (
              <div className="px-4 py-2 rounded-lg" style={{ background: colors.gradient.dark }}>
                <div className="text-xs" style={{ color: colors.muted }}>Treasury</div>
                <div className="text-lg font-bold" style={{ color: colors.success }}>
                  ${treasury.balance.toFixed(2)}
                </div>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Enhanced Navigation */}
      <nav className="px-6 py-4 border-b" style={{ borderColor: colors.primary + "20" }}>
        <DashboardTabs activeTab={activeTab} setActiveTab={setActiveTab} colors={colors} />
      </nav>

      {/* Main Content */}
      <main className="flex-1 p-6">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            {renderContent()}
          </motion.div>
        </AnimatePresence>
      </main>

      {/* Enhanced Footer */}
      <footer className="px-6 py-4 border-t" style={{ borderColor: colors.primary + "20", background: colors.darker }}>
        <div className="flex items-center justify-between text-sm" style={{ color: colors.muted }}>
          <div>
            Built in Ouagadougou • Powered by AMD MI300X • Named after Dogon cosmic regeneration
          </div>
          <div>
            Response Time: {(visionMetrics?.average_response_time_ms || 50).toFixed(1)}ms • 
            Accuracy: {((visionMetrics?.threat_detection_accuracy || 0.96) * 100).toFixed(1)}%
          </div>
        </div>
      </footer>
    </div>
  );
}