import Link from "next/link";
import type { Metadata } from "next";
import { MarketingNav } from "@/components/marketing-nav";
import { Wordmark } from "@/components/brand";
import { Badge } from "@/components/ui/badge";

export const metadata: Metadata = {
  title: "Docs — FinCopilot",
  description: "Quickstart and API reference for the FinCopilot cited-RAG engine.",
};

function Code({ children }: { children: string }) {
  return (
    <pre className="mt-3 overflow-x-auto rounded-lg border border-border bg-muted/40 p-4 text-xs leading-relaxed scrollbar-thin">
      <code className="font-mono text-foreground">{children}</code>
    </pre>
  );
}

function Method({ m }: { m: string }) {
  const color =
    m === "POST"
      ? "text-route-agentic"
      : m === "DELETE"
        ? "text-danger"
        : "text-route-hybrid";
  return <span className={`font-mono text-xs font-semibold ${color}`}>{m}</span>;
}

const NAV = [
  ["quickstart", "Quickstart"],
  ["auth", "Authentication"],
  ["ask", "Ask (cited answer)"],
  ["stream", "Streaming"],
  ["rooms", "Data rooms"],
  ["usage", "Usage & quotas"],
];

export default function DocsPage() {
  return (
    <div className="min-h-dvh bg-background">
      <MarketingNav />
      <div className="container flex gap-10 py-12">
        {/* Sidebar */}
        <aside className="sticky top-24 hidden h-max w-48 shrink-0 lg:block">
          <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            On this page
          </p>
          <nav className="flex flex-col gap-1.5 text-sm">
            {NAV.map(([id, label]) => (
              <a key={id} href={`#${id}`} className="text-muted-foreground hover:text-foreground">
                {label}
              </a>
            ))}
          </nav>
        </aside>

        {/* Content */}
        <main className="min-w-0 max-w-2xl">
          <h1 className="text-3xl font-semibold tracking-tight">Documentation</h1>
          <p className="mt-2 text-muted-foreground">
            FinCopilot is a cited, multi-agent RAG engine over real filings. Use it in the app or
            programmatically via the API. Base URL is your deployed API origin.
          </p>

          <section id="quickstart" className="mt-10">
            <h2 className="text-xl font-semibold">Quickstart</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Sign in, then ask a question in the workspace — you&apos;ll get a cited answer with a
              route badge, or an honest &quot;insufficient evidence&quot; refusal.
            </p>
            <Code>{`# Local dev
cp .env.example .env        # add GEMINI_API_KEY / GROQ_API_KEY (optional)
docker compose up           # backend :8000 + frontend :3000`}</Code>
          </section>

          <section id="auth" className="mt-10">
            <h2 className="text-xl font-semibold">Authentication</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              The app uses Supabase session tokens. For programmatic access, create an API key in
              Settings and send it as <span className="font-mono">X-API-Key</span>.
            </p>
            <div className="mt-3 flex items-center gap-2 text-sm">
              <Method m="POST" /> <span className="font-mono">/api-keys</span>{" "}
              <Badge variant="outline">returns the key once</Badge>
            </div>
            <Code>{`curl -X POST https://api.example.com/api-keys \\
  -H 'content-type: application/json' -d '{"name":"prod"}'
# -> { "api_key": "fk_...", "prefix": "fk_...", "expires_at": "..." }

# then authenticate:
curl https://api.example.com/usage -H 'X-API-Key: fk_...'`}</Code>
          </section>

          <section id="ask" className="mt-10">
            <h2 className="text-xl font-semibold">Ask a question</h2>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <Method m="POST" /> <span className="font-mono">/ask</span>
            </div>
            <Code>{`curl -X POST https://api.example.com/ask \\
  -H 'content-type: application/json' -H 'X-API-Key: fk_...' \\
  -d '{"query":"What risk factors does Apple disclose?","tickers":["AAPL"]}'`}</Code>
            <p className="mt-3 text-sm text-muted-foreground">
              Returns the cited <span className="font-mono">answer</span>, an array of{" "}
              <span className="font-mono">citations</span> (ticker/page/section/url), analyst{" "}
              <span className="font-mono">findings</span>, compliance{" "}
              <span className="font-mono">flags</span>, chart specs, the{" "}
              <span className="font-mono">verdict</span>, faithfulness score, provider trace,{" "}
              latency, and estimated cost.
            </p>
          </section>

          <section id="stream" className="mt-10">
            <h2 className="text-xl font-semibold">Streaming (SSE)</h2>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <Method m="POST" /> <span className="font-mono">/ask/stream</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Server-Sent Events: a <span className="font-mono">step</span> event per agent
              (classify → research → analyze → comply → synthesize → verify), streamed{" "}
              <span className="font-mono">token</span> events, then a final{" "}
              <span className="font-mono">answer</span> event with the full cited result.
            </p>
            <Code>{`data: {"event":"step","node":"research","label":"Researching evidence"}
data: {"event":"token","text":"Apple "}
data: {"event":"answer","answer": { ...AgentAnswer } }
data: {"event":"done"}`}</Code>
          </section>

          <section id="rooms" className="mt-10">
            <h2 className="text-xl font-semibold">Data rooms</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Upload private documents into a workspace and scope questions to it. Content is
              tenant-isolated (workspace filter + Postgres RLS in production).
            </p>
            <Code>{`curl -X POST .../workspaces -d '{"name":"Deal A"}'          # -> { id }
curl -X POST .../workspaces/<id>/documents -F file=@q3.pdf   # ingest
curl -X POST .../ask -d '{"query":"...","workspace_id":"<id>"}'`}</Code>
          </section>

          <section id="usage" className="mt-10">
            <h2 className="text-xl font-semibold">Usage & quotas</h2>
            <div className="mt-2 flex items-center gap-2 text-sm">
              <Method m="GET" /> <span className="font-mono">/usage</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              Plans (Free/Pro/Team) enforce per-month query and document quotas plus a per-minute
              rate limit. Requests over quota return <span className="font-mono">402</span>; over
              the rate limit, <span className="font-mono">429</span>.
            </p>
          </section>

          <div className="mt-12 rounded-xl border border-border bg-card p-6">
            <p className="text-sm font-medium">Ready to try it?</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Open the workspace and ask your first cited question.
            </p>
            <Link
              href="/workspace"
              className="mt-3 inline-block text-sm font-medium text-accent hover:underline"
            >
              Open workspace →
            </Link>
          </div>
        </main>
      </div>

      <footer className="border-t border-border/60">
        <div className="container flex items-center justify-between py-8">
          <Wordmark />
          <p className="text-xs text-muted-foreground">Not investment advice.</p>
        </div>
      </footer>
    </div>
  );
}
