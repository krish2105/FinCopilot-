"""Filing-alert poller (Phase 14).

Checks each watchlisted ticker's latest EDGAR filing against the last one we saw;
new filings are returned (and the watermark advanced). Intended to run on a cron
(e.g. GitHub Actions schedule or Render cron) and fan out notifications.

    python -m src.alerts.poller
"""

from __future__ import annotations

import logging

import httpx

from src.config.settings import get_settings
from src.db.database import get_db
from src.ingestion.fetchers.edgar import ticker_to_cik
from src.tenancy import saas

logger = logging.getLogger(__name__)

_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def poll_watchlists() -> list[dict]:
    settings = get_settings()
    db = get_db()
    rows = db.query("SELECT id, org_id, ticker, last_accession FROM watchlists", ())
    new_filings: list[dict] = []
    with httpx.Client(headers={"User-Agent": settings.edgar_user_agent}, timeout=30.0) as client:
        for wl in rows:
            try:
                cik = ticker_to_cik(wl["ticker"], client)
                if cik is None:
                    continue
                sub = client.get(_SUBMISSIONS.format(cik=cik))
                sub.raise_for_status()
                recent = sub.json()["filings"]["recent"]
                if not recent["accessionNumber"]:
                    continue
                latest = recent["accessionNumber"][0]
                form = recent["form"][0]
                date = recent["filingDate"][0]
                if latest != wl["last_accession"]:
                    saas.set_watchlist_accession(db, wl["id"], latest)
                    if wl["last_accession"]:  # skip first-seen (baseline)
                        new_filings.append(
                            {
                                "org_id": wl["org_id"],
                                "ticker": wl["ticker"],
                                "form": form,
                                "accession": latest,
                                "date": date,
                            }
                        )
            except Exception as exc:
                logger.warning("poll failed for %s: %s", wl["ticker"], exc)
    logger.info("poll complete: %d new filings", len(new_filings))
    return new_filings


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    for f in poll_watchlists():
        print(f"NEW: {f['ticker']} {f['form']} {f['date']} ({f['accession']})")
