"use client";

import { motion } from "framer-motion";
import { Bell, Plus, Star, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, type Quote, type Watchlist } from "@/lib/api";
import { formatCompact } from "@/lib/utils";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { Button } from "@/components/ui/button";

const CURRENCY: Record<string, string> = { USD: "$", EUR: "€", GBP: "£", INR: "₹", JPY: "¥" };
const fmt = (n: number | null, cur = "USD") =>
  n == null ? "—" : (CURRENCY[cur] ?? `${cur} `) + n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function Row({ w, quote, onRemove }: { w: Watchlist; quote?: Quote | null; onRemove: () => void }) {
  const up = (quote?.change_pct ?? 0) >= 0;
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      className="flex items-center justify-between gap-4 border-t border-border/60 px-5 py-4 first:border-t-0"
    >
      <div className="min-w-0">
        <p className="font-mono text-sm font-semibold text-foreground">{w.ticker}</p>
        <p className="truncate text-xs text-muted-foreground">{quote?.name ?? "—"}</p>
      </div>
      <div className="flex items-center gap-6">
        <div className="text-right">
          <p className="font-mono text-sm tabular text-foreground">
            {fmt(quote?.price ?? null, quote?.currency)}
          </p>
          {quote?.change_pct != null && (
            <p className={`text-xs font-medium ${up ? "text-emerald-500" : "text-red-500"}`}>
              {up ? "+" : ""}
              {quote.change_pct.toFixed(2)}%
            </p>
          )}
        </div>
        <div className="hidden text-right sm:block">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Mkt cap</p>
          <p className="font-mono text-xs tabular text-foreground">
            {quote?.market_cap != null ? formatCompact(quote.market_cap) : "—"}
          </p>
        </div>
        <button
          onClick={onRemove}
          aria-label={`Remove ${w.ticker}`}
          className="rounded-lg p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-danger cursor-pointer"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </motion.div>
  );
}

export default function WatchlistPage() {
  const [items, setItems] = useState<Watchlist[]>([]);
  const [quotes, setQuotes] = useState<Record<string, Quote | null>>({});
  const [tickers, setTickers] = useState<string[]>([]);
  const [pick, setPick] = useState("");
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    api
      .meta()
      .then((m) => {
        setTickers(m.tickers || []);
        setPick((p) => p || m.tickers?.[0] || "");
      })
      .catch(() => {});
    api
      .watchlists()
      .then((r) => setItems(r.watchlists || []))
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  // Fetch a live quote for each watched ticker (market endpoints are DB-independent).
  useEffect(() => {
    items.forEach((w) => {
      if (w.ticker in quotes) return;
      api
        .quote(w.ticker)
        .then((q) => setQuotes((s) => ({ ...s, [w.ticker]: q })))
        .catch(() => setQuotes((s) => ({ ...s, [w.ticker]: null })));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items]);

  async function add() {
    if (!pick) return;
    if (items.some((w) => w.ticker === pick)) {
      toast.info(`${pick} is already on your watchlist`);
      return;
    }
    try {
      const w = await api.addWatch(pick);
      setItems((s) => [...s, w]);
      toast.success(`Added ${pick}`);
    } catch {
      toast.error("Could not add to watchlist");
    }
  }

  async function remove(w: Watchlist) {
    const prev = items;
    setItems((s) => s.filter((x) => x.id !== w.id));
    try {
      await api.removeWatch(w.id);
    } catch {
      setItems(prev);
      toast.error("Could not remove");
    }
  }

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Watchlist"
        description="Track the companies you care about — live prices, and filing alerts when they publish something new."
      />

      <Card className="flex flex-wrap items-center gap-2 p-4">
        <Bell className="h-4 w-4 text-accent" />
        <span className="text-sm text-muted-foreground">Add a company</span>
        <select
          value={pick}
          onChange={(e) => setPick(e.target.value)}
          className="rounded-lg border border-border bg-card px-3 py-1.5 font-mono text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
        >
          {tickers.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <Button size="sm" onClick={add} disabled={!pick}>
          <Plus className="h-4 w-4" /> Add
        </Button>
      </Card>

      <Card className="p-0">
        {loading ? (
          <div className="space-y-2 p-5">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14" />
            ))}
          </div>
        ) : offline ? (
          <div className="p-5">
            <EmptyState
              icon={Star}
              title="Backend unreachable"
              description="Start the API and set NEXT_PUBLIC_API_URL to manage your watchlist."
            />
          </div>
        ) : items.length ? (
          items.map((w) => (
            <Row key={w.id} w={w} quote={quotes[w.ticker]} onRemove={() => remove(w)} />
          ))
        ) : (
          <div className="p-5">
            <EmptyState
              icon={Star}
              title="Your watchlist is empty"
              description="Add a company above to track its price and get alerted when it files."
            />
          </div>
        )}
      </Card>
    </div>
  );
}
