"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CheckCircle2, XCircle, Loader2, RefreshCw } from "lucide-react";
import { api, API_BASE } from "@/lib/api";
import { MarketingNav } from "@/components/marketing-nav";
import { Wordmark } from "@/components/brand";
import { Card } from "@/components/ui/card";

type State = "checking" | "up" | "down";

interface Component {
  name: string;
  detail: string;
  state: State;
}

function Dot({ state }: { state: State }) {
  if (state === "checking")
    return <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />;
  return state === "up" ? (
    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
  ) : (
    <XCircle className="h-5 w-5 text-red-500" />
  );
}

export default function StatusPage() {
  const [components, setComponents] = useState<Component[]>([
    { name: "API", detail: "FastAPI service", state: "checking" },
    { name: "Database", detail: "Supabase Postgres + pgvector", state: "checking" },
    { name: "Market data", detail: "Live quotes provider", state: "checking" },
  ]);
  const [checkedAt, setCheckedAt] = useState<string>("");

  async function check() {
    setComponents((c) => c.map((x) => ({ ...x, state: "checking" })));
    const [health, ready, quote] = await Promise.allSettled([
      api.health(),
      api.ready(),
      api.quote("AAPL"),
    ]);
    setComponents([
      {
        name: "API",
        detail: "FastAPI service",
        state: health.status === "fulfilled" && health.value.status === "ok" ? "up" : "down",
      },
      {
        name: "Database",
        detail: "Supabase Postgres + pgvector",
        state: ready.status === "fulfilled" && ready.value.ready ? "up" : "down",
      },
      {
        name: "Market data",
        detail: "Live quotes provider",
        state: quote.status === "fulfilled" ? "up" : "down",
      },
    ]);
    setCheckedAt(new Date().toLocaleString());
  }

  useEffect(() => {
    check();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const allUp = components.every((c) => c.state === "up");
  const anyChecking = components.some((c) => c.state === "checking");

  return (
    <div className="min-h-dvh bg-background">
      <MarketingNav />
      <section className="container py-16">
        <div className="mx-auto max-w-2xl">
          <div className="mb-8 flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">System status</h1>
              <p className="mt-2 text-sm text-muted-foreground">
                Live checks against <span className="font-mono">{API_BASE}</span>.
              </p>
            </div>
            <button
              onClick={check}
              className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground hover:bg-muted cursor-pointer"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>
          </div>

          <div
            className={`mb-6 rounded-xl border p-4 text-sm font-medium ${
              anyChecking
                ? "border-border bg-muted/40 text-muted-foreground"
                : allUp
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                  : "border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400"
            }`}
          >
            {anyChecking
              ? "Checking components…"
              : allUp
                ? "All systems operational."
                : "Some components are degraded. The free-tier backend may be waking up — refresh in ~50s."}
          </div>

          <Card className="divide-y divide-border p-0">
            {components.map((c) => (
              <div key={c.name} className="flex items-center justify-between px-5 py-4">
                <div>
                  <p className="text-sm font-medium text-foreground">{c.name}</p>
                  <p className="text-xs text-muted-foreground">{c.detail}</p>
                </div>
                <Dot state={c.state} />
              </div>
            ))}
          </Card>

          {checkedAt && (
            <p className="mt-4 text-center text-xs text-muted-foreground">
              Last checked {checkedAt}
            </p>
          )}
        </div>
      </section>

      <footer className="border-t border-border/60">
        <div className="container flex items-center justify-between py-8">
          <Wordmark />
          <Link href="/trust" className="text-xs text-muted-foreground hover:text-foreground">
            Trust & security →
          </Link>
        </div>
      </footer>
    </div>
  );
}
