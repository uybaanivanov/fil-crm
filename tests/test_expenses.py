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


def test_create_expense_with_apartment_id(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={
            "amount": 1500, "category": "internet",
            "occurred_at": "2026-04-10", "apartment_id": apt["id"],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["apartment_id"] == apt["id"]
    assert body["source"] == "manual"


def test_create_expense_with_invalid_apartment_id(client):
    u = seed_user(client, role="owner")
    r = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={
            "amount": 1500, "category": "x",
            "occurred_at": "2026-04-10", "apartment_id": 99999,
        },
    )
    assert r.status_code == 400


def test_list_expenses_filter_by_apartment(client):
    u = seed_user(client, role="owner")
    a1 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A1", "address": "x", "price_per_night": 1000}).json()
    a2 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A2", "address": "x", "price_per_night": 1000}).json()
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 100, "category": "x", "occurred_at": "2026-04-01", "apartment_id": a1["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 200, "category": "x", "occurred_at": "2026-04-02", "apartment_id": a2["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 300, "category": "x", "occurred_at": "2026-04-03"})
    r = client.get(f"/expenses?apartment_id={a1['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["amount"] == 100


def test_list_expenses_only_general(client):
    u = seed_user(client, role="owner")
    a = client.post("/apartments", headers=auth(u["id"]),
                    json={"title": "A", "address": "x", "price_per_night": 1000}).json()
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 100, "category": "x", "occurred_at": "2026-04-01", "apartment_id": a["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 200, "category": "x", "occurred_at": "2026-04-02"})
    r = client.get("/expenses?only_general=true", headers=auth(u["id"]))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["amount"] == 200


def test_list_expenses_mutually_exclusive_filters(client):
    u = seed_user(client, role="owner")
    r = client.get("/expenses?apartment_id=1&only_general=true", headers=auth(u["id"]))
    assert r.status_code == 400
