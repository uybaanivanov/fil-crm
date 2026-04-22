"""Обновляет курсы USD/VND в локальной БД из open.er-api.com.

Запуск:
    uv run --env-file .env python scripts/refresh_rates.py

Cron:
    0 6 * * * cd /opt/fil-crm && uv run --env-file .env python scripts/refresh_rates.py
"""
import datetime as dt
import os
import sqlite3
from pathlib import Path

import httpx

DB = Path(os.environ.get("FIL_DB_PATH") or (Path(__file__).resolve().parent.parent / "db.sqlite3"))
URL = "https://open.er-api.com/v6/latest/RUB"
CODES = ("USD", "VND")


def main():
    r = httpx.get(URL, timeout=10.0)
    r.raise_for_status()
    rates = (r.json() or {}).get("rates") or {}
    today = dt.date.today().isoformat()
    conn = sqlite3.connect(str(DB))
    try:
        for code in CODES:
            v = rates.get(code)
            if v is None:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO currency_rates(date, code, rate_to_rub) VALUES (?, ?, ?)",
                (today, code, float(v)),
            )
        conn.commit()
        print(f"OK: {today} {[(c, rates.get(c)) for c in CODES]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
