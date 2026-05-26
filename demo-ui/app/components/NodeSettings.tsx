import React, { useState } from "react";

export function NodeSettings() {
  const [cpuLimit, setCpuLimit] = useState(40);
  const [storageLimit, setStorageLimit] = useState(10);
  const [tlsEnabled, setTlsEnabled] = useState(true);
  const [autoBan, setAutoBan] = useState(true);
  const [meshRouting, setMeshRouting] = useState(true);

  return (
    <div className="panel p-6">
      <div className="text-xl font-bold text-white mb-6 font-mono">Node Configuration</div>
      
      <div className="space-y-6">
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-bold text-muted">CPU Allocation Limit</label>
            <span className="text-primary font-mono">{cpuLimit}%</span>
          </div>
          <input 
            type="range" 
            min="10" max="100" 
            value={cpuLimit} 
            onChange={(e) => setCpuLimit(parseInt(e.target.value))}
            className="w-full h-2 bg-bg-2 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-bold text-muted">Local Storage Cap</label>
            <span className="text-secondary font-mono">{storageLimit} GB</span>
          </div>
          <input 
            type="range" 
            min="1" max="100" 
            value={storageLimit} 
            onChange={(e) => setStorageLimit(parseInt(e.target.value))}
            className="w-full h-2 bg-bg-2 rounded-lg appearance-none cursor-pointer"
          />
        </div>

        <div className="pt-4 border-t border-border">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-bold text-white">Enforce TLS 1.3</div>
              <div className="text-xs text-dim">Require strict encryption for P2P links</div>
            </div>
            <button 
              onClick={() => setTlsEnabled(!tlsEnabled)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${tlsEnabled ? 'bg-success' : 'bg-bg-2'}`}
            >
              <div className={`w-4 h-4 bg-white rounded-full transition-transform ${tlsEnabled ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-bold text-white">Auto-ban Corrupt Nodes</div>
              <div className="text-xs text-dim">Isolate nodes failing cryptographic proofs</div>
            </div>
            <button 
              onClick={() => setAutoBan(!autoBan)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${autoBan ? 'bg-danger' : 'bg-bg-2'}`}
            >
              <div className={`w-4 h-4 bg-white rounded-full transition-transform ${autoBan ? 'translate-x-6' : ''}`} />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm font-bold text-white">P2P Mesh Routing</div>
              <div className="text-xs text-dim">Enable decentralized task propagation</div>
            </div>
            <button 
              onClick={() => setMeshRouting(!meshRouting)}
              className={`w-12 h-6 rounded-full p-1 transition-colors ${meshRouting ? 'bg-primary' : 'bg-bg-2'}`}
            >
              <div className={`w-4 h-4 bg-white rounded-full transition-transform ${meshRouting ? 'translate-x-6' : ''}`} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
