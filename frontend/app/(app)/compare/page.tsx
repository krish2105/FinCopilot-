"use client";

import { motion } from "framer-motion";
import { ArrowLeftRight, Loader2, Sparkles, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  api,
  PRICE_RANGES,
  type AgentAnswer,
  type PriceHistory,
  type PriceRange,
  type Quote,
} from "@/lib/api";
import { formatCompact } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";
import { PriceViz } from "@/components/charts/chart-kit";
import { AnswerCard } from "@/components/workspace/answer-card";

const CURRENCY: Record<string, string> = { USD: "$", EUR: "€", GBP: "£", INR: "₹", JPY: "¥" };
const fmt = (n: number | null, cur = "USD") =>
  n == null ? "—" : (CURRENCY[cur] ?? `${cur} `) + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** One company column: quote header + price chart. */
function Side({
  tickers,
  value,
  onChange,
  quote,
  history,
  loading,
}: {
  tickers: string[];
  value: string;
  onChange: (t: string) => void;
  quote: Quote | null;
  history: PriceHistory | null;
  loading: boolean;
}) {
  const up = (quote?.change ?? history?.change_pct ?? 0) >= 0;
  return (
    <Card className="p-5">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mb-4 w-full rounded-lg border border-border bg-card px-3 py-2 font-mono text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
      >
        {tickers.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </select>

      {loading ? (
        <Skeleton className="h-20" />
      ) : quote ? (
        <>
          <p className="truncate text-sm font-semibold text-foreground">{quote.name}</p>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="font-mono text-2xl font-semibold tabular text-foreground">
              {fmt(quote.price, quote.currency)}
            </span>
            {quote.change_pct != null && (
              <span className={`text-sm font-medium ${up ? "text-emerald-500" : "text-red-500"}`}>
                {up ? "+" : ""}
                {quote.change_pct.toFixed(2)}%
              </span>
            )}
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
            <div>
              <p className="text-muted-foreground">Mkt cap</p>
              <p className="font-mono tabular text-foreground">
                {quote.market_cap != null ? formatCompact(quote.market_cap) : "—"}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">P/E</p>
              <p className="font-mono tabular text-foreground">
                {quote.pe != null ? quote.pe.toFixed(1) : "—"}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Volume</p>
              <p className="font-mono tabular text-foreground">
                {quote.volume != null ? formatCompact(quote.volume) : "—"}
              </p>
            </div>
          </div>
        </>
      ) : (
        <p className="text-xs text-muted-foreground">
          No live quote for {value}. Add an FMP_API_KEY on the backend.
        </p>
      )}

      <div className="mt-4">
        {loading ? (
          <Skeleton className="h-[220px]" />
        ) : history && history.points.length ? (
          <PriceViz data={history.points} up={up} height={220} />
        ) : (
          <div className="flex h-[220px] items-center justify-center text-xs text-muted-foreground">
            No price history
          </div>
        )}
      </div>
    </Card>
  );
}

export default function ComparePage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [left, setLeft] = useState("AAPL");
  const [right, setRight] = useState("MSFT");
  const [range, setRange] = useState<PriceRange>("1Y");

  const [lq, setLq] = useState<Quote | null>(null);
  const [rq, setRq] = useState<Quote | null>(null);
  const [lh, setLh] = useState<PriceHistory | null>(null);
  const [rh, setRh] = useState<PriceHistory | null>(null);
  const [loadingL, setLoadingL] = useState(true);
  const [loadingR, setLoadingR] = useState(true);

  const [answer, setAnswer] = useState<AgentAnswer | null>(null);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    api
      .meta()
      .then((m) => setTickers(m.tickers?.length ? m.tickers : ["AAPL", "MSFT"]))
      .catch(() => setTickers(["AAPL", "MSFT"]));
  }, []);

  const load = useCallback(
    (t: string, r: PriceRange, setQ: (q: Quote | null) => void, setH: (h: PriceHistory | null) => void, setL: (b: boolean) => void) => {
      setL(true);
      Promise.allSettled([api.quote(t), api.history(t, r)])
        .then(([q, h]) => {
          setQ(q.status === "fulfilled" ? q.value : null);
          setH(h.status === "fulfilled" ? h.value : null);
        })
        .finally(() => setL(false));
    },
    [],
  );

  useEffect(() => load(left, range, setLq, setLh, setLoadingL), [left, range, load]);
  useEffect(() => load(right, range, setRq, setRh, setLoadingR), [right, range, load]);

  async function compare() {
    setAsking(true);
    setAnswer(null);
    try {
      const a = await api.ask(
        `Compare ${left} and ${right}: revenue, margins, growth, and the key risks each discloses. Cite every figure.`,
        [left, right],
      );
      setAnswer(a);
    } catch {
      setAnswer(null);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Compare companies"
        description="Put two companies side by side — live prices and charts, plus a fully cited AI comparison drawn from their real filings."
      />

      {/* Range toggle */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <TrendingUp className="h-4 w-4 text-accent" /> Price ({range})
        </div>
        <div className="flex gap-1">
          {PRICE_RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded-md px-2 py-1 font-mono text-[11px] transition-colors cursor-pointer ${
                range === r ? "bg-accent/15 text-accent" : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* Side-by-side */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="grid gap-4 lg:grid-cols-2"
      >
        <Side tickers={tickers} value={left} onChange={setLeft} quote={lq} history={lh} loading={loadingL} />
        <Side tickers={tickers} value={right} onChange={setRight} quote={rq} history={rh} loading={loadingR} />
      </motion.div>

      {/* AI comparison */}
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <ArrowLeftRight className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-semibold">
              AI comparison — {left} vs {right}
            </h3>
          </div>
          <Button size="sm" onClick={compare} disabled={asking || left === right}>
            {asking ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" /> Analyzing…
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" /> Compare with AI
              </>
            )}
          </Button>
        </div>

        <div className="mt-4">
          {left === right ? (
            <p className="text-xs text-muted-foreground">Pick two different companies to compare.</p>
          ) : asking ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin" />
            </div>
          ) : answer ? (
            <AnswerCard answer={answer} onCite={() => {}} />
          ) : (
            <EmptyState
              icon={Sparkles}
              title="No comparison yet"
              description="Run an AI comparison to get a cited, side-by-side read on both companies' filings."
            />
          )}
        </div>
      </Card>
    </div>
  );
}
