from tests.conftest import auth, seed_user


def test_missing_header_is_401(client):
    # No X-User-Id header → 401
    r = client.get("/apartments")
    assert r.status_code == 401


def test_invalid_user_id_is_401(client):
    r = client.get("/apartments", headers={"X-User-Id": "99999"})
    assert r.status_code == 401


def test_maid_cannot_access_apartments_list(client):
    u = seed_user(client, role="maid", name="Анна")
    r = client.get("/apartments", headers=auth(u["id"]))
    assert r.status_code == 403


def test_admin_can_access_apartments_list(client):
    u = seed_user(client, role="admin", name="Дарья")
    r = client.get("/apartments", headers=auth(u["id"]))
    assert r.status_code == 200


def test_maid_can_access_apartments_cleaning(client):
    # /apartments/cleaning allows maid role
    u = seed_user(client, role="maid", name="Анна")
    r = client.get("/apartments/cleaning", headers=auth(u["id"]))
    assert r.status_code == 200


def test_admin_cannot_access_users(client):
    # /users is owner-only
    u = seed_user(client, role="admin", name="Дарья")
    r = client.get("/users", headers=auth(u["id"]))
    assert r.status_code == 403


def test_owner_can_access_users(client):
    u = seed_user(client, role="owner", name="Айсен")
    r = client.get("/users", headers=auth(u["id"]))
    assert r.status_code == 200
