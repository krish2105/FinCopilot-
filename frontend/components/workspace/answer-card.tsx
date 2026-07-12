"use client";

import { motion } from "framer-motion";
import {
  AlertTriangle,
  BadgeCheck,
  Clock,
  Cpu,
  Quote,
  ShieldAlert,
  ThumbsDown,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { api, type AgentAnswer } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { RouteBadge } from "@/components/route-badge";
import { CitationText } from "@/components/workspace/citation-text";
import { BarViz } from "@/components/charts/chart-kit";
import { cn } from "@/lib/utils";

const FLAG_STYLE: Record<string, "danger" | "warning"> = {
  going_concern: "danger",
  restatement: "danger",
  material_weakness: "danger",
  litigation: "warning",
  impairment: "warning",
  risk_factors: "warning",
};

function InsufficientEvidence({ answer }: { answer: AgentAnswer }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-warning/30 bg-warning/[0.07] p-6"
    >
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-warning/15">
          <AlertTriangle className="h-5 w-5 text-warning" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-foreground">Insufficient evidence</h3>
          <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{answer.answer}</p>
          {answer.faithfulness?.ungrounded_numbers?.length > 0 && (
            <p className="mt-2 text-xs text-muted-foreground">
              Blocked figures:{" "}
              <span className="font-mono text-warning">
                {answer.faithfulness.ungrounded_numbers.join(", ")}
              </span>
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="text-xs text-muted-foreground">
              This is a designed state — FinCopilot refuses rather than guesses.
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function StatChip({ icon: Icon, label }: { icon: typeof Clock; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
      <Icon className="h-3.5 w-3.5" />
      {label}
    </span>
  );
}

export function AnswerCard({
  answer,
  onCite,
}: {
  answer: AgentAnswer;
  onCite: (marker: string) => void;
}) {
  const insufficient = answer.verdict !== "ok";
  const faithPct = Math.round((answer.faithfulness?.score ?? 0) * 100);
  const chart = answer.charts?.[0];
  const chartData = chart?.series?.[0]?.points ?? [];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.4, 0, 0.2, 1] }}
      className="flex flex-col gap-4"
    >
      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-2">
        <RouteBadge route={answer.route} />
        {answer.verdict === "ok" ? (
          <Badge variant="positive">
            <BadgeCheck className="h-3.5 w-3.5" /> Verified
          </Badge>
        ) : (
          <Badge variant="warning">
            <AlertTriangle className="h-3.5 w-3.5" /> Insufficient evidence
          </Badge>
        )}
        <span className="ml-auto flex items-center gap-3">
          <StatChip icon={Clock} label={`${answer.latency_ms} ms`} />
          <StatChip icon={Quote} label={`${answer.evidence_count} sources`} />
          {answer.cost_usd > 0 && (
            <StatChip icon={Cpu} label={`$${answer.cost_usd.toFixed(4)}`} />
          )}
        </span>
      </div>

      {insufficient ? (
        <InsufficientEvidence answer={answer} />
      ) : (
        <>
          {/* Answer */}
          <div className="rounded-xl border border-border bg-card p-6 shadow-card">
            <CitationText
              text={answer.answer}
              citations={answer.citations}
              onCite={onCite}
              className="text-[15px] text-foreground"
            />

            {/* Faithfulness bar */}
            <div className="mt-5 border-t border-border pt-4">
              <div className="mb-1.5 flex items-center justify-between text-xs">
                <span className="flex items-center gap-1.5 font-medium text-foreground">
                  <BadgeCheck className="h-3.5 w-3.5 text-positive" />
                  Faithfulness
                </span>
                <span className="font-mono tabular text-muted-foreground">{faithPct}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                <motion.div
                  className="h-full rounded-full bg-positive"
                  initial={{ width: 0 }}
                  animate={{ width: `${faithPct}%` }}
                  transition={{ duration: 0.7, ease: "easeOut" }}
                />
              </div>
            </div>
          </div>

          {/* Findings */}
          {answer.findings.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5 shadow-card">
              <div className="mb-3 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-accent" />
                <h4 className="text-sm font-semibold">Analyst findings</h4>
              </div>
              <div className="grid gap-2 sm:grid-cols-2">
                {answer.findings.slice(0, 8).map((f, i) => (
                  <button
                    key={i}
                    onClick={() => f.citation_marker && onCite(f.citation_marker)}
                    className="group flex items-center justify-between gap-3 rounded-lg border border-border bg-muted/30 px-3.5 py-2.5 text-left transition-colors hover:bg-muted cursor-pointer"
                  >
                    <span className="min-w-0 truncate text-xs text-muted-foreground">
                      {f.label || f.kind}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="font-mono text-sm font-semibold tabular text-foreground">
                        {f.value}
                      </span>
                      {f.citation_marker && (
                        <span className="font-mono text-[10px] text-accent">
                          {f.citation_marker}
                        </span>
                      )}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Chart */}
          {chartData.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5 shadow-card">
              <h4 className="mb-3 text-sm font-semibold">{chart?.title || "Key figures"}</h4>
              <BarViz data={chartData} />
            </div>
          )}

          {/* Compliance flags */}
          {answer.flags.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5 shadow-card">
              <div className="mb-3 flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-warning" />
                <h4 className="text-sm font-semibold">Compliance flags</h4>
              </div>
              <div className="flex flex-col gap-2">
                {answer.flags.slice(0, 6).map((flag, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/30 p-3"
                  >
                    <Badge variant={FLAG_STYLE[flag.category] ?? "warning"}>
                      {flag.category.replace(/_/g, " ")}
                    </Badge>
                    <p className="min-w-0 flex-1 text-xs leading-relaxed text-muted-foreground">
                      {flag.detail}
                    </p>
                    {flag.citation_marker && (
                      <button
                        onClick={() => onCite(flag.citation_marker)}
                        className="font-mono text-[10px] text-accent hover:underline"
                      >
                        {flag.citation_marker}
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources + provider trace */}
          <div className="grid gap-4 md:grid-cols-2">
            {answer.citations.length > 0 && (
              <div className="rounded-xl border border-border bg-card p-5 shadow-card">
                <h4 className="mb-3 text-sm font-semibold">Sources</h4>
                <ul className="flex flex-col gap-1.5">
                  {answer.citations.map((c) => (
                    <li key={c.marker}>
                      <button
                        onClick={() => onCite(c.marker)}
                        className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground cursor-pointer"
                      >
                        <span className="font-mono text-accent">{c.marker}</span>
                        <span className="truncate">
                          {c.ticker} {c.doc_type}
                          {c.page != null ? ` · p.${c.page}` : ""}
                          {c.section ? ` · ${c.section}` : ""}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="rounded-xl border border-border bg-card p-5 shadow-card">
              <div className="mb-3 flex items-center gap-2">
                <Cpu className="h-4 w-4 text-muted-foreground" />
                <h4 className="text-sm font-semibold">Provider trace</h4>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {answer.provider_trace.map((p, i) => (
                  <span
                    key={i}
                    className={cn(
                      "rounded-md border border-border bg-muted/40 px-2 py-1 font-mono text-[11px]",
                      p.cached ? "text-positive" : "text-muted-foreground",
                    )}
                    title={p.cached ? "cache hit" : `${p.latency_ms} ms`}
                  >
                    {p.provider}:{p.model}
                    {p.cached ? " ·cached" : ""}
                  </span>
                ))}
                {answer.provider_trace.length === 0 && (
                  <span className="text-xs text-muted-foreground">No LLM calls recorded.</span>
                )}
              </div>
              <p className="mt-3 text-[11px] text-muted-foreground">
                Embeddings: <span className="font-mono">{answer.embed_backend}</span> · Reranker:{" "}
                <span className="font-mono">{answer.reranker}</span>
              </p>
            </div>
          </div>
        </>
      )}

      <div className="flex flex-wrap items-center justify-between gap-2">
        <FeedbackButtons query={answer.query} />
        <div className="flex items-center gap-2">
          <span
            className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground"
            title="This answer was generated by an AI system (EU AI Act Art. 50). Verify before acting."
          >
            AI-generated
          </span>
          <p className="text-[11px] text-muted-foreground">{answer.disclaimer}</p>
        </div>
      </div>
    </motion.div>
  );
}

function FeedbackButtons({ query }: { query: string }) {
  const [sent, setSent] = useState<number | null>(null);
  function rate(r: number) {
    if (sent !== null) return;
    setSent(r);
    api.feedback(r, query).catch(() => {});
    toast.success("Thanks for the feedback");
  }
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px] text-muted-foreground">Helpful?</span>
      <button
        onClick={() => rate(1)}
        aria-label="Helpful"
        className={`rounded-md p-1.5 transition-colors hover:bg-muted ${sent === 1 ? "text-positive" : "text-muted-foreground"}`}
      >
        <ThumbsUp className="h-3.5 w-3.5" />
      </button>
      <button
        onClick={() => rate(-1)}
        aria-label="Not helpful"
        className={`rounded-md p-1.5 transition-colors hover:bg-muted ${sent === -1 ? "text-danger" : "text-muted-foreground"}`}
      >
        <ThumbsDown className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
