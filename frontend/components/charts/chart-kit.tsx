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
  Sankey,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
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

function PriceTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-card">
      <p className="mb-1 text-xs font-medium text-foreground">{label}</p>
      <p className="font-mono tabular text-xs text-foreground">
        {Number(payload[0].value).toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })}
      </p>
    </div>
  );
}

/** Price line/area chart with finance-standard green(up)/red(down) coloring. */
export function PriceViz({
  data,
  up = true,
  height = 300,
}: {
  data: { x: string; y: number }[];
  up?: boolean;
  height?: number;
}) {
  const color = up ? "#10b981" : "#ef4444"; // emerald-500 / red-500 — legible in both themes
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -4, bottom: 8 }}>
        <defs>
          <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.32} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="hsl(var(--chart-grid))" strokeDasharray="4 4" />
        <XAxis
          dataKey="x"
          {...axisProps}
          minTickGap={48}
          tickFormatter={(v) => String(v).slice(5)}
        />
        <YAxis
          {...axisProps}
          width={56}
          domain={["auto", "auto"]}
          tickFormatter={(v) => Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}
        />
        <Tooltip content={<PriceTooltip />} />
        <Area type="monotone" dataKey="y" stroke={color} strokeWidth={2} fill="url(#priceGrad)" />
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


// ---- Sankey income statement (Phase 47) ------------------------------------
export function SankeyViz({
  nodes,
  links,
  height = 340,
}: {
  nodes: string[];
  links: { source: string; target: string; value: number }[];
  height?: number;
}) {
  const index = new Map(nodes.map((n, i) => [n, i]));
  const data = {
    nodes: nodes.map((name) => ({ name })),
    links: links
      .filter((l) => index.has(l.source) && index.has(l.target))
      .map((l) => ({ source: index.get(l.source)!, target: index.get(l.target)!, value: l.value })),
  };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <Sankey
        data={data}
        nodePadding={26}
        nodeWidth={12}
        linkCurvature={0.5}
        node={<SankeyNode />}
        link={{ stroke: "hsl(var(--chart-2))", strokeOpacity: 0.22 }}
        margin={{ top: 8, right: 120, bottom: 8, left: 8 }}
      >
        <Tooltip content={<ChartTooltip />} />
      </Sankey>
    </ResponsiveContainer>
  );
}

function SankeyNode({ x, y, width, height, payload }: any) {
  if (x == null) return null;
  const right = x < 250;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} rx={2} fill="hsl(var(--chart-2))" fillOpacity={0.85} />
      <text
        x={right ? x + width + 6 : x - 6}
        y={y + height / 2}
        textAnchor={right ? "start" : "end"}
        dominantBaseline="middle"
        className="fill-foreground"
        fontSize={11}
      >
        {payload?.name}
      </text>
    </g>
  );
}

