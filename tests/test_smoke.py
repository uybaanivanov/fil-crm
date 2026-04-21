def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_tmp_db_isolated(client, tmp_db):
    assert tmp_db.exists()
    # Seed и проверка — БД пустая изначально
    import sqlite3

    with sqlite3.connect(str(tmp_db)) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        assert rows[0] == 0
