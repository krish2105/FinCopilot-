"""SEC EDGAR fetcher — real 10-K / 10-Q / 8-K filings, free, no API key.

Flow: ticker -> CIK (company_tickers.json) -> submissions API -> pick recent
filings by form -> fetch the primary document HTML. Honors SEC fair-access:
descriptive User-Agent, polite pacing.

Non-US tickers (e.g. UAE `.AE` names) aren't in EDGAR — those return [] and the
pipeline relies on market/news sources for them instead.
"""

from __future__ import annotations

import logging
import re
import time

import httpx

from src.config.settings import get_settings
from src.ingestion.models import DocType, RawDocument, SourceMetadata

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
_ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"

_FORM_TO_DOCTYPE = {"10-K": DocType.TEN_K, "10-Q": DocType.TEN_Q, "8-K": DocType.EIGHT_K}

_cik_cache: dict[str, int] | None = None


def _client() -> httpx.Client:
    ua = get_settings().edgar_user_agent
    return httpx.Client(
        headers={"User-Agent": ua, "Accept-Encoding": "gzip, deflate"},
        timeout=30.0,
    )


def _load_cik_map(client: httpx.Client) -> dict[str, int]:
    global _cik_cache
    if _cik_cache is not None:
        return _cik_cache
    resp = client.get(_TICKERS_URL)
    resp.raise_for_status()
    data = resp.json()
    _cik_cache = {row["ticker"].upper(): int(row["cik_str"]) for row in data.values()}
    return _cik_cache


def ticker_to_cik(ticker: str, client: httpx.Client) -> int | None:
    return _load_cik_map(client).get(ticker.upper())


def fetch_filings(
    ticker: str, forms: list[str] | None = None, per_form: int | None = None
) -> list[RawDocument]:
    settings = get_settings()
    forms = forms or ["10-K", "10-Q", "8-K"]
    per_form = per_form or settings.max_filings_per_type

    if "." in ticker:  # e.g. EMAAR.AE — not an EDGAR registrant
        logger.info("Skipping EDGAR for non-US ticker %s", ticker)
        return []

    docs: list[RawDocument] = []
    with _client() as client:
        cik = ticker_to_cik(ticker, client)
        if cik is None:
            logger.warning("No EDGAR CIK for %s", ticker)
            return []

        try:
            sub = client.get(_SUBMISSIONS_URL.format(cik=cik))
            sub.raise_for_status()
            recent = sub.json()["filings"]["recent"]
        except Exception as exc:
            logger.warning("EDGAR submissions fetch failed for %s: %s", ticker, exc)
            return []

        counts = {f: 0 for f in forms}
        n = len(recent["form"])
        for i in range(n):
            form = recent["form"][i]
            if form not in forms or counts[form] >= per_form:
                continue
            acc = recent["accessionNumber"][i].replace("-", "")
            primary = recent["primaryDocument"][i]
            if not primary:
                continue
            url = _ARCHIVE_URL.format(cik=cik, acc=acc, doc=primary)
            time.sleep(0.2)  # polite pacing (<10 req/s)
            try:
                page = client.get(url)
                page.raise_for_status()
            except Exception as exc:
                logger.warning("EDGAR doc fetch failed (%s): %s", url, exc)
                continue

            doc_type = _FORM_TO_DOCTYPE[form]
            filing_date = recent["filingDate"][i]
            md = SourceMetadata(
                ticker=ticker.upper(),
                doc_type=doc_type,
                title=f"{ticker.upper()} {form} ({filing_date})",
                source_url=url,
                filing_date=filing_date,
            )
            docs.append(
                RawDocument(
                    doc_id=RawDocument.make_doc_id(ticker, doc_type, acc),
                    metadata=md,
                    content=page.text,
                    content_type="html",
                )
            )
            counts[form] += 1
            if all(counts[f] >= per_form for f in forms):
                break

    logger.info("EDGAR: fetched %d filings for %s", len(docs), ticker)
    return docs


_INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json"


def fetch_subsidiaries(ticker: str) -> list[RawDocument]:
    """Fetch the latest 10-K's Exhibit 21 (list of subsidiaries), if present."""
    if "." in ticker:
        return []
    with _client() as client:
        cik = ticker_to_cik(ticker, client)
        if cik is None:
            return []
        try:
            sub = client.get(_SUBMISSIONS_URL.format(cik=cik))
            sub.raise_for_status()
            recent = sub.json()["filings"]["recent"]
        except Exception as exc:
            logger.warning("EDGAR submissions fetch failed for %s: %s", ticker, exc)
            return []

        # Find the most recent 10-K accession.
        acc = next(
            (
                recent["accessionNumber"][i].replace("-", "")
                for i in range(len(recent["form"]))
                if recent["form"][i] == "10-K"
            ),
            None,
        )
        if not acc:
            return []

        try:
            idx = client.get(_INDEX_URL.format(cik=cik, acc=acc))
            idx.raise_for_status()
            items = idx.json()["directory"]["item"]
        except Exception as exc:
            logger.warning("EDGAR index fetch failed for %s: %s", ticker, exc)
            return []

        # The index.json `type` is often just an icon, so match the filename too.
        # EDGAR names look like "ex-21.htm", "aapl-ex211.htm", "a2025exhibit2110k.htm".
        ex21 = next(
            (
                it["name"]
                for it in items
                if str(it.get("type", "")).upper().startswith("EX-21")
                or re.search(r"(?:ex|exhibit)[\s_-]?21", it.get("name", ""), re.IGNORECASE)
            ),
            None,
        )
        if not ex21:
            return []

        url = _ARCHIVE_URL.format(cik=cik, acc=acc, doc=ex21)
        time.sleep(0.2)
        try:
            page = client.get(url)
            page.raise_for_status()
        except Exception as exc:
            logger.warning("EDGAR Exhibit 21 fetch failed (%s): %s", url, exc)
            return []

    md = SourceMetadata(
        ticker=ticker.upper(),
        doc_type=DocType.SUBSIDIARIES,
        title=f"{ticker.upper()} 10-K Exhibit 21 (Subsidiaries)",
        source_url=url,
    )
    return [
        RawDocument(
            doc_id=RawDocument.make_doc_id(ticker, DocType.SUBSIDIARIES, acc),
            metadata=md,
            content=page.text,
            content_type="html",
        )
    ]
