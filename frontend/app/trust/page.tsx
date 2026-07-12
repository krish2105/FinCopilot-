import Link from "next/link";
import type { Metadata } from "next";
import {
  ClipboardCheck,
  FileLock2,
  KeyRound,
  Lock,
  ScanEye,
  ShieldCheck,
  Trash2,
  Users,
} from "lucide-react";
import { MarketingNav } from "@/components/marketing-nav";
import { Wordmark } from "@/components/brand";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = {
  title: "Trust & Security — FinCopilot",
  description: "How FinCopilot protects your data: tenant isolation, RLS, RBAC, audit, GDPR.",
};

const CONTROLS = [
  { icon: FileLock2, title: "Tenant isolation + RLS", body: "Every document is workspace-scoped; in production, Postgres row-level security makes cross-tenant reads impossible even if app code has a bug." },
  { icon: ShieldCheck, title: "Grounded, refused-when-unsure", body: "A Self-RAG faithfulness gate blocks any ungrounded number. FinCopilot refuses instead of hallucinating." },
  { icon: ScanEye, title: "Prompt-injection defenses", body: "Uploaded content is treated as untrusted data, flagged for override patterns, and wrapped so the model never follows instructions inside it." },
  { icon: Users, title: "RBAC + SSO-ready", body: "Owner/admin/member/viewer roles enforced on every route, seat-limited invites, API keys. SSO/SAML on the enterprise roadmap." },
  { icon: KeyRound, title: "Secrets & keys", body: "No secrets in code — environment only. API keys are stored hashed and expire; CORS is locked to your frontend origin." },
  { icon: ClipboardCheck, title: "Audit trail", body: "Every query, route, sources, provider, verdict, and latency is recorded per-tenant and exportable." },
  { icon: Trash2, title: "Your data rights", body: "One-click data export and permanent deletion (GDPR-style), including purge of your vectors from the store." },
  { icon: Lock, title: "Supply chain", body: "CodeQL scanning (Python + TypeScript) and automated Dependabot updates on every dependency." },
];

export default function TrustPage() {
  return (
    <div className="min-h-dvh bg-background">
      <MarketingNav />
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute inset-0 grid-bg opacity-50" />
        <div className="container relative py-16 text-center sm:py-20">
          <Badge variant="accent" className="mb-5">
            <ShieldCheck className="h-3.5 w-3.5" /> Trust & Security
          </Badge>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
            Built for teams that can&apos;t afford a hallucination
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-muted-foreground">
            Finance research demands provable answers and airtight data handling. Here&apos;s how
            FinCopilot protects your firm and your data.
          </p>
        </div>
      </section>

      <section className="container pb-16">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CONTROLS.map((c) => (
            <Card key={c.title} className="p-5">
              <c.icon className="h-5 w-5 text-accent" />
              <h3 className="mt-3 text-sm font-semibold">{c.title}</h3>
              <p className="mt-1.5 text-sm text-muted-foreground">{c.body}</p>
            </Card>
          ))}
        </div>

        <Card className="mt-6 flex flex-col items-start gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-sm font-semibold">Compliance</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              SOC 2 Type II is on our roadmap; EU AI Act transparency (this is informational
              research, not investment advice, and AI-generated) is disclosed in-product. Report a
              vulnerability via a GitHub Security Advisory.
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <Badge variant="outline">SOC 2 — planned</Badge>
            <Badge variant="positive">GDPR export/delete</Badge>
          </div>
        </Card>
      </section>

      <footer className="border-t border-border/60">
        <div className="container flex flex-wrap items-center justify-between gap-4 py-8">
          <Wordmark />
          <nav className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <Link href="/legal/terms" className="hover:text-foreground">Terms</Link>
            <Link href="/legal/privacy" className="hover:text-foreground">Privacy</Link>
            <Link href="/legal/dpa" className="hover:text-foreground">DPA</Link>
            <Link href="/legal/subprocessors" className="hover:text-foreground">Subprocessors</Link>
            <Link href="/status" className="hover:text-foreground">Status</Link>
            <Link href="/docs" className="hover:text-foreground">Docs</Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
