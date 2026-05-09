"use client";

import ReactECharts from "echarts-for-react";
import { useMemo } from "react";

interface TimePoint {
  ts: number;
  allow: number;
  block: number;
  escalate: number;
  revenue: number;
}

interface TimeSeriesPanelProps {
  data: TimePoint[];
}

export function TimeSeriesPanel({ data }: TimeSeriesPanelProps) {
  const option = useMemo(() => {
    const times = data.map((d) =>
      new Date(d.ts).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    );
    return {
      backgroundColor: "transparent",
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: {
        data: ["ALLOW", "BLOCK", "ESCALATE", "Revenue (USDC)"],
        textStyle: { color: "#aab2d5", fontSize: 11 },
        top: 4,
      },
      grid: { left: 48, right: 64, top: 36, bottom: 28 },
      xAxis: {
        type: "category",
        data: times,
        axisLabel: { color: "#7180b9", fontSize: 10 },
        axisLine: { lineStyle: { color: "rgba(246,201,14,0.15)" } },
      },
      yAxis: [
        {
          type: "value",
          name: "Decisions",
          axisLabel: { color: "#7180b9", fontSize: 10 },
          splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
        },
        {
          type: "value",
          name: "USDC",
          axisLabel: { color: "#7180b9", fontSize: 10 },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "ALLOW",
          type: "line",
          data: data.map((d) => d.allow),
          smooth: true,
          symbol: "none",
          lineStyle: { color: "#1d9e75", width: 2 },
          areaStyle: { color: "rgba(29,158,117,0.08)" },
        },
        {
          name: "BLOCK",
          type: "line",
          data: data.map((d) => d.block),
          smooth: true,
          symbol: "none",
          lineStyle: { color: "#e24b4a", width: 2 },
          areaStyle: { color: "rgba(226,75,74,0.08)" },
        },
        {
          name: "ESCALATE",
          type: "line",
          data: data.map((d) => d.escalate),
          smooth: true,
          symbol: "none",
          lineStyle: { color: "#8b5cf6", width: 2 },
        },
        {
          name: "Revenue (USDC)",
          type: "bar",
          yAxisIndex: 1,
          data: data.map((d) => d.revenue),
          itemStyle: { color: "rgba(246,201,14,0.55)", borderRadius: [3, 3, 0, 0] },
        },
      ],
    };
  }, [data]);

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: 240 }}
      notMerge
    />
  );
}

interface DecisionDonutProps {
  allow: number;
  block: number;
  escalate: number;
}

export function DecisionDonut({ allow, block, escalate }: DecisionDonutProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      legend: { show: false },
      series: [
        {
          name: "Decisions",
          type: "pie",
          radius: ["52%", "76%"],
          center: ["50%", "52%"],
          data: [
            { value: allow || 0, name: "ALLOW", itemStyle: { color: "#1d9e75" } },
            { value: block || 0, name: "BLOCK", itemStyle: { color: "#e24b4a" } },
            { value: escalate || 0, name: "ESCALATE", itemStyle: { color: "#8b5cf6" } },
          ],
          label: { show: true, color: "#aab2d5", fontSize: 11, formatter: "{b}\n{d}%" },
          labelLine: { lineStyle: { color: "rgba(246,201,14,0.3)" } },
          emphasis: { itemStyle: { shadowBlur: 12, shadowColor: "rgba(246,201,14,0.3)" } },
        },
      ],
    }),
    [allow, block, escalate]
  );

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: 220 }}
      notMerge
    />
  );
}

interface BarGaugeProps {
  cpuMs: number;
  amdMs: number;
  visionMs: number;
}

export function BarGauge({ cpuMs, amdMs, visionMs }: BarGaugeProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      grid: { left: 100, right: 20, top: 8, bottom: 8 },
      xAxis: {
        type: "value",
        axisLabel: { color: "#7180b9", fontSize: 10, formatter: "{value}ms" },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      },
      yAxis: {
        type: "category",
        data: ["CPU Baseline", "AMD MI300X", "Vision (Imina Na)"],
        axisLabel: { color: "#aab2d5", fontSize: 11 },
        axisLine: { lineStyle: { color: "rgba(246,201,14,0.15)" } },
      },
      series: [
        {
          type: "bar",
          data: [
            { value: cpuMs, itemStyle: { color: "rgba(115,167,255,0.5)", borderRadius: [0, 6, 6, 0] } },
            { value: amdMs, itemStyle: { color: "rgba(246,201,14,0.8)", borderRadius: [0, 6, 6, 0] } },
            { value: visionMs, itemStyle: { color: "rgba(139,92,246,0.7)", borderRadius: [0, 6, 6, 0] } },
          ],
          barWidth: 22,
          label: { show: true, position: "right", color: "#f5f7ff", fontSize: 11, formatter: "{c}ms" },
        },
      ],
    }),
    [cpuMs, amdMs, visionMs]
  );

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: 120 }}
      notMerge
    />
  );
}

