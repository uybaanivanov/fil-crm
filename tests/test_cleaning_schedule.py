from tests.conftest import auth, seed_user


def _owner(client):
    return seed_user(client, role="owner", name="Айсен")


def _apt(client, u_id):
    return client.post(
        "/apartments",
        headers=auth(u_id),
        json={"title": "A", "address": "addr", "price_per_night": 1000},
    ).json()


def test_mark_dirty_requires_body(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(f"/apartments/{a['id']}/mark-dirty", headers=auth(u["id"]))
    assert r.status_code == 422


def test_mark_dirty_requires_cleaning_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(f"/apartments/{a['id']}/mark-dirty", headers=auth(u["id"]), json={})
    assert r.status_code == 422


def test_mark_dirty_rejects_invalid_datetime(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "not-a-date"},
    )
    assert r.status_code == 422


def test_mark_dirty_sets_flag_and_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["needs_cleaning"] == 1
    assert body["cleaning_due_at"] == "2026-04-24T14:00:00"


def test_mark_dirty_overwrites_existing_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    r = client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T16:30:00"},
    )
    assert r.status_code == 200
    assert r.json()["cleaning_due_at"] == "2026-04-24T16:30:00"


def test_mark_clean_clears_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    r = client.post(f"/apartments/{a['id']}/mark-clean", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["needs_cleaning"] == 0
    assert body["cleaning_due_at"] is None


def test_cleaning_list_includes_due_at_and_sorts(client):
    u = _owner(client)
    a1 = _apt(client, u["id"])
    a2 = _apt(client, u["id"])
    client.post(
        f"/apartments/{a1['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T16:30:00"},
    )
    client.post(
        f"/apartments/{a2['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T10:00:00"},
    )
    r = client.get("/apartments/cleaning", headers=auth(u["id"]))
    assert r.status_code == 200
    rows = r.json()
    ids = [x["id"] for x in rows]
    assert ids == [a2["id"], a1["id"]]
    assert rows[0]["cleaning_due_at"] == "2026-04-24T10:00:00"


def test_get_apartment_returns_cleaning_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    r = client.get(f"/apartments/{a['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    assert r.json()["cleaning_due_at"] == "2026-04-24T14:00:00"
