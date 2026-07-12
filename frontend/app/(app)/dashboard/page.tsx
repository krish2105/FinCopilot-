"use client";

import { motion } from "framer-motion";
import {
  Activity,
  ArrowDownRight,
  ArrowUpRight,
  CalendarClock,
  Database,
  GitBranch,
  Layers,
  Loader2,
  TrendingUp,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  PRICE_RANGES,
  type CorpusStats,
  type Earnings,
  type GraphStats,
  type PriceHistory,
  type PriceRange,
  type Quote,
} from "@/lib/api";
import { formatCompact } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { BarViz, DonutViz, PriceViz, CHART_COLORS } from "@/components/charts/chart-kit";

const CURRENCY_SYMBOL: Record<string, string> = {
  USD: "$",
  EUR: "€",
  GBP: "£",
  INR: "₹",
  JPY: "¥",
  AED: "AED ",
};

function fmtPrice(n: number | null, cur = "USD"): string {
  if (n == null) return "—";
  const sym = CURRENCY_SYMBOL[cur] ?? `${cur} `;
  return sym + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function TickerPills({
  tickers,
  active,
  onPick,
}: {
  tickers: string[];
  active: string;
  onPick: (t: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {tickers.map((t) => (
        <button
          key={t}
          onClick={() => onPick(t)}
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
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-0.5 font-mono text-sm tabular text-foreground">{value}</p>
    </div>
  );
}

function QuoteHeader({ quote }: { quote: Quote }) {
  const up = (quote.change ?? 0) >= 0;
  const Arrow = up ? ArrowUpRight : ArrowDownRight;
  const color = up ? "text-emerald-500" : "text-red-500";
  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-foreground">{quote.name}</h2>
            <span className="rounded-md border border-border px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
              {quote.ticker}
              {quote.exchange ? ` · ${quote.exchange}` : ""}
            </span>
          </div>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="font-mono text-3xl font-semibold tabular text-foreground">
              {fmtPrice(quote.price, quote.currency)}
            </span>
            <span className={`flex items-center gap-1 text-sm font-medium ${color}`}>
              <Arrow className="h-4 w-4" />
              {quote.change != null ? fmtPrice(Math.abs(quote.change), quote.currency) : "—"}
              {quote.change_pct != null ? ` (${up ? "+" : ""}${quote.change_pct.toFixed(2)}%)` : ""}
            </span>
          </div>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <MiniStat label="Mkt cap" value={quote.market_cap != null ? formatCompact(quote.market_cap) : "—"} />
        <MiniStat label="P/E" value={quote.pe != null ? quote.pe.toFixed(1) : "—"} />
        <MiniStat
          label="Day range"
          value={
            quote.day_low != null && quote.day_high != null
              ? `${quote.day_low.toFixed(2)}–${quote.day_high.toFixed(2)}`
              : "—"
          }
        />
        <MiniStat
          label="52w range"
          value={
            quote.fifty_two_week_low != null && quote.fifty_two_week_high != null
              ? `${formatCompact(quote.fifty_two_week_low)}–${formatCompact(quote.fifty_two_week_high)}`
              : "—"
          }
        />
        <MiniStat label="Volume" value={quote.volume != null ? formatCompact(quote.volume) : "—"} />
        <MiniStat label="Prev close" value={fmtPrice(quote.previous_close, quote.currency)} />
      </div>
    </div>
  );
}

function EarningsCard({ earnings }: { earnings: Earnings }) {
  return (
    <div>
      <div className="mb-3 flex items-center gap-2">
        <CalendarClock className="h-4 w-4 text-accent" />
        <h3 className="text-sm font-semibold">Earnings</h3>
        {earnings.next_date && (
          <span className="ml-auto rounded-full border border-accent/40 bg-accent/10 px-2 py-0.5 text-[11px] text-accent">
            Next report: {earnings.next_date}
          </span>
        )}
      </div>
      {earnings.history.length ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="text-muted-foreground">
              <tr>
                <th className="pb-2 font-medium">Date</th>
                <th className="pb-2 text-right font-medium">EPS est.</th>
                <th className="pb-2 text-right font-medium">EPS actual</th>
                <th className="pb-2 text-right font-medium">Surprise</th>
              </tr>
            </thead>
            <tbody className="font-mono tabular">
              {earnings.history.map((r) => {
                const beat = (r.surprise_pct ?? 0) >= 0;
                return (
                  <tr key={r.date} className="border-t border-border/60">
                    <td className="py-2 text-foreground">{r.date}</td>
                    <td className="py-2 text-right text-muted-foreground">
                      {r.eps_estimate != null ? r.eps_estimate.toFixed(2) : "—"}
                    </td>
                    <td className="py-2 text-right text-foreground">
                      {r.eps_reported != null ? r.eps_reported.toFixed(2) : "—"}
                    </td>
                    <td
                      className={`py-2 text-right ${
                        r.surprise_pct == null ? "text-muted-foreground" : beat ? "text-emerald-500" : "text-red-500"
                      }`}
                    >
                      {r.surprise_pct != null ? `${beat ? "+" : ""}${r.surprise_pct.toFixed(1)}%` : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="py-6 text-center text-xs text-muted-foreground">
          No reported earnings history{earnings.next_date ? " yet — see next report date above." : "."}
        </p>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [active, setActive] = useState<string>("");

  // market state (independent of the RAG corpus / DB)
  const [quote, setQuote] = useState<Quote | null>(null);
  const [history, setHistory] = useState<PriceHistory | null>(null);
  const [earnings, setEarnings] = useState<Earnings | null>(null);
  const [range, setRange] = useState<PriceRange>("1Y");
  const [loadingQuote, setLoadingQuote] = useState(true);
  const [loadingHist, setLoadingHist] = useState(true);
  const [mktError, setMktError] = useState(false);

  // corpus/graph state (secondary; loads separately so market always renders)
  const [corpus, setCorpus] = useState<CorpusStats | null>(null);
  const [graph, setGraph] = useState<GraphStats | null>(null);
  const [corpusReady, setCorpusReady] = useState(false);
  const [corpusFailed, setCorpusFailed] = useState(false);

  // bootstrap: tickers, then kick off corpus/graph independently
  useEffect(() => {
    api
      .meta()
      .then((m) => {
        const list = m.tickers || [];
        setTickers(list);
        setActive((cur) => cur || list[0] || "");
      })
      .catch(() => setMktError(true));

    Promise.all([api.corpusStats(), api.graphStats()])
      .then(([c, g]) => {
        setCorpus(c);
        setGraph(g);
      })
      .catch(() => setCorpusFailed(true))
      .finally(() => setCorpusReady(true));
  }, []);

  const loadHistory = useCallback((ticker: string, r: PriceRange) => {
    setLoadingHist(true);
    api
      .history(ticker, r)
      .then(setHistory)
      .catch(() => setHistory(null))
      .finally(() => setLoadingHist(false));
  }, []);

  // active ticker -> load quote + earnings + history
  useEffect(() => {
    if (!active) return;
    setLoadingQuote(true);
    setQuote(null);
    setEarnings(null);
    api
      .quote(active)
      .then(setQuote)
      .catch(() => setQuote(null))
      .finally(() => setLoadingQuote(false));
    api
      .earnings(active)
      .then(setEarnings)
      .catch(() => setEarnings(null));
    loadHistory(active, range);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const onRange = (r: PriceRange) => {
    setRange(r);
    if (active) loadHistory(active, r);
  };

  const up = (quote?.change ?? history?.change_pct ?? 0) >= 0;

  const tickerBars = useMemo(
    () =>
      corpus
        ? Object.entries(corpus.chunks_by_ticker)
            .map(([x, y]) => ({ x, y }))
            .sort((a, b) => b.y - a.y)
        : [],
    [corpus],
  );
  const kindData = useMemo(
    () => (graph?.by_kind ? Object.entries(graph.by_kind).map(([x, y]) => ({ x, y })) : []),
    [graph],
  );

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Ticker Dashboard"
        description="Live prices, interactive charts and earnings — plus the RAG corpus that grounds every cited answer."
      />

      {/* Ticker selector */}
      {tickers.length > 0 && (
        <TickerPills tickers={tickers} active={active} onPick={setActive} />
      )}

      {/* Quote + price chart */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <Card className="p-5">
          {loadingQuote ? (
            <Skeleton className="h-24" />
          ) : quote ? (
            <QuoteHeader quote={quote} />
          ) : (
            <EmptyState
              icon={Activity}
              title={mktError ? "Backend unreachable" : `No live quote for ${active || "—"}`}
              description={
                mktError
                  ? "Set NEXT_PUBLIC_API_URL to the API and redeploy."
                  : "Market data provider returned nothing. Add a free FMP_API_KEY on the backend for reliable quotes, or try another ticker."
              }
            />
          )}

          {/* Range toggle + chart */}
          <div className="mt-5 flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <TrendingUp className="h-4 w-4 text-accent" />
              Price
              {history?.change_pct != null && (
                <span className={up ? "text-emerald-500" : "text-red-500"}>
                  {up ? "+" : ""}
                  {history.change_pct.toFixed(2)}% · {range}
                </span>
              )}
            </div>
            <div className="flex gap-1">
              {PRICE_RANGES.map((r) => (
                <button
                  key={r}
                  onClick={() => onRange(r)}
                  className={`rounded-md px-2 py-1 font-mono text-[11px] transition-colors cursor-pointer ${
                    range === r
                      ? "bg-accent/15 text-accent"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>
          <div className="mt-3">
            {loadingHist ? (
              <div className="flex h-[300px] items-center justify-center text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : history && history.points.length ? (
              <PriceViz data={history.points} up={up} />
            ) : (
              <EmptyState
                icon={TrendingUp}
                title="No price history"
                description={`No chart data for ${active}. Try another range or ticker.`}
              />
            )}
          </div>
        </Card>
      </motion.div>

      {/* Earnings */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.4 }}
      >
        <Card className="p-5">
          {earnings ? (
            <EarningsCard earnings={earnings} />
          ) : (
            <div className="flex items-center gap-2 text-sm">
              <CalendarClock className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">
                No earnings data for {active || "—"}.
              </span>
            </div>
          )}
        </Card>
      </motion.div>

      {/* Under the hood — retrieval corpus (secondary; degrades inline) */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <Layers className="h-4 w-4 text-accent" /> Corpus — chunks by ticker
          </h3>
          {!corpusReady ? (
            <Skeleton className="h-64" />
          ) : tickerBars.length ? (
            <BarViz data={tickerBars} />
          ) : (
            <EmptyState
              icon={Database}
              title={corpusFailed ? "Corpus offline" : "No corpus yet"}
              description={
                corpusFailed
                  ? "The backend can't reach the database (check DATABASE_URL). Live prices above still work."
                  : "Seed filings to populate the RAG corpus."
              }
            />
          )}
        </Card>

        <Card className="p-5">
          <h3 className="mb-4 flex items-center gap-2 text-sm font-semibold">
            <GitBranch className="h-4 w-4 text-accent" /> Entity graph composition
          </h3>
          {!corpusReady ? (
            <Skeleton className="h-64" />
          ) : kindData.length ? (
            <div className="flex flex-col items-center gap-4 sm:flex-row">
              <div className="w-full sm:w-1/2">
                <DonutViz data={kindData} />
              </div>
              <ul className="grid w-full grid-cols-2 gap-2 sm:w-1/2 sm:grid-cols-1">
                {kindData.map((k, i) => (
                  <li key={k.x} className="flex items-center gap-2 text-xs">
                    <span
                      className="h-2.5 w-2.5 rounded-full"
                      style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
                    />
                    <span className="capitalize text-muted-foreground">{k.x}</span>
                    <span className="ml-auto font-mono tabular text-foreground">{k.y}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <EmptyState
              icon={GitBranch}
              title="No graph yet"
              description="Run ingestion to build the entity graph."
            />
          )}
        </Card>
      </div>
    </div>
  );
}