// ---- Heatmap (DCF sensitivity + risk matrix) -------------------------------
export function HeatmapViz({
  rows,
  cols,
  values,
  format = (v) => formatCompact(v),
  binary = false,
}: {
  rows: string[];
  cols: string[];
  values: (number | null)[][];
  format?: (v: number) => string;
  binary?: boolean;
}) {
  const flat = values.flat().filter((v): v is number => v != null);
  const min = Math.min(...flat, 0);
  const max = Math.max(...flat, 1);
  const color = (v: number | null) => {
    if (v == null) return "hsl(var(--muted))";
    if (binary) return v > 0 ? "hsl(var(--chart-2))" : "hsl(var(--muted))";
    const t = max === min ? 0.5 : (v - min) / (max - min);
    return `color-mix(in srgb, hsl(var(--chart-2)) ${Math.round(t * 100)}%, hsl(var(--muted)))`;
  };
  return (
    <div className="overflow-x-auto">
      <table className="border-separate" style={{ borderSpacing: 3 }}>
        <thead>
          <tr>
            <th />
            {cols.map((c) => (
              <th key={c} className="px-1 pb-1 text-center text-[10px] font-medium text-muted-foreground">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r}>
              <td className="pr-2 text-right text-[10px] font-medium text-muted-foreground whitespace-nowrap">
                {r}
              </td>
              {cols.map((_, j) => {
                const v = values[i]?.[j] ?? null;
                return (
                  <td key={j}>
                    <div
                      title={v != null ? format(v) : "—"}
                      className="flex h-9 min-w-[46px] items-center justify-center rounded-md text-[10px] font-medium tabular text-foreground/90"
                      style={{ background: color(v) }}
                    >
                      {binary ? (v ? "●" : "") : v != null ? format(v) : "—"}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---- Peer scatter ----------------------------------------------------------
export function ScatterViz({
  data,
  xLabel,
  yLabel,
  height = 300,
}: {
  data: { x: number; y: number; label: string }[];
  xLabel: string;
  yLabel: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ScatterChart margin={{ top: 12, right: 16, bottom: 24, left: 4 }}>
        <CartesianGrid stroke="hsl(var(--chart-grid))" strokeDasharray="4 4" />
        <XAxis
          type="number"
          dataKey="x"
          name={xLabel}
          {...axisProps}
          tickFormatter={(v) => formatCompact(Number(v))}
          label={{ value: xLabel, position: "insideBottom", offset: -12, fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
        />
        <YAxis type="number" dataKey="y" name={yLabel} {...axisProps} width={48} tickFormatter={(v) => formatCompact(Number(v))} />
        <ZAxis range={[120, 120]} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} content={<ScatterTip xl={xLabel} yl={yLabel} />} />
        <Scatter data={data} fill="hsl(var(--chart-2))">
          {data.map((_, i) => (
            <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function ScatterTip({ active, payload, xl, yl }: any) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 shadow-card">
      <p className="mb-1 text-xs font-semibold text-foreground">{p.label}</p>
      <p className="text-xs text-muted-foreground">{xl}: <span className="font-mono text-foreground">{formatCompact(p.x)}</span></p>
      <p className="text-xs text-muted-foreground">{yl}: <span className="font-mono text-foreground">{formatCompact(p.y)}</span></p>
    </div>
  );
}

// ---- Entity network (companies to risks) -----------------------------------
export function EntityNetworkViz({
  nodes,
  links,
  height = 460,
}: {
  nodes: { id: string; label: string; kind: string; degree?: number }[];
  links: { source: string; target: string }[];
  height?: number;
}) {
  const W = 640;
  const H = height;
  const cx = W / 2;
  const cy = H / 2;
  const companies = nodes.filter((n) => n.kind === "company");
  const risks = nodes.filter((n) => n.kind === "risk");

  const pos = new Map<string, { x: number; y: number }>();
  const place = (arr: typeof nodes, radius: number) => {
    arr.forEach((n, i) => {
      const a = (i / Math.max(1, arr.length)) * Math.PI * 2 - Math.PI / 2;
      pos.set(n.id, { x: cx + radius * Math.cos(a), y: cy + radius * Math.sin(a) });
    });
  };
  const rMin = Math.min(W, H) / 2;
  place(companies, rMin - 40);
  place(risks, rMin - 150);
  const maxDeg = Math.max(1, ...risks.map((r) => r.degree ?? 1));

  return (
    <div className="overflow-hidden">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Entity network">
        {links.map((l, i) => {
          const a = pos.get(l.source);
          const b = pos.get(l.target);
          if (!a || !b) return null;
          return <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="hsl(var(--chart-grid))" strokeWidth={1} strokeOpacity={0.5} />;
        })}
        {risks.map((n) => {
          const p = pos.get(n.id)!;
          const size = 5 + 10 * ((n.degree ?? 1) / maxDeg);
          return (
            <g key={n.id}>
              <circle cx={p.x} cy={p.y} r={size} fill="#f59e0b" fillOpacity={0.9} />
              <text x={p.x} y={p.y - size - 4} textAnchor="middle" fontSize={9} className="fill-muted-foreground">{n.label}</text>
            </g>
          );
        })}
        {companies.map((n) => {
          const p = pos.get(n.id)!;
          return (
            <g key={n.id}>
              <circle cx={p.x} cy={p.y} r={7} fill="hsl(var(--chart-2))" />
              <text x={p.x} y={p.y - 10} textAnchor="middle" fontSize={10} fontWeight={600} className="fill-foreground">{n.label}</text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
