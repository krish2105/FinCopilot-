"""News fetcher via GDELT DOC API (free, no key, public articles).

Each recent article becomes a short text document (headline + domain + date) with
a citeable source URL. Failures degrade gracefully to [].
"""

from __future__ import annotations

import logging

import httpx

from src.config.settings import get_settings
from src.ingestion.models import DocType, RawDocument, SourceMetadata

logger = logging.getLogger(__name__)

_GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

# Map tickers to a searchable company name for better news recall.
_NAME_HINTS = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "AMZN": "Amazon",
    "TSLA": "Tesla",
    "JPM": "JPMorgan",
    "NVDA": "Nvidia",
    "META": "Meta Platforms",
    "GOOGL": "Alphabet Google",
    "EMAAR.AE": "Emaar Properties",
    "IHC.AE": "International Holding Company",
}


def _query_for(ticker: str) -> str:
    return _NAME_HINTS.get(ticker.upper(), ticker.upper())


def fetch_news(ticker: str, max_records: int | None = None) -> list[RawDocument]:
    settings = get_settings()
    max_records = max_records or settings.max_news_per_ticker
    params = {
        "query": f'"{_query_for(ticker)}"',
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "sort": "DateDesc",
    }
    try:
        with httpx.Client(timeout=30.0, headers={"User-Agent": "FinCopilot/0.1"}) as c:
            resp = c.get(_GDELT_URL, params=params)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
    except Exception as exc:
        logger.warning("GDELT news fetch failed for %s: %s", ticker, exc)
        return []

    docs: list[RawDocument] = []
    for art in articles:
        title = (art.get("title") or "").strip()
        if not title:
            continue
        domain = art.get("domain", "")
        seendate = art.get("seendate", "")
        filing_date = seendate[:8] if seendate else None
        if filing_date and len(filing_date) == 8:
            filing_date = f"{filing_date[:4]}-{filing_date[4:6]}-{filing_date[6:]}"
        text = f"News ({domain}, {filing_date or 'n/a'}): {title}"
        md = SourceMetadata(
            ticker=ticker.upper(),
            doc_type=DocType.NEWS,
            title=title[:200],
            source_url=art.get("url", ""),
            filing_date=filing_date,
        )
        docs.append(
            RawDocument(
                doc_id=RawDocument.make_doc_id(ticker, DocType.NEWS, art.get("url", title)),
                metadata=md,
                content=text,
                content_type="text",
            )
        )
    logger.info("News: fetched %d articles for %s", len(docs), ticker)
    return docs
