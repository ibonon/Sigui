"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface FeedItem {
  id: string;
  agent_id: string;
  action_type: string;
  amount_usdc: number;
  decision: "ALLOW" | "BLOCK" | "ESCALATE" | "APPROVE";
  risk_score: number;
  arc_tx_hash: string;
  timestamp: string;
  processing_time_ms: number;
}

export interface GraphEdge {
  id: string;
  from: number;
  to: number;
  decision: "ALLOW" | "BLOCK" | "ESCALATE" | "APPROVE";
  createdAt: number; // timestamp ms
}

export interface LiveStats {
  allow: number;
  block: number;
  escalate: number;
  total: number;
  usdc_saved: number;
  patterns_learned: number;
}

export interface LiveTreasury {
  balance: number;
  total_earned: number;
  total_spent: number;
  net_profit: number;
  balances_by_chain: Record<string, number>;
}

export interface LiveAgents {
  [key: string]: { status: string; transactions: number };
}

export interface WebSocketState {
  isConnected: boolean;
  feed: FeedItem[];
  stats: LiveStats;
  treasury: LiveTreasury;
  agents: LiveAgents;
  graphEdges: GraphEdge[];
  lastTx: FeedItem | null;
}

const INITIAL_STATS: LiveStats = {
  allow: 0,
  block: 0,
  escalate: 0,
  total: 0,
  usdc_saved: 0,
  patterns_learned: 42,
};

const INITIAL_TREASURY: LiveTreasury = {
  balance: 0,
  total_earned: 0,
  total_spent: 0,
  net_profit: 0,
  balances_by_chain: { arc: 0, ethereum: 0 },
};

const MAX_FEED = 50;
const MAX_EDGES = 20;
const EDGE_LIFETIME_MS = 2500;
const RECONNECT_DELAY_MS = 3000;

// Stable node-pair mapping for the graph (12 nodes)
// We map agent names to node indices 0–4, destinations to 5–11
const AGENT_NODE_MAP: Record<string, number> = {
  agent_payer: 0,
  agent_attacker: 1,
  agent_learner: 2,
  agent_grayzone: 3,
  agent_monitor: 4,
};

function getDestNodeIdx(hash: string): number {
  // Hash → deterministic node index 5–11
  let sum = 0;
  for (let i = 0; i < hash.length; i++) sum += hash.charCodeAt(i);
  return 5 + (sum % 7);
}

export function useWebSocket(url: string): WebSocketState {
  const [isConnected, setIsConnected] = useState(false);
  const [feed, setFeed] = useState<FeedItem[]>([]);
  const [stats, setStats] = useState<LiveStats>(INITIAL_STATS);
  const [treasury, setTreasury] = useState<LiveTreasury>(INITIAL_TREASURY);
  const [agents, setAgents] = useState<LiveAgents>({});
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [lastTx, setLastTx] = useState<FeedItem | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const edgePruneTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // Prune expired edges every 500ms
  useEffect(() => {
    edgePruneTimer.current = setInterval(() => {
      const now = Date.now();
      setGraphEdges((prev) =>
        prev.filter((e) => now - e.createdAt < EDGE_LIFETIME_MS)
      );
    }, 500);
    return () => {
      if (edgePruneTimer.current) clearInterval(edgePruneTimer.current);
    };
  }, []);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;
    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) return;
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const payload = JSON.parse(event.data);

          // Update treasury
          if (payload.treasury) {
            setTreasury(payload.treasury);
          }

          // Update stats
          if (payload.decisions) {
            setStats({
              allow: payload.decisions.allow ?? 0,
              block: payload.decisions.block ?? 0,
              escalate: payload.decisions.escalate ?? 0,
              total: payload.decisions.total ?? 0,
              usdc_saved: payload.decisions.usdc_saved ?? 0,
              patterns_learned: payload.decisions.patterns_learned ?? 42,
            });
          }

          // Update agents
          if (payload.ecosystem?.agents) {
            setAgents(payload.ecosystem.agents);
          }

          // Process new transactions from recent_logs
          if (payload.recent_logs && payload.recent_logs.length > 0) {
            const newItems: FeedItem[] = payload.recent_logs.map(
              (log: any) => ({
                id: log.arc_tx_hash || `tx-${Date.now()}-${Math.random()}`,
                agent_id: log.agent_id,
                action_type: log.action_type,
                amount_usdc: log.amount_usdc,
                decision: log.decision,
                risk_score: log.risk_score,
                arc_tx_hash: log.arc_tx_hash,
                timestamp: log.timestamp,
                processing_time_ms: log.processing_time_ms,
              })
            );

            // Update feed (FIFO, max 50)
            setFeed((prev) => {
              const combined = [...newItems, ...prev];
              return combined.slice(0, MAX_FEED);
            });

            // Set last transaction for UI flash
            setLastTx(newItems[0]);

            // Create graph edges
            const now = Date.now();
            const newEdges: GraphEdge[] = newItems.map((item) => ({
              id: item.id,
              from: AGENT_NODE_MAP[item.agent_id] ?? Math.floor(Math.random() * 5),
              to: getDestNodeIdx(item.arc_tx_hash || item.id),
              decision: item.decision,
              createdAt: now,
            }));

            setGraphEdges((prev) => {
              const combined = [...newEdges, ...prev];
              return combined.slice(0, MAX_EDGES);
            });
          }
        } catch (_) {
          // Ignore parse errors
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setIsConnected(false);
        wsRef.current = null;
        // Auto-reconnect
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (_) {
      // WebSocket not available (SSR), retry
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY_MS);
    }
  }, [url]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on intentional close
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { isConnected, feed, stats, treasury, agents, graphEdges, lastTx };
}
