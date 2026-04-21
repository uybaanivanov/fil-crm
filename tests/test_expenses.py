from tests.conftest import auth, seed_user


def _owner(client):
    return seed_user(client, role="owner", name="O")


def test_create_expense(client):
    u = _owner(client)
    r = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={
            "amount": 4200,
            "category": "Уборка",
            "description": "Лермонтова 58",
            "occurred_at": "2026-04-20",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["amount"] == 4200
    assert body["category"] == "Уборка"


def test_list_expenses_filter_by_month(client):
    u = _owner(client)
    for ym, amt in [("2026-03-10", 1000), ("2026-04-15", 2000), ("2026-04-20", 500)]:
        client.post(
            "/expenses",
            headers=auth(u["id"]),
            json={"amount": amt, "category": "X", "occurred_at": ym},
        )
    r = client.get("/expenses?month=2026-04", headers=auth(u["id"]))
    assert r.status_code == 200
    data = r.json()
    assert sum(e["amount"] for e in data) == 2500
    assert len(data) == 2


def test_patch_expense(client):
    u = _owner(client)
    e = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 100, "category": "X", "occurred_at": "2026-04-01"},
    ).json()
    r = client.patch(
        f"/expenses/{e['id']}",
        headers=auth(u["id"]),
        json={"amount": 150},
    )
    assert r.status_code == 200
    assert r.json()["amount"] == 150


def test_delete_expense(client):
    u = _owner(client)
    e = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 100, "category": "X", "occurred_at": "2026-04-01"},
    ).json()
    r = client.delete(f"/expenses/{e['id']}", headers=auth(u["id"]))
    assert r.status_code == 204
    r = client.get("/expenses", headers=auth(u["id"]))
    assert r.json() == []
