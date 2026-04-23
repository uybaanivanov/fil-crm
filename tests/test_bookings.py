from tests.conftest import auth, seed_user


def _prep(client):
    u = seed_user(client, role="owner", name="Айсен")
    a = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    c = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7 000"},
    ).json()
    return u, a, c


def test_get_booking_by_id(client):
    u, a, c = _prep(client)
    b = client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
        },
    ).json()
    r = client.get(f"/bookings/{b['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == b["id"]
    assert body["apartment_title"] == "A"
    assert body["client_name"] == "Смирнов"


def test_get_booking_404(client):
    u, _, _ = _prep(client)
    r = client.get("/bookings/9999", headers=auth(u["id"]))
    assert r.status_code == 404


def test_bookings_calendar_returns_groups(client):
    u, a, c = _prep(client)
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
        },
    )
    r = client.get(
        "/bookings/calendar?from=2026-04-21&to=2026-05-05",
        headers=auth(u["id"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    apt_entry = next(e for e in body if e["apartment_id"] == a["id"])
    assert apt_entry["apartment_address"] == "addr"
    assert len(apt_entry["bookings"]) == 1
    assert apt_entry["bookings"][0]["status"] == "active"


def test_create_booking_with_source(client):
    u, a, c = _prep(client)
    r = client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
            "source": "Авито",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["source"] == "Авито"


def test_get_booking_returns_source(client):
    u, a, c = _prep(client)
    b = client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
            "source": "Островок",
        },
    ).json()
    r = client.get(f"/bookings/{b['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    assert r.json()["source"] == "Островок"


def test_patch_booking_source(client):
    u, a, c = _prep(client)
    b = client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
        },
    ).json()
    r = client.patch(
        f"/bookings/{b['id']}",
        headers=auth(u["id"]),
        json={"source": "Суточно.ру"},
    )
    assert r.status_code == 200
    assert r.json()["source"] == "Суточно.ру"
