"""Live market data service — Phase 25. Quotes, price history, earnings.

Free-tier, keyless-preferred, cloud-reliable. Provider strategy (in order):

1. **Financial Modeling Prep (FMP)** when ``FMP_API_KEY`` is set — reliable from
   datacenter IPs (Render), free tier ~250 req/day. Primary in production.
2. **yfinance** fallback — keyless, but Yahoo rate-limits datacenter IPs (429), so
   it mainly helps from a laptop / residential IP. Best-effort enrichment.

Every public call:
- degrades gracefully to ``None`` on any failure (never raises up),
- is cached in-process with a short TTL (respect quotas + snappy cold starts),
- is **database-independent** — the dashboard shows live prices before the RAG
  corpus is seeded.

Public market data only — safe to expose unauthenticated.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# range key -> (approx lookback days, downsample stride for the chart)
RANGE_MAP: dict[str, tuple[int, int]] = {
    "1M": (31, 1),
    "3M": (93, 1),
    "6M": (186, 1),
    "1Y": (366, 1),
    "5Y": (1830, 5),
}

# yfinance period/interval per range (fallback path)
_YF_RANGE: dict[str, tuple[str, str]] = {
    "1M": ("1mo", "1d"),
    "3M": ("3mo", "1d"),
    "6M": ("6mo", "1d"),
    "1Y": ("1y", "1d"),
    "5Y": ("5y", "1wk"),
}

# FMP moved to a "stable" API; newly-issued free keys no longer have access to the
# legacy /api/v3 endpoints (they return an auth/plan error). Try stable first and
# fall back to v3 so both old and new keys work.
_FMP_STABLE = "https://financialmodelingprep.com/stable"
_FMP_V3 = "https://financialmodelingprep.com/api/v3"
_CACHE: dict[str, tuple[float, Any]] = {}


def _cached(key: str, ttl: float, fn: Callable[[], Any]) -> Any:
    now = time.time()
    hit = _CACHE.get(key)
    if hit is not None and now - hit[0] < ttl:
        return hit[1]
    val = fn()
    _CACHE[key] = (now, val)
    return val


def _f(v: Any) -> float | None:
    """Coerce to float; None for missing/NaN so the JSON stays clean."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN check


def _fmp_key() -> str | None:
    return get_settings().fmp_api_key or None


def _fmp_get(base: str, path: str, params: dict[str, Any]) -> Any | None:
    key = _fmp_key()
    if not key:
        return None
    import requests

    try:
        resp = requests.get(f"{base}/{path}", params={**params, "apikey": key}, timeout=15)
        if resp.status_code != 200:
            logger.warning("FMP %s/%s -> HTTP %s: %s", base, path, resp.status_code, resp.text[:120])
            return None
        data = resp.json()
        # FMP returns {"Error Message": ...} with HTTP 200 for plan/auth problems.
        if isinstance(data, dict) and ("Error Message" in data or "error" in data):
            logger.warning("FMP %s/%s -> %s", base, path, str(data)[:120])
            return None
        return data
    except Exception as exc:  # noqa: BLE001
        logger.warning("FMP %s/%s failed: %s", base, path, exc)
        return None


# --------------------------------------------------------------------------- #
# Quote
# --------------------------------------------------------------------------- #
def _fmp_quote(ticker: str) -> dict[str, Any] | None:
    sym = ticker.upper()
    # stable: /quote?symbol=AAPL   |   legacy v3: /quote/AAPL
    data = _fmp_get(_FMP_STABLE, "quote", {"symbol": sym}) or _fmp_get(_FMP_V3, f"quote/{sym}", {})
    if not isinstance(data, list) or not data:
        return None
    d = data[0]
    price = _f(d.get("price"))
    if price is None:
        return None
    prev = _f(d.get("previousClose"))
    # stable renamed changesPercentage -> changePercentage
    pct = _f(d.get("changePercentage"))
    if pct is None:
        pct = _f(d.get("changesPercentage"))
    change = _f(d.get("change"))
    return {
        "ticker": sym,
        "name": d.get("name") or sym,
        "price": round(price, 2),
        "previous_close": round(prev, 2) if prev is not None else None,
        "change": round(change, 2) if change is not None else None,
        "change_pct": round(pct, 2) if pct is not None else None,
        "currency": "USD",
        "market_cap": _f(d.get("marketCap")),
        "day_high": _f(d.get("dayHigh")),
        "day_low": _f(d.get("dayLow")),
        "volume": _f(d.get("volume")),
        "pe": _f(d.get("pe")),
        "fifty_two_week_high": _f(d.get("yearHigh")),
        "fifty_two_week_low": _f(d.get("yearLow")),
        "exchange": d.get("exchange"),
        "sector": None,
        "source": "fmp",
    }


