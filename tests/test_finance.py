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
