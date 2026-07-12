"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  BadgeCheck,
  Calculator,
  Compass,
  GitBranch,
  Github,
  Layers,
  ScanSearch,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { Wordmark } from "@/components/brand";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SampleAnswer } from "@/components/landing/sample-answer";

const STEPS = [
  { icon: ScanSearch, title: "Retrieve", body: "Adaptive RAG pulls evidence from real SEC filings — hybrid search, agentic loops, or GraphRAG per query." },
  { icon: Calculator, title: "Analyze", body: "Specialist agents compute ratios and trends from retrieved figures only, citing every input line." },
  { icon: ShieldCheck, title: "Verify", body: "A Self-RAG gate blocks any ungrounded claim, so you get a cited answer — or an honest refusal." },
];

const FEATURES = [
  { icon: Compass, title: "Adaptive routing", body: "The cheapest pipeline that can answer each query — simple lookups stay cheap, hard questions get GraphRAG." },
  { icon: BadgeCheck, title: "Every claim cited", body: "Each number traces to a filing page and section. Uncited figures are blocked, not shown." },
  { icon: GitBranch, title: "GraphRAG relationships", body: "An entity graph answers 'which companies share this risk?' by traversal, not guesswork." },
  { icon: Layers, title: "Multi-provider LLM", body: "Gemini ↔ Groq fallback with rate-limit handling. Zero API cost to run on free tiers." },
  { icon: ShieldCheck, title: "Compliance & audit", body: "Risk-language flags, a faithfulness gate, and a full audit trail of every query and verdict." },
  { icon: Sparkles, title: "Insufficient-evidence contract", body: "A designed refusal state — FinCopilot says 'I don't know' instead of hallucinating." },
];

const TICKERS = ["AAPL", "MSFT", "AMZN", "TSLA", "JPM", "NVDA", "META", "GOOGL", "EMAAR.AE", "IHC.AE"];

export default function Landing() {
  return (
    <div className="min-h-dvh bg-background">
      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-border/60 bg-background/70 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-8">
            <Wordmark />
            <nav className="hidden items-center gap-6 md:flex">
              <Link
                href="/pricing"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                Pricing
              </Link>
              <Link
                href="/docs"
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                Docs
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <a
              href="https://github.com/krish2105/FinCopilot-"
              target="_blank"
              rel="noreferrer"
              className="hidden rounded-lg border border-border p-2 text-muted-foreground transition-colors hover:text-foreground hover:bg-muted sm:inline-flex"
              aria-label="GitHub"
            >
              <Github className="h-[18px] w-[18px]" />
            </a>
            <ThemeToggle />
            <Link href="/workspace">
              <Button size="sm">
                Open workspace <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 grid-bg opacity-60" />
        <div className="container relative grid gap-12 py-16 lg:grid-cols-2 lg:items-center lg:py-24">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <Badge variant="accent" className="mb-5">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-pulse-ring rounded-full bg-accent" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
              </span>
              Agentic RAG · fully cited · free-tier
            </Badge>
            <h1 className="text-4xl font-semibold leading-[1.1] tracking-tight sm:text-5xl">
              A financial analyst copilot that <span className="text-gradient">refuses to guess</span>.
            </h1>
            <p className="mt-5 max-w-xl text-lg text-muted-foreground">
              A team of AI agents reads real SEC filings, runs the analysis, checks compliance, and
              returns a fully cited answer — or honestly says{" "}
              <span className="font-medium text-warning">insufficient evidence</span>.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link href="/workspace">
                <Button size="lg">
                  Try the workspace <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button size="lg" variant="secondary">
                  View the dashboard
                </Button>
              </Link>
            </div>
            <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <BadgeCheck className="h-4 w-4 text-positive" /> Every number cited
              </span>
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4 text-positive" /> Self-RAG faithfulness gate
              </span>
            </div>
          </motion.div>

          <div className="flex justify-center lg:justify-end">
            <SampleAnswer />
          </div>
        </div>

        {/* Ticker marquee */}
        <div className="relative border-y border-border/60 bg-card/30 py-3">
          <div className="flex overflow-hidden [mask-image:linear-gradient(90deg,transparent,#000_10%,#000_90%,transparent)]">
            <div className="flex shrink-0 animate-marquee items-center gap-8 pr-8">
              {[...TICKERS, ...TICKERS].map((t, i) => (
                <span key={i} className="font-mono text-sm text-muted-foreground">
                  {t}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="container py-20">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight">How it works</h2>
          <p className="mt-3 text-muted-foreground">
            Retrieve → analyze → verify. Complexity is a cost, not a virtue — the easy 80% stays
            cheap, and only hard questions pay for agentic or graph reasoning.
          </p>
        </div>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {STEPS.map((s, i) => (
            <motion.div
              key={s.title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ delay: i * 0.1 }}
              className="relative rounded-2xl border border-border bg-card p-6 shadow-card"
            >
              <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-accent/30 bg-accent/10">
                <s.icon className="h-5 w-5 text-accent" />
              </div>
              <span className="absolute right-6 top-6 font-mono text-sm text-muted-foreground/50">
                0{i + 1}
              </span>
              <h3 className="text-base font-semibold">{s.title}</h3>
              <p className="mt-2 text-sm text-muted-foreground">{s.body}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-border/60 bg-card/20">
        <div className="container py-20">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-semibold tracking-tight">Built for trust</h2>
            <p className="mt-3 text-muted-foreground">
              The features that separate a real research tool from a chatbot that makes up numbers.
            </p>
          </div>
          <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-60px" }}
                transition={{ delay: (i % 3) * 0.08 }}
                className="rounded-2xl border border-border bg-card p-6 transition-colors hover:border-accent/40"
              >
                <f.icon className="h-5 w-5 text-accent" />
                <h3 className="mt-4 text-sm font-semibold">{f.title}</h3>
                <p className="mt-1.5 text-sm text-muted-foreground">{f.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="container py-24">
        <div className="relative overflow-hidden rounded-3xl border border-border bg-card p-10 text-center shadow-card sm:p-16">
          <div className="pointer-events-none absolute inset-0 grid-bg opacity-40" />
          <div className="relative">
            <h2 className="mx-auto max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
              Ask a question the data can actually answer.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
              Every answer is cited to a real filing, or refused. No fabricated figures.
            </p>
            <Link href="/workspace" className="mt-8 inline-block">
              <Button size="lg">
                Open the workspace <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60">
        <div className="container flex flex-col items-center justify-between gap-4 py-8 sm:flex-row">
          <Wordmark />
          <p className="text-xs text-muted-foreground">
            Informational research only — not investment advice.
          </p>
          <a
            href="https://github.com/krish2105/FinCopilot-"
            target="_blank"
            rel="noreferrer"
            className="text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            github.com/krish2105/FinCopilot-
          </a>
        </div>
      </footer>
    </div>
  );
}
