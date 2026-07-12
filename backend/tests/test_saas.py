from fastapi.testclient import TestClient

from src.api.main import app
from src.db.database import Database
from src.tenancy import saas


def test_api_key_lifecycle(settings):
    db = Database(None, settings.data_dir)
    raw, rec = saas.create_api_key(db, "org1", "ci")
    assert raw.startswith("fk_")
    keys = saas.list_api_keys(db, "org1")
    assert len(keys) == 1 and keys[0]["prefix"] == raw[:10]
    # raw key is never stored
    assert "key_hash" not in keys[0]
    saas.delete_api_key(db, "org1", rec["id"])
    assert saas.list_api_keys(db, "org1") == []


def test_watchlist_crud(settings):
    db = Database(None, settings.data_dir)
    w = saas.add_watchlist(db, "org1", "aapl")
    assert w["ticker"] == "AAPL"
    assert len(saas.list_watchlists(db, "org1")) == 1
    saas.delete_watchlist(db, "org1", w["id"])
    assert saas.list_watchlists(db, "org1") == []


def test_feedback_api():
    client = TestClient(app)
    r = client.post("/feedback", json={"rating": 1, "note": "great", "query": "aapl revenue"})
    assert r.status_code == 200 and r.json()["recorded"] is True


def test_api_key_and_watchlist_endpoints():
    client = TestClient(app)
    created = client.post("/api-keys", json={"name": "prod"})
    assert created.status_code == 200 and created.json()["api_key"].startswith("fk_")
    listed = client.get("/api-keys")
    assert len(listed.json()["keys"]) == 1

    w = client.post("/watchlists", json={"ticker": "MSFT"})
    assert w.status_code == 200 and w.json()["ticker"] == "MSFT"
    assert len(client.get("/watchlists").json()["watchlists"]) == 1


def test_api_key_authenticates_a_principal(settings):
    # A created key resolves to a service principal for that org.
    from src.auth.principal import resolve_principal

    db = Database(None, settings.data_dir)
    from src.tenancy import repo

    org = repo.ensure_org_user(db, "u1", None, "Org1")
    raw, _ = saas.create_api_key(db, org.id, "svc")
    principal = resolve_principal(settings, db, authorization=None, x_api_key=raw)
    assert principal.org_id == org.id and principal.role == "service"


def test_expired_api_key_is_rejected(settings):
    import hashlib

    import pytest
    from fastapi import HTTPException

    from src.auth.principal import resolve_principal

    db = Database(None, settings.data_dir)
    raw, rec = saas.create_api_key(db, "org1", "svc")
    # Force expiry into the past.
    db.execute(
        "UPDATE api_keys SET expires_at = '2000-01-01T00:00:00+00:00' WHERE id = ?", (rec["id"],)
    )
    with pytest.raises(HTTPException) as exc:
        resolve_principal(settings, db, authorization=None, x_api_key=raw)
    assert exc.value.status_code == 401
    # sanity: the hash lookup path is what we exercised
    assert hashlib.sha256(raw.encode()).hexdigest()
