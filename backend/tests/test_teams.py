import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.principal import Principal, require_role
from src.db.database import Database
from src.tenancy import repo, teams


@pytest.fixture
def db(settings) -> Database:
    return Database(None, settings.data_dir)


# --- RBAC helper ---
def test_require_role_hierarchy():
    owner = Principal(user_id="u", org_id="o", role="owner")
    viewer = Principal(user_id="v", org_id="o", role="viewer")
    require_role(owner, "admin")  # ok
    require_role(viewer, "viewer")  # ok
    with pytest.raises(HTTPException) as exc:
        require_role(viewer, "member")
    assert exc.value.status_code == 403


# --- invites + members ---
def test_invite_and_accept_flow(db):
    repo.ensure_org_user(db, "owner1", "owner@x.com", "Org1")
    org_id = _org_of(db, "owner1")

    inv = teams.create_invite(db, org_id, "new@x.com", "member", seat_limit=10)
    assert inv["token"].startswith("inv_")
    assert len(teams.pending_invites(db, org_id)) == 1

    # a different user accepts
    joined = teams.accept_invite(db, inv["token"], "user2", "new@x.com")
    assert joined == org_id
    members = teams.list_members(db, org_id)
    assert any(m["id"] == "user2" and m["role"] == "member" for m in members)
    assert teams.pending_invites(db, org_id) == []  # invite consumed


def test_seat_limit_enforced(db):
    org_id = _org_of_new(db, "owner1")
    teams.create_invite(db, org_id, "a@x.com", "member", seat_limit=2)  # owner=1 + invite=1 = 2
    with pytest.raises(teams.TeamError):
        teams.create_invite(db, org_id, "b@x.com", "member", seat_limit=2)


def test_role_change_and_remove(db):
    org_id = _org_of_new(db, "owner1")
    inv = teams.create_invite(db, org_id, "m@x.com", "member", seat_limit=10)
    teams.accept_invite(db, inv["token"], "u2", "m@x.com")
    teams.set_member_role(db, org_id, "u2", "admin")
    assert [m["role"] for m in teams.list_members(db, org_id) if m["id"] == "u2"] == ["admin"]
    teams.remove_member(db, org_id, "u2")
    assert all(m["id"] != "u2" for m in teams.list_members(db, org_id))


# --- API (demo principal is owner) ---
def test_members_api_and_invite():
    from src.auth.principal import DEMO_USER
    from src.db.database import get_db

    client = TestClient(app)
    members = client.get("/org/members")  # creates the demo org
    assert members.status_code == 200
    assert members.json()["seats_used"] >= 1

    # Free plan has 1 seat -> inviting is blocked (owner already fills it).
    assert client.post("/org/invites", json={"email": "a@x.com"}).status_code == 400

    # Upgrade the org to a multi-seat plan, then inviting succeeds.
    db = get_db()
    org = db.query_one("SELECT org_id FROM users WHERE id = ?", (DEMO_USER,))["org_id"]
    db.execute("UPDATE orgs SET plan = 'team' WHERE id = ?", (org,))
    created = client.post("/org/invites", json={"email": "teammate@x.com", "role": "member"})
    assert created.status_code == 200
    assert created.json()["token"].startswith("inv_")
    assert len(client.get("/org/invites").json()["invites"]) == 1


def _org_of(db, user_id):
    return db.query_one("SELECT org_id FROM users WHERE id = ?", (user_id,))["org_id"]


def _org_of_new(db, user_id):
    repo.ensure_org_user(db, user_id, None, "Org")
    return _org_of(db, user_id)
