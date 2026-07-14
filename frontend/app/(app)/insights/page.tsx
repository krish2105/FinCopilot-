"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  ExternalLink,
  GitCompareArrows,
  Layers,
  Loader2,
  PieChart,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  type Fundamentals,
  type PeerTable,
  type PortfolioOverlap,
  type RedFlagReport,
  type RiskDiff,
} from "@/lib/api";
import { formatCompact } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";
import { BarViz, CHART_COLORS } from "@/components/charts/chart-kit";

const SEVERITY_STYLE: Record<string, string> = {
  high: "border-red-500/40 bg-red-500/10 text-red-500",
  medium: "border-amber-500/40 bg-amber-500/10 text-amber-500",
  low: "border-border bg-muted text-muted-foreground",
};

const CHANGE_STYLE: Record<string, { cls: string; label: string }> = {
  new: { cls: "border-red-500/40 bg-red-500/10 text-red-500", label: "NEW" },
  escalated: { cls: "border-amber-500/40 bg-amber-500/10 text-amber-500", label: "ESCALATED" },
  removed: { cls: "border-emerald-500/40 bg-emerald-500/10 text-emerald-500", label: "DROPPED" },
};

function Section({
  icon: Icon,
  title,
  subtitle,
  children,
  delay = 0,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
    >
      <Card className="p-5">
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-accent/30 bg-accent/10">
            <Icon className="h-4 w-4 text-accent" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold text-foreground">{title}</h3>
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          </div>
        </div>
        {children}
      </Card>
    </motion.div>
  );
}

