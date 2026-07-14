"use client";

import { motion } from "framer-motion";
import { Calculator, Loader2, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type Dcf } from "@/lib/api";
import { formatCompact } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { AreaViz, HeatmapViz } from "@/components/charts/chart-kit";

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function Assumption({
  label,
  value,
  onChange,
  min,
  max,
  step,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step: number;
}) {
  return (
    <div>
      <div className="flex items-center justify-between">
        <label className="text-xs text-muted-foreground">{label}</label>
        <span className="font-mono text-xs tabular text-foreground">{pct(value)}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="mt-1 w-full accent-[color:hsl(var(--accent))]"
      />
    </div>
  );
}

export default function ValuationPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [active, setActive] = useState("AAPL");
  const [dcf, setDcf] = useState<Dcf | null>(null);
  const [loading, setLoading] = useState(true);

  const [growth, setGrowth] = useState(0.1);
  const [discount, setDiscount] = useState(0.09);
  const [terminal, setTerminal] = useState(0.025);

  useEffect(() => {
    api
      .meta()
      .then((m) => setTickers(m.tickers?.length ? m.tickers : ["AAPL"]))
      .catch(() => setTickers(["AAPL"]));
  }, []);

  const load = useCallback(
    (ticker: string, overrides?: Record<string, number>) => {
      setLoading(true);
      const p = overrides ? api.dcfCustom(ticker, overrides) : api.dcf(ticker);
      p.then((d) => {
        setDcf(d);
        setGrowth(d.assumptions.growth_rate);
        setDiscount(d.assumptions.discount_rate);
        setTerminal(d.assumptions.terminal_growth);
      })
        .catch(() => setDcf(null))
        .finally(() => setLoading(false));
    },
    [],
  );

  useEffect(() => {
    if (active) load(active);
  }, [active, load]);

  function recompute() {
    load(active, { growth_rate: growth, discount_rate: discount, terminal_growth: terminal });
  }

  const fcfChart =
    dcf?.projected_fcf.map((p) => ({ x: `Y${p.year}`, y: p.fcf })) ?? [];
  const undervalued = (dcf?.upside_pct ?? 0) >= 0;

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Valuation"
        description="A transparent two-stage DCF built from the company's own filed cash flows. Every assumption is yours to change — this is a calculator, not a recommendation."
      />

      <div className="flex flex-wrap gap-1.5">
        {tickers.map((t) => (
          <button
            key={t}
            onClick={() => setActive(t)}
            className={`rounded-full border px-3 py-1 font-mono text-xs transition-colors cursor-pointer ${
              active === t
                ? "border-accent/40 bg-accent/15 text-accent"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading && !dcf ? (
        <Skeleton className="h-64" />
      ) : !dcf ? (
        <EmptyState
          icon={Calculator}
          title="No cash-flow data"
          description={`No filed free cash flow to value ${active}.`}
        />
      ) : (
        <>
          {/* Headline */}
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="p-6">
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Fair value / share</p>
                  <p className="mt-1 font-mono text-3xl font-semibold tabular text-foreground">
                    {dcf.fair_value_per_share != null ? `$${dcf.fair_value_per_share.toFixed(2)}` : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Market price</p>
                  <p className="mt-1 font-mono text-3xl font-semibold tabular text-foreground">
                    {dcf.market_price != null ? `$${dcf.market_price.toFixed(2)}` : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wide text-muted-foreground">Implied upside</p>
                  <p
                    className={`mt-1 font-mono text-3xl font-semibold tabular ${
                      dcf.upside_pct == null ? "text-foreground" : undervalued ? "text-emerald-500" : "text-red-500"
                    }`}
                  >
                    {dcf.upside_pct != null ? `${undervalued ? "+" : ""}${dcf.upside_pct}%` : "—"}
                  </p>
                </div>
              </div>
              <p className="mt-4 text-[11px] text-muted-foreground">{dcf.disclaimer}</p>
            </Card>
          </motion.div>

          <div className="grid gap-4 lg:grid-cols-2">
            {/* Assumptions */}
            <Card className="p-5">
              <h3 className="mb-4 text-sm font-semibold">Assumptions</h3>
              <div className="space-y-4">
                <Assumption label="Stage-1 FCF growth" value={growth} onChange={setGrowth} min={-0.05} max={0.3} step={0.005} />
                <Assumption label="Discount rate (WACC)" value={discount} onChange={setDiscount} min={0.05} max={0.2} step={0.005} />
                <Assumption label="Terminal growth" value={terminal} onChange={setTerminal} min={0} max={0.05} step={0.0025} />
              </div>
              <button
                onClick={recompute}
                className="mt-5 inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Calculator className="h-4 w-4" />}
                Recompute
              </button>
              <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-muted-foreground">Base FCF (filed)</p>
                  <p className="font-mono tabular text-foreground">{formatCompact(dcf.assumptions.base_fcf)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Net cash</p>
                  <p className="font-mono tabular text-foreground">{formatCompact(dcf.assumptions.net_cash)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Enterprise value</p>
                  <p className="font-mono tabular text-foreground">{formatCompact(dcf.enterprise_value)}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Terminal value</p>
                  <p className="font-mono tabular text-foreground">{formatCompact(dcf.terminal_value)}</p>
                </div>
              </div>
            </Card>

            {/* Projected FCF */}
            <Card className="p-5">
              <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
                <TrendingUp className="h-4 w-4 text-accent" /> Projected free cash flow
              </h3>
              <AreaViz data={fcfChart} height={260} />
            </Card>
          </div>

          {/* Sensitivity heatmap */}
          <Card className="p-5">
            <h3 className="mb-1 text-sm font-semibold">Sensitivity — fair value / share</h3>
            <p className="mb-4 text-xs text-muted-foreground">
              How the valuation moves with growth (rows) × discount rate (columns). The honest output of a DCF isn&apos;t one number — it&apos;s this surface.
            </p>
            <HeatmapViz
              rows={dcf.sensitivity.growth_rates.map((g) => pct(g))}
              cols={dcf.sensitivity.discount_rates.map((d) => pct(d))}
              values={dcf.sensitivity.grid}
              format={(v) => `$${v.toFixed(0)}`}
            />
          </Card>
        </>
      )}
    </div>
  );
}
