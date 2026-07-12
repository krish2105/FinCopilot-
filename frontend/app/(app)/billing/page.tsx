"use client";

import { motion } from "framer-motion";
import { Check, CreditCard, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, type Plan, type Usage } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";

function UsageBar({ label, used, limit }: { label: string; used: number; limit: number }) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0;
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono tabular text-foreground">
          {used.toLocaleString()} / {limit.toLocaleString()}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <motion.div
          className={`h-full rounded-full ${pct > 90 ? "bg-warning" : "bg-accent"}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

export default function BillingPage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [configured, setConfigured] = useState(false);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    Promise.all([api.usage(), api.plans()])
      .then(([u, p]) => {
        setUsage(u);
        setPlans(p.plans);
        setConfigured(p.configured);
      })
      .catch(() => setOffline(true))
      .finally(() => setLoading(false));
  }, []);

  async function upgrade(planId: string) {
    if (!configured) {
      toast.info("Billing isn't configured", {
        description: "Set STRIPE_SECRET_KEY on the backend to enable checkout.",
      });
      return;
    }
    try {
      const { url } = await api.checkout(planId);
      window.location.href = url;
    } catch (err) {
      toast.error("Checkout failed", {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  }

  if (offline) {
    return (
      <div className="p-4 sm:p-6 lg:p-8">
        <PageHeader title="Billing" />
        <div className="mt-6">
          <EmptyState
            icon={CreditCard}
            title="Backend unreachable"
            description="Start the API and set NEXT_PUBLIC_API_URL to view plans and usage."
          />
        </div>
      </div>
    );
  }

  const currentPlan = usage?.plan.id;

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Billing & Usage"
        description="Per-seat plans with monthly query and document quotas. Usage is metered from the audit trail."
      >
        {usage && <Badge variant="accent">{usage.plan.name} plan</Badge>}
      </PageHeader>

      {/* Usage */}
      <Card className="p-5">
        <h3 className="mb-4 text-sm font-semibold">This month</h3>
        {loading || !usage ? (
          <div className="space-y-4">
            <Skeleton className="h-10" />
            <Skeleton className="h-10" />
          </div>
        ) : (
          <div className="grid gap-5 sm:grid-cols-2">
            <UsageBar label="Queries" used={usage.queries_used} limit={usage.queries_limit} />
            <UsageBar label="Documents" used={usage.documents_used} limit={usage.documents_limit} />
          </div>
        )}
      </Card>

      {/* Plans */}
      <div className="grid gap-4 md:grid-cols-3">
        {(loading ? [] : plans).map((p, i) => {
          const current = p.id === currentPlan;
          return (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.06 }}
            >
              <Card
                className={`flex h-full flex-col p-6 ${
                  p.id === "pro" ? "border-accent/40 shadow-glow" : ""
                }`}
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-base font-semibold">{p.name}</h3>
                  {p.id === "pro" && (
                    <Badge variant="accent">
                      <Zap className="h-3 w-3" /> Popular
                    </Badge>
                  )}
                </div>
                <p className="mt-2">
                  <span className="font-mono text-3xl font-semibold">${p.price_usd_month}</span>
                  <span className="text-sm text-muted-foreground">/mo</span>
                </p>
                <ul className="mt-4 flex flex-1 flex-col gap-2 text-sm">
                  <li className="text-muted-foreground">
                    {p.queries_per_month.toLocaleString()} queries/mo ·{" "}
                    {p.max_documents.toLocaleString()} docs
                  </li>
                  {p.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-muted-foreground">
                      <Check className="h-4 w-4 text-positive" /> {f}
                    </li>
                  ))}
                </ul>
                <Button
                  className="mt-6 w-full"
                  variant={current ? "secondary" : p.id === "free" ? "outline" : "default"}
                  disabled={current}
                  onClick={() => upgrade(p.id)}
                >
                  {current ? "Current plan" : p.price_usd_month === 0 ? "Downgrade" : `Upgrade to ${p.name}`}
                </Button>
              </Card>
            </motion.div>
          );
        })}
      </div>

      {!configured && !loading && (
        <p className="text-center text-xs text-muted-foreground">
          Checkout is disabled until <span className="font-mono">STRIPE_SECRET_KEY</span> is set on
          the backend. Plans, quotas, and metering are fully functional.
        </p>
      )}
    </div>
  );
}
