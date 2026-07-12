"""Market/fundamentals fetcher via yfinance (free, no key).

Financial statements are rendered to citeable text documents (DocType.market) so
the Analyst agent can retrieve and cite specific line items just like filing text.
Network/parse failures degrade gracefully to [].
"""

from __future__ import annotations

import logging

from src.ingestion.models import DocType, RawDocument, SourceMetadata

logger = logging.getLogger(__name__)

_YF_URL = "https://finance.yahoo.com/quote/{ticker}"


def _fmt_num(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "n/a"
    if f != f:  # NaN
        return "n/a"
    return f"{f:,.0f}"


def _statement_to_text(ticker: str, name: str, df) -> str | None:
    if df is None or getattr(df, "empty", True):
        return None
    lines = [f"{ticker} — {name} (values in reporting currency):"]
    cols = list(df.columns)[:4]  # most recent periods
    for row_label in df.index:
        vals = []
        for c in cols:
            period = str(getattr(c, "date", c))[:10]
            vals.append(f"{period}={_fmt_num(df.loc[row_label, c])}")
        lines.append(f"  {row_label}: " + "; ".join(vals))
    return "\n".join(lines)


def _profile_to_text(ticker: str, info: dict) -> str | None:
    if not info:
        return None
    fields = [
        ("Company", info.get("longName")),
        ("Sector", info.get("sector")),
        ("Industry", info.get("industry")),
        ("Market cap", _fmt_num(info.get("marketCap"))),
        ("Trailing P/E", info.get("trailingPE")),
        ("Profit margin", info.get("profitMargins")),
        ("Total revenue (ttm)", _fmt_num(info.get("totalRevenue"))),
        ("Total debt", _fmt_num(info.get("totalDebt"))),
        ("Current ratio", info.get("currentRatio")),
    ]
    body = "; ".join(f"{k}: {v}" for k, v in fields if v not in (None, "n/a"))
    if not body:
        return None
    return f"{ticker} — company profile & key figures. {body}."


def fetch_market(ticker: str) -> list[RawDocument]:
    try:
        import yfinance as yf
    except Exception as exc:
        logger.warning("yfinance unavailable: %s", exc)
        return []

    try:
        t = yf.Ticker(ticker)
    except Exception as exc:
        logger.warning("yfinance Ticker(%s) failed: %s", ticker, exc)
        return []

    parts: list[tuple[str, str | None]] = []
    try:
        parts.append(("profile", _profile_to_text(ticker, t.info or {})))
    except Exception as exc:
        logger.warning("yfinance info(%s) failed: %s", ticker, exc)
    for name, attr in [
        ("income statement (annual)", "income_stmt"),
        ("balance sheet (annual)", "balance_sheet"),
        ("cash flow (annual)", "cashflow"),
    ]:
        try:
            df = getattr(t, attr)
            parts.append((name, _statement_to_text(ticker, name, df)))
        except Exception as exc:
            logger.warning("yfinance %s(%s) failed: %s", attr, ticker, exc)

    url = _YF_URL.format(ticker=ticker)
    docs: list[RawDocument] = []
    for name, text in parts:
        if not text:
            continue
        md = SourceMetadata(
            ticker=ticker.upper(),
            doc_type=DocType.MARKET,
            title=f"{ticker.upper()} {name}",
            source_url=url,
        )
        docs.append(
            RawDocument(
                doc_id=RawDocument.make_doc_id(ticker, DocType.MARKET, name),
                metadata=md,
                content=text,
                content_type="text",
            )
        )
    logger.info("Market: fetched %d docs for %s", len(docs), ticker)
    return docs
