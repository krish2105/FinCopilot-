"""Request authentication → a tenant Principal.

Resolves the caller from a Supabase-issued JWT (verified with SUPABASE_JWT_SECRET)
or an API key. When auth isn't configured and AUTH_REQUIRED is false, requests get
a shared **demo tenant** so the app stays usable offline and in CI — mirroring the
frontend's demo mode. Set AUTH_REQUIRED=true in production to reject anonymous
requests.
"""

from __future__ import annotations

import hashlib
import logging

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from src.config.settings import Settings, get_settings
from src.db.database import Database, get_db
from src.tenancy import repo

logger = logging.getLogger(__name__)

DEMO_USER = "demo-user"
DEMO_EMAIL = "demo@fincopilot.local"


class Principal(BaseModel):
    user_id: str
    email: str | None = None
    org_id: str
    role: str = "member"
    is_demo: bool = False


def _verify_jwt(token: str, secret: str) -> dict | None:
    try:
        import jwt

        return jwt.decode(token, secret, algorithms=["HS256"], audience="authenticated")
    except Exception as exc:  # invalid/expired token
        logger.info("JWT verification failed: %s", exc)
        return None


def _api_key_principal(db: Database, api_key: str) -> Principal | None:
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    row = db.query_one("SELECT * FROM api_keys WHERE key_hash = ?", (key_hash,))
    if not row:
        return None
    if row.get("expires_at") and row["expires_at"] < _now():
        return None  # expired key
    db.execute("UPDATE api_keys SET last_used = ? WHERE id = ?", (_now(), row["id"]))
    org = repo.get_org(db, row["org_id"])
    if not org:
        return None
    return Principal(user_id=f"apikey:{row['id']}", org_id=org.id, role="service")


def _now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def resolve_principal(
    settings: Settings,
    db: Database,
    authorization: str | None,
    x_api_key: str | None,
) -> Principal:
    # 1) API key
    if x_api_key:
        p = _api_key_principal(db, x_api_key)
        if p:
            return p
        raise HTTPException(status_code=401, detail="Invalid API key")

    # 2) Supabase JWT
    if (
        authorization
        and authorization.lower().startswith("bearer ")
        and settings.supabase_jwt_secret
    ):
        claims = _verify_jwt(authorization.split(" ", 1)[1], settings.supabase_jwt_secret)
        if claims and claims.get("sub"):
            org = repo.ensure_org_user(
                db, claims["sub"], claims.get("email"), claims.get("email") or "Workspace"
            )
            return Principal(
                user_id=claims["sub"], email=claims.get("email"), org_id=org.id, role="owner"
            )
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # 3) Demo tenant (only when auth isn't required)
    if settings.auth_required:
        raise HTTPException(status_code=401, detail="Authentication required")
    repo.ensure_org_user(db, DEMO_USER, DEMO_EMAIL, "Demo Org")
    org = repo.get_org(db, _demo_org_id(db))
    return Principal(user_id=DEMO_USER, email=DEMO_EMAIL, org_id=org.id, role="owner", is_demo=True)


def _demo_org_id(db: Database) -> str:
    row = db.query_one("SELECT org_id FROM users WHERE id = ?", (DEMO_USER,))
    return row["org_id"]


def get_principal(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> Principal:
    return resolve_principal(settings, get_db(settings), authorization, x_api_key)
