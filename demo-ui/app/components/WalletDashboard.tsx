import React, { useState, useEffect } from "react";

export function WalletDashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/nexusmind/wallet/balance?node_id=node_001")
      .then((res) => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data) return <div className="p-4 text-muted">Loading Wallet...</div>;

  return (
    <div className="wallet-dashboard grid gap-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="panel p-6 bg-gradient-to-br from-[#101439] to-[#0a0c21] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-6 opacity-10">
            <span className="text-8xl font-black">USDC</span>
          </div>
          <div className="relative z-10">
            <div className="text-sm text-[#aab2d5] uppercase tracking-widest mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#1d9e75]"></span>
              Sigui Oracle Earnings (USDC)
            </div>
            <div className="text-5xl font-mono text-white mb-6">
              ${data.usdc.balance.toFixed(4)}
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-[#7180b9] mb-1">Earned Today</div>
                <div className="text-sm text-[#1d9e75] font-mono">+${data.usdc.earned_today.toFixed(4)}</div>
              </div>
              <div>
                <div className="text-xs text-[#7180b9] mb-1">Earned 7d</div>
                <div className="text-sm text-[#f6c90e] font-mono">+${data.usdc.earned_7d.toFixed(4)}</div>
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button className="flex-1 py-2 bg-[#f6c90e]/10 text-[#f6c90e] border border-[#f6c90e]/30 rounded-lg hover:bg-[#f6c90e]/20 transition">
                Withdraw to Arc
              </button>
              <button className="flex-1 py-2 bg-[#1d9e75]/10 text-[#1d9e75] border border-[#1d9e75]/30 rounded-lg hover:bg-[#1d9e75]/20 transition">
                Stake to Hogonat
              </button>
            </div>
          </div>
        </div>

        <div className="panel p-6 bg-gradient-to-br from-[#101439] to-[#0a0c21] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-6 opacity-10">
            <span className="text-8xl font-black">TKN</span>
          </div>
          <div className="relative z-10">
            <div className="text-sm text-[#aab2d5] uppercase tracking-widest mb-2 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#73a7ff]"></span>
              NexusMind Compute (TKN)
            </div>
            <div className="text-5xl font-mono text-white mb-2">
              {data.tkn.balance.toLocaleString()} <span className="text-2xl text-[#aab2d5]">TKN</span>
            </div>
            <div className="text-sm text-[#aab2d5] mb-6 font-mono">≈ ${data.tkn.approx_usdc} USDC</div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-[#7180b9] mb-1">Earned Today</div>
                <div className="text-sm text-[#73a7ff] font-mono">+{data.tkn.earned_today.toFixed(2)}</div>
              </div>
              <div>
                <div className="text-xs text-[#7180b9] mb-1">Earned 7d</div>
                <div className="text-sm text-[#73a7ff] font-mono">+{data.tkn.earned_7d.toFixed(2)}</div>
              </div>
            </div>
            <div className="mt-6 flex gap-3">
              <button className="flex-1 py-2 bg-[#73a7ff]/10 text-[#73a7ff] border border-[#73a7ff]/30 rounded-lg hover:bg-[#73a7ff]/20 transition">
                Withdraw
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
