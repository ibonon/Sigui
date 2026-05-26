import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";

export function ScientificMetrics() {
  const [stats, setStats] = useState({
    spectralRadius: 0.85,
    entropy: 4.2,
    variance: 0.12,
    avgWatts: 450,
    eta: 0.92
  });

  useEffect(() => {
    // Simuler des fluctuations scientifiques légères basées sur la charge
    const interval = setInterval(() => {
      setStats(prev => ({
        spectralRadius: Math.max(0.1, Math.min(1.0, prev.spectralRadius + (Math.random() - 0.5) * 0.05)),
        entropy: Math.max(1, prev.entropy + (Math.random() - 0.5) * 0.2),
        variance: Math.max(0, prev.variance + (Math.random() - 0.5) * 0.02),
        avgWatts: Math.max(100, prev.avgWatts + (Math.random() - 0.5) * 10),
        eta: Math.max(0.5, Math.min(1.0, prev.eta + (Math.random() - 0.5) * 0.01))
      }));
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const varianceColor = stats.variance > 0.2 ? 'text-danger' : stats.variance > 0.1 ? 'text-gold' : 'text-success';

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <div className="panel p-4 border-t-2 border-[#10b981]">
        <div className="text-xs text-muted font-mono mb-1">Spectral Radius</div>
        <div className="text-2xl font-bold text-white">{stats.spectralRadius.toFixed(3)}</div>
        <div className="text-[10px] text-dim">Convergence boundary</div>
      </div>
      
      <div className="panel p-4 border-t-2 border-[#0ea5e9]">
        <div className="text-xs text-muted font-mono mb-1">Network Entropy</div>
        <div className="text-2xl font-bold text-white">{stats.entropy.toFixed(2)} nats</div>
        <div className="text-[10px] text-dim">Information distribution</div>
      </div>
      
      <div className="panel p-4 border-t-2 border-[#ef4444]">
        <div className="text-xs text-muted font-mono mb-1">Variance Alert</div>
        <div className={`text-2xl font-bold ${varianceColor}`}>{stats.variance.toFixed(3)}</div>
        <div className="text-[10px] text-dim">Informational collapse risk</div>
      </div>

      <div className="panel p-4 border-t-2 border-[#f6c90e]">
        <div className="text-xs text-muted font-mono mb-1">Energy Average</div>
        <div className="text-2xl font-bold text-white">{Math.round(stats.avgWatts)} W</div>
        <div className="text-[10px] text-dim">Local consumption</div>
      </div>

      <div className="panel p-4 border-t-2 border-[#8b5cf6]">
        <div className="text-xs text-muted font-mono mb-1">Efficiency (η)</div>
        <div className="text-2xl font-bold text-white">{stats.eta.toFixed(3)}</div>
        <div className="text-[10px] text-dim">TKN / Watt coefficient</div>
      </div>
    </div>
  );
}
