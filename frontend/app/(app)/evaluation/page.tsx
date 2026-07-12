"use client";

import { motion } from "framer-motion";
import { CheckCircle2, FlaskConical, ShieldCheck, Target } from "lucide-react";
import { useEffect, useState } from "react";
import { api, type EvalResult } from "@/lib/api";
import { PageHeader, EmptyState } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Gauge } from "@/components/charts/gauge";
import { RouteBadge } from "@/components/route-badge";

export default function EvaluationPage() {
  const [data, setData] = useState<EvalResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .eval()
      .then(setData)
      .catch(() => setData({ available: false, message: "Backend unreachable." }))
      .finally(() => setLoading(false));
  }, []);

  const m = data?.metrics;
  const ragas = data?.ragas;

  const detMetrics = m
    ? [
        { v: m.context_hit, label: "Context Hit", color: "hsl(var(--chart-1))", desc: "Retrieved the correct gold source" },
        { v: m.faithful_rate, label: "Faithfulness", color: "hsl(var(--chart-2))", desc: "Passed the Self-RAG gate" },
        { v: m.answer_match, label: "Answer Match", color: "hsl(var(--chart-4))", desc: "Answer contains the gold value" },
        { v: m.citation_coverage, label: "Citation Coverage", color: "hsl(var(--chart-3))", desc: "Answers carrying a citation" },
      ]
    : [];

  const ragasMetrics = [
    { key: "faithfulness", label: "Faithfulness" },
    { key: "answer_relevancy", label: "Answer Relevance" },
    { key: "context_precision", label: "Context Precision" },
    { key: "context_recall", label: "Context Recall" },
  ] as const;

  return (
    <div className="space-y-6 p-4 sm:p-6 lg:p-8">
      <PageHeader
        title="Evaluation"
        description="Measured on real, human-curated FinanceBench questions over real 10-K filings — not self-generated questions."
      >
        {loading ? (
          <Badge variant="outline">Loading…</Badge>
        ) : data?.available && m ? (
          <Badge variant="positive">
            {m.n_questions} questions · {data.n_companies} companies
          </Badge>
        ) : (
          <Badge variant="warning">No run yet</Badge>
        )}
      </PageHeader>

      {!loading && !data?.available ? (
        <EmptyState
          icon={FlaskConical}
          title="No evaluation results yet"
          description="Run `python -m src.evaluation.run` (with the local semantic stack) to populate real numbers here."
        />
      ) : (
        <>
          {/* Stack banner */}
          {data?.stack && (
            <Card className="flex flex-wrap items-center gap-x-6 gap-y-2 p-4 text-xs">
              <span className="text-muted-foreground">
                Embeddings <span className="font-mono text-foreground">{data.stack.embed_backend}</span>
              </span>
              <span className="text-muted-foreground">
                Reranker <span className="font-mono text-foreground">{data.stack.reranker}</span>
              </span>
              <span className="text-muted-foreground">
                LLM <span className="font-mono text-foreground">{data.stack.llm_mode}</span>
              </span>
              {m && (
                <span className="ml-auto text-muted-foreground">
                  avg latency{" "}
                  <span className="font-mono text-foreground">{m.avg_latency_ms} ms</span> · refusal{" "}
                  <span className="font-mono text-foreground">{Math.round(m.refusal_rate * 100)}%</span>
                </span>
              )}
            </Card>
          )}

          {/* Deterministic metrics (real, no LLM needed) */}
          <div>
            <h2 className="mb-3 text-sm font-semibold text-muted-foreground">
              Retrieval & grounding metrics
            </h2>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {detMetrics.map((d, i) => (
                <motion.div
                  key={d.label}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.06 }}
                >
                  <Card className="flex flex-col items-center p-5">
                    <Gauge value={d.v} label={d.label} color={d.color} />
                    <p className="mt-2 text-center text-[11px] leading-snug text-muted-foreground">
                      {d.desc}
                    </p>
                  </Card>
                </motion.div>
              ))}
            </div>
          </div>

          {/* RAGAS (LLM-judged) */}
          <div>
            <div className="mb-3 flex items-center gap-2">
              <h2 className="text-sm font-semibold text-muted-foreground">RAGAS (LLM-judged)</h2>
              {!ragas && <Badge variant="outline">requires an LLM key</Badge>}
            </div>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
              {ragasMetrics.map((r) => (
                <Card key={r.key} className="flex flex-col items-center p-5">
                  <Gauge
                    value={ragas ? (ragas as Record<string, number>)[r.key] ?? null : null}
                    label={r.label}
                    color="hsl(var(--chart-5))"
                  />
                </Card>
              ))}
            </div>
          </div>

          {/* Methodology */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="p-5">
              <FlaskConical className="h-5 w-5 text-accent" />
              <h3 className="mt-3 text-sm font-semibold">Real benchmarks only</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Questions and gold answers come from{" "}
                <span className="font-medium text-foreground">FinanceBench</span> — peer-reviewed,
                human-curated open-book QA over real 10-Ks. No LLM-generated questions.
              </p>
            </Card>
            <Card className="p-5">
              <ShieldCheck className="h-5 w-5 text-positive" />
              <h3 className="mt-3 text-sm font-semibold">Faithfulness is the headline</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">
                The Self-RAG gate enforces grounding at runtime; here we measure its pass rate over
                the benchmark, plus whether retrieval surfaced the correct source.
              </p>
            </Card>
            <Card className="p-5">
              <Target className="h-5 w-5 text-route-graphrag" />
              <h3 className="mt-3 text-sm font-semibold">Honest answer match</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Answer-match reflects the offline extractive synthesizer — many FinanceBench answers
                require LLM computation, which lifts this metric substantially with a key configured.
              </p>
            </Card>
          </div>

          {/* Sample per-question */}
          {data?.per_question && data.per_question.length > 0 && (
            <Card className="overflow-hidden p-0">
              <div className="border-b border-border px-5 py-3">
                <h3 className="text-sm font-semibold">Sample results</h3>
              </div>
              <div className="overflow-x-auto scrollbar-thin">
                <table className="w-full min-w-[640px] text-sm">
                  <thead>
                    <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="px-5 py-2.5 font-medium">Company</th>
                      <th className="px-5 py-2.5 font-medium">Question</th>
                      <th className="px-5 py-2.5 font-medium">Route</th>
                      <th className="px-5 py-2.5 font-medium">Retrieved</th>
                      <th className="px-5 py-2.5 font-medium">Matched</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.per_question.slice(0, 10).map((r, i) => (
                      <tr key={i} className="border-b border-border/60 last:border-0 hover:bg-muted/40">
                        <td className="whitespace-nowrap px-5 py-2.5 font-medium text-foreground">
                          {r.company}
                        </td>
                        <td className="max-w-[280px] px-5 py-2.5">
                          <span className="block truncate text-muted-foreground" title={r.question}>
                            {r.question}
                          </span>
                        </td>
                        <td className="px-5 py-2.5">
                          <RouteBadge route={r.route} />
                        </td>
                        <td className="px-5 py-2.5">
                          <Dot ok={!!r.context_hit} />
                        </td>
                        <td className="px-5 py-2.5">
                          <Dot ok={!!r.answer_match} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Dot({ ok }: { ok: boolean }) {
  return ok ? (
    <CheckCircle2 className="h-4 w-4 text-positive" />
  ) : (
    <span className="inline-block h-2 w-2 rounded-full bg-muted-foreground/40" />
  );
}
