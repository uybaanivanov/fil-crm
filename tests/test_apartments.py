from tests.conftest import auth, seed_user


def _owner(client):
    return seed_user(client, role="owner", name="Айсен")


def test_create_apartment_with_new_fields(client):
    u = _owner(client)
    r = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "Лермонтова 58/24",
            "address": "ул. Лермонтова, 58, кв. 24",
            "price_per_night": 4280,
            "rooms": "2-комн",
            "area_m2": 52,
            "floor": "3/5",
            "district": "Сайсары",
            "cover_url": "https://example.com/cover.jpg",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["rooms"] == "2-комн"
    assert body["area_m2"] == 52
    assert body["floor"] == "3/5"
    assert body["district"] == "Сайсары"
    assert body["cover_url"] == "https://example.com/cover.jpg"


def test_patch_apartment_updates_new_fields(client):
    u = _owner(client)
    created = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "A",
            "address": "addr",
            "price_per_night": 1000,
            "monthly_rent": 40000,
            "monthly_utilities": 5000,
        },
    ).json()
    r = client.patch(
        f"/apartments/{created['id']}",
        headers=auth(u["id"]),
        json={"rooms": "Студия", "area_m2": 28, "district": "центр"},
    )
    assert r.status_code == 200
    assert r.json()["rooms"] == "Студия"
    assert r.json()["area_m2"] == 28
    assert r.json()["district"] == "центр"


def test_get_apartment_returns_baseline_fields(client):
    u = seed_user(client, role="owner")
    r = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    )
    apt = r.json()
    assert "monthly_rent" in apt
    assert "monthly_utilities" in apt
    assert apt["monthly_rent"] is None
    assert apt["monthly_utilities"] is None


def test_create_apartment_with_baseline(client):
    u = seed_user(client, role="owner")
    r = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "A", "address": "X", "price_per_night": 1000,
            "monthly_rent": 50000, "monthly_utilities": 7000,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["monthly_rent"] == 50000
    assert body["monthly_utilities"] == 7000


def test_patch_apartment_fails_without_baseline(client):
    """У существующей квартиры без baseline любой PATCH падает 400."""
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"price_per_night": 1500},
    )
    assert r.status_code == 400
    assert "monthly_rent" in r.json()["detail"]


def test_patch_apartment_ok_with_baseline_in_payload(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"monthly_rent": 50000, "monthly_utilities": 7000},
    )
    assert r.status_code == 200
    assert r.json()["monthly_rent"] == 50000


def test_patch_apartment_ok_when_baseline_already_in_db(client):
    """Если baseline уже в БД, можно патчить другое поле без него."""
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "A", "address": "X", "price_per_night": 1000,
            "monthly_rent": 40000, "monthly_utilities": 5000,
        },
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"price_per_night": 1500},
    )
    assert r.status_code == 200


def test_patch_apartment_ok_with_only_rent_no_utilities(client):
    """PATCH с только monthly_rent без utilities теперь валиден (ЖКХ опционально)."""
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"monthly_rent": 50000},
    )
    assert r.status_code == 200
    assert r.json()["monthly_rent"] == 50000
    assert r.json()["monthly_utilities"] is None


