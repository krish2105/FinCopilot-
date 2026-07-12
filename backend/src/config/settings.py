"""Central typed configuration, loaded from environment / .env.

Everything is optional at Phase 0 so the app boots without secrets; later phases
enforce presence of the keys they actually need.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM providers ---
    gemini_api_key: str | None = None
    groq_api_key: str | None = None

    # --- Supabase / database ---
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    database_url: str | None = None

    # --- Optional data providers ---
    fmp_api_key: str | None = None
    newsapi_key: str | None = None

    # --- Graph (Phase 9) ---
    neo4j_uri: str | None = None
    neo4j_user: str | None = None
    neo4j_password: str | None = None

    # --- Runtime ---
    fincopilot_tickers: str = "AAPL,MSFT,AMZN,TSLA,JPM,NVDA,META,GOOGL,EMAAR.AE,IHC.AE"
    fincopilot_offline_mode: bool = False
    log_level: str = "INFO"

    # --- Ingestion ---
    # SEC EDGAR fair-access requires a descriptive User-Agent with contact info.
    edgar_user_agent: str = "FinCopilot research fincopilot@example.com"
    # Where BM25 index / local vector store / raw docs live (gitignored).
    data_dir: str = "data"
    # Embedding backend: "auto" | "gemini" | "local" | "hash".
    #   auto  -> gemini if key present and not offline, else local
    #   local -> sentence-transformers bge-small (falls back to hash if unavailable)
    #   hash  -> deterministic hashing embedder (CI/tests: no torch, no network)
    fincopilot_embed_backend: str = "auto"
    # Reranker backend: "auto" | "cross-encoder" | "lexical".
    #   auto -> cross-encoder unless offline mode (which forces lexical)
    fincopilot_rerank_backend: str = "auto"
    # Chunking (token estimates use ~4 chars/token).
    chunk_target_tokens: int = 512
    chunk_overlap_tokens: int = 64
    # Pseudo-page size in characters for page-level citations in HTML filings.
    page_char_size: int = 3000
    # Ingestion volume caps (keep free tiers happy).
    max_filings_per_type: int = 2
    max_news_per_ticker: int = 10

    @property
    def tickers(self) -> list[str]:
        return [t.strip().upper() for t in self.fincopilot_tickers.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
