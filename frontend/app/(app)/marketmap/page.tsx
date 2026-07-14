"use client";

import { motion } from "framer-motion";
import { GitFork, Layers, Network } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type GraphNetwork, type IncomeFlow, type RiskHeatmap } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { EntityNetworkViz, HeatmapViz, SankeyViz } from "@/components/charts/chart-kit";
import { formatCompact } from "@/lib/utils";

export default function MarketMapPage() {
  const [tickers, setTickers] = useState<string[]>([]);
  const [active, setActive] = useState("AAPL");

  const [flow, setFlow] = useState<IncomeFlow | null>(null);
  const [flowLoading, setFlowLoading] = useState(true);
  const [heatmap, setHeatmap] = useState<RiskHeatmap | null>(null);
  const [network, setNetwork] = useState<GraphNetwork | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .meta()
      .then((m) => setTickers(m.tickers?.length ? m.tickers : ["AAPL"]))
      .catch(() => setTickers(["AAPL"]));
    Promise.allSettled([api.graphHeatmap(), api.graphNetwork()])
      .then(([h, n]) => {
        setHeatmap(h.status === "fulfilled" ? h.value : null);
        setNetwork(n.status === "fulfilled" ? n.value : null);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!active) return;
    setFlowLoading(true);
    setFlow(null);
    api
      .incomeFlow(active)
      .then(setFlow)
      .catch(() => setFlow(null))
      .finally(() => setFlowLoading(false));
  }, [active]);

  const sankeyNodes = flow
    ? Array.from(new Set(flow.links.flatMap((l) => [l.source, l.target])))
    : [];

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Market map"
        description="See the whole picture: an income statement as one flow, where risk concentrates across companies, and the entity graph that powers relationship answers."
      />

      {/* Income-statement Sankey */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <GitFork className="h-4 w-4 rotate-90 text-accent" />
              <h3 className="text-sm font-semibold">Income statement — where every dollar goes</h3>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {tickers.map((t) => (
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
          {flowLoading ? (
            <Skeleton className="h-[340px]" />
          ) : flow ? (
            <>
              <p className="mb-2 text-xs text-muted-foreground">
                {flow.ticker}: revenue{" "}
                <span className="font-mono text-foreground">${formatCompact(flow.revenue)}</span>
                {flow.net_income != null && (
                  <>
                    {" "}→ net income{" "}
                    <span className="font-mono text-emerald-500">${formatCompact(flow.net_income)}</span>
                  </>
                )}
                . Every figure filed with the SEC.
              </p>
              <SankeyViz nodes={sankeyNodes} links={flow.links} />
            </>
          ) : (
            <EmptyState icon={GitFork} title="No income data" description={`Not enough filed detail to chart ${active}.`} />
          )}
        </Card>
      </motion.div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Risk heatmap */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <Card className="p-5">
            <div className="mb-4 flex items-center gap-2">
              <Layers className="h-4 w-4 text-accent" />
              <h3 className="text-sm font-semibold">Risk exposure — companies × topics</h3>
            </div>
            {loading ? (
              <Skeleton className="h-64" />
            ) : heatmap && heatmap.companies.length ? (
              <HeatmapViz
                rows={heatmap.companies}
                cols={heatmap.topics}
                values={heatmap.matrix}
                binary
              />
            ) : (
              <EmptyState icon={Layers} title="No graph yet" description="Ingest filings to build the risk matrix." />
            )}
          </Card>
        </motion.div>

        {/* Entity network */}
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <Card className="p-5">
            <div className="mb-4 flex items-center gap-2">
              <Network className="h-4 w-4 text-accent" />
              <h3 className="text-sm font-semibold">Entity graph — companies linked by shared risk</h3>
            </div>
            {loading ? (
              <Skeleton className="h-[460px]" />
            ) : network && network.nodes.length ? (
              <EntityNetworkViz nodes={network.nodes} links={network.links} />
            ) : (
              <EmptyState icon={Network} title="No graph yet" description="This is the graph behind GraphRAG relationship answers." />
            )}
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