def test_get_apartment_by_id(client):
    u = _owner(client)
    created = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 1000},
    ).json()
    r = client.get(f"/apartments/{created['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_apartment_by_id_404(client):
    u = _owner(client)
    r = client.get("/apartments/9999", headers=auth(u["id"]))
    assert r.status_code == 404


def _apt_with_price(client, u_id: int, price: int) -> dict:
    return client.post(
        "/apartments",
        headers=auth(u_id),
        json={"title": "A", "address": "addr", "price_per_night": price},
    ).json()


def _client_and_booking(client, u_id: int, apt_id: int, ci: str, co: str, total: int, status_: str = "active"):
    cl = client.post(
        "/clients",
        headers=auth(u_id),
        json={"full_name": "Гость", "phone": "+7 000"},
    ).json()
    b = client.post(
        "/bookings",
        headers=auth(u_id),
        json={
            "apartment_id": apt_id,
            "client_id": cl["id"],
            "check_in": ci,
            "check_out": co,
            "total_price": total,
        },
    ).json()
    if status_ != "active":
        client.patch(f"/bookings/{b['id']}", headers=auth(u_id), json={"status": status_})
    return b


def test_apartment_stats_empty_month(client):
    u = _owner(client)
    apt = _apt_with_price(client, u["id"], 4000)
    r = client.get(
        f"/apartments/{apt['id']}/stats?month=2026-04", headers=auth(u["id"])
    )
    assert r.status_code == 200
    body = r.json()
    assert body["nights"] == 0
    assert body["revenue"] == 0
    assert body["adr"] == 0
    assert body["utilization"] == 0.0


def test_apartment_stats_one_booking(client):
    u = _owner(client)
    apt = _apt_with_price(client, u["id"], 4000)
    _client_and_booking(client, u["id"], apt["id"], "2026-04-10", "2026-04-13", 12000)
    r = client.get(
        f"/apartments/{apt['id']}/stats?month=2026-04", headers=auth(u["id"])
    )
    body = r.json()
    assert body["nights"] == 3
    assert body["revenue"] == 12000
    assert body["adr"] == 4000
    # 3 / 30 = 0.1
    assert abs(body["utilization"] - 0.1) < 1e-6


def test_apartment_source_url_unique(client):
    u = seed_user(client, role="owner", name="Айсен")
    h = auth(u["id"])
    payload = {
        "title": "Т1", "address": "А1", "price_per_night": 1000,
        "source": "doska_ykt",
        "source_url": "https://doska.ykt.ru/12345",
    }
    r1 = client.post("/apartments", json=payload, headers=h)
    assert r1.status_code == 201
    assert r1.json()["source"] == "doska_ykt"
    assert r1.json()["source_url"] == "https://doska.ykt.ru/12345"
    r2 = client.post("/apartments", json=payload, headers=h)
    assert r2.status_code == 409


def test_apartment_without_source_url_ok(client):
    u = seed_user(client, role="owner", name="Айсен")
    h = auth(u["id"])
    r1 = client.post("/apartments", json={"title": "X", "address": "Y", "price_per_night": 100}, headers=h)
    r2 = client.post("/apartments", json={"title": "X2", "address": "Y2", "price_per_night": 200}, headers=h)
    assert r1.status_code == 201 and r2.status_code == 201


def test_parse_url_returns_listing(client, monkeypatch):
    from backend.parsers.types import ParsedListing
    import backend.routes.apartments as apts_mod

    async def fake_fetch(url):
        return ParsedListing(
            source="doska_ykt", source_url=url,
            title="Flat", address="Addr", price_per_night=3000,
        )
    monkeypatch.setattr(apts_mod, "_fetch_listing", fake_fetch)

    u = seed_user(client, role="owner", name="Айсен")
    r = client.post(
        "/apartments/parse-url",
        json={"url": "https://doska.ykt.ru/1"},
        headers=auth(u["id"]),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Flat"
    assert data["source"] == "doska_ykt"


def test_parse_url_unsupported_is_422(client):
    u = seed_user(client, role="owner", name="Айсен")
    r = client.post(
        "/apartments/parse-url",
        json={"url": "https://example.com/1"},
        headers=auth(u["id"]),
    )
    assert r.status_code == 422


def test_list_with_stats_includes_utilization_and_status(client):
    u = _owner(client)
    apt = _apt_with_price(client, u["id"], 4000)
    _client_and_booking(client, u["id"], apt["id"], "2026-04-10", "2026-04-13", 12000)
    r = client.get(
        "/apartments?with_stats=1&month=2026-04", headers=auth(u["id"])
    )
    assert r.status_code == 200
    row = next(a for a in r.json() if a["id"] == apt["id"])
    assert row["utilization"] > 0
    assert row["status"] in ("occupied", "free", "needs_cleaning")