export default function InsightsPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [active, setActive] = useState("AAPL");

  const [diff, setDiff] = useState<RiskDiff | null>(null);
  const [flags, setFlags] = useState<RedFlagReport | null>(null);
  const [fund, setFund] = useState<Fundamentals | null>(null);
  const [loading, setLoading] = useState(true);

  // Portfolio
  const [holdings, setHoldings] = useState<string[]>(["AAPL", "MSFT", "NVDA"]);
  const [overlap, setOverlap] = useState<PortfolioOverlap | null>(null);
  const [peers, setPeers] = useState<PeerTable | null>(null);
  const [pLoading, setPLoading] = useState(false);

  useEffect(() => {
    api
      .meta()
      .then((m) => {
        const list = m.tickers?.length ? m.tickers : ["AAPL", "MSFT"];
        setTickers(list);
        setActive((a) => (list.includes(a) ? a : list[0]));
      })
      .catch(() => setTickers(["AAPL", "MSFT"]));
  }, []);

  useEffect(() => {
    if (!active) return;
    setLoading(true);
    setDiff(null);
    setFlags(null);
    setFund(null);
    Promise.allSettled([api.riskDiff(active), api.redFlags(active), api.fundamentals(active)])
      .then(([d, f, u]) => {
        setDiff(d.status === "fulfilled" ? d.value : null);
        setFlags(f.status === "fulfilled" ? f.value : null);
        setFund(u.status === "fulfilled" ? u.value : null);
      })
      .finally(() => setLoading(false));
  }, [active]);

  const runPortfolio = useCallback(() => {
    if (holdings.length < 2) return;
    setPLoading(true);
    Promise.allSettled([api.portfolio(holdings), api.peers(holdings)])
      .then(([o, p]) => {
        setOverlap(o.status === "fulfilled" ? o.value : null);
        setPeers(p.status === "fulfilled" ? p.value : null);
      })
      .finally(() => setPLoading(false));
  }, [holdings]);

  useEffect(() => {
    if (tickers.length) runPortfolio();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tickers.length]);

  function toggleHolding(t: string) {
    setHoldings((h) => (h.includes(t) ? h.filter((x) => x !== t) : [...h, t]));
  }

  const revenueBars =
    fund?.points
      ?.slice()
      .reverse()
      .filter((p) => p.revenue != null)
      .map((p) => ({ x: p.period.slice(0, 4), y: p.revenue as number })) ?? [];

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Insights"
        description="What you didn't think to ask — how disclosures changed, what's buried in the filings, and where your holdings are quietly concentrated."
      />

      {/* Company selector */}
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

      <div className="grid gap-4 lg:grid-cols-2">
        {/* 40a — Risk Diff */}
        <Section
          icon={GitCompareArrows}
          title={`Risk Diff — what changed at ${active}`}
          subtitle="Year-over-year movement in disclosed risk factors"
        >
          {loading ? (
            <Skeleton className="h-40" />
          ) : diff?.available ? (
            <>
              <div className="mb-3 flex items-center gap-2">
                <Badge variant="outline">{diff.year_from}</Badge>
                <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground" />
                <Badge variant="accent">{diff.year_to}</Badge>
              </div>
              {diff.summary && (
                <p className="mb-3 text-sm leading-relaxed text-muted-foreground">{diff.summary}</p>
              )}
              <ul className="space-y-2">
                {diff.changes.slice(0, 6).map((c, i) => {
                  const s = CHANGE_STYLE[c.change] ?? CHANGE_STYLE.new;
                  return (
                    <li key={i} className="rounded-lg border border-border p-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`rounded-full border px-1.5 py-0.5 text-[10px] font-semibold ${s.cls}`}
                        >
                          {s.label}
                        </span>
                        <span className="text-xs font-medium text-foreground">{c.topic}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">{c.detail}</p>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <EmptyState
              icon={GitCompareArrows}
              title="Not enough filings yet"
              description={diff?.message || "Two annual reports are needed to compare disclosures."}
            />
          )}
        </Section>

        {/* 40b — Red flags */}
        <Section
          icon={ShieldAlert}
          title={`Red flags — ${active}`}
          subtitle="Going concern · restatements · material weakness · litigation"
          delay={0.05}
        >
          {loading ? (
            <Skeleton className="h-40" />
          ) : flags && flags.flags.length ? (
            <ul className="space-y-2">
              {flags.flags.slice(0, 6).map((f, i) => (
                <li key={i} className="rounded-lg border border-border p-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded-full border px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                        SEVERITY_STYLE[f.severity] ?? SEVERITY_STYLE.low
                      }`}
                    >
                      {f.severity}
                    </span>
                    <span className="text-xs font-medium capitalize text-foreground">
                      {f.category.replace(/_/g, " ")}
                    </span>
                    {f.source_url && (
                      <a
                        href={f.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-auto text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="h-3.5 w-3.5" />
                      </a>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{f.detail}</p>
                </li>
              ))}
            </ul>
          ) : (
            <div className="flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
              <AlertTriangle className="h-4 w-4 text-emerald-500" />
              <p className="text-xs text-emerald-600 dark:text-emerald-400">
                No red flags detected across {flags?.scanned_sources ?? 0} scanned sources.
              </p>
            </div>
          )}
        </Section>
      </div>

      {/* 40c — Fundamentals */}
      <Section
        icon={TrendingUp}
        title={`Fundamentals — ${active}`}
        subtitle="Revenue, margins and EPS straight from the income statements"
        delay={0.1}
      >
        {loading ? (
          <Skeleton className="h-56" />
        ) : fund && fund.points.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <p className="mb-2 text-xs text-muted-foreground">Revenue by year</p>
              <BarViz data={revenueBars} color={CHART_COLORS[1]} height={220} />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-muted-foreground">
                  <tr>
                    <th className="pb-2 font-medium">Year</th>
                    <th className="pb-2 text-right font-medium">Revenue</th>
                    <th className="pb-2 text-right font-medium">Net margin</th>
                    <th className="pb-2 text-right font-medium">EPS</th>
                  </tr>
                </thead>
                <tbody className="font-mono tabular">
                  {fund.points.map((p) => (
                    <tr key={p.period} className="border-t border-border/60">
                      <td className="py-2 text-foreground">{p.period.slice(0, 4)}</td>
                      <td className="py-2 text-right text-foreground">
                        {p.revenue != null ? formatCompact(p.revenue) : "—"}
                      </td>
                      <td
                        className={`py-2 text-right ${
                          (p.net_margin ?? 0) >= 20 ? "text-emerald-500" : "text-muted-foreground"
                        }`}
                      >
                        {p.net_margin != null ? `${p.net_margin.toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-2 text-right text-foreground">
                        {p.eps != null ? p.eps.toFixed(2) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState
            icon={TrendingUp}
            title="No fundamentals"
            description="Add a free FMP_API_KEY on the backend to pull income statements."
          />
        )}
      </Section>

      {/* 40d — Portfolio risk overlap */}
      <Section
        icon={PieChart}
        title="Portfolio risk overlap"
        subtitle="Concentration is the danger a price chart can't show you"
        delay={0.15}
      >
        <div className="mb-4 flex flex-wrap items-center gap-1.5">
          <span className="mr-1 text-xs text-muted-foreground">Holdings:</span>
          {tickers.map((t) => (
            <button
              key={t}
              onClick={() => toggleHolding(t)}
              className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors cursor-pointer ${
                holdings.includes(t)
                  ? "border-accent/40 bg-accent/15 text-accent"
                  : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {t}
            </button>
          ))}
          <Button size="sm" className="ml-2" onClick={runPortfolio} disabled={holdings.length < 2}>
            {pLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Layers className="h-4 w-4" />}
            Analyze
          </Button>
        </div>

        {pLoading ? (
          <Skeleton className="h-40" />
        ) : (
          <>
            {overlap?.summary && (
              <div className="mb-4 rounded-xl border border-accent/30 bg-accent/10 p-4">
                <p className="text-sm text-foreground">{overlap.summary}</p>
              </div>
            )}

            {overlap?.shared_risks?.length ? (
              <ul className="mb-5 space-y-2">
                {overlap.shared_risks.slice(0, 6).map((s) => (
                  <li
                    key={s.topic}
                    className="flex flex-wrap items-center gap-2 rounded-lg border border-border p-3"
                  >
                    <span className="text-xs font-medium capitalize text-foreground">
                      {s.topic.replace(/_/g, " ")}
                    </span>
                    <span className="flex gap-1">
                      {s.companies.map((c) => (
                        <span
                          key={c}
                          className="rounded border border-border px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                        >
                          {c}
                        </span>
                      ))}
                    </span>
                    <span className="ml-auto flex items-center gap-2">
                      <span className="h-1.5 w-24 overflow-hidden rounded-full bg-muted">
                        <span
                          className="block h-full rounded-full bg-accent"
                          style={{ width: `${Math.round(s.concentration * 100)}%` }}
                        />
                      </span>
                      <span className="font-mono text-[11px] tabular text-foreground">
                        {Math.round(s.concentration * 100)}%
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mb-5 text-xs text-muted-foreground">
                No shared risk topics found across these holdings yet (the entity graph builds
                during ingestion).
              </p>
            )}

            {/* Peer benchmarking */}
            {peers?.rows?.length ? (
              <div className="overflow-x-auto">
                <p className="mb-2 text-xs font-medium text-foreground">Peer benchmarking</p>
                <table className="w-full text-left text-xs">
                  <thead className="text-muted-foreground">
                    <tr>
                      <th className="pb-2 font-medium">Ticker</th>
                      <th className="pb-2 text-right font-medium">Price</th>
                      <th className="pb-2 text-right font-medium">Chg</th>
                      <th className="pb-2 text-right font-medium">Mkt cap</th>
                      <th className="pb-2 text-right font-medium">Revenue</th>
                      <th className="pb-2 text-right font-medium">Net margin</th>
                    </tr>
                  </thead>
                  <tbody className="font-mono tabular">
                    {peers.rows.map((r) => {
                      const up = (r.change_pct ?? 0) >= 0;
                      return (
                        <tr key={r.ticker} className="border-t border-border/60">
                          <td className="py-2 font-semibold text-foreground">{r.ticker}</td>
                          <td className="py-2 text-right text-foreground">
                            {r.price != null ? `$${r.price.toFixed(2)}` : "—"}
                          </td>
                          <td
                            className={`py-2 text-right ${up ? "text-emerald-500" : "text-red-500"}`}
                          >
                            {r.change_pct != null ? (
                              <span className="inline-flex items-center">
                                {up ? (
                                  <ArrowUpRight className="h-3 w-3" />
                                ) : (
                                  <ArrowDownRight className="h-3 w-3" />
                                )}
                                {Math.abs(r.change_pct).toFixed(2)}%
                              </span>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="py-2 text-right text-foreground">
                            {r.market_cap != null ? formatCompact(r.market_cap) : "—"}
                          </td>
                          <td className="py-2 text-right text-foreground">
                            {r.revenue != null ? formatCompact(r.revenue) : "—"}
                          </td>
                          <td className="py-2 text-right text-foreground">
                            {r.net_margin != null ? `${r.net_margin.toFixed(1)}%` : "—"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        )}
      </Section>
    </div>
  );
}