interface FunnelChartProps {
  total: number;
  evaluated: number;
  blocked: number;
  escalated: number;
  onchain: number;
}

export function FunnelChart({ total, evaluated, blocked, escalated, onchain }: FunnelChartProps) {
  const option = useMemo(
    () => ({
      backgroundColor: "transparent",
      tooltip: { trigger: "item", formatter: "{b}: {c}" },
      series: [
        {
          name: "Pipeline",
          type: "funnel",
          left: "10%",
          width: "80%",
          top: 8,
          bottom: 8,
          min: 0,
          max: Math.max(total, 1),
          gap: 3,
          label: { show: true, position: "inside", color: "#f5f7ff", fontSize: 11 },
          data: [
            { value: total, name: "Agents Actifs", itemStyle: { color: "rgba(115,167,255,0.65)" } },
            { value: evaluated, name: "Évaluations", itemStyle: { color: "rgba(29,158,117,0.65)" } },
            { value: blocked, name: "Menaces Bloquées", itemStyle: { color: "rgba(226,75,74,0.65)" } },
            { value: escalated, name: "Escaladées", itemStyle: { color: "rgba(139,92,246,0.65)" } },
            { value: onchain, name: "On-Chain", itemStyle: { color: "rgba(246,201,14,0.75)" } },
          ],
        },
      ],
    }),
    [total, evaluated, blocked, escalated, onchain]
  );

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: 200 }}
      notMerge
    />
  );
}

interface SankeyFlowProps {
  agents: Record<string, { transactions?: number; balance_usdc?: number }>;
}

export function SankeyFlow({ agents }: SankeyFlowProps) {
  const AGENT_NAMES: Record<string, string> = {
    agent_payer: "Danseur du Feu",
    agent_attacker: "Renard Pâle",
    agent_learner: "Étoile App.",
    agent_grayzone: "Gray Zone",
    agent_monitor: "Œil Société",
  };

  const option = useMemo(() => {
    const agentList = Object.entries(AGENT_NAMES);
    const nodes = [
      ...agentList.map(([, name]) => ({ name })),
      { name: "Sigui Oracle", itemStyle: { color: "#f6c90e" } },
      { name: "Treasury (80%)", itemStyle: { color: "#1d9e75" } },
      { name: "Hogonat DAO (20%)", itemStyle: { color: "#8b5cf6" } },
      { name: "Arc L1", itemStyle: { color: "#73a7ff" } },
    ];

    const links = agentList.flatMap(([id, name]) => {
      const tx = agents[id]?.transactions ?? 1;
      const fee = tx * 0.001;
      return [{ source: name, target: "Sigui Oracle", value: Math.max(fee, 0.001) }];
    }).concat([
      { source: "Sigui Oracle", target: "Treasury (80%)", value: 0.008 },
      { source: "Sigui Oracle", target: "Hogonat DAO (20%)", value: 0.002 },
      { source: "Treasury (80%)", target: "Arc L1", value: 0.003 },
    ]);

    return {
      backgroundColor: "transparent",
      tooltip: {
        trigger: "item",
        formatter: (params: { dataType: string; data: { source?: string; target?: string; value: number }; name: string }) =>
          params.dataType === "edge"
            ? `${params.data.source} → ${params.data.target}: $${params.data.value.toFixed(4)}`
            : params.name,
      },
      series: [
        {
          type: "sankey",
          layout: "none",
          emphasis: { focus: "adjacency" },
          data: nodes,
          links,
          lineStyle: { color: "gradient", opacity: 0.4 },
          label: { color: "#aab2d5", fontSize: 11 },
          nodeWidth: 16,
          nodeGap: 10,
        },
      ],
    };
  }, [agents]);

  return (
    <ReactECharts
      option={option}
      style={{ width: "100%", height: 260 }}
      notMerge
    />
  );
}
