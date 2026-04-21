from tests.conftest import seed_user


def test_dev_auth_users_lists(client):
    seed_user(client, role="owner", name="Айсен")
    seed_user(client, role="maid", name="Анна")
    r = client.get("/dev_auth/users")
    assert r.status_code == 200
    data = r.json()
    assert {u["full_name"] for u in data} == {"Айсен", "Анна"}
    assert all("role" in u and "id" in u for u in data)


def test_dev_auth_login_ok(client):
    u = seed_user(client, role="admin", name="Дарья")
    r = client.post("/dev_auth/login", json={"user_id": u["id"]})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Дарья"
    assert r.json()["role"] == "admin"


def test_dev_auth_login_not_found(client):
    r = client.post("/dev_auth/login", json={"user_id": 9999})
    assert r.status_code == 404


def test_dev_auth_gated_by_debug(monkeypatch, tmp_db):
    monkeypatch.delenv("DEBUG", raising=False)
    import importlib

    import backend.main as main_mod

    importlib.reload(main_mod)
    from fastapi.testclient import TestClient

    with TestClient(main_mod.app) as c:
        r = c.get("/dev_auth/users")
        assert r.status_code == 404
