"""Billing + usage API (Phase 11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.auth.principal import Principal, get_principal
from src.billing import service
from src.billing.plans import PLANS
from src.billing.quota import usage_summary
from src.config.settings import Settings, get_settings
from src.db.database import get_db
from src.tenancy import repo

router = APIRouter(tags=["billing"])


@router.get("/billing/plans")
def list_plans() -> dict:
    return {
        "plans": [p.model_dump() for p in PLANS.values()],
        "configured": service.is_configured(get_settings()),
    }


@router.get("/usage")
def usage(principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    org = repo.get_org(db, principal.org_id)
    return usage_summary(db, principal.org_id, org.plan if org else "free")


class CheckoutRequest(BaseModel):
    plan_id: str
    success_url: str
    cancel_url: str


@router.post("/billing/checkout")
def checkout(
    body: CheckoutRequest,
    principal: Principal = Depends(get_principal),
    settings: Settings = Depends(get_settings),
) -> dict:
    url = service.create_checkout_session(
        settings, principal.org_id, body.plan_id, body.success_url, body.cancel_url
    )
    return {"url": url}


class PortalRequest(BaseModel):
    return_url: str


@router.post("/billing/portal")
def portal(
    body: PortalRequest,
    principal: Principal = Depends(get_principal),
    settings: Settings = Depends(get_settings),
) -> dict:
    url = service.create_portal_session(settings, get_db(), principal.org_id, body.return_url)
    return {"url": url}


@router.post("/billing/webhook")
async def webhook(request: Request, settings: Settings = Depends(get_settings)) -> dict:
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    return service.handle_webhook(settings, get_db(), payload, sig)
