import React, { useState, useEffect } from "react";

export function TaskFeed() {
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    const ws = new WebSocket("ws://localhost:8000/nexusmind/ws/tracker");
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "announce", node_id: "dashboard_feed", port: 3002 }));
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "compute_result") {
          setLogs(prev => {
            const newLogs = [data, ...prev].slice(0, 50);
            return newLogs;
          });
        }
      } catch (e) {}
    };

    return () => ws.close();
  }, []);

  return (
    <div className="panel p-0 flex flex-col h-full border border-primary/30">
      <div className="panel-header bg-bg-2 border-b border-primary/20">
        <div className="panel-title text-primary font-mono flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse"></span>
          P2P Task Execution Terminal
        </div>
      </div>
      <div className="p-4 bg-[#02040a] flex-1 overflow-y-auto font-mono text-xs">
        {logs.map((log, i) => (
          <div key={i} className="mb-2 border-b border-white/5 pb-2">
            <span className="text-muted">[{new Date().toLocaleTimeString()}]</span>{" "}
            <span className="text-secondary">{log.node_id}</span>{" "}
            <span className="text-text">computed</span>{" "}
            <span className="text-accent">{log.task_id}</span>{" "}
            <span className="text-dim">in</span>{" "}
            <span className="text-gold">{log.latency_ms.toFixed(1)}ms</span>{" "}
            <span className="text-success ml-2">+0.01 TKN</span>
          </div>
        ))}
        {logs.length === 0 && (
          <div className="text-dim animate-pulse">Waiting for P2P tasks...</div>
        )}
      </div>
    </div>
  );
}
