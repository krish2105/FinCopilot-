"""Weekly watchlist digest (Phase 41).

Composes, per watched company: the current price move, any red flags found in its
filings, and what changed in its risk disclosures. That last one is the hook — it's
information the reader cannot get anywhere else, which is exactly why they'd open
the email.

The HTML is inlined (no external CSS/images) so it renders in every mail client.
"""

from __future__ import annotations

import logging
from typing import Any

from src.insights import service as insights
from src.market import quotes
from src.notify.email import send_email
from src.providers.router import ProviderRouter
from src.retrieval.retriever import Retriever

logger = logging.getLogger(__name__)

_ACCENT = "#10b981"
_MUTED = "#6b7280"


def build_ticker_block(retriever: Retriever, router: ProviderRouter, ticker: str) -> dict[str, Any]:
    """Everything worth saying about one company this week."""
    quote = quotes.get_quote(ticker) or {}
    try:
        flags = insights.red_flags(retriever, ticker).flags
    except Exception as exc:  # noqa: BLE001
        logger.warning("digest red_flags(%s) failed: %s", ticker, exc)
        flags = []
    try:
        diff = insights.risk_diff(retriever, router, ticker)
        changes = diff.changes if diff.available else []
    except Exception as exc:  # noqa: BLE001
        logger.warning("digest risk_diff(%s) failed: %s", ticker, exc)
        changes = []

    return {
        "ticker": ticker.upper(),
        "name": quote.get("name", ticker.upper()),
        "price": quote.get("price"),
        "change_pct": quote.get("change_pct"),
        "flags": flags[:3],
        "changes": changes[:3],
    }


def render_html(blocks: list[dict[str, Any]], app_url: str) -> str:
    rows: list[str] = []
    for b in blocks:
        pct = b.get("change_pct")
        colour = _MUTED if pct is None else (_ACCENT if pct >= 0 else "#ef4444")
        move = "—" if pct is None else f"{'+' if pct >= 0 else ''}{pct:.2f}%"
        price = "—" if b.get("price") is None else f"${b['price']:,.2f}"

        bullets = "".join(
            f'<li style="margin:4px 0;color:#374151;">'
            f'<strong style="color:#b45309;">{c.change.upper()}</strong> — {c.topic}: {c.detail}'
            f"</li>"
            for c in b["changes"]
        )
        flag_items = "".join(
            f'<li style="margin:4px 0;color:#374151;">'
            f'<strong style="color:#dc2626;">{f.category.replace("_", " ").title()}</strong> — {f.detail}'
            f"</li>"
            for f in b["flags"]
        )

        body = ""
        if bullets:
            body += f'<p style="margin:10px 0 4px;font-weight:600;color:#111827;">Risk disclosures changed</p><ul style="margin:0;padding-left:18px;">{bullets}</ul>'
        if flag_items:
            body += f'<p style="margin:10px 0 4px;font-weight:600;color:#111827;">Red flags</p><ul style="margin:0;padding-left:18px;">{flag_items}</ul>'
        if not body:
            body = '<p style="margin:8px 0;color:#6b7280;">No new disclosure changes or red flags this week.</p>'

        rows.append(
            f"""
            <tr><td style="padding:18px 0;border-bottom:1px solid #e5e7eb;">
              <table width="100%"><tr>
                <td><span style="font:600 15px system-ui;color:#111827;">{b['name']}</span>
                    <span style="font:12px ui-monospace;color:#6b7280;"> {b['ticker']}</span></td>
                <td align="right"><span style="font:600 15px ui-monospace;color:#111827;">{price}</span>
                    <span style="font:600 13px ui-monospace;color:{colour};"> {move}</span></td>
              </tr></table>
              {body}
            </td></tr>"""
        )

    return f"""<!doctype html><html><body style="margin:0;background:#f9fafb;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f9fafb;padding:28px 12px;">
<tr><td align="center">
  <table width="600" cellpadding="0" cellspacing="0" style="background:#fff;border:1px solid #e5e7eb;border-radius:14px;padding:28px;font-family:system-ui,-apple-system,sans-serif;">
    <tr><td>
      <p style="margin:0;font:700 20px system-ui;color:#111827;">Your week in filings</p>
      <p style="margin:6px 0 0;font:14px system-ui;color:{_MUTED};">
        What changed in the companies you watch — pulled from their real SEC filings, every claim cited.
      </p>
    </td></tr>
    {''.join(rows)}
    <tr><td style="padding-top:22px;">
      <a href="{app_url}/insights" style="display:inline-block;background:{_ACCENT};color:#fff;text-decoration:none;font:600 14px system-ui;padding:11px 18px;border-radius:9px;">
        Open FinCopilot →</a>
      <p style="margin:18px 0 0;font:11px system-ui;color:#9ca3af;">
        AI-generated. Informational research only — not investment advice.
      </p>
    </td></tr>
  </table>
</td></tr></table></body></html>"""


def send_digest(
    retriever: Retriever,
    router: ProviderRouter,
    to: str,
    tickers: list[str],
    app_url: str = "https://fin-copilot-six.vercel.app",
) -> bool:
    """Build and send one subscriber's weekly digest."""
    if not tickers:
        logger.info("digest skipped for %s: empty watchlist", to)
        return False

    blocks = [build_ticker_block(retriever, router, t) for t in tickers[:8]]
    notable = sum(len(b["changes"]) + len(b["flags"]) for b in blocks)
    subject = (
        f"FinCopilot — {notable} notable change{'s' if notable != 1 else ''} in your watchlist"
        if notable
        else "FinCopilot — your weekly watchlist digest"
    )
    return send_email(to, subject, render_html(blocks, app_url))
