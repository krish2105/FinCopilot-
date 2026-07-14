// Typed client for the FinCopilot FastAPI backend.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

// ---- Types mirroring backend Pydantic schemas ----
export interface Citation {
  marker: string;
  ticker: string;
  doc_type: string;
  title: string;
  page: number | null;
  section: string | null;
  source_url: string;
  excerpt: string;
}

export interface Finding {
  label: string;
  value: string;
  citation_marker: string;
  kind: string;
}

export interface ComplianceFlag {
  category: string;
  detail: string;
  citation_marker: string;
}

export interface ChartPoint {
  x: string;
  y: number;
}
export interface ChartSeries {
  name: string;
  points: ChartPoint[];
}
export interface ChartSpec {
  type: string;
  title: string;
  x_label: string;
  y_label: string;
  series: ChartSeries[];
}

export interface ProviderCall {
  provider: string;
  model: string;
  cached: boolean;
  latency_ms: number;
}

export interface Faithfulness {
  faithful: boolean;
  score: number;
  unsupported_claims: string[];
  ungrounded_numbers: string[];
  reason: string;
}

export interface AgentAnswer {
  query: string;
  route: string;
  planned_route: string;
  verdict: string;
  answer: string;
  citations: Citation[];
  findings: Finding[];
  flags: ComplianceFlag[];
  charts: ChartSpec[];
  provider_trace: ProviderCall[];
  faithfulness: Faithfulness;
  reranker: string;
  embed_backend: string;
  evidence_count: number;
  latency_ms: number;
  cost_usd: number;
  disclaimer: string;
}

// ---- Live market data (Phase 25) ----
export interface Quote {
  ticker: string;
  name: string;
  price: number;
  previous_close: number | null;
  change: number | null;
  change_pct: number | null;
  currency: string;
  market_cap: number | null;
  day_high: number | null;
  day_low: number | null;
  volume: number | null;
  pe: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  exchange: string | null;
  sector: string | null;
  source: string;
}

export interface PriceHistory {
  ticker: string;
  range: string;
  points: { x: string; y: number }[];
  change_pct: number | null;
  source: string;
}

export interface EarningsRow {
  date: string;
  eps_estimate: number | null;
  eps_reported: number | null;
  surprise_pct: number | null;
}
export interface Earnings {
  ticker: string;
  next_date: string | null;
  history: EarningsRow[];
  source: string;
}

export const PRICE_RANGES = ["1M", "3M", "6M", "1Y", "5Y"] as const;
export type PriceRange = (typeof PRICE_RANGES)[number];

export interface Watchlist {
  id: string;
  ticker: string;
  created_at?: string;
}

// ---- Insight layer (Phase 40) ----
export interface RiskChange {
  change: string; // new | removed | escalated
  topic: string;
  detail: string;
  citation_marker: string;
}
export interface RiskDiff {
  ticker: string;
  year_from: string;
  year_to: string;
  summary: string;
  changes: RiskChange[];
  available: boolean;
  message: string;
}

export interface RedFlag {
  category: string;
  detail: string;
  severity: string; // high | medium | low
  source_url: string;
  title: string;
}
export interface RedFlagReport {
  ticker: string;
  flags: RedFlag[];
  scanned_sources: number;
  clean: boolean;
}

export interface SharedRisk {
  topic: string;
  companies: string[];
  concentration: number;
}
export interface PortfolioOverlap {
  tickers: string[];
  shared_risks: SharedRisk[];
  summary: string;
}

export interface FundamentalPoint {
  period: string;
  revenue: number | null;
  net_income: number | null;
  gross_margin: number | null;
  net_margin: number | null;
  eps: number | null;
}
export interface Fundamentals {
  ticker: string;
  points: FundamentalPoint[];
  source: string;
}

export interface PeerRow {
  ticker: string;
  name: string;
  price: number | null;
  change_pct: number | null;
  market_cap: number | null;
  pe: number | null;
  revenue: number | null;
  net_margin: number | null;
}
export interface PeerTable {
  rows: PeerRow[];
}

export interface CorpusStats {
  embed_backend: string;
  embed_dim: number;
  vector_chunks: number;
  bm25_docs: number;
  chunks_by_ticker: Record<string, number>;
}

export interface GraphStats {
  built: boolean;
  nodes?: number;
  edges?: number;
  by_kind?: Record<string, number>;
  risk_topics?: string[];
  message?: string;
}

