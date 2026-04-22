from tests.conftest import seed_user, auth


def test_patch_without_utilities_ok(client):
    owner = seed_user(client, role="owner")
    create = client.post(
        "/apartments",
        json={
            "title": "Test", "address": "ул. Тест, 1",
            "price_per_night": 3000,
            "monthly_rent": 50000,
        },
        headers=auth(owner["id"]),
    )
    assert create.status_code in (200, 201), create.text
    apt_id = create.json()["id"]

    r = client.patch(
        f"/apartments/{apt_id}",
        json={"area_m2": 42},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["area_m2"] == 42
    assert r.json()["monthly_utilities"] is None


def test_patch_without_rent_fails(client):
    owner = seed_user(client, role="owner")
    create = client.post(
        "/apartments",
        json={"title": "T", "address": "a", "price_per_night": 1000},
        headers=auth(owner["id"]),
    )
    apt_id = create.json()["id"]
    r = client.patch(
        f"/apartments/{apt_id}",
        json={"area_m2": 30},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 400
    assert "monthly_rent" in r.json()["detail"]
