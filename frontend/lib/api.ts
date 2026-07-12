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
  disclaimer: string;
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
  corpusStats: () => req<CorpusStats>("/corpus/stats"),
  graphStats: () => req<GraphStats>("/graph/stats"),
  audit: (limit = 100) =>
    req<{ count: number; records: AuditRecord[] }>(`/audit?limit=${limit}`),
  eval: () => req<EvalResult>("/eval"),
  meta: () => req<{ tickers: string[]; phase: string }>("/"),
};

export const ROUTE_LABEL: Record<string, string> = {
  hybrid: "Hybrid Search",
  agentic: "Agentic Retrieval",
  graphrag: "GraphRAG",
};
