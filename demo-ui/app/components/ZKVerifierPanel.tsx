'use client';

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export interface ZKVerifierPanelProps {
  colors?: any;
  styles?: any;
}

export const ZKVerifierPanel: React.FC<ZKVerifierPanelProps> = () => {
  const [pattern, setPattern] = useState<'NORMAL' | 'MIXING_CHAIN' | 'DRAIN_STAR'>('NORMAL');
  const [peerCount, setPeerCount] = useState<number>(4);
  const [chainCount, setChainCount] = useState<number>(2);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [proofResult, setProofResult] = useState<{
    commitment: string;
    proof_a: string;
    proof_b: string;
    is_benign: boolean;
    verify_ms: number;
    proof_size_bytes: number;
  } | null>(null);

  const handleGenerateProof = async () => {
    setIsGenerating(true);
    setProofResult(null);

    // Simulate ZK Witness & Proof Generation over BN128 Scalar Field
    setTimeout(() => {
      const isBenign = pattern !== 'DRAIN_STAR';
      const commitment = Array.from({ length: 16 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join('');
      const proofA = '0x' + Array.from({ length: 32 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join('');
      const proofB = '0x' + Array.from({ length: 32 }, () =>
        Math.floor(Math.random() * 16).toString(16)
      ).join('');

      setProofResult({
        commitment,
        proof_a: proofA,
        proof_b: proofB,
        is_benign: isBenign,
        verify_ms: parseFloat((Math.random() * 0.005 + 0.001).toFixed(4)),
        proof_size_bytes: 64,
      });
      setIsGenerating(false);
    }, 600);
  };

  return (
    <div
      style={{
        background: 'rgba(17, 24, 39, 0.65)',
        backdropFilter: 'blur(24px)',
        border: '1px solid rgba(148, 163, 184, 0.12)',
        borderRadius: '16px',
        padding: '24px',
        color: '#f8fafc',
        fontFamily: "'Inter', sans-serif",
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '20px' }}>🔐</span>
            <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, letterSpacing: '-0.02em', color: '#f8fafc' }}>
              ZK-Sigui Zero-Knowledge Proof Engine
            </h3>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#94a3b8' }}>
            Groth16 SNARK simulation over BN128 scalar field — 64-byte proofs for benign transaction topologies
          </p>
        </div>
        <span
          style={{
            background: 'rgba(139, 92, 246, 0.15)',
            border: '1px solid rgba(139, 92, 246, 0.3)',
            color: '#a78bfa',
            fontSize: '11px',
            fontWeight: 600,
            padding: '4px 10px',
            borderRadius: '20px',
          }}
        >
          BN128 Curve • 64 Bytes
        </span>
      </div>

      {/* Controls Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '20px' }}>
        {/* Pattern Selection */}
        <div>
          <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
            Transaction Topology Pattern
          </label>
          <select
            value={pattern}
            onChange={(e) => setPattern(e.target.value as any)}
            style={{
              width: '100%',
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid rgba(148, 163, 184, 0.2)',
              borderRadius: '8px',
              padding: '10px 12px',
              color: '#f8fafc',
              fontSize: '13px',
              outline: 'none',
            }}
          >
            <option value="NORMAL">NORMAL (Benign Transfer)</option>
            <option value="MIXING_CHAIN">MIXING_CHAIN (Multi-hop Relay)</option>
            <option value="DRAIN_STAR">DRAIN_STAR (Malicious Drain)</option>
          </select>
        </div>

        {/* Peer Count */}
        <div>
          <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
            Peer Nodes Count: <strong style={{ color: '#0ea5e9' }}>{peerCount}</strong>
          </label>
          <input
            type="range"
            min={1}
            max={20}
            value={peerCount}
            onChange={(e) => setPeerCount(parseInt(e.target.value))}
            style={{ width: '100%', accentColor: '#0ea5e9' }}
          />
        </div>

        {/* Chain Count */}
        <div>
          <label style={{ display: 'block', fontSize: '12px', color: '#94a3b8', marginBottom: '6px' }}>
            Interacted Chains: <strong style={{ color: '#8b5cf6' }}>{chainCount}</strong>
          </label>
          <input
            type="range"
            min={1}
            max={8}
            value={chainCount}
            onChange={(e) => setChainCount(parseInt(e.target.value))}
            style={{ width: '100%', accentColor: '#8b5cf6' }}
          />
        </div>
      </div>

      {/* Action Button */}
      <button
        onClick={handleGenerateProof}
        disabled={isGenerating}
        style={{
          width: '100%',
          background: isGenerating
            ? 'rgba(148, 163, 184, 0.2)'
            : 'linear-gradient(135deg, #0ea5e9 0%, #8b5cf6 100%)',
          border: 'none',
          borderRadius: '10px',
          padding: '12px 20px',
          color: '#ffffff',
          fontWeight: 600,
          fontSize: '14px',
          cursor: isGenerating ? 'not-allowed' : 'pointer',
          boxShadow: isGenerating ? 'none' : '0 4px 14px rgba(14, 165, 233, 0.35)',
          transition: 'all 0.2s ease',
        }}
      >
        {isGenerating ? '⚡ Computing Groth16 SNARK Witness…' : '🔐 Generate & Verify ZK-Proof'}
      </button>

      {/* Results Display */}
      <AnimatePresence>
        {proofResult && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            style={{
              marginTop: '20px',
              padding: '16px',
              borderRadius: '12px',
              background: proofResult.is_benign ? 'rgba(16, 185, 129, 0.08)' : 'rgba(244, 63, 94, 0.08)',
              border: `1px solid ${proofResult.is_benign ? 'rgba(16, 185, 129, 0.3)' : 'rgba(244, 63, 94, 0.3)'}`,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '18px' }}>{proofResult.is_benign ? '✅' : '🚨'}</span>
                <span
                  style={{
                    fontWeight: 700,
                    fontSize: '14px',
                    color: proofResult.is_benign ? '#10b981' : '#f43f5e',
                  }}
                >
                  {proofResult.is_benign ? 'ZK-PROOF VERIFIED (BENIGN)' : 'ZK-PROOF REJECTED (MALICIOUS TOPOLOGY)'}
                </span>
              </div>
              <span style={{ fontSize: '12px', fontFamily: 'JetBrains Mono, monospace', color: '#94a3b8' }}>
                Verify time: {proofResult.verify_ms} ms
              </span>
            </div>

            {/* Proof Data Hex Grid */}
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '11px',
                background: 'rgba(15, 23, 42, 0.6)',
                padding: '12px',
                borderRadius: '8px',
                color: '#cbd5e1',
                lineHeight: 1.6,
              }}
            >
              <div><strong style={{ color: '#0ea5e9' }}>Commitment:</strong> {proofResult.commitment}...</div>
              <div><strong style={{ color: '#8b5cf6' }}>Proof_A (32B):</strong> {proofResult.proof_a}</div>
              <div><strong style={{ color: '#8b5cf6' }}>Proof_B (32B):</strong> {proofResult.proof_b}</div>
              <div style={{ marginTop: '4px', color: '#64748b' }}>
                Circuit: zk-sigui-poc-v1 | Scalar Prime: BN128 Field | Size: {proofResult.proof_size_bytes} Bytes
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
