"""Импортирует брони из docs/inbox/artyom_bookings_parsed.tsv в БД.

Идемпотентный: сначала DELETE FROM bookings WHERE apartment_id IN (смапленные),
потом INSERT. Клиенты — по телефону (upsert), без телефона → один глобальный
"Аноним".

Самодостаточный — без импорта backend.

uv run --with pyyaml python scripts/artyom_import_bookings.py [--dry-run]
"""

import argparse
import csv
import re
import sqlite3
import sys
from pathlib import Path

import yaml

DB = Path("db.sqlite3")
MAPPING = Path("docs/inbox/apartment_mapping.yaml")
TSV = Path("docs/inbox/artyom_bookings_parsed.tsv")

ANON_FULL_NAME = "Аноним"
ANON_PHONE = "—"


def normalize_phone(raw: str) -> str | None:
    """'+7 914 296‑53‑45' → '+79142965345'; '89142965345' → '+79142965345'."""
    if not raw:
        return None
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        return "+" + digits
    if len(digits) == 10:
        return "+7" + digits
    return None


def upsert_client(
    conn: sqlite3.Connection,
    *,
    full_name: str,
    phone: str,
    source: str | None = None,
) -> int:
    row = conn.execute(
        "SELECT id FROM clients WHERE phone = ?", (phone,)
    ).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO clients (full_name, phone, source) VALUES (?, ?, ?)",
        (full_name, phone, source),
    )
    return cur.lastrowid


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    mapping = yaml.safe_load(MAPPING.read_text(encoding="utf-8"))
    confirmed_apt_ids = [
        e["apt_id"] for e in mapping if e.get("status") == "confirmed"
    ]
    print(f"confirmed apts: {confirmed_apt_ids}")

    rows = list(csv.DictReader(open(TSV, encoding="utf-8"), delimiter="\t"))
    print(f"rows to import: {len(rows)}")

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys = ON")

    # идемпотентность: стираем только брони 7 смапленных
    placeholders = ",".join("?" * len(confirmed_apt_ids))
    existing = conn.execute(
        f"SELECT COUNT(*) FROM bookings WHERE apartment_id IN ({placeholders})",
        confirmed_apt_ids,
    ).fetchone()[0]
    print(f"existing bookings for these apts: {existing}  → будет удалено")

    if not args.dry_run:
        conn.execute(
            f"DELETE FROM bookings WHERE apartment_id IN ({placeholders})",
            confirmed_apt_ids,
        )

    # глобальный Аноним
    if not args.dry_run:
        anon_id = upsert_client(
            conn, full_name=ANON_FULL_NAME, phone=ANON_PHONE, source="artyom_import"
        )
    else:
        anon_id = -1

    inserted = 0
    with_phone = 0
    without_phone = 0
    for r in rows:
        apt_id = int(r["apt_id"])
        check_in = r["check_in"]
        check_out = r["check_out"]
        price_raw = r["total_price"]
        total_price = int(price_raw) if price_raw else 0

        phone_norm = normalize_phone(r["phone"])
        notes_parts = [r["notes"]]
        if r["hourly_extra"]:
            notes_parts.append(f"+{r['hourly_extra']}₽ hourly")
        notes_parts.append(f"raw: {r['raw']}")
        notes = " | ".join(p for p in notes_parts if p)

        if phone_norm:
            with_phone += 1
            client_id = (
                upsert_client(
                    conn,
                    full_name="Клиент Артёма",
                    phone=phone_norm,
                    source="artyom_import",
                )
                if not args.dry_run
                else -1
            )
        else:
            without_phone += 1
            client_id = anon_id

        if not args.dry_run:
            conn.execute(
                "INSERT INTO bookings (apartment_id, client_id, check_in, check_out, "
                "total_price, status, notes) VALUES (?, ?, ?, ?, ?, 'active', ?)",
                (apt_id, client_id, check_in, check_out, total_price, notes),
            )
        inserted += 1

    if not args.dry_run:
        conn.commit()
    conn.close()

    print(
        f"\ninserted: {inserted}  with_phone: {with_phone}  "
        f"without_phone (→ anon): {without_phone}  "
        f"{'(dry-run)' if args.dry_run else ''}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
