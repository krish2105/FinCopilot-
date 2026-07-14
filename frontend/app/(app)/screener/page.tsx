"use client";

import { motion } from "framer-motion";
import { Filter, Loader2, Plus, SlidersHorizontal, X } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type ScreenResult } from "@/lib/api";
import { formatCompact } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";

interface FilterRow {
  field: string;
  op: string;
  value: number;
}

const PCT_FIELDS = new Set(["net_margin", "gross_margin", "operating_margin"]);
const LABELS: Record<string, string> = {
  revenue: "Revenue",
  net_income: "Net income",
  net_margin: "Net margin %",
  gross_margin: "Gross margin %",
  operating_margin: "Operating margin %",
  free_cash_flow: "Free cash flow",
  rnd_expense: "R&D expense",
  assets: "Total assets",
  cash: "Cash",
  eps: "EPS",
};

function fmtCell(field: string, v: number | string | null) {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  if (PCT_FIELDS.has(field)) return `${v.toFixed(1)}%`;
  if (field === "eps") return `$${v.toFixed(2)}`;
  return formatCompact(v);
}

export default function ScreenerPage() {
  const [fields, setFields] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterRow[]>([{ field: "net_margin", op: ">", value: 25 }]);
  const [result, setResult] = useState<ScreenResult | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .screenerFields()
      .then((r) => setFields(r.fields))
      .catch(() => setFields(Object.keys(LABELS)));
  }, []);

  function run() {
    setLoading(true);
    api
      .screen(filters)
      .then(setResult)
      .catch(() => setResult(null))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cols = result?.fields ?? Object.keys(LABELS);

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Screener"
        description="Filter the covered universe by filed fundamentals. Every value is a real SEC figure — no vendor estimates, no model-written SQL."
      />

      {/* Filter builder */}
      <Card className="p-5">
        <div className="mb-3 flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-accent" />
          <h3 className="text-sm font-semibold">Filters</h3>
        </div>
        <div className="space-y-2">
          {filters.map((f, i) => (
            <div key={i} className="flex flex-wrap items-center gap-2">
              <select
                value={f.field}
                onChange={(e) =>
                  setFilters((fs) => fs.map((x, j) => (j === i ? { ...x, field: e.target.value } : x)))
                }
                className="rounded-lg border border-border bg-card px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
              >
                {fields.map((fld) => (
                  <option key={fld} value={fld}>
                    {LABELS[fld] ?? fld}
                  </option>
                ))}
              </select>
              <select
                value={f.op}
                onChange={(e) =>
                  setFilters((fs) => fs.map((x, j) => (j === i ? { ...x, op: e.target.value } : x)))
                }
                className="rounded-lg border border-border bg-card px-2.5 py-1.5 font-mono text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
              >
                {[">", ">=", "<", "<="].map((op) => (
                  <option key={op} value={op}>
                    {op}
                  </option>
                ))}
              </select>
              <input
                type="number"
                value={f.value}
                onChange={(e) =>
                  setFilters((fs) =>
                    fs.map((x, j) => (j === i ? { ...x, value: parseFloat(e.target.value) || 0 } : x)),
                  )
                }
                className="w-28 rounded-lg border border-border bg-card px-2.5 py-1.5 font-mono text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              />
              {filters.length > 1 && (
                <button
                  onClick={() => setFilters((fs) => fs.filter((_, j) => j !== i))}
                  className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-danger"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </div>
        <div className="mt-3 flex items-center gap-2">
          <button
            onClick={() => setFilters((fs) => [...fs, { field: "revenue", op: ">", value: 0 }])}
            className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted"
          >
            <Plus className="h-3.5 w-3.5" /> Add filter
          </button>
          <button
            onClick={run}
            className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-1.5 text-xs font-medium text-accent-foreground transition-opacity hover:opacity-90"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Filter className="h-4 w-4" />}
            Run screen
          </button>
        </div>
      </Card>

      {/* Results */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <Card className="p-5">
          <h3 className="mb-4 text-sm font-semibold">
            Results {result ? <span className="text-muted-foreground">· {result.count} match</span> : null}
          </h3>
          {loading && !result ? (
            <Skeleton className="h-40" />
          ) : result && result.results.length ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="text-muted-foreground">
                  <tr>
                    <th className="pb-2 pr-3 font-medium">Ticker</th>
                    {cols.map((c) => (
                      <th key={c} className="pb-2 px-2 text-right font-medium whitespace-nowrap">
                        {LABELS[c] ?? c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="font-mono tabular">
                  {result.results.map((row) => (
                    <tr key={String(row.ticker)} className="border-t border-border/60">
                      <td className="py-2 pr-3 font-semibold text-foreground">{row.ticker}</td>
                      {cols.map((c) => (
                        <td key={c} className="py-2 px-2 text-right text-muted-foreground">
                          {fmtCell(c, row[c] as number | null)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState icon={Filter} title="No matches" description="No companies pass every filter. Loosen a threshold." />
          )}
        </Card>
      </motion.div>
    </div>
  );
}
