import type { Metadata } from "next";
import Link from "next/link";
import { ArrowUpRight, Compass } from "lucide-react";
import { MarketingNav } from "@/components/marketing-nav";
import { Wordmark } from "@/components/brand";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = {
  title: "Explore — FinCopilot",
  description: "Browse example cited AI research answers over real SEC filings and market data.",
};

const CATEGORIES: { title: string; questions: string[] }[] = [
  {
    title: "Risk & disclosures",
    questions: [
      "What risk factors does Apple disclose?",
      "What supply-chain risks does Microsoft cite?",
      "Which companies share competition risk?",
    ],
  },
  {
    title: "Fundamentals",
    questions: [
      "What was Apple's total net sales?",
      "Compare Apple net sales and Microsoft revenue",
      "What is NVIDIA's gross margin trend?",
    ],
  },
  {
    title: "Relationships & structure",
    questions: [
      "Who are Apple's key executives?",
      "What are 3M's subsidiaries?",
      "Which companies face regulatory risk?",
    ],
  },
];

export default function ExplorePage() {
  return (
    <div className="min-h-dvh bg-background">
      <MarketingNav />
      <section className="container py-14">
        <div className="mx-auto max-w-3xl">
          <Badge variant="accent" className="mb-4">
            <Compass className="h-3.5 w-3.5" /> Explore
          </Badge>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Example cited research answers
          </h1>
          <p className="mt-3 text-muted-foreground">
            Every answer is grounded in real filings and market data, with inline citations — or an
            honest refusal when the evidence isn&apos;t there. Pick a question to see it answered.
          </p>

          <div className="mt-10 space-y-8">
            {CATEGORIES.map((cat) => (
              <div key={cat.title}>
                <h2 className="mb-3 text-sm font-semibold text-foreground">{cat.title}</h2>
                <div className="grid gap-2 sm:grid-cols-2">
                  {cat.questions.map((q) => (
                    <Link key={q} href={`/a/${encodeURIComponent(q)}`}>
                      <Card className="flex items-center justify-between gap-3 p-4 text-sm text-muted-foreground transition-all hover:border-accent/40 hover:text-foreground hover:shadow-card">
                        <span>{q}</span>
                        <ArrowUpRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <footer className="border-t border-border/60">
        <div className="container flex items-center justify-between py-8">
          <Wordmark />
          <Link href="/workspace" className="text-xs text-muted-foreground hover:text-foreground">
            Open the workspace →
          </Link>
        </div>
      </footer>
    </div>
  );
}
