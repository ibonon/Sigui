import React, { useState, useEffect } from "react";

export function MarketplaceDashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/nexusmind/marketplace/plans")
      .then((res) => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

  if (!data) return <div className="p-4 text-muted">Loading Marketplace...</div>;

  return (
    <div className="marketplace-dashboard grid gap-6">
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">Sigui API Subscriptions</div>
          <div className="panel-caption">Upgrade your agent's protection tier</div>
        </div>
        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
          {data.plans.map((plan: any) => (
            <div key={plan.id} className={`rounded-xl border p-6 flex flex-col ${plan.current ? 'border-[#f6c90e] bg-[#f6c90e]/5' : 'border-[#1a1d42] bg-[#0a0c21]'}`}>
              <div className="flex justify-between items-start mb-4">
                <div className="text-xl font-bold text-white">{plan.name}</div>
                {plan.current && <span className="px-2 py-1 bg-[#f6c90e]/20 text-[#f6c90e] text-xs font-mono rounded border border-[#f6c90e]/30">ACTIVE</span>}
              </div>
              <div className="mb-6">
                <span className="text-3xl font-bold text-white">${plan.price_usdc_month}</span>
                <span className="text-sm text-[#aab2d5]"> USDC/mo</span>
              </div>
              
              <ul className="flex-1 space-y-3 mb-8">
                <li className="flex items-center gap-2 text-sm text-[#aab2d5]">
                  <span className="text-[#1d9e75]">✓</span>
                  {plan.evaluations_month === -1 ? "Unlimited" : plan.evaluations_month.toLocaleString()} Evaluations/mo
                </li>
                <li className="flex items-center gap-2 text-sm text-[#aab2d5]">
                  <span className={plan.vision_layer ? "text-[#1d9e75]" : "text-gray-600"}>
                    {plan.vision_layer ? "✓" : "✗"}
                  </span>
                  Imina-Na Vision Layer
                </li>
                <li className="flex items-center gap-2 text-sm text-[#aab2d5]">
                  <span className="text-[#1d9e75]">✓</span>
                  {plan.rate_limit_per_minute === -1 ? "Unlimited" : plan.rate_limit_per_minute} req/min limit
                </li>
                <li className="flex items-center gap-2 text-sm text-[#aab2d5]">
                  <span className={plan.priority_routing ? "text-[#1d9e75]" : "text-gray-600"}>
                    {plan.priority_routing ? "✓" : "✗"}
                  </span>
                  Priority Node Routing
                </li>
              </ul>
              
              <button 
                className={`w-full py-3 rounded-lg font-bold transition-all ${
                  plan.current 
                    ? 'bg-transparent border border-[#f6c90e]/30 text-[#f6c90e]' 
                    : 'bg-[#f6c90e] text-black hover:bg-[#ffd84d] hover:shadow-[0_0_15px_rgba(246,201,14,0.3)]'
                }`}
              >
                {plan.current ? 'Current Plan' : 'Subscribe'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
