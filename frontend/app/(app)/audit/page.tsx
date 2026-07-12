"use client";

import { motion } from "framer-motion";
import { ClipboardList, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, type AuditRecord } from "@/lib/api";
import { timeAgo } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RouteBadge } from "@/components/route-badge";
import { Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";

const FILTERS = ["all", "ok", "insufficient_evidence"] as const;

export default function AuditPage() {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("all");

  const load = useCallback(() => {
    setLoading(true);
    api
      .audit(200)
      .then((r) => {
        setRecords(r.records);
        setCount(r.count);
        setOffline(false);
      })
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => load(), [load]);

  const shown = records.filter((r) => filter === "all" || r.verdict === filter);

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Audit Log"
        description="Every query, the route it took, the sources and LLM providers used, the verdict, faithfulness, and latency — the compliance trail and FinOps story in one table."
      >
        <Button variant="secondary" size="sm" onClick={load}>
          <RefreshCw className="h-3.5 w-3.5" /> Refresh
        </Button>
      </PageHeader>

      <div className="flex flex-wrap items-center gap-2">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors cursor-pointer ${
              filter === f
                ? "border-accent/40 bg-accent/15 text-accent"
                : "border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {f === "all" ? "All" : f === "ok" ? "Verified" : "Insufficient"}
          </button>
        ))}
        <span className="ml-auto text-xs text-muted-foreground">
          {count} total record{count === 1 ? "" : "s"}
        </span>
      </div>

      {offline ? (
        <EmptyState
          icon={ClipboardList}
          title="Backend unreachable"
          description="Start the FastAPI backend and set NEXT_PUBLIC_API_URL to view the audit trail."
        />
      ) : loading ? (
        <div className="space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : shown.length === 0 ? (
        <EmptyState
          icon={ClipboardList}
          title="No queries yet"
          description="Ask something in the Workspace and it will be recorded here."
        />
      ) : (
        <Card className="overflow-hidden p-0">
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                  <th className="px-4 py-3 font-medium">Time</th>
                  <th className="px-4 py-3 font-medium">Query</th>
                  <th className="px-4 py-3 font-medium">Route</th>
                  <th className="px-4 py-3 font-medium">Verdict</th>
                  <th className="px-4 py-3 font-medium">Faithful</th>
                  <th className="px-4 py-3 font-medium">Providers</th>
                  <th className="px-4 py-3 text-right font-medium">Latency</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
                  <motion.tr
                    key={r.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: Math.min(i * 0.02, 0.3) }}
                    className="border-b border-border/60 last:border-0 hover:bg-muted/40"
                  >
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-muted-foreground">
                      {timeAgo(r.timestamp)}
                    </td>
                    <td className="max-w-[240px] px-4 py-3">
                      <span className="block truncate text-foreground" title={r.query}>
                        {r.query}
                      </span>
                      {r.tickers.length > 0 && (
                        <span className="font-mono text-[11px] text-muted-foreground">
                          {r.tickers.join(", ")}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <RouteBadge route={r.route} />
                    </td>
                    <td className="px-4 py-3">
                      {r.verdict === "ok" ? (
                        <Badge variant="positive">Verified</Badge>
                      ) : (
                        <Badge variant="warning">Insufficient</Badge>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-14 overflow-hidden rounded-full bg-muted">
                          <div
                            className="h-full rounded-full bg-positive"
                            style={{ width: `${Math.round(r.faithfulness_score * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono text-xs tabular text-muted-foreground">
                          {Math.round(r.faithfulness_score * 100)}%
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {r.providers.slice(0, 2).map((p) => (
                          <span
                            key={p}
                            className="rounded border border-border bg-muted/40 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
                          >
                            {p.split(":")[0]}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-right font-mono text-xs tabular text-muted-foreground">
                      {r.latency_ms} ms
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
