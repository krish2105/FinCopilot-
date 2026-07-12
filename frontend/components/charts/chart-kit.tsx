"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatCompact } from "@/lib/utils";

export const CHART_COLORS = [
  "hsl(var(--chart-1))",
  "hsl(var(--chart-2))",
  "hsl(var(--chart-3))",
  "hsl(var(--chart-4))",
  "hsl(var(--chart-5))",
];

const axisProps = {
  stroke: "hsl(var(--muted-foreground))",
  fontSize: 11,
  tickLine: false,
  axisLine: false,
} as const;

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-card">
      {label != null && (
        <p className="mb-1 text-xs font-medium text-foreground">{label}</p>
      )}
      {payload.map((p: any, i: number) => (
        <p key={i} className="flex items-center gap-2 text-xs text-muted-foreground">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: p.color || p.payload?.fill }}
          />
          <span className="tabular font-mono text-foreground">
            {typeof p.value === "number" ? formatCompact(p.value) : p.value}
          </span>
          {p.name && p.name !== "value" ? <span>{p.name}</span> : null}
        </p>
      ))}
    </div>
  );
}

export function BarViz({
  data,
  color = CHART_COLORS[0],
  height = 260,
}: {
  data: { x: string; y: number }[];
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 8 }}>
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.95} />
            <stop offset="100%" stopColor={color} stopOpacity={0.55} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="hsl(var(--chart-grid))" strokeDasharray="4 4" />
        <XAxis dataKey="x" {...axisProps} interval={0} angle={-12} height={44} textAnchor="end" />
        <YAxis {...axisProps} tickFormatter={(v) => formatCompact(Number(v))} width={52} />
        <Tooltip cursor={{ fill: "hsl(var(--muted) / 0.5)" }} content={<ChartTooltip />} />
        <Bar dataKey="y" fill="url(#barGrad)" radius={[6, 6, 0, 0]} maxBarSize={54} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function AreaViz({
  data,
  color = CHART_COLORS[1],
  height = 260,
}: {
  data: { x: string; y: number }[];
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 8 }}>
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.4} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="hsl(var(--chart-grid))" strokeDasharray="4 4" />
        <XAxis dataKey="x" {...axisProps} />
        <YAxis {...axisProps} tickFormatter={(v) => formatCompact(Number(v))} width={52} />
        <Tooltip content={<ChartTooltip />} />
        <Area
          type="monotone"
          dataKey="y"
          stroke={color}
          strokeWidth={2.5}
          fill="url(#areaGrad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function DonutViz({
  data,
  height = 260,
}: {
  data: { x: string; y: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          dataKey="y"
          nameKey="x"
          innerRadius="58%"
          outerRadius="82%"
          paddingAngle={2}
          stroke="hsl(var(--card))"
          strokeWidth={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}
