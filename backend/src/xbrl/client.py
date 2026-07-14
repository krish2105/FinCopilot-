"""SEC XBRL client (Phase 45) — free, keyless, uncapped.

`data.sec.gov` serves every XBRL fact every company has ever filed. No API key, no
daily quota; the only requirement is a descriptive User-Agent (SEC fair-access rules)
and staying under ~10 requests/second.

This is the one financial data source that is genuinely free *at scale*, which is why
fundamentals, the screener, DCF and the Sankey are all built on it rather than on a
250-calls-a-day vendor tier.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
_MIN_INTERVAL = 0.12  # ~8 req/s, comfortably inside SEC's fair-access limit

_last_call = 0.0
_ticker_map: dict[str, int] | None = None


def _headers() -> dict[str, str]:
    ua = get_settings().edgar_user_agent
    if not ua:
        # SEC blocks anonymous traffic; be explicit rather than failing obscurely.
        raise RuntimeError("EDGAR_USER_AGENT must be set (SEC fair-access requires it)")
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


def _get(url: str) -> Any | None:
    """One throttled GET against the SEC."""
    global _last_call
    import requests

    wait = _MIN_INTERVAL - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = requests.get(url, headers=_headers(), timeout=30)
        _last_call = time.monotonic()
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            logger.warning("SEC %s -> HTTP %s", url, resp.status_code)
            return None
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("SEC %s failed: %s", url, exc)
        return None


def cik_for(ticker: str) -> int | None:
    """CIK for a ticker (the SEC keys everything by CIK, not by symbol)."""
    global _ticker_map
    if _ticker_map is None:
        data = _get(_TICKERS_URL)
        if not data:
            return None
        _ticker_map = {
            row["ticker"].upper(): int(row["cik_str"])
            for row in data.values()
            if row.get("ticker")
        }
        logger.info("SEC ticker map loaded: %d symbols", len(_ticker_map))
    return _ticker_map.get(ticker.upper())


def company_facts(ticker: str) -> dict | None:
    """Every XBRL fact this company has filed."""
    cik = cik_for(ticker)
    if cik is None:
        logger.warning("no CIK for %s", ticker)
        return None
    return _get(_FACTS_URL.format(cik=cik))