def _yf_quote(ticker: str) -> dict[str, Any] | None:
    import yfinance as yf

    t = yf.Ticker(ticker)
    info = t.info or {}
    price = _f(info.get("currentPrice") or info.get("regularMarketPrice"))
    prev = _f(info.get("previousClose") or info.get("regularMarketPreviousClose"))
    if price is None:
        hist = t.history(period="5d", interval="1d")
        if hist is not None and not hist.empty:
            price = _f(hist["Close"].iloc[-1])
            if prev is None and len(hist) >= 2:
                prev = _f(hist["Close"].iloc[-2])
    if price is None:
        return None
    change = (price - prev) if prev is not None else None
    change_pct = (change / prev * 100) if (change is not None and prev) else None
    return {
        "ticker": ticker.upper(),
        "name": info.get("longName") or info.get("shortName") or ticker.upper(),
        "price": round(price, 2),
        "previous_close": round(prev, 2) if prev is not None else None,
        "change": round(change, 2) if change is not None else None,
        "change_pct": round(change_pct, 2) if change_pct is not None else None,
        "currency": info.get("currency") or "USD",
        "market_cap": _f(info.get("marketCap")),
        "day_high": _f(info.get("dayHigh")),
        "day_low": _f(info.get("dayLow")),
        "volume": _f(info.get("volume") or info.get("regularMarketVolume")),
        "pe": _f(info.get("trailingPE")),
        "fifty_two_week_high": _f(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": _f(info.get("fiftyTwoWeekLow")),
        "exchange": info.get("exchange"),
        "sector": info.get("sector"),
        "source": "yfinance",
    }


def get_quote(ticker: str) -> dict[str, Any] | None:
    """Current price + day stats (60s TTL). FMP first, yfinance fallback."""

    def _load() -> dict[str, Any] | None:
        for provider in (_fmp_quote, _yf_quote):
            try:
                q = provider(ticker)
                if q is not None:
                    return q
            except Exception as exc:  # noqa: BLE001
                logger.warning("quote provider %s(%s) failed: %s", provider.__name__, ticker, exc)
        return None

    return _cached(f"quote:{ticker.upper()}", 60.0, _load)


# --------------------------------------------------------------------------- #
# Price history
# --------------------------------------------------------------------------- #
def _downsample(points: list[dict[str, Any]], stride: int) -> list[dict[str, Any]]:
    if stride <= 1 or len(points) <= 2:
        return points
    kept = points[::stride]
    if kept[-1] is not points[-1]:  # always keep the most recent point
        kept.append(points[-1])
    return kept


def _fmp_history(ticker: str, rng: str) -> dict[str, Any] | None:
    sym = ticker.upper()
    days, stride = RANGE_MAP[rng]
    window = {"from": (date.today() - timedelta(days=days)).isoformat(), "to": date.today().isoformat()}

    # stable returns a bare list; legacy v3 wraps rows in {"historical": [...]}.
    data = _fmp_get(_FMP_STABLE, "historical-price-eod/full", {"symbol": sym, **window})
    rows = data if isinstance(data, list) else None
    if rows is None:
        data = _fmp_get(_FMP_V3, f"historical-price-full/{sym}", window)
        rows = data.get("historical") if isinstance(data, dict) else None
    if not rows:
        return None

    points = [
        {"x": row["date"], "y": round(c, 2)}
        for row in rows
        if row.get("date") and (c := _f(row.get("close"))) is not None
    ]
    if not points:
        return None
    points.sort(key=lambda p: p["x"])  # FMP returns newest-first; charts want oldest-first
    points = _downsample(points, stride)
    first, last = points[0]["y"], points[-1]["y"]
    return {
        "ticker": sym,
        "range": rng,
        "points": points,
        "change_pct": round((last - first) / first * 100, 2) if first else None,
        "source": "fmp",
    }


def _yf_history(ticker: str, rng: str) -> dict[str, Any] | None:
    import yfinance as yf

    period, interval = _YF_RANGE[rng]
    hist = yf.Ticker(ticker).history(period=period, interval=interval)
    if hist is None or hist.empty:
        return None
    points: list[dict[str, Any]] = []
    for idx, row in hist.iterrows():
        close = _f(row.get("Close"))
        if close is None:
            continue
        points.append({"x": str(getattr(idx, "date", idx))[:10], "y": round(close, 2)})
    if not points:
        return None
    first, last = points[0]["y"], points[-1]["y"]
    return {
        "ticker": ticker.upper(),
        "range": rng,
        "points": points,
        "change_pct": round((last - first) / first * 100, 2) if first else None,
        "source": "yfinance",
    }


def get_history(ticker: str, rng: str = "1Y") -> dict[str, Any] | None:
    """Close-price series shaped for the chart (300s TTL)."""
    rng = (rng or "1Y").upper()
    if rng not in RANGE_MAP:
        rng = "1Y"

    def _load() -> dict[str, Any] | None:
        for provider in (_fmp_history, _yf_history):
            try:
                h = provider(ticker, rng)
                if h is not None:
                    return h
            except Exception as exc:  # noqa: BLE001
                logger.warning("history provider %s(%s) failed: %s", provider.__name__, ticker, exc)
        return None

    return _cached(f"hist:{ticker.upper()}:{rng}", 300.0, _load)


# --------------------------------------------------------------------------- #
# Earnings
# --------------------------------------------------------------------------- #
def _fmp_earnings(ticker: str) -> dict[str, Any] | None:
    sym = ticker.upper()
    # stable: /earnings?symbol=AAPL (epsActual)  |  v3: /historical/earning_calendar/AAPL (eps)
    data = _fmp_get(_FMP_STABLE, "earnings", {"symbol": sym, "limit": 20})
    if not isinstance(data, list) or not data:
        data = _fmp_get(_FMP_V3, f"historical/earning_calendar/{sym}", {"limit": 20})
    if not isinstance(data, list) or not data:
        return None
    today = date.today().isoformat()
    past: list[dict[str, Any]] = []
    future: list[str] = []
    for row in data:
        d = row.get("date")
        if not d:
            continue
        d = d[:10]
        eps = _f(row.get("epsActual")) if row.get("epsActual") is not None else _f(row.get("eps"))
        est = _f(row.get("epsEstimated"))
        if eps is None:
            if d >= today:
                future.append(d)
            continue
        surprise = ((eps - est) / abs(est) * 100) if (est not in (None, 0)) else None
        past.append(
            {
                "date": d,
                "eps_estimate": est,
                "eps_reported": eps,
                "surprise_pct": round(surprise, 1) if surprise is not None else None,
            }
        )
    past.sort(key=lambda r: r["date"], reverse=True)
    next_date = min(future) if future else None
    if not past and next_date is None:
        return None
    return {"ticker": sym, "next_date": next_date, "history": past[:6], "source": "fmp"}


def _yf_earnings(ticker: str) -> dict[str, Any] | None:
    import yfinance as yf

    t = yf.Ticker(ticker)
    recs: list[dict[str, Any]] = []
    ed = t.earnings_dates
    if ed is not None and not ed.empty:
        for idx, row in ed.iterrows():
            recs.append(
                {
                    "date": str(getattr(idx, "date", idx))[:10],
                    "eps_estimate": _f(row.get("EPS Estimate")),
                    "eps_reported": _f(row.get("Reported EPS")),
                    "surprise_pct": _f(row.get("Surprise(%)")),
                }
            )
    today = date.today().isoformat()
    past = sorted(
        (r for r in recs if r["eps_reported"] is not None),
        key=lambda r: r["date"],
        reverse=True,
    )[:6]
    upcoming = sorted(r["date"] for r in recs if r["eps_reported"] is None and r["date"] >= today)
    next_date = upcoming[0] if upcoming else None
    if not past and next_date is None:
        return None
    return {"ticker": ticker.upper(), "next_date": next_date, "history": past, "source": "yfinance"}


def get_earnings(ticker: str) -> dict[str, Any] | None:
    """Recent EPS beats/misses + next report date (900s TTL)."""

    def _load() -> dict[str, Any] | None:
        for provider in (_fmp_earnings, _yf_earnings):
            try:
                e = provider(ticker)
                if e is not None:
                    return e
            except Exception as exc:  # noqa: BLE001
                logger.warning("earnings provider %s(%s) failed: %s", provider.__name__, ticker, exc)
        return None

    return _cached(f"earn:{ticker.upper()}", 900.0, _load)
