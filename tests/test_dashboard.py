from tests.conftest import auth, seed_user


def test_dashboard_summary_shape(client):
    u = seed_user(client, role="owner")
    r = client.get("/dashboard/summary", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    # Shape: occupancy, revenue_mtd, revenue_prev_month, daily_series, today_events
    assert "occupancy" in body
    assert set(body["occupancy"]) == {"occupied", "total"}
    assert "revenue_mtd" in body
    assert "revenue_prev_month" in body
    assert isinstance(body["daily_series"], list)
    assert isinstance(body["today_events"], list)


def test_dashboard_summary_with_data(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7 000"},
    ).json()
    from datetime import date, timedelta

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=3)).isoformat()
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": apt["id"],
            "client_id": cl["id"],
            "check_in": today,
            "check_out": tomorrow,
            "total_price": 12000,
        },
    )
    r = client.get("/dashboard/summary", headers=auth(u["id"]))
    body = r.json()
    assert body["occupancy"]["total"] == 1
    assert body["occupancy"]["occupied"] == 1
    # Today has a check-in
    assert any(e["kind"] == "check_in" for e in body["today_events"])
