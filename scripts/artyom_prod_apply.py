"""Применяет artyom_prod_dump.json к прод-БД (db.sqlite3 рядом со скриптом).

Запускать НА ПРОДЕ. Идемпотентный: перед заливкой стирает artyom-клиентов
и их брони.

  python3 artyom_prod_apply.py artyom_prod_dump.json
"""

import json
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    dump_path = Path(sys.argv[1])
    db_path = Path(__file__).resolve().parent / "db.sqlite3"

    payload = json.loads(dump_path.read_text(encoding="utf-8"))
    clients = payload["clients"]
    bookings = payload["bookings"]

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Идемпотентность: сначала брони (FK зависят от clients), потом клиенты.
    b_del = conn.execute(
        "DELETE FROM bookings WHERE client_id IN "
        "(SELECT id FROM clients WHERE source = 'artyom_import')"
    ).rowcount
    c_del = conn.execute(
        "DELETE FROM clients WHERE source = 'artyom_import'"
    ).rowcount
    print(f"deleted: {b_del} bookings, {c_del} clients (old artyom data)")

    phone_to_id: dict[str, int] = {}
    for cl in clients:
        cur = conn.execute(
            "INSERT INTO clients (full_name, phone, source) VALUES (?, ?, ?)",
            (cl["full_name"], cl["phone"], cl["source"]),
        )
        phone_to_id[cl["phone"]] = cur.lastrowid

    for b in bookings:
        conn.execute(
            "INSERT INTO bookings "
            "(apartment_id, client_id, check_in, check_out, total_price, status, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                b["apartment_id"],
                phone_to_id[b["phone"]],
                b["check_in"],
                b["check_out"],
                b["total_price"],
                b["status"],
                b["notes"],
            ),
        )

    conn.commit()
    print(
        f"inserted: {len(clients)} clients, {len(bookings)} bookings"
    )
    # Sanity per apartment
    for r in conn.execute(
        "SELECT apartment_id, COUNT(*), SUM(total_price) FROM bookings "
        "GROUP BY apartment_id ORDER BY apartment_id"
    ):
        print("  apt", r)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
