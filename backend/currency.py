"""Курсы валют. rate_to_rub: сколько единиц валюты за 1 рубль (формат open.er-api.com base=RUB)."""
import datetime as dt

import httpx

from backend.db import get_conn

RATES_URL = "https://open.er-api.com/v6/latest/RUB"
SUPPORTED = ("USD", "VND")


async def refresh_rates() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(RATES_URL)
        r.raise_for_status()
        body = r.json()
    rates = body.get("rates") or {}
    today = dt.date.today().isoformat()
    out: dict[str, float] = {}
    with get_conn() as conn:
        for code in SUPPORTED:
            v = rates.get(code)
            if v is None:
                continue
            out[code] = float(v)
            conn.execute(
                "INSERT OR REPLACE INTO currency_rates(date, code, rate_to_rub) VALUES (?, ?, ?)",
                (today, code, float(v)),
            )
    return {"date": today, "rates": out}


def get_latest_rates() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(date) AS d FROM currency_rates").fetchone()
        d = row["d"]
        if not d:
            return {"updated_at": None, "usd": None, "vnd": None}
        rows = conn.execute(
            "SELECT code, rate_to_rub FROM currency_rates WHERE date = ?", (d,)
        ).fetchall()
    by = {r["code"]: r["rate_to_rub"] for r in rows}
    return {"updated_at": d, "usd": by.get("USD"), "vnd": by.get("VND")}
