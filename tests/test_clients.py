from tests.conftest import auth, seed_user


def test_get_client_with_history(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7 914 330 05 12"},
    ).json()
    for ci, co, total in [
        ("2026-01-10", "2026-01-12", 8000),
        ("2026-02-15", "2026-02-18", 12000),
        ("2026-04-21", "2026-04-24", 12840),
    ]:
        client.post(
            "/bookings",
            headers=auth(u["id"]),
            json={
                "apartment_id": apt["id"],
                "client_id": cl["id"],
                "check_in": ci,
                "check_out": co,
                "total_price": total,
            },
        )
    r = client.get(f"/clients/{cl['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == cl["id"]
    assert body["full_name"] == "Смирнов"
    assert body["stats"]["count"] == 3
    assert body["stats"]["nights"] == 2 + 3 + 3
    assert body["stats"]["revenue"] == 8000 + 12000 + 12840
    assert len(body["bookings"]) == 3
    assert body["bookings"][0]["apartment_title"] == "A"


def test_get_client_404(client):
    u = seed_user(client, role="owner")
    r = client.get("/clients/9999", headers=auth(u["id"]))
    assert r.status_code == 404
