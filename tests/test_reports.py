from datetime import date, timedelta

from tests.conftest import auth, seed_user


def test_reports_month_empty(client):
    u = seed_user(client, role="owner")
    r = client.get("/reports?period=month", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {
        "period",
        "from",
        "to",
        "occupancy",
        "adr",
        "revpar",
        "avg_nights",
        "per_apartment",
    }
    assert body["period"] == "month"


def test_reports_month_with_data(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7"},
    ).json()
    today = date.today()
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": apt["id"],
            "client_id": cl["id"],
            "check_in": today.isoformat(),
            "check_out": (today + timedelta(days=3)).isoformat(),
            "total_price": 12000,
        },
    )
    r = client.get("/reports?period=month", headers=auth(u["id"]))
    body = r.json()
    assert body["adr"] > 0
    per = body["per_apartment"]
    assert per[0]["apartment_id"] == apt["id"]
    assert per[0]["util"] > 0
