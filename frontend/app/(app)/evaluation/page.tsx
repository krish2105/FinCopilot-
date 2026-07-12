"use client";

import { motion } from "framer-motion";
import { FlaskConical, ShieldCheck, Target, Waypoints } from "lucide-react";
import { useEffect, useState } from "react";
import { API_BASE } from "@/lib/api";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Gauge } from "@/components/charts/gauge";

interface RagasResult {
  faithfulness?: number;
  answer_relevancy?: number;
  context_precision?: number;
  context_recall?: number;
  n_questions?: number;
  benchmark?: string;
}

const METRICS: {
  key: keyof RagasResult;
  label: string;
  color: string;
  desc: string;
}[] = [
  { key: "faithfulness", label: "Faithfulness", color: "hsl(var(--chart-1))", desc: "Claims grounded in retrieved context" },
  { key: "answer_relevancy", label: "Answer Relevance", color: "hsl(var(--chart-2))", desc: "Answer addresses the question" },
  { key: "context_precision", label: "Context Precision", color: "hsl(var(--chart-3))", desc: "Retrieved the right chunks" },
  { key: "context_recall", label: "Context Recall", color: "hsl(var(--chart-4))", desc: "Retrieved all needed chunks" },
];

export default function EvaluationPage() {
  const [result, setResult] = useState<RagasResult | null>(null);
  const [pending, setPending] = useState(true);

  useEffect(() => {
    // Wired for Phase 7: a /eval endpoint (or bundled results) populates this.
    fetch(`${API_BASE}/eval`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setResult(d))
      .catch(() => {})
      .finally(() => setPending(false));
  }, []);

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Evaluation"
        description="RAGAS metrics on real, human-curated financial-QA benchmarks — not self-generated questions."
      >
        {pending ? (
          <Badge variant="outline">Loading…</Badge>
        ) : result ? (
          <Badge variant="positive">
            {result.n_questions ?? "—"} questions · {result.benchmark ?? "benchmark"}
          </Badge>
        ) : (
          <Badge variant="warning">Awaiting Phase 7 run</Badge>
        )}
      </PageHeader>

      {/* Gauges */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {METRICS.map((m, i) => (
          <motion.div
            key={m.key}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.06 }}
          >
            <Card className="flex flex-col items-center p-5">
              <Gauge
                value={result ? (result[m.key] as number) ?? null : null}
                label={m.label}
                color={m.color}
              />
              <p className="mt-2 text-center text-[11px] leading-snug text-muted-foreground">
                {m.desc}
              </p>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Methodology */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="p-5">
          <FlaskConical className="h-5 w-5 text-accent" />
          <h3 className="mt-3 text-sm font-semibold">Real benchmarks only</h3>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Questions are sampled from <span className="font-medium text-foreground">FinQA</span>,{" "}
            <span className="font-medium text-foreground">TAT-QA</span>, and{" "}
            <span className="font-medium text-foreground">FinanceBench</span> — peer-reviewed,
            human-curated QA over real filings. No LLM-generated questions.
          </p>
        </Card>
        <Card className="p-5">
          <ShieldCheck className="h-5 w-5 text-positive" />
          <h3 className="mt-3 text-sm font-semibold">Faithfulness is the headline</h3>
          <p className="mt-1.5 text-sm text-muted-foreground">
            In finance, a grounded-but-incomplete answer beats a fluent hallucination. The Self-RAG
            gate enforces this at runtime; RAGAS measures it at eval time.
          </p>
        </Card>
        <Card className="p-5">
          <div className="flex gap-2">
            <Target className="h-5 w-5 text-route-graphrag" />
            <Waypoints className="h-5 w-5 text-route-agentic" />
          </div>
          <h3 className="mt-3 text-sm font-semibold">Precision & recall</h3>
          <p className="mt-1.5 text-sm text-muted-foreground">
            Context precision/recall isolate the retriever from the generator, so we know whether a
            miss came from search or synthesis.
          </p>
        </Card>
      </div>

      {!result && !pending && (
        <Card className="p-5">
          <p className="text-sm text-muted-foreground">
            Scores populate once the Phase 7 RAGAS harness runs and exposes results at{" "}
            <span className="font-mono text-foreground">/eval</span>. The gauges and methodology
            above are the finished dashboard — only the numbers are pending.
          </p>
        </Card>
      )}
    </div>
  );
}
