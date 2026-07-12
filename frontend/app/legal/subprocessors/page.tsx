import type { Metadata } from "next";
import { LegalShell } from "@/components/legal-shell";

export const metadata: Metadata = {
  title: "Subprocessors — FinCopilot",
  description: "The infrastructure and AI subprocessors FinCopilot uses.",
};

const SUBPROCESSORS: { name: string; purpose: string; location: string }[] = [
  { name: "Vercel", purpose: "Frontend hosting & CDN", location: "USA" },
  { name: "Render", purpose: "Backend API hosting", location: "USA (Oregon)" },
  { name: "Supabase", purpose: "Database (Postgres + pgvector), auth, storage", location: "Configurable region" },
  { name: "Google (Gemini API)", purpose: "LLM & embeddings (no-training terms)", location: "USA" },
  { name: "Groq", purpose: "LLM inference fallback", location: "USA" },
  { name: "Financial Modeling Prep", purpose: "Market quotes, price history, earnings", location: "USA" },
  { name: "PostHog", purpose: "Product analytics (optional)", location: "USA / EU" },
  { name: "Sentry", purpose: "Error monitoring (optional)", location: "USA" },
  { name: "Langfuse", purpose: "LLM tracing/observability (optional)", location: "EU / USA" },
];

export default function SubprocessorsPage() {
  return (
    <LegalShell title="Subprocessors" updated="July 13, 2026">
      <p>
        We use the third-party subprocessors below to operate FinCopilot. Each is bound by
        data-protection obligations. We provide notice before adding a new subprocessor. Optional
        services run only when configured.
      </p>

      <table>
        <thead>
          <tr>
            <th>Subprocessor</th>
            <th>Purpose</th>
            <th>Location</th>
          </tr>
        </thead>
        <tbody>
          {SUBPROCESSORS.map((s) => (
            <tr key={s.name}>
              <td className="font-medium text-foreground">{s.name}</td>
              <td className="text-muted-foreground">{s.purpose}</td>
              <td className="text-muted-foreground">{s.location}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p>
        Questions about our subprocessors? Contact{" "}
        <a href="mailto:privacy@fincopilot.app">privacy@fincopilot.app</a>.
      </p>
    </LegalShell>
  );
}
