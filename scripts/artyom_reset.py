"""Откатывает локальные изменения Артёмовского импорта.

- DELETE FROM bookings (все смапленные квартиры)
- DELETE FROM clients WHERE source = 'artyom_import'
- NULL-ит паспортные поля во ВСЕХ apartments (они у нас всё равно только
  от Артёмовского импорта проставлены).

uv run python scripts/artyom_reset.py
"""

import sqlite3
from pathlib import Path

DB = Path("db.sqlite3")


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")

    b = conn.execute("DELETE FROM bookings").rowcount
    c = conn.execute("DELETE FROM clients WHERE source = 'artyom_import'").rowcount
    a = conn.execute(
        "UPDATE apartments SET "
        "entrance = NULL, apt_number = NULL, intercom_code = NULL, "
        "safe_code = NULL, utility_account = NULL, "
        "price_weekday = NULL, price_weekend = NULL"
    ).rowcount

    conn.commit()
    conn.close()
    print(f"deleted {b} bookings, {c} artyom clients; reset passport on {a} apartments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
