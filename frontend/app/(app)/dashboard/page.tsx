"use client";

import { motion } from "framer-motion";
import { Boxes, Database, GitBranch, Layers, Loader2, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  api,
  type AgentAnswer,
  type CorpusStats,
  type GraphStats,
} from "@/lib/api";
import { formatCompact } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { BarViz, DonutViz, CHART_COLORS } from "@/components/charts/chart-kit";

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  delay = 0,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  hint?: string;
  delay?: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
    >
      <Card className="p-5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          <Icon className="h-4 w-4 text-accent" />
        </div>
        <p className="mt-3 font-mono text-2xl font-semibold tabular text-foreground">{value}</p>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </Card>
    </motion.div>
  );
}

export default function DashboardPage() {
  const [corpus, setCorpus] = useState<CorpusStats | null>(null);
  const [graph, setGraph] = useState<GraphStats | null>(null);
  const [tickers, setTickers] = useState<string[]>([]);
  const [active, setActive] = useState<string>("");
  const [answer, setAnswer] = useState<AgentAnswer | null>(null);
  const [loading, setLoading] = useState(true);
  const [figLoading, setFigLoading] = useState(false);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    Promise.all([api.corpusStats(), api.graphStats(), api.meta()])
      .then(([c, g, m]) => {
        setCorpus(c);
        setGraph(g);
        setTickers(m.tickers || []);
        const first = Object.keys(c.chunks_by_ticker)[0] || m.tickers?.[0] || "";
        setActive(first);
      })
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!active) return;
    setFigLoading(true);
    setAnswer(null);
    api
      .ask(`Key financial figures, margins and growth for ${active}`, [active])
      .then(setAnswer)
      .catch(() => {})
      .finally(() => setFigLoading(false));
  }, [active]);

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
    () =>
      graph?.by_kind
        ? Object.entries(graph.by_kind).map(([x, y]) => ({ x, y }))
        : [],
    [graph],
  );

  const figures =
    answer?.charts?.[0]?.series?.[0]?.points?.filter((p) => Number.isFinite(p.y)) ?? [];

  if (offline) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <PageHeader title="Ticker Dashboard" />
        <div className="mt-6">
          <EmptyState
            icon={Database}
            title="Backend unreachable"
            description="Start the FastAPI backend and set NEXT_PUBLIC_API_URL to view live corpus and graph analytics."
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Ticker Dashboard"
        description="Live view of the ingested corpus, the GraphRAG entity graph, and per-company figures — all traced to real filings."
      />

      {/* Stat row */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {loading || !corpus ? (
          Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)
        ) : (
          <>
            <StatCard
              icon={Layers}
              label="Vector chunks"
              value={formatCompact(corpus.vector_chunks)}
              hint={corpus.embed_backend}
              delay={0}
            />
            <StatCard
              icon={Boxes}
              label="Tickers"
              value={String(Object.keys(corpus.chunks_by_ticker).length || tickers.length)}
              hint="ingested companies"
              delay={0.05}
            />
            <StatCard
              icon={GitBranch}
              label="Graph nodes"
              value={formatCompact(graph?.nodes ?? 0)}
              hint={`${formatCompact(graph?.edges ?? 0)} edges`}
              delay={0.1}
            />
            <StatCard
              icon={Database}
              label="BM25 docs"
              value={formatCompact(corpus.bm25_docs)}
              hint="lexical index"
              delay={0.15}
            />
          </>
        )}
      </div>

      {/* Corpus + graph charts */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="p-5">
          <h3 className="mb-4 text-sm font-semibold">Chunks by ticker</h3>
          {loading ? (
            <Skeleton className="h-64" />
          ) : tickerBars.length ? (
            <BarViz data={tickerBars} />
          ) : (
            <EmptyState icon={Layers} title="No corpus yet" description="Run ingestion to populate." />
          )}
        </Card>

        <Card className="p-5">
          <h3 className="mb-4 text-sm font-semibold">Entity graph composition</h3>
          {loading ? (
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
            <EmptyState icon={GitBranch} title="No graph yet" description="Run ingestion to build it." />
          )}
        </Card>
      </div>

      {/* Per-ticker figures via /ask */}
      <Card className="p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-accent" />
            <h3 className="text-sm font-semibold">Key figures</h3>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(Object.keys(corpus?.chunks_by_ticker ?? {}).length
              ? Object.keys(corpus!.chunks_by_ticker)
              : tickers
            ).map((t) => (
              <button
                key={t}
                onClick={() => setActive(t)}
                className={`rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors cursor-pointer ${
                  active === t
                    ? "border-accent/40 bg-accent/15 text-accent"
                    : "border-border text-muted-foreground hover:text-foreground"
                }`}
              >
                {t}
              </button>
            ))}
          </div>
        </div>
        {figLoading ? (
          <div className="flex h-64 items-center justify-center text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : figures.length ? (
          <BarViz data={figures} color={CHART_COLORS[3]} height={300} />
        ) : (
          <EmptyState
            icon={TrendingUp}
            title="No figures extracted"
            description={`The analyst found no chartable figures for ${active}. Try another ticker.`}
          />
        )}
      </Card>
    </div>
  );
}