export interface AuditRecord {
  id: string;
  timestamp: string;
  query: string;
  tickers: string[];
  planned_route: string;
  route: string;
  verdict: string;
  evidence_count: number;
  sources: string[];
  providers: string[];
  faithfulness_score: number;
  latency_ms: number;
}

export interface EvalResult {
  available: boolean;
  message?: string;
  benchmark?: string;
  generated_at?: string;
  n_questions?: number;
  n_companies?: number;
  stack?: { embed_backend: string; reranker: string; llm_mode: string };
  metrics?: {
    n_questions: number;
    context_hit: number;
    answer_match: number;
    faithful_rate: number;
    citation_coverage: number;
    refusal_rate: number;
    avg_latency_ms: number;
  };
  ragas?: {
    faithfulness?: number;
    answer_relevancy?: number;
    context_precision?: number;
    context_recall?: number;
  } | null;
  per_question?: {
    company: string;
    question: string;
    gold: string;
    context_hit: number;
    answer_match: number;
    faithful: number;
    route: string;
  }[];
}

export interface Workspace {
  id: string;
  org_id: string;
  name: string;
  kind: string;
}
export interface DocumentMeta {
  id: string;
  workspace_id: string;
  filename: string;
  doc_type: string;
  status: string;
  chunk_count: number;
  created_at: string;
}
export interface ConversationMeta {
  id: string;
  workspace_id: string;
  title: string;
  created_at: string;
}
export interface Plan {
  id: string;
  name: string;
  price_usd_month: number;
  queries_per_month: number;
  max_documents: number;
  max_seats: number;
  features: string[];
}
export interface Usage {
  plan: Plan;
  queries_used: number;
  queries_limit: number;
  queries_remaining: number;
  documents_used: number;
  documents_limit: number;
  tokens_used: number;
  est_cost_usd: number;
}

