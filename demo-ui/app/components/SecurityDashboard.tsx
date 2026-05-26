import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";

export function SecurityDashboard() {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/nexusmind/stats")
      .then((res) => res.json())
      .then((data) => setStats(data))
      .catch(console.error);
  }, []);

  return (
    <div className="security-dashboard grid gap-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="panel p-6 border-l-4 border-l-[#1d9e75]">
          <div className="text-xs text-[#aab2d5] uppercase tracking-widest mb-2 font-mono">Total Evaluations (24h)</div>
          <div className="text-3xl font-bold text-white mb-1">
            {stats ? stats.evaluations_24h.toLocaleString() : "..."}
          </div>
          <div className="text-sm text-[#1d9e75]">↑ 12.4% vs yesterday</div>
        </div>
        
        <div className="panel p-6 border-l-4 border-l-[#e24b4a]">
          <div className="text-xs text-[#aab2d5] uppercase tracking-widest mb-2 font-mono">Threats Blocked</div>
          <div className="text-3xl font-bold text-white mb-1">
            {stats ? stats.threats_blocked_24h.toLocaleString() : "..."}
          </div>
          <div className="text-sm text-[#e24b4a]">
            {stats ? `${stats.block_rate_pct}% block rate` : "..."}
          </div>
        </div>

        <div className="panel p-6 border-l-4 border-l-[#f6c90e]">
          <div className="text-xs text-[#aab2d5] uppercase tracking-widest mb-2 font-mono">USDC Protected</div>
          <div className="text-3xl font-bold text-[#f6c90e] mb-1">
            ${stats ? stats.usdc_protected_24h.toLocaleString() : "..."}
          </div>
          <div className="text-sm text-[#f6c90e]/70">
            Total: ${stats ? stats.total_usdc_protected.toLocaleString() : "..."}
          </div>
        </div>
      </div>

      <div className="panel p-0 overflow-hidden">
        <div className="panel-header">
          <div className="panel-title">Imina-Na Vision Model Status</div>
          <div className="panel-caption">Topology-based evaluation parameters</div>
        </div>
        <div className="p-6 grid grid-cols-2 md:grid-cols-4 gap-4 bg-[#0a0c21]/50">
          <div>
            <div className="text-xs text-[#aab2d5] mb-1">Active Version</div>
            <div className="text-white font-mono">{stats?.imina_na_status?.model || "..."}</div>
          </div>
          <div>
            <div className="text-xs text-[#aab2d5] mb-1">F1 Accuracy Score</div>
            <div className="text-[#1d9e75] font-mono">{stats?.imina_na_status?.f1_score || "..."}%</div>
          </div>
          <div>
            <div className="text-xs text-[#aab2d5] mb-1">Avg Inference Latency</div>
            <div className="text-[#8b5cf6] font-mono">{stats?.imina_na_status?.avg_latency_ms || "..."} ms</div>
          </div>
          <div>
            <div className="text-xs text-[#aab2d5] mb-1">Nodes with Vision (GPU)</div>
            <div className="text-[#73a7ff] font-mono">{stats?.imina_na_status?.nodes_with_gpu || "..."} online</div>
          </div>
        </div>
      </div>
    </div>
  );
}
