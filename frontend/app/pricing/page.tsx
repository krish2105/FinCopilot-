"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type Plan } from "@/lib/api";
import { MarketingNav } from "@/components/marketing-nav";
import { Wordmark } from "@/components/brand";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const FALLBACK: Plan[] = [
  { id: "free", name: "Free", price_usd_month: 0, queries_per_month: 25, max_documents: 3, max_seats: 1, features: ["Public filings corpus", "Cited answers", "1 data room"] },
  { id: "pro", name: "Pro", price_usd_month: 49, queries_per_month: 1000, max_documents: 100, max_seats: 1, features: ["Everything in Free", "Document upload", "GraphRAG", "Audit + export"] },
  { id: "team", name: "Team", price_usd_month: 199, queries_per_month: 5000, max_documents: 2000, max_seats: 10, features: ["Everything in Pro", "10 seats", "Shared data rooms", "Priority support"] },
];

const FAQ = [
  { q: "Is it really cited?", a: "Every factual claim links to a filing page/section, and a faithfulness gate blocks any ungrounded number. When the evidence isn't there, FinCopilot refuses instead of guessing." },
  { q: "Can I upload my own documents?", a: "Yes — Pro and Team include private, tenant-isolated data rooms. Upload PDFs or filings and ask questions scoped to just those files." },
  { q: "How is usage metered?", a: "Per-query and per-document quotas by plan, metered from the audit trail. You can see live usage and estimated spend in the app." },
  { q: "Is my data isolated?", a: "Every chunk is workspace-scoped and, in production, enforced by Postgres row-level security — a tenant can only ever read the public corpus plus its own rooms." },
];

export default function PricingPage() {
  const [plans, setPlans] = useState<Plan[]>(FALLBACK);

  useEffect(() => {
    api.plans().then((p) => p.plans?.length && setPlans(p.plans)).catch(() => {});
  }, []);

  return (
    <div className="min-h-dvh bg-background">
      <MarketingNav />
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 grid-bg opacity-50" />
        <div className="container relative py-16 text-center sm:py-20">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
              Pricing that scales with your research
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-lg text-muted-foreground">
              Start free on public filings. Upgrade for private data rooms, GraphRAG, and
              team seats. Cancel anytime.
            </p>
          </motion.div>

          <div className="mx-auto mt-12 grid max-w-5xl gap-4 md:grid-cols-3">
            {plans.map((p, i) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06 }}
              >
                <Card
                  className={`flex h-full flex-col p-6 text-left ${p.id === "pro" ? "border-accent/40 shadow-glow" : ""}`}
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-semibold">{p.name}</h3>
                    {p.id === "pro" && <Badge variant="accent">Most popular</Badge>}
                  </div>
                  <p className="mt-3">
                    <span className="font-mono text-4xl font-semibold">${p.price_usd_month}</span>
                    <span className="text-sm text-muted-foreground">/seat/mo</span>
                  </p>
                  <ul className="mt-5 flex flex-1 flex-col gap-2.5 text-sm">
                    <li className="text-muted-foreground">
                      {p.queries_per_month.toLocaleString()} queries/mo ·{" "}
                      {p.max_documents.toLocaleString()} docs
                    </li>
                    {p.features.map((f) => (
                      <li key={f} className="flex items-center gap-2 text-muted-foreground">
                        <Check className="h-4 w-4 shrink-0 text-positive" /> {f}
                      </li>
                    ))}
                  </ul>
                  <Link href="/login" className="mt-6">
                    <Button className="w-full" variant={p.id === "pro" ? "default" : "outline"}>
                      {p.price_usd_month === 0 ? "Start free" : `Start ${p.name}`}
                      <ArrowRight className="h-4 w-4" />
                    </Button>
                  </Link>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="container py-16">
        <h2 className="text-center text-3xl font-semibold tracking-tight">Questions</h2>
        <div className="mx-auto mt-10 grid max-w-3xl gap-4 sm:grid-cols-2">
          {FAQ.map((f) => (
            <Card key={f.q} className="p-5">
              <h3 className="text-sm font-semibold">{f.q}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{f.a}</p>
            </Card>
          ))}
        </div>
      </section>

      <footer className="border-t border-border/60">
        <div className="container flex flex-col items-center justify-between gap-4 py-8 sm:flex-row">
          <Wordmark />
          <p className="text-xs text-muted-foreground">Informational research only — not investment advice.</p>
          <Link href="/docs" className="text-xs text-muted-foreground hover:text-foreground">
            Read the docs →
          </Link>
        </div>
      </footer>
    </div>
  );
}
