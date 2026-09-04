"use client";

import React, { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface VisionInferenceEvent {
  pattern: string;
  confidence: number;
  inference_source: 'gpu_imina_na' | 'heuristic_fallback' | 'disabled';
  inference_time_ms: number;
  model: string;
  timestamp?: number;
}

export interface VisionMetricsPanelProps {
  visionInferences?: VisionInferenceEvent[];
  visionMetrics?: any;
  colors?: any;
  styles?: any;
}

const panelStyle: React.CSSProperties = {
  background: 'rgba(17, 24, 39, 0.65)',
  backdropFilter: 'blur(24px)',
  border: '1px solid rgba(148, 163, 184, 0.1)',
  borderRadius: '16px',
  padding: '24px',
  color: '#fff',
  fontFamily: '"Inter", sans-serif',
  display: 'flex',
  flexDirection: 'column',
  gap: '24px',
  overflow: 'hidden',
};

const sectionStyle: React.CSSProperties = {
  background: 'rgba(255, 255, 255, 0.03)',
  borderRadius: '12px',
  padding: '16px',
  border: '1px solid rgba(148, 163, 184, 0.05)',
};

const fontMono = '"JetBrains Mono", monospace';

const getPatternColor = (pattern: string) => {
  if (pattern.includes('DRAIN_STAR')) return 'var(--rose)';
  if (pattern.includes('MIXING_CHAIN')) return 'var(--amber)';
  if (pattern.includes('COORDINATED_CLUSTER')) return 'var(--violet)';
  return 'var(--emerald)';
};

const getLatencyColor = (ms: number) => {
  if (ms < 50) return 'var(--emerald)';
  if (ms <= 150) return 'var(--amber)';
  return 'var(--rose)';
};

export function VisionMetricsPanel({
  visionInferences = [],
  visionMetrics,
  colors,
  styles
}: VisionMetricsPanelProps) {
  
  const stats = useMemo(() => {
    let gpu = 0;
    let heuristic = 0;
    visionInferences.forEach(ev => {
      if (ev.inference_source === 'gpu_imina_na') gpu++;
      else if (ev.inference_source === 'heuristic_fallback') heuristic++;
    });
    const total = gpu + heuristic;
    const gpuPercent = total === 0 ? 0 : (gpu / total) * 100;
    
    const lastSource = visionInferences.length > 0 ? visionInferences[visionInferences.length - 1].inference_source : null;
    const isGpuActive = lastSource === 'gpu_imina_na';

    return { gpu, heuristic, total, gpuPercent, isGpuActive, lastSource };
  }, [visionInferences]);

  const histogramData = useMemo(() => {
    return visionInferences.slice(-20);
  }, [visionInferences]);

  const feedData = useMemo(() => {
    return visionInferences.slice(-10).reverse();
  }, [visionInferences]);

  return (
    <div style={panelStyle}>
      {/* Top section — GPU vs Heuristic Live Indicator */}
      <div style={{ ...sectionStyle, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 600 }}>Vision Engine Status</h3>
            {stats.isGpuActive ? (
              <span style={{ 
                background: 'rgba(16, 185, 129, 0.1)', 
                color: 'var(--emerald)', 
                padding: '4px 10px', 
                borderRadius: '999px',
                fontSize: '12px',
                fontWeight: 600,
                border: '1px solid rgba(16, 185, 129, 0.2)',
                boxShadow: '0 0 10px rgba(16, 185, 129, 0.2)'
              }}>🔥 AMD MI300X LIVE</span>
            ) : (
              <span style={{ 
                background: 'rgba(245, 158, 11, 0.1)', 
                color: 'var(--amber)', 
                padding: '4px 10px', 
                borderRadius: '999px',
                fontSize: '12px',
                fontWeight: 600,
                border: '1px solid rgba(245, 158, 11, 0.2)'
              }}>⚡ Heuristic Mode</span>
            )}
          </div>
          <div style={{ fontFamily: fontMono, fontSize: '14px', color: '#94a3b8' }}>
            {stats.gpu} GPU / {stats.heuristic} Heuristic
          </div>
        </div>

        <div style={{ position: 'relative', width: '64px', height: '64px' }}>
          <svg width="64" height="64" viewBox="0 0 64 64">
            <circle cx="32" cy="32" r="28" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" />
            <motion.circle 
              cx="32" cy="32" r="28" 
              fill="none" 
              stroke={stats.isGpuActive ? 'var(--emerald)' : 'var(--amber)'} 
              strokeWidth="8"
              strokeDasharray="175.93"
              initial={{ strokeDashoffset: 175.93 }}
              animate={{ strokeDashoffset: 175.93 - (175.93 * (stats.gpuPercent || 0)) / 100 }}
              transition={{ duration: 0.5 }}
              strokeLinecap="round"
              style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
            />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 'bold', fontFamily: fontMono }}>
            {Math.round(stats.gpuPercent || 0)}%
          </div>
        </div>
      </div>

      {/* Latency Histogram */}
      <div style={sectionStyle}>
        <div style={{ marginBottom: '16px', fontSize: '14px', fontWeight: 600, color: '#e2e8f0' }}>Imina Na V2 — Inference Latency</div>
        <div style={{ height: '120px', display: 'flex', alignItems: 'flex-end', gap: '4px' }}>
          {histogramData.length === 0 ? (
             <div style={{ width: '100%', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>Awaiting data...</div>
          ) : (
            histogramData.map((ev, i) => {
              const maxLatency = Math.max(200, ...histogramData.map(d => d.inference_time_ms));
              const heightPct = Math.min(100, (ev.inference_time_ms / maxLatency) * 100);
              return (
                <motion.div
                  key={`${ev.timestamp}-${i}`}
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: `${heightPct}%`, opacity: 1 }}
                  style={{
                    flex: 1,
                    background: getLatencyColor(ev.inference_time_ms),
                    borderRadius: '4px 4px 0 0',
                    minHeight: '4px'
                  }}
                  title={`${ev.inference_time_ms.toFixed(1)} ms`}
                />
              )
            })
          )}
        </div>
      </div>

      {/* Live Inference Feed */}
      <div style={{ ...sectionStyle, flex: 1, minHeight: '250px' }}>
        <div style={{ marginBottom: '16px', fontSize: '14px', fontWeight: 600, color: '#e2e8f0' }}>Live Inference Feed</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <AnimatePresence>
            {feedData.length === 0 ? (
              <motion.div 
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                style={{ textAlign: 'center', color: '#64748b', padding: '20px 0', fontSize: '13px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}
              >
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--cyan)' }} />
                Awaiting Imina Na inferences…
              </motion.div>
            ) : (
              feedData.map((ev, i) => (
                <motion.div
                  key={`${ev.timestamp}-${ev.pattern}-${i}`}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2 }}
                  style={{ 
                    display: 'flex', alignItems: 'center', gap: '12px', padding: '8px 12px', 
                    background: 'rgba(0,0,0,0.2)', borderRadius: '8px', fontSize: '12px' 
                  }}
                >
                  <span style={{ color: getPatternColor(ev.pattern), fontWeight: 'bold', width: '130px', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                    {ev.pattern}
                  </span>
                  <span style={{ 
                    padding: '2px 6px', borderRadius: '4px', fontSize: '10px', 
                    background: ev.inference_source === 'gpu_imina_na' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(245, 158, 11, 0.1)',
                    color: ev.inference_source === 'gpu_imina_na' ? 'var(--emerald)' : 'var(--amber)'
                  }}>
                    {ev.inference_source === 'gpu_imina_na' ? 'GPU' : 'HEU'}
                  </span>
                  <span style={{ fontFamily: fontMono, color: '#cbd5e1' }}>{(ev.confidence * 100).toFixed(1)}%</span>
                  <span style={{ fontFamily: fontMono, color: getLatencyColor(ev.inference_time_ms), marginLeft: 'auto' }}>
                    {ev.inference_time_ms.toFixed(1)}ms
                  </span>
                  <span style={{ color: '#64748b', maxWidth: '60px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={ev.model}>
                    {ev.model}
                  </span>
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Benchmark section */}
      <div style={{ ...sectionStyle, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: '13px', color: '#94a3b8', marginBottom: '4px' }}>Hardware Benchmark</div>
          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--cyan)' }}>AMD MI300X</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '18px', fontWeight: 'bold', fontFamily: fontMono, color: '#fff' }}>35.3<span style={{ fontSize: '14px', color: '#94a3b8' }}>ms</span></div>
          <div style={{ fontSize: '12px', color: 'var(--emerald)' }}>Avg Latency</div>
        </div>
      </div>

      {/* ZK-Sigui Status Card */}
      <div style={{ ...sectionStyle, display: 'flex', gap: '16px', alignItems: 'center' }}>
        <div style={{ width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="40" height="40" viewBox="0 0 40 40">
            <motion.path 
              d="M20 2 L38 12 L38 28 L20 38 L2 28 L2 12 Z" 
              fill="rgba(139, 92, 246, 0.1)" 
              stroke="var(--violet)" 
              strokeWidth="2"
              animate={{ rotate: 360 }}
              transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
              style={{ transformOrigin: "50% 50%" }}
            />
            <circle cx="20" cy="20" r="4" fill="var(--violet)" />
          </svg>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--violet)' }}>🔐 ZK-Sigui PoC Active — Circuit v1</div>
            <span style={{ fontSize: '10px', background: 'rgba(139, 92, 246, 0.15)', color: 'var(--violet)', padding: '2px 6px', borderRadius: '4px' }}>
              Circom/Noir Q4 2026
            </span>
          </div>
          <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#94a3b8', fontFamily: fontMono }}>
            <span>Size: 64 bytes per proof</span>
            <span>Status: Groth16-style simulation (BN128)</span>
          </div>
        </div>
      </div>

    </div>
  );
}

export default VisionMetricsPanel;