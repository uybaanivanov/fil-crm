"""Дамп локальных Артёмовских clients+bookings в JSON для заливки на прод.

Выход: docs/inbox/artyom_prod_dump.json

Bookings ссылаются на клиента через phone (не через id), чтобы на проде
клиенты могли получить свои auto-id.
"""

import json
import sqlite3
from pathlib import Path

DB = Path("db.sqlite3")
OUT = Path("docs/inbox/artyom_prod_dump.json")


def main() -> int:
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row

    clients = [
        dict(r)
        for r in c.execute(
            "SELECT full_name, phone, source FROM clients WHERE source = 'artyom_import' "
            "ORDER BY id"
        )
    ]
    bookings_rows = c.execute(
        "SELECT b.apartment_id, b.check_in, b.check_out, b.total_price, "
        "b.status, b.notes, cl.phone "
        "FROM bookings b JOIN clients cl ON cl.id = b.client_id "
        "WHERE cl.source = 'artyom_import' ORDER BY b.id"
    ).fetchall()
    bookings = [dict(r) for r in bookings_rows]

    phones_in_bookings = {b["phone"] for b in bookings}
    phones_in_clients = {cl["phone"] for cl in clients}
    missing = phones_in_bookings - phones_in_clients
    if missing:
        raise SystemExit(f"bookings referencing unknown phones: {missing}")

    OUT.write_text(
        json.dumps(
            {"clients": clients, "bookings": bookings},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"clients: {len(clients)}  bookings: {len(bookings)}  → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
