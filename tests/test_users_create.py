from tests.conftest import seed_user, auth


def test_owner_creates_user(client):
    owner = seed_user(client, role="owner")
    r = client.post(
        "/users",
        json={
            "username": "kolya",
            "password": "supersecret",
            "full_name": "Коля",
            "role": "admin",
        },
        headers=auth(owner["id"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "kolya"
    assert body["role"] == "admin"
    assert "password" not in body and "password_hash" not in body


def test_admin_cannot_create_user(client):
    owner = seed_user(client, role="owner")
    admin = seed_user(client, role="admin", name="Админ")
    r = client.post(
        "/users",
        json={"username": "x", "password": "12345678", "full_name": "X", "role": "maid"},
        headers=auth(admin["id"]),
    )
    assert r.status_code == 403


def test_username_conflict(client):
    owner = seed_user(client, role="owner")
    payload = {"username": "alice", "password": "12345678", "full_name": "A", "role": "maid"}
    r1 = client.post("/users", json=payload, headers=auth(owner["id"]))
    assert r1.status_code == 201
    r2 = client.post("/users", json=payload, headers=auth(owner["id"]))
    assert r2.status_code == 409


def test_password_too_short(client):
    owner = seed_user(client, role="owner")
    r = client.post(
        "/users",
        json={"username": "u", "password": "short", "full_name": "U", "role": "maid"},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 422
