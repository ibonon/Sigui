import React, { useState, useEffect } from "react";

export function ResearchDashboard() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("http://localhost:8000/nexusmind/swarm")
      .then((res) => res.json())
      .then(setData)
      .catch(console.error);
  }, []);

  const [integrationCode, setIntegrationCode] = useState<string>("");

  const handleCreateSwarm = () => {
    fetch("http://localhost:8000/nexusmind/swarm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: "New Auto-Trading Swarm",
        framework: "langchain",
        agent_count: 5,
        sigui_protection: true,
      })
    })
    .then(res => res.json())
    .then(res => {
      setData({ ...data, swarms: [...(data?.swarms || []), res.swarm] });
    });
  };

  const showIntegration = (id: string) => {
    fetch(`http://localhost:8000/nexusmind/swarm/${id}/integration-code`)
      .then(res => res.json())
      .then(res => setIntegrationCode(res.code));
  };

  return (
    <div className="research-dashboard grid gap-6">
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">Agent Swarm Management</div>
          <div className="panel-caption">Deploy and protect multi-agent research swarms</div>
        </div>
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <div className="text-white">Active Swarms: {data?.swarms?.length || 0}</div>
            <button 
              onClick={handleCreateSwarm}
              className="px-4 py-2 bg-[#8b5cf6] hover:bg-[#7c3aed] text-white rounded-lg font-bold transition-colors"
            >
              + Create Protected Swarm
            </button>
          </div>

          <div className="grid gap-4 mb-6">
            {data?.swarms?.map((swarm: any) => (
              <div key={swarm.id} className="bg-[#0a0c21] border border-[#1a1d42] rounded-xl p-5 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <span className="font-bold text-white text-lg">{swarm.name}</span>
                    <span className={`px-2 py-0.5 rounded text-xs font-mono border ${
                      swarm.status === 'active' ? 'bg-[#1d9e75]/10 text-[#1d9e75] border-[#1d9e75]/30' : 'bg-gray-800 text-gray-400 border-gray-700'
                    }`}>
                      {swarm.status.toUpperCase()}
                    </span>
                  </div>
                  <div className="text-sm text-[#aab2d5] font-mono mb-3">ID: {swarm.id}</div>
                  
                  <div className="flex gap-4 text-sm text-[#7180b9]">
                    <span className="flex items-center gap-1"><span className="text-white">{swarm.agent_count}</span> agents</span>
                    <span className="flex items-center gap-1"><span className="text-[#8b5cf6]">{swarm.framework}</span> framework</span>
                    <span className="flex items-center gap-1">Threshold: <span className="text-white">{swarm.threshold}</span></span>
                  </div>
                </div>
                
                <div className="flex gap-2 w-full md:w-auto">
                  <button 
                    onClick={() => showIntegration(swarm.id)}
                    className="flex-1 md:flex-none px-4 py-2 bg-[#f6c90e]/10 text-[#f6c90e] border border-[#f6c90e]/30 rounded-lg hover:bg-[#f6c90e]/20 transition-colors"
                  >
                    SDK Snippet
                  </button>
                </div>
              </div>
            ))}
            
            {(!data?.swarms || data.swarms.length === 0) && (
              <div className="text-center py-12 border border-dashed border-[#1a1d42] rounded-xl text-[#7180b9]">
                No active swarms found. Create one to get started.
              </div>
            )}
          </div>

          {integrationCode && (
            <div className="bg-[#0a0c21] border border-[#1a1d42] rounded-xl overflow-hidden mt-6">
              <div className="bg-[#1a1d42] px-4 py-2 text-sm text-[#aab2d5] flex justify-between items-center">
                <span>Python Integration Code (sigui-sdk v0.2.0)</span>
                <button onClick={() => setIntegrationCode("")} className="hover:text-white">✕</button>
              </div>
              <pre className="p-4 text-sm text-gray-300 font-mono overflow-x-auto">
                <code>{integrationCode}</code>
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
