"""Team management (Phase 20): invites, members, seat accounting.

Seat limits come from the org's plan (Phase 11). SSO/SAML/MFA are the remaining
enterprise-auth pieces and need an external identity provider; invites + RBAC are
implemented here and enforced at the API layer.
"""

from __future__ import annotations

import secrets

from src.db.database import Database
from src.tenancy.repo import _id, _now


class TeamError(Exception):
    pass


# --- members ---
def list_members(db: Database, org_id: str) -> list[dict]:
    return db.query(
        "SELECT id, email, role, created_at FROM users WHERE org_id = ? ORDER BY created_at",
        (org_id,),
    )


def member_count(db: Database, org_id: str) -> int:
    row = db.query_one("SELECT COUNT(*) AS n FROM users WHERE org_id = ?", (org_id,))
    return int(row["n"]) if row else 0


def set_member_role(db: Database, org_id: str, user_id: str, role: str) -> None:
    if role not in ("viewer", "member", "admin", "owner"):
        raise TeamError("Invalid role.")
    db.execute("UPDATE users SET role = ? WHERE id = ? AND org_id = ?", (role, user_id, org_id))


def remove_member(db: Database, org_id: str, user_id: str) -> None:
    db.execute("DELETE FROM users WHERE id = ? AND org_id = ?", (user_id, org_id))


# --- invites ---
def pending_invites(db: Database, org_id: str) -> list[dict]:
    return db.query(
        "SELECT id, email, role, status, created_at FROM invites "
        "WHERE org_id = ? AND status = 'pending' ORDER BY created_at DESC",
        (org_id,),
    )


def seat_usage(db: Database, org_id: str) -> int:
    """Members + pending invites count against the seat limit."""
    return member_count(db, org_id) + len(pending_invites(db, org_id))


def create_invite(db: Database, org_id: str, email: str, role: str, seat_limit: int) -> dict:
    if role not in ("viewer", "member", "admin"):
        raise TeamError("Invalid role.")
    if seat_usage(db, org_id) >= seat_limit:
        raise TeamError(f"Seat limit reached ({seat_limit}). Upgrade to add members.")
    token = "inv_" + secrets.token_urlsafe(24)
    iid = _id("inv")
    db.execute(
        "INSERT INTO invites (id, org_id, email, role, token, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
        (iid, org_id, email.lower(), role, token, _now()),
    )
    return {"id": iid, "email": email.lower(), "role": role, "token": token}


def revoke_invite(db: Database, org_id: str, invite_id: str) -> None:
    db.execute("DELETE FROM invites WHERE id = ? AND org_id = ?", (invite_id, org_id))


def accept_invite(db: Database, token: str, user_id: str, email: str | None) -> str:
    """Move the accepting user into the inviting org. Returns the org_id."""
    inv = db.query_one("SELECT * FROM invites WHERE token = ? AND status = 'pending'", (token,))
    if not inv:
        raise TeamError("Invalid or already-used invite.")
    org_id = inv["org_id"]
    existing = db.query_one("SELECT id FROM users WHERE id = ?", (user_id,))
    if existing:
        db.execute(
            "UPDATE users SET org_id = ?, role = ? WHERE id = ?", (org_id, inv["role"], user_id)
        )
    else:
        db.execute(
            "INSERT INTO users (id, email, org_id, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email or inv["email"], org_id, inv["role"], _now()),
        )
    db.execute("UPDATE invites SET status = 'accepted' WHERE id = ?", (inv["id"],))
    return org_id
