from tests.conftest import auth, seed_user


def test_finance_summary_combines_revenue_and_expenses(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "X", "phone": "+7"},
    ).json()
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": apt["id"],
            "client_id": cl["id"],
            "check_in": "2026-04-10",
            "check_out": "2026-04-13",
            "total_price": 12000,
        },
    )
    client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 4200, "category": "Уборка", "occurred_at": "2026-04-15"},
    )
    client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 3000, "category": "ЖКХ", "occurred_at": "2026-04-18"},
    )
    r = client.get("/finance/summary?month=2026-04", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["revenue"] == 12000
    assert body["expenses_total"] == 7200
    assert body["net"] == 4800
    assert body["by_category"] == {"Уборка": 4200, "ЖКХ": 3000}
    assert len(body["feed"]) == 3
    # feed отсортирован по дате убывающе
    dates = [f["dt"] for f in body["feed"]]
    assert dates == sorted(dates, reverse=True)


def test_summary_includes_by_apartment(client):
    u = seed_user(client, role="owner")
    a1 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A1", "address": "x", "price_per_night": 1000}).json()
    a2 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A2", "address": "x", "price_per_night": 1000}).json()
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 5000, "category": "rent", "occurred_at": "2026-04-01",
        "apartment_id": a1["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 9999, "category": "общий", "occurred_at": "2026-04-02"})
    r = client.get("/finance/summary?month=2026-04", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert "by_apartment" in body
    assert "general_expenses_total" in body
    assert body["general_expenses_total"] == 9999
    rows = {x["apartment_id"]: x for x in body["by_apartment"]}
    assert a1["id"] in rows
    assert rows[a1["id"]]["expenses_total"] == 5000
    assert rows[a1["id"]]["title"] == "A1"
    for item in body["feed"]:
        if item["type"] == "expense":
            assert "apartment_id" in item
            assert "apartment_title" in item
