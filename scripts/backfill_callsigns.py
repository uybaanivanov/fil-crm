"""One-shot data fix:
1. youla-записи без человеческого адреса (адрес = NULL или 'Якутск') → 'Ленина'.
2. Заполнить callsign для всех квартир по схеме «{район}-{N}» (счётчик в районе по id ASC).
   Существующие callsign не перезаписываются.

Запуск (на каждой среде, где обновляем БД):
  uv run --env-file .env python scripts/backfill_callsigns.py

  # На проде:
  ssh cms-gen-bot 'cd /opt/fil-crm && uv run --env-file .env python scripts/backfill_callsigns.py'

Скрипт самодостаточный — без импорта backend. Использует FIL_DB_PATH (см. backend/db.py)
или дефолтный путь в корне проекта.
"""
import os
import sqlite3
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parent.parent / "db.sqlite3"
DB_PATH = Path(os.environ.get("FIL_DB_PATH", str(DEFAULT_DB)))


def main() -> int:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        # 1. youla без адреса → 'Ленина'
        cur = conn.execute(
            "UPDATE apartments SET address = 'Ленина' "
            "WHERE source = 'youla' AND (address IS NULL OR address = 'Якутск')"
        )
        print(f"address backfill (youla → 'Ленина'): {cur.rowcount} rows")

        # 2. callsign — только там где сейчас NULL
        rows = conn.execute(
            "SELECT id, district, callsign FROM apartments ORDER BY id"
        ).fetchall()
        per_district: dict[str, int] = {}
        # Сначала проинициализируем счётчики уже существующими callsign,
        # чтобы новые не наступили на старые «{район}-N».
        import re
        for r in rows:
            cs = r["callsign"]
            if not cs:
                continue
            m = re.match(r"^(?P<dist>.+)-(?P<n>\d+)$", cs)
            if not m:
                continue
            d = m.group("dist")
            n = int(m.group("n"))
            per_district[d] = max(per_district.get(d, 0), n)

        updates = 0
        for r in rows:
            if r["callsign"]:
                continue
            district = (r["district"] or "без района").strip() or "без района"
            per_district[district] = per_district.get(district, 0) + 1
            new_cs = f"{district}-{per_district[district]}"
            conn.execute(
                "UPDATE apartments SET callsign = ? WHERE id = ?",
                (new_cs, r["id"]),
            )
            updates += 1
            print(f"  id={r['id']:>3} district={district!r} → callsign={new_cs!r}")
        print(f"callsign backfill: {updates} rows")

        conn.commit()
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
