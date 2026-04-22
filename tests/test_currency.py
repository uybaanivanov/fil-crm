import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from backend.db import get_conn


def test_refresh_writes_rates(tmp_db):
    """refresh_rates пишет в БД полученные курсы."""
    from backend import currency as cur
    from backend.db import apply_migrations

    apply_migrations()

    fake_resp = MagicMock()
    fake_resp.json = MagicMock(return_value={"rates": {"USD": 0.011, "VND": 273.5}})
    fake_resp.raise_for_status = MagicMock(return_value=None)

    fake_client = MagicMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=None)
    fake_client.get = AsyncMock(return_value=fake_resp)

    with patch("backend.currency.httpx.AsyncClient", return_value=fake_client):
        asyncio.run(cur.refresh_rates())

    with get_conn() as conn:
        rows = {r["code"]: r["rate_to_rub"] for r in conn.execute("SELECT code, rate_to_rub FROM currency_rates")}
    assert rows["USD"] == 0.011
    assert rows["VND"] == 273.5


def test_endpoint_returns_latest(client):
    with get_conn() as conn:
        conn.execute("INSERT INTO currency_rates VALUES ('2026-04-22', 'USD', 0.012)")
        conn.execute("INSERT INTO currency_rates VALUES ('2026-04-22', 'VND', 280.0)")
    r = client.get("/currency/rates")
    assert r.status_code == 200
    body = r.json()
    assert body["usd"] == 0.012 and body["vnd"] == 280.0 and body["updated_at"] == "2026-04-22"


def test_endpoint_empty(client):
    r = client.get("/currency/rates")
    assert r.status_code == 200
    body = r.json()
    assert body == {"updated_at": None, "usd": None, "vnd": None}
