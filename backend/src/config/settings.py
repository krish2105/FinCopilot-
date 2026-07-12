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

    @property
    def tickers(self) -> list[str]:
        return [t.strip().upper() for t in self.fincopilot_tickers.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
