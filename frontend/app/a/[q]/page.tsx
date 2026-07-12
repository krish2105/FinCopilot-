import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, ExternalLink, ShieldCheck } from "lucide-react";
import { MarketingNav } from "@/components/marketing-nav";
import { Wordmark } from "@/components/brand";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AgentAnswer } from "@/lib/api";

// Server-rendered, SEO-crawlable public answer page. Fetches a cited answer from
// the backend at request time so shared/indexed links show real content.
export const dynamic = "force-dynamic";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

async function fetchAnswer(q: string): Promise<AgentAnswer | null> {
  try {
    const res = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: q, tickers: null, workspace_id: null }),
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as AgentAnswer;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { q: string };
}): Promise<Metadata> {
  const q = decodeURIComponent(params.q);
  return {
    title: `${q} — FinCopilot`,
    description: `AI-researched, fully cited answer to: ${q}. Grounded in real SEC filings and market data.`,
    openGraph: { title: q, description: `Cited AI research answer — FinCopilot` },
  };
}

export default async function PublicAnswerPage({ params }: { params: { q: string } }) {
  const q = decodeURIComponent(params.q);
  const answer = await fetchAnswer(q);
  const refused = answer?.verdict && answer.verdict !== "ok";

  return (
    <div className="min-h-dvh bg-background">
      <MarketingNav />
      <article className="container max-w-3xl py-14">
        <Badge variant="accent" className="mb-4">
          <ShieldCheck className="h-3.5 w-3.5" /> Cited AI research
        </Badge>
        <h1 className="text-3xl font-semibold tracking-tight">{q}</h1>

        {answer && !refused ? (
          <>
            <Card className="mt-6 p-6">
              <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                {answer.answer}
              </p>
            </Card>

            {answer.citations.length > 0 && (
              <div className="mt-6">
                <h2 className="mb-3 text-sm font-semibold">Sources</h2>
                <ul className="space-y-2">
                  {answer.citations.map((c) => (
                    <li key={c.marker}>
                      <a
                        href={c.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-start gap-2 rounded-lg border border-border p-3 text-sm transition-colors hover:border-accent/40 hover:bg-muted"
                      >
                        <span className="font-mono text-xs text-accent">{c.marker}</span>
                        <span className="min-w-0 flex-1">
                          <span className="font-medium text-foreground">
                            {c.ticker} · {c.title}
                          </span>
                          {c.excerpt && (
                            <span className="mt-0.5 block truncate text-xs text-muted-foreground">
                              {c.excerpt}
                            </span>
                          )}
                        </span>
                        <ExternalLink className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <p className="mt-4 text-[11px] text-muted-foreground">
              <span className="mr-2 rounded-full border border-border px-2 py-0.5 uppercase tracking-wide">
                AI-generated
              </span>
              {answer.disclaimer}
            </p>
          </>
        ) : (
          <Card className="mt-6 p-6 text-sm text-muted-foreground">
            {refused
              ? "There isn't enough evidence in the corpus to answer this confidently yet — FinCopilot refuses rather than guess. Try it live in the workspace."
              : "This answer isn't available right now (the research backend may be waking up). Open it live in the workspace."}
          </Card>
        )}

        <Link
          href={`/workspace?q=${encodeURIComponent(q)}`}
          className="mt-8 inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-foreground transition-opacity hover:opacity-90"
        >
          Ask this live in the workspace <ArrowRight className="h-4 w-4" />
        </Link>
      </article>

      <footer className="border-t border-border/60">
        <div className="container flex items-center justify-between py-8">
          <Wordmark />
          <Link href="/explore" className="text-xs text-muted-foreground hover:text-foreground">
            Explore more questions →
          </Link>
        </div>
      </footer>
    </div>
  );
}
