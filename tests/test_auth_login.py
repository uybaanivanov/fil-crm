from tests.conftest import seed_user, auth


def test_login_ok(client):
    owner = seed_user(client, role="owner")
    # создаём юзера через POST /users чтобы получить хеш
    r = client.post(
        "/users",
        json={"username": "petya", "password": "supersecret", "full_name": "Петя", "role": "admin"},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 201

    r = client.post("/auth/login", json={"username": "petya", "password": "supersecret"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["username"] == "petya"
    assert body["role"] == "admin"
    assert "password_hash" not in body and "password" not in body


def test_login_wrong_password(client):
    owner = seed_user(client, role="owner")
    client.post(
        "/users",
        json={"username": "kolya", "password": "rightpass1", "full_name": "Коля", "role": "admin"},
        headers=auth(owner["id"]),
    )
    r = client.post("/auth/login", json={"username": "kolya", "password": "wrongpass"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/auth/login", json={"username": "nobody", "password": "x"})
    assert r.status_code == 401


def test_login_user_without_password_hash(client):
    """Юзеры созданные через dev_auth (или старые) не имеют password_hash → 401."""
    owner = seed_user(client, role="owner")
    r = client.post("/auth/login", json={"username": "anyone", "password": "x"})
    assert r.status_code == 401
