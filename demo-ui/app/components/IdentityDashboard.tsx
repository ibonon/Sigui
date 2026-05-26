import React, { useState, useEffect } from "react";
import { Sparklines, SparklinesLine, SparklinesSpots } from 'react-sparklines';

export function IdentityDashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/nexusmind/identity/node_001")
      .then((res) => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data) return <div className="p-4 text-muted">Loading Identity...</div>;

  const sparklineData = data.history ? data.history.map((h: any) => h.score) : [];

  return (
    <div className="identity-dashboard grid gap-6">
      <div className="panel p-6">
        <div className="flex justify-between items-start mb-8">
          <div>
            <div className="text-sm text-[#aab2d5] uppercase tracking-widest mb-1">ERC-8259 Identity</div>
            <div className="text-2xl font-mono text-white flex items-center gap-3">
              {data.did}
              <button className="text-[#aab2d5] hover:text-white transition" title="Copy DID">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              </button>
            </div>
          </div>
          <div className="flex gap-2">
            <span className={`px-4 py-1 rounded-full text-xs font-bold uppercase ${
              data.verification_tier === 'SILVER' 
                ? 'bg-[#aab2d5]/20 text-[#aab2d5] border border-[#aab2d5]/30'
                : 'bg-[#b87333]/20 text-[#b87333] border border-[#b87333]/30'
            }`}>
              {data.verification_tier} TIER
            </span>
            <span className="px-4 py-1 rounded-full bg-[#1d9e75]/20 text-[#1d9e75] border border-[#1d9e75]/30 text-xs font-bold">
              VERIFIED
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div className="bg-[#0a0c21] rounded-xl p-5 border border-[#1a1d42]">
            <div className="text-sm text-[#aab2d5] mb-2">Reputation Score</div>
            <div className="flex items-end gap-3 mb-2">
              <span className="text-5xl font-mono text-white">{data.reputation.score}</span>
              <span className="text-xl text-[#7180b9] mb-1">/ {data.reputation.max}</span>
            </div>
            <div className="w-full h-2 bg-[#1a1d42] rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-[#e24b4a] via-[#f6c90e] to-[#1d9e75]"
                style={{ width: `${(data.reputation.score / data.reputation.max) * 100}%` }}
              ></div>
            </div>
            <div className="mt-3 text-xs text-[#aab2d5] flex justify-between">
              <span>Confidence Level:</span>
              <span className={
                data.reputation.confidence === 'HIGH' ? 'text-[#1d9e75]' : 
                data.reputation.confidence === 'MEDIUM' ? 'text-[#f6c90e]' : 'text-[#e24b4a]'
              }>{data.reputation.confidence}</span>
            </div>
          </div>

          <div className="md:col-span-2 bg-[#0a0c21] rounded-xl p-5 border border-[#1a1d42]">
            <div className="text-sm text-[#aab2d5] mb-2">Reputation History (30d)</div>
            <div className="h-24 w-full">
              {sparklineData.length > 0 && (
                <Sparklines data={sparklineData} width={300} height={60} margin={5}>
                  <SparklinesLine color="#f6c90e" style={{ fill: "none", strokeWidth: 3 }} />
                  <SparklinesSpots style={{ fill: "#f6c90e" }} />
                </Sparklines>
              )}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 border border-[#1a1d42] rounded-lg">
            <div className="text-xs text-[#7180b9] mb-1">Accuracy</div>
            <div className="text-xl text-white font-mono">{data.breakdown.evaluations_accuracy_pct}%</div>
          </div>
          <div className="p-4 border border-[#1a1d42] rounded-lg">
            <div className="text-xs text-[#7180b9] mb-1">Uptime (30d)</div>
            <div className="text-xl text-white font-mono">{data.breakdown.uptime_30d_pct}%</div>
          </div>
          <div className="p-4 border border-[#1a1d42] rounded-lg">
            <div className="text-xs text-[#7180b9] mb-1">False Positives</div>
            <div className="text-xl text-white font-mono">{data.breakdown.false_positive_rate_pct}%</div>
          </div>
          <div className="p-4 border border-[#1a1d42] rounded-lg">
            <div className="text-xs text-[#7180b9] mb-1">Staked Collateral</div>
            <div className="text-xl text-white font-mono">{data.breakdown.stake_collateral_tkn} TKN</div>
          </div>
        </div>
      </div>
    </div>
  );
}
