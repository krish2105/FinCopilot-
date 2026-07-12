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

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  ask: (query: string, tickers?: string[]) =>
    req<AgentAnswer>("/ask", {
      method: "POST",
      body: JSON.stringify({ query, tickers: tickers?.length ? tickers : null }),
    }),
  corpusStats: () => req<CorpusStats>("/corpus/stats"),
  graphStats: () => req<GraphStats>("/graph/stats"),
  audit: (limit = 100) =>
    req<{ count: number; records: AuditRecord[] }>(`/audit?limit=${limit}`),
  meta: () => req<{ tickers: string[]; phase: string }>("/"),
};

export const ROUTE_LABEL: Record<string, string> = {
  hybrid: "Hybrid Search",
  agentic: "Agentic Retrieval",
  graphrag: "GraphRAG",
};
