"""Team management API (Phase 20): members, roles, invites — with RBAC."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field

from src.auth.principal import Principal, get_principal, require_role
from src.billing.plans import get_plan
from src.db.database import get_db
from src.tenancy import repo, teams

router = APIRouter(tags=["team"])


@router.get("/org/members")
def list_members(principal: Principal = Depends(get_principal)) -> dict:
    db = get_db()
    org = repo.get_org(db, principal.org_id)
    return {
        "members": teams.list_members(db, principal.org_id),
        "seats_used": teams.seat_usage(db, principal.org_id),
        "seats_limit": get_plan(org.plan if org else "free").max_seats,
    }


class RoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(viewer|member|admin|owner)$")


@router.patch("/org/members/{user_id}")
def update_member(
    user_id: str, body: RoleUpdate, principal: Principal = Depends(get_principal)
) -> dict:
    require_role(principal, "admin")
    if user_id == principal.user_id:
        raise HTTPException(status_code=400, detail="You can't change your own role.")
    teams.set_member_role(get_db(), principal.org_id, user_id, body.role)
    return {"updated": user_id, "role": body.role}


@router.delete("/org/members/{user_id}")
def remove_member(user_id: str, principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "admin")
    if user_id == principal.user_id:
        raise HTTPException(status_code=400, detail="You can't remove yourself.")
    teams.remove_member(get_db(), principal.org_id, user_id)
    return {"removed": user_id}


# --- invites ---
class CreateInvite(BaseModel):
    email: EmailStr
    role: str = Field("member", pattern="^(viewer|member|admin)$")


@router.get("/org/invites")
def list_invites(principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "admin")
    return {"invites": teams.pending_invites(get_db(), principal.org_id)}


@router.post("/org/invites")
def create_invite(body: CreateInvite, principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "admin")
    db = get_db()
    org = repo.get_org(db, principal.org_id)
    limit = get_plan(org.plan if org else "free").max_seats
    try:
        inv = teams.create_invite(db, principal.org_id, str(body.email), body.role, limit)
    except teams.TeamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {**inv, "note": "Share this invite token with the invitee."}


@router.delete("/org/invites/{invite_id}")
def revoke_invite(invite_id: str, principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "admin")
    teams.revoke_invite(get_db(), principal.org_id, invite_id)
    return {"revoked": invite_id}


class AcceptInvite(BaseModel):
    token: str


@router.post("/org/invites/accept")
def accept_invite(body: AcceptInvite, principal: Principal = Depends(get_principal)) -> dict:
    try:
        org_id = teams.accept_invite(get_db(), body.token, principal.user_id, principal.email)
    except teams.TeamError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"joined_org": org_id}
