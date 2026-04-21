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
