import React, { useEffect, useState } from "react";
import ReactECharts from "echarts-for-react";

export function NetworkMap() {
  const [nodes, setNodes] = useState<any[]>([]);

  useEffect(() => {
    // Initial fetch
    fetch("http://localhost:8000/nexusmind/nodes")
      .then((res) => res.json())
      .then((data) => {
        setNodes(data.nodes || []);
      })
      .catch(console.error);
      
    // Connect to tracker to get real peer list
    const ws = new WebSocket("ws://localhost:8000/nexusmind/ws/tracker");
    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "announce", node_id: "dashboard", port: 3001 }));
    };
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "peer_list") {
          // Add tracker peers as active nodes
          const activePorts = data.peers;
          const dynamicNodes = activePorts.map((port: number) => ({
            id: `node_${port}`,
            name: `Port ${port}`,
            value: 20,
            category: 1
          }));
          
          setNodes(prev => {
            const merged = [...dynamicNodes];
            return merged;
          });
        } else if (data.type === "compute_result") {
          // Visual pulse effect for computing node can be added here
        }
      } catch (e) {}
    };

    return () => ws.close();
  }, []);

  const graphData = {
    nodes: [
      { id: "tracker", name: "Tracker (8000)", value: 40, category: 0, fixed: true, x: 500, y: 300 },
      ...nodes.map((n, i) => ({
        id: n.id || n.node_id,
        name: n.name || n.node_id,
        value: 20,
        category: 1
      }))
    ],
    links: nodes.map(n => ({
      source: "tracker",
      target: n.id || n.node_id,
      value: 1
    }))
  };

  const option = {
    backgroundColor: 'transparent',
    tooltip: {},
    animationDurationUpdate: 1500,
    animationEasingUpdate: 'quinticInOut',
    color: ['#0ea5e9', '#10b981', '#f6c90e', '#8b5cf6'],
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: graphData.nodes.map(n => ({
          ...n,
          symbolSize: n.value,
          label: {
            show: true,
            position: 'right',
            formatter: '{b}',
            color: '#e2e8f0'
          },
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 1,
            shadowBlur: 10,
            shadowColor: n.category === 0 ? '#0ea5e9' : '#10b981'
          }
        })),
        links: graphData.links,
        roam: true,
        force: {
          repulsion: 400,
          edgeLength: [50, 150],
          gravity: 0.1
        },
        lineStyle: {
          color: 'source',
          curveness: 0.3,
          width: 2,
          opacity: 0.7
        }
      }
    ]
  };

  return (
    <div className="panel p-0 relative overflow-hidden" style={{ height: "400px" }}>
      <div className="absolute top-4 left-4 z-10">
        <h3 className="text-xl font-bold text-white font-mono uppercase">Network Map</h3>
        <p className="text-sm text-[#0ea5e9]">P2P Real-time Topology</p>
      </div>
      <ReactECharts 
        option={option} 
        style={{ height: '100%', width: '100%' }} 
        opts={{ renderer: 'canvas' }} 
      />
    </div>
  );
}
