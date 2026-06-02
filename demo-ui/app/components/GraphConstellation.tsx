"use client";

import { useEffect, useRef, useMemo } from "react";
import type { GraphEdge } from "../hooks/useWebSocket";

// ── Node layout — 12 nodes in a constellation ──────────────────────────────
// Nodes 0–4 = Agents (left cluster), Nodes 5–11 = Destinations (right cluster)
const NODE_POSITIONS = [
  // Agents (left)
  { x: 110, y: 80,  label: "Danseur",  icon: "🔥", type: "agent" },
  { x: 65,  y: 200, label: "Renard",   icon: "🦊", type: "agent" },
  { x: 110, y: 320, label: "Étoile",   icon: "⭐", type: "agent" },
  { x: 180, y: 140, label: "GrayZone", icon: "🌫", type: "agent" },
  { x: 180, y: 260, label: "Œil",      icon: "👁", type: "agent" },
  // Destinations (right)
  { x: 380, y: 60,  label: "0xA1...", icon: "🏦", type: "dest" },
  { x: 460, y: 130, label: "0xB2...", icon: "🔗", type: "dest" },
  { x: 520, y: 220, label: "0xC3...", icon: "🏛", type: "dest" },
  { x: 460, y: 310, label: "0xD4...", icon: "💎", type: "dest" },
  { x: 380, y: 370, label: "0xE5...", icon: "🌐", type: "dest" },
  { x: 560, y: 80,  label: "0xF6...", icon: "⚡", type: "dest" },
  { x: 570, y: 340, label: "0xG7...", icon: "🔮", type: "dest" },
];

// Oracle node in the center
const ORACLE_NODE = { x: 300, y: 200, label: "SIGUI", type: "oracle" };

const DECISION_COLORS: Record<string, { stroke: string; glow: string }> = {
  ALLOW:   { stroke: "#10b981", glow: "rgba(16,185,129,0.8)" },
  APPROVE: { stroke: "#10b981", glow: "rgba(16,185,129,0.8)" },
  BLOCK:   { stroke: "#f43f5e", glow: "rgba(244,63,94,0.9)" },
  ESCALATE:{ stroke: "#f59e0b", glow: "rgba(245,158,11,0.8)" },
};

interface GraphConstellationProps {
  edges: GraphEdge[];
}