async function authHeaders(): Promise<Record<string, string>> {
  // Attach the Supabase session token when auth is configured; else demo tenant.
  try {
    const { getSupabase } = await import("@/lib/supabase");
    const sb = getSupabase();
    if (sb) {
      const {
        data: { session },
      } = await sb.auth.getSession();
      if (session?.access_token) return { Authorization: `Bearer ${session.access_token}` };
    }
  } catch {
    /* demo mode */
  }
  return {};
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const auth = await authHeaders();
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...auth, ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  ask: (query: string, tickers?: string[], workspaceId?: string) =>
    req<AgentAnswer>("/ask", {
      method: "POST",
      body: JSON.stringify({
        query,
        tickers: tickers?.length ? tickers : null,
        workspace_id: workspaceId || null,
      }),
    }),
  askStream: async (
    query: string,
    tickers: string[] | undefined,
    workspaceId: string | undefined,
    on: {
      onStep?: (label: string) => void;
      onToken?: (text: string) => void;
      onAnswer?: (a: AgentAnswer) => void;
    },
  ) => {
    const auth = await authHeaders();
    const res = await fetch(`${API_BASE}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...auth },
      body: JSON.stringify({
        query,
        tickers: tickers?.length ? tickers : null,
        workspace_id: workspaceId || null,
      }),
    });
    if (!res.ok || !res.body) throw new Error(`API ${res.status}`);
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split("\n\n");
      buf = parts.pop() || "";
      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data:")) continue;
        const ev = JSON.parse(line.slice(5).trim());
        if (ev.event === "step") on.onStep?.(ev.label);
        else if (ev.event === "token") on.onToken?.(ev.text);
        else if (ev.event === "answer") on.onAnswer?.(ev.answer as AgentAnswer);
      }
    }
  },
  // workspaces / data rooms
  workspaces: () => req<{ workspaces: Workspace[] }>("/workspaces"),
  createWorkspace: (name: string) =>
    req<Workspace>("/workspaces", { method: "POST", body: JSON.stringify({ name }) }),
  documents: (wsId: string) =>
    req<{ documents: DocumentMeta[] }>(`/workspaces/${wsId}/documents`),
  deleteDocument: (docId: string) =>
    req<{ deleted: string }>(`/documents/${docId}`, { method: "DELETE" }),
  uploadDocument: async (wsId: string, file: File) => {
    const auth = await authHeaders();
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/workspaces/${wsId}/documents`, {
      method: "POST",
      headers: auth,
      body: form,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text().catch(() => "")}`);
    return res.json() as Promise<DocumentMeta>;
  },
  // conversation history
  conversations: () =>
    req<{ conversations: ConversationMeta[] }>("/conversations"),
  conversation: (id: string) =>
    req<{ messages: { role: string; content: string; answer?: AgentAnswer; created_at: string }[] }>(
      `/conversations/${id}`,
    ),
  // billing / usage
  usage: () => req<Usage>("/usage"),
  plans: () => req<{ plans: Plan[]; configured: boolean }>("/billing/plans"),
  checkout: (planId: string) =>
    req<{ url: string }>("/billing/checkout", {
      method: "POST",
      body: JSON.stringify({
        plan_id: planId,
        success_url: `${window.location.origin}/billing?ok=1`,
        cancel_url: `${window.location.origin}/billing`,
      }),
    }),
  feedback: (rating: number, query: string) =>
    req<{ recorded: boolean }>("/feedback", {
      method: "POST",
      body: JSON.stringify({ rating, query }),
    }),
  // team / RBAC
  members: () =>
    req<{
      members: { id: string; email: string; role: string }[];
      seats_used: number;
      seats_limit: number;
    }>("/org/members"),
  invites: () =>
    req<{ invites: { id: string; email: string; role: string }[] }>("/org/invites"),
  invite: (email: string, role: string) =>
    req<{ token: string; email: string }>("/org/invites", {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }),
  revokeInvite: (id: string) =>
    req<{ revoked: string }>(`/org/invites/${id}`, { method: "DELETE" }),
  updateMember: (userId: string, role: string) =>
    req(`/org/members/${userId}`, { method: "PATCH", body: JSON.stringify({ role }) }),
  removeMember: (userId: string) =>
    req(`/org/members/${userId}`, { method: "DELETE" }),
  // API keys
  apiKeys: () =>
    req<{ keys: { id: string; name: string; prefix: string; last_used: string | null }[] }>(
      "/api-keys",
    ),
  createApiKey: (name: string) =>
    req<{ api_key: string; prefix: string }>("/api-keys", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  deleteApiKey: (id: string) => req(`/api-keys/${id}`, { method: "DELETE" }),
  // insights (Phase 40)
  riskDiff: (ticker: string) => req<RiskDiff>(`/insights/risk-diff/${encodeURIComponent(ticker)}`),
  redFlags: (ticker: string) =>
    req<RedFlagReport>(`/insights/red-flags/${encodeURIComponent(ticker)}`),
  fundamentals: (ticker: string) =>
    req<Fundamentals>(`/insights/fundamentals/${encodeURIComponent(ticker)}`),
  peers: (tickers: string[]) =>
    req<PeerTable>(`/insights/peers?tickers=${encodeURIComponent(tickers.join(","))}`),
  portfolio: (tickers: string[]) =>
    req<PortfolioOverlap>("/insights/portfolio", {
      method: "POST",
      body: JSON.stringify({ tickers }),
    }),
  // watchlist (Phase 34)
  watchlists: () => req<{ watchlists: Watchlist[] }>("/watchlists"),
  addWatch: (ticker: string) =>
    req<Watchlist>("/watchlists", { method: "POST", body: JSON.stringify({ ticker }) }),
  removeWatch: (id: string) => req<{ deleted: string }>(`/watchlists/${id}`, { method: "DELETE" }),
  // live market data (Phase 25)
  quote: (ticker: string) => req<Quote>(`/market/quote/${encodeURIComponent(ticker)}`),
  history: (ticker: string, range: string) =>
    req<PriceHistory>(`/market/history/${encodeURIComponent(ticker)}?range=${range}`),
  earnings: (ticker: string) => req<Earnings>(`/market/earnings/${encodeURIComponent(ticker)}`),
  corpusStats: () => req<CorpusStats>("/corpus/stats"),
  graphStats: () => req<GraphStats>("/graph/stats"),
  audit: (limit = 100) =>
    req<{ count: number; records: AuditRecord[] }>(`/audit?limit=${limit}`),
  eval: () => req<EvalResult>("/eval"),
  meta: () => req<{ tickers: string[]; phase: string }>("/"),
  health: () => req<{ status: string }>("/health"),
  ready: () => req<{ ready: boolean; error?: string }>("/ready"),
};

export const ROUTE_LABEL: Record<string, string> = {
  hybrid: "Hybrid Search",
  agentic: "Agentic Retrieval",
  graphrag: "GraphRAG",
};
