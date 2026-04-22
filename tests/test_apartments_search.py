from tests.conftest import seed_user, auth


def _create(client, owner_id, **kw):
    body = {"title": "T", "address": "ул. Ленина, 1", "price_per_night": 1000, **kw}
    r = client.post("/apartments", json=body, headers=auth(owner_id))
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def test_search_by_callsign(client):
    owner = seed_user(client, role="owner")
    a = _create(client, owner["id"], title="Кв 1", callsign="alpha")
    b = _create(client, owner["id"], title="Кв 2", callsign="bravo")
    r = client.get("/apartments?q=alp", headers=auth(owner["id"]))
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert a in ids and b not in ids


def test_search_by_address(client):
    owner = seed_user(client, role="owner")
    a = _create(client, owner["id"], address="проспект Мира, 5")
    b = _create(client, owner["id"], address="ул. Кулаковского, 12")
    r = client.get("/apartments?q=кулак", headers=auth(owner["id"]))
    ids = [x["id"] for x in r.json()]
    assert b in ids and a not in ids


def test_next_booked_from(client):
    owner = seed_user(client, role="owner")
    apt_id = _create(client, owner["id"])
    cli = client.post("/clients", json={"full_name": "G", "phone": "+7..."},
                      headers=auth(owner["id"])).json()
    client.post("/bookings", json={
        "apartment_id": apt_id, "client_id": cli["id"],
        "check_in": "2026-05-10", "check_out": "2026-05-12",
        "total_price": 5000,
    }, headers=auth(owner["id"]))
    r = client.get(
        "/apartments?check_in=2026-05-09&check_out=2026-05-15",
        headers=auth(owner["id"]),
    )
    apt = next(x for x in r.json() if x["id"] == apt_id)
    assert apt["next_booked_from"] == "2026-05-10"


def test_no_dates_no_next_booked(client):
    owner = seed_user(client, role="owner")
    _create(client, owner["id"])
    r = client.get("/apartments", headers=auth(owner["id"]))
    assert all(x["next_booked_from"] is None for x in r.json())
