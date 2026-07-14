"""Notification API (Phase 41) — the weekly digest.

`/notify/digest/preview` renders the HTML without sending, so you can eyeball it.
`/notify/digest/send` actually sends, and is protected by a shared token so the
weekly cron can call it but the public internet cannot.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from starlette.responses import HTMLResponse

from src.auth.principal import Principal, get_principal
from src.config.settings import get_settings
from src.db.database import get_db
from src.notify import digest as digest_svc
from src.notify.email import is_configured
from src.providers.router import ProviderRouter
from src.retrieval.retriever import get_retriever
from src.tenancy import saas

router = APIRouter(prefix="/notify", tags=["notify"])


class DigestRequest(BaseModel):
    to: EmailStr
    tickers: list[str] = Field(default_factory=list, max_length=8)


@router.get("/digest/preview", response_class=HTMLResponse)
def preview(
    tickers: str = "AAPL,MSFT",
    principal: Principal = Depends(get_principal),
) -> HTMLResponse:
    """Render the digest you *would* receive — no email sent."""
    settings = get_settings()
    syms = [t.strip().upper() for t in tickers.split(",") if t.strip()][:8]
    blocks = [
        digest_svc.build_ticker_block(get_retriever(), ProviderRouter(settings), t) for t in syms
    ]
    return HTMLResponse(digest_svc.render_html(blocks, settings.frontend_origin or ""))


@router.post("/digest/send")
def send(body: DigestRequest, principal: Principal = Depends(get_principal)) -> dict:
    """Send a digest to one address. Falls back to the caller's watchlist."""
    settings = get_settings()
    if not is_configured(settings):
        raise HTTPException(
            status_code=400,
            detail="Email is not configured — set RESEND_API_KEY on the backend.",
        )

    tickers = body.tickers or [
        w["ticker"] for w in saas.list_watchlists(get_db(), principal.org_id)
    ]
    sent = digest_svc.send_digest(
        get_retriever(),
        ProviderRouter(settings),
        str(body.to),
        tickers,
        app_url=settings.frontend_origin or "https://fin-copilot-six.vercel.app",
    )
    return {"sent": sent, "to": str(body.to), "tickers": tickers}
