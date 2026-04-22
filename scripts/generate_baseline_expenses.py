#!/usr/bin/env python3
"""Генерирует ежемесячные авто-записи расходов (rent/utilities) из baseline-полей квартир.

Самодостаточный, не импортирует backend. Идемпотентен через UNIQUE-индекс
expenses.idx_expenses_auto_unique.
"""
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path


def run(db_path: Path, month: str, dry_run: bool) -> int:
    occurred_at = f"{month}-01"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        apartments = conn.execute(
            "SELECT id, monthly_rent, monthly_utilities FROM apartments "
            "WHERE monthly_rent IS NOT NULL"
        ).fetchall()
        created = 0
        skipped = 0
        for apt_id, rent, util in apartments:
            rows = [("rent", rent)]
            if util is not None:
                rows.append(("utilities", util))
            for category, amount in rows:
                if dry_run:
                    created += 1
                    continue
                cur = conn.execute(
                    "INSERT INTO expenses(amount, category, description, occurred_at, "
                    "apartment_id, source) "
                    "VALUES (?, ?, 'auto-generated', ?, ?, 'auto') "
                    "ON CONFLICT DO NOTHING",
                    (amount, category, occurred_at, apt_id),
                )
                if cur.rowcount == 1:
                    created += 1
                else:
                    skipped += 1
        if not dry_run:
            conn.commit()
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"{prefix}baseline-expenses for {month}: created={created} skipped={skipped}")
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--month", default=date.today().strftime("%Y-%m"),
        help="YYYY-MM; по умолчанию текущий",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_path = Path(os.environ.get("DB_PATH", "db.sqlite3"))
    if not db_path.exists():
        print(f"DB not found: {db_path}", file=sys.stderr)
        return 1
    if len(args.month) != 7 or args.month[4] != "-":
        print(f"--month must be YYYY-MM, got {args.month!r}", file=sys.stderr)
        return 1
    return run(db_path, args.month, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