export function GraphConstellation({ edges }: GraphConstellationProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const edgeEls = useRef<Map<string, SVGLineElement>>(new Map());
  const rafRef = useRef<number>(0);
  const lastEdgesRef = useRef<GraphEdge[]>([]);

  // RAF loop — animates edges without React re-renders
  useEffect(() => {
    const animate = () => {
      const svg = svgRef.current;
      if (!svg) {
        rafRef.current = requestAnimationFrame(animate);
        return;
      }

      const now = Date.now();
      const currentEdges = lastEdgesRef.current;

      currentEdges.forEach((edge) => {
        const el = edgeEls.current.get(edge.id);
        if (!el) return;

        const age = now - edge.createdAt;
        const lifetime = 2500;

        if (age > lifetime) {
          el.style.opacity = "0";
          return;
        }

        // Draw-in phase (0–400ms): animate stroke-dashoffset
        const drawPhase = Math.min(1, age / 400);
        const totalLen = parseFloat(el.getAttribute("data-len") || "200");
        el.style.strokeDashoffset = String(totalLen * (1 - drawPhase));

        // Fade-out phase (last 800ms)
        if (age > lifetime - 800) {
          const fadeOut = 1 - (age - (lifetime - 800)) / 800;
          el.style.opacity = String(Math.max(0, fadeOut));
        } else {
          el.style.opacity = "1";
        }
      });

      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, []);

  // Sync edges ref when prop changes
  useEffect(() => {
    lastEdgesRef.current = edges;

    const svg = svgRef.current;
    if (!svg) return;

    // Create new edge elements
    edges.forEach((edge) => {
      if (edgeEls.current.has(edge.id)) return;

      const from = NODE_POSITIONS[edge.from] ?? NODE_POSITIONS[0];
      const to = NODE_POSITIONS[edge.to] ?? NODE_POSITIONS[5];
      const colors = DECISION_COLORS[edge.decision] ?? DECISION_COLORS["ALLOW"];

      // Route through oracle node
      const x1 = from.x, y1 = from.y;
      const xM = ORACLE_NODE.x, yM = ORACLE_NODE.y;
      const x2 = to.x, y2 = to.y;

      // Segment 1: agent → oracle
      const seg1 = document.createElementNS("http://www.w3.org/2000/svg", "line");
      const len1 = Math.hypot(xM - x1, yM - y1);
      seg1.setAttribute("x1", String(x1));
      seg1.setAttribute("y1", String(y1));
      seg1.setAttribute("x2", String(xM));
      seg1.setAttribute("y2", String(yM));
      seg1.setAttribute("stroke", colors.stroke);
      seg1.setAttribute("stroke-width", "2.5");
      seg1.setAttribute("stroke-linecap", "round");
      seg1.setAttribute("data-len", String(len1));
      seg1.style.strokeDasharray = String(len1);
      seg1.style.strokeDashoffset = String(len1);
      seg1.style.filter = `drop-shadow(0 0 6px ${colors.glow})`;
      seg1.style.opacity = "0";
      seg1.style.transition = "none";

      // Segment 2: oracle → dest
      const seg2 = document.createElementNS("http://www.w3.org/2000/svg", "line");
      const len2 = Math.hypot(x2 - xM, y2 - yM);
      seg2.setAttribute("x1", String(xM));
      seg2.setAttribute("y1", String(yM));
      seg2.setAttribute("x2", String(x2));
      seg2.setAttribute("y2", String(y2));
      seg2.setAttribute("stroke", colors.stroke);
      seg2.setAttribute("stroke-width", "2.5");
      seg2.setAttribute("stroke-linecap", "round");
      seg2.setAttribute("data-len", String(len2));
      seg2.style.strokeDasharray = String(len2);
      seg2.style.strokeDashoffset = String(len2);
      seg2.style.filter = `drop-shadow(0 0 6px ${colors.glow})`;
      seg2.style.opacity = "0";
      seg2.style.transition = "none";

      // Use a group so we can store one ref per edge
      const g = document.createElementNS("http://www.w3.org/2000/svg", "g");
      g.setAttribute("data-edge-id", edge.id);
      g.appendChild(seg1);
      g.appendChild(seg2);

      const edgeLayer = svg.querySelector("#edge-layer");
      if (edgeLayer) edgeLayer.appendChild(g);

      // Store seg1 as the "primary" element for opacity/offset control
      // We use a composite approach: store the group reference
      // and animate both children in the RAF loop
      edgeEls.current.set(edge.id, seg1 as unknown as SVGLineElement);

      // Clean up after lifetime
      setTimeout(() => {
        g.remove();
        edgeEls.current.delete(edge.id);
      }, 3200);
    });
  }, [edges]);

  // Memoize static SVG background (nodes)
  const staticNodes = useMemo(() => (
    <>
      {/* Background connections (faint) */}
      {NODE_POSITIONS.slice(0, 5).map((agent, i) => (
        <line
          key={`bg-${i}`}
          x1={agent.x} y1={agent.y}
          x2={ORACLE_NODE.x} y2={ORACLE_NODE.y}
          stroke="rgba(148,163,184,0.08)"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
      ))}
      {NODE_POSITIONS.slice(5).map((dest, i) => (
        <line
          key={`bg-d-${i}`}
          x1={ORACLE_NODE.x} y1={ORACLE_NODE.y}
          x2={dest.x} y2={dest.y}
          stroke="rgba(148,163,184,0.06)"
          strokeWidth="1"
          strokeDasharray="3 6"
        />
      ))}

      {/* Destination nodes */}
      {NODE_POSITIONS.slice(5).map((n, i) => (
        <g key={`dest-${i}`}>
          <circle cx={n.x} cy={n.y} r={16} fill="rgba(17,24,39,0.8)" stroke="rgba(148,163,184,0.2)" strokeWidth="1" />
          <text x={n.x} y={n.y + 4} textAnchor="middle" fontSize="12" fill="rgba(148,163,184,0.7)">{n.icon}</text>
          <text x={n.x} y={n.y + 26} textAnchor="middle" fontSize="8" fill="rgba(148,163,184,0.4)" fontFamily="monospace">{n.label}</text>
        </g>
      ))}

      {/* Agent nodes */}
      {NODE_POSITIONS.slice(0, 5).map((n, i) => (
        <g key={`agent-${i}`}>
          <circle cx={n.x} cy={n.y} r={20} fill="rgba(17,24,39,0.9)" stroke="rgba(14,165,233,0.3)" strokeWidth="1.5" />
          <circle cx={n.x} cy={n.y} r={20} fill="none" stroke="rgba(14,165,233,0.1)" strokeWidth="8" />
          <text x={n.x} y={n.y + 5} textAnchor="middle" fontSize="14">{n.icon}</text>
          <text x={n.x} y={n.y + 34} textAnchor="middle" fontSize="9" fill="rgba(148,163,184,0.6)" fontFamily="monospace">{n.label}</text>
        </g>
      ))}

      {/* Oracle node (center) */}
      <g>
        <circle cx={ORACLE_NODE.x} cy={ORACLE_NODE.y} r={32}
          fill="rgba(17,24,39,0.95)"
          stroke="rgba(246,201,14,0.5)"
          strokeWidth="2"
        />
        <circle cx={ORACLE_NODE.x} cy={ORACLE_NODE.y} r={32}
          fill="none"
          stroke="rgba(246,201,14,0.15)"
          strokeWidth="14"
        />
        <text x={ORACLE_NODE.x} y={ORACLE_NODE.y - 6} textAnchor="middle" fontSize="16">⚡</text>
        <text x={ORACLE_NODE.x} y={ORACLE_NODE.y + 12} textAnchor="middle" fontSize="9"
          fill="rgba(246,201,14,0.9)" fontFamily="monospace" fontWeight="bold"
          letterSpacing="2">SIGUI</text>
      </g>
    </>
  ), []);

  return (
    <div className="graph-constellation-wrapper">
      <svg
        ref={svgRef}
        viewBox="0 0 640 400"
        width="100%"
        height="100%"
        style={{ overflow: "visible" }}
      >
        {/* Defs */}
        <defs>
          <radialGradient id="oracle-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(246,201,14,0.3)" />
            <stop offset="100%" stopColor="rgba(246,201,14,0)" />
          </radialGradient>
        </defs>

        {/* Oracle ambient glow */}
        <circle cx={ORACLE_NODE.x} cy={ORACLE_NODE.y} r={80}
          fill="url(#oracle-glow)" style={{ pointerEvents: "none" }} />

        {/* Edge layer (dynamic, managed via DOM) */}
        <g id="edge-layer" />

        {/* Static nodes on top */}
        {staticNodes}
      </svg>

      <style>{`
        .graph-constellation-wrapper {
          width: 100%;
          height: 100%;
          min-height: 360px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
      `}</style>
    </div>
  );
}
