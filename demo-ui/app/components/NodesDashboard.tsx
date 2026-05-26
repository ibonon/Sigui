import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";

export function NodesDashboard() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Fetch nodes
    fetch("http://localhost:8000/nexusmind/nodes")
      .then((res) => res.json())
      .then((data) => {
        setNodes(data.nodes || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleToggleSiguiWorker = (nodeId: string, enabled: boolean) => {
    fetch(`http://localhost:8000/nexusmind/nodes/${nodeId}/sigui-settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    })
      .then((res) => res.json())
      .then(() => {
        setNodes(
          nodes.map((n) =>
            n.node_id === nodeId ? { ...n, is_sigui_worker: enabled } : n
          )
        );
      });
  };

  return (
    <div className="nodes-dashboard grid gap-6">
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">NexusMind Compute Nodes</div>
          <div className="panel-caption">Manage your decentralized infrastructure</div>
        </div>
        <div className="p-5">
          {loading ? (
            <div className="text-muted">Loading nodes...</div>
          ) : (
            <div className="grid gap-4">
              {nodes.map((node) => (
                <div
                  key={node.node_id}
                  className="bg-[#1a1d42] border border-[#f6c90e]/20 rounded-xl p-5"
                >
                  <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center font-bold text-white">
                        {node.node_id.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-bold text-white">{node.node_id}</div>
                        <div className="text-xs text-[#aab2d5] font-mono">
                          {node.address.substring(0, 10)}...{node.address.substring(38)}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <span className="px-3 py-1 rounded-full bg-[#1d9e75]/20 text-[#1d9e75] text-xs font-mono border border-[#1d9e75]/30">
                        {node.is_online ? "ONLINE" : "OFFLINE"}
                      </span>
                      <span className="px-3 py-1 rounded-full bg-[#8b5cf6]/20 text-[#8b5cf6] text-xs font-mono border border-[#8b5cf6]/30">
                        {node.capabilities.gpu}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-4 gap-4 mb-4">
                    <div>
                      <div className="text-xs text-[#aab2d5] uppercase tracking-wider mb-1">Reputation</div>
                      <div className="text-xl font-mono text-white">{node.reputation_score}</div>
                    </div>
                    <div>
                      <div className="text-xs text-[#aab2d5] uppercase tracking-wider mb-1">Evals (24h)</div>
                      <div className="text-xl font-mono text-white">{node.stats.evaluations_today}</div>
                    </div>
                    <div>
                      <div className="text-xs text-[#aab2d5] uppercase tracking-wider mb-1">USDC Earned</div>
                      <div className="text-xl font-mono text-[#f6c90e]">${node.stats.total_usdc_earned.toFixed(4)}</div>
                    </div>
                    <div>
                      <div className="text-xs text-[#aab2d5] uppercase tracking-wider mb-1">TKN Earned</div>
                      <div className="text-xl font-mono text-[#73a7ff]">{node.tkn.balance.toFixed(2)}</div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between border-t border-[#f6c90e]/10 pt-4 mt-2">
                    <div className="flex items-center gap-2">
                      <div className="text-sm text-white">Dual-Mining (Sigui Worker)</div>
                      <div
                        className={`w-12 h-6 rounded-full p-1 cursor-pointer transition-colors ${
                          node.is_sigui_worker ? "bg-[#1d9e75]" : "bg-gray-600"
                        }`}
                        onClick={() => handleToggleSiguiWorker(node.node_id, !node.is_sigui_worker)}
                      >
                        <motion.div
                          className="w-4 h-4 bg-white rounded-full"
                          animate={{ x: node.is_sigui_worker ? 24 : 0 }}
                          transition={{ type: "spring", stiffness: 500, damping: 30 }}
                        />
                      </div>
                    </div>
                    <button className="px-4 py-2 rounded-lg bg-[#f6c90e]/10 text-[#f6c90e] border border-[#f6c90e]/30 text-sm hover:bg-[#f6c90e]/20 transition-colors">
                      Configure Allocation
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
