"""Генерирует обезличенный demo-фикстур из дампа прод-БД.

Usage: uv run python scripts/demo_make_seed.py <path-to-prod-dump.sqlite3>

Что делает:
- копирует входной файл в docs/demo-seed.sqlite3
- идёт по списку RULES (таблица.колонка → функция замены) и UPDATE'ит данные
- удаляет sensitive blob-таблицы целиком (если есть)

ВАЖНО: список RULES ниже — стартовый, основан на схеме на момент написания.
Перед запуском ОБЯЗАТЕЛЬНО пройдись по `PRAGMA table_info` каждой таблицы и
дополни RULES любыми полями где встречается имя/телефон/паспорт/документ.
"""

from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

# Простой детерминированный пул имён — без faker'а ради одной задачи.
_FIRST = [
    "Алексей", "Мария", "Иван", "Дарья", "Никита", "Анна", "Сергей",
    "Ольга", "Павел", "Екатерина", "Михаил", "София", "Дмитрий", "Юлия",
    "Артур", "Татьяна",
]
_LAST = [
    "Иванов", "Петров", "Сидоров", "Кузнецов", "Смирнов", "Попов",
    "Новиков", "Морозов", "Волков", "Соколов", "Лебедев", "Семёнов",
]


def fake_full_name(seed: int) -> str:
    f = _FIRST[seed % len(_FIRST)]
    l = _LAST[(seed // len(_FIRST)) % len(_LAST)]
    # Согласование рода — простая эвристика по окончанию first name.
    if f.endswith(("а", "я")) and l.endswith(("ов", "ев", "ин")):
        l = l + "а"
    return f"{f} {l}"


def fake_phone(seed: int) -> str:
    return f"+7 999 {(seed // 100) % 1000:03d} {seed % 100:02d}{(seed * 7) % 100:02d}"


def fake_email(seed: int, role: str = "client") -> str:
    return f"{role}{seed}@example.com"


def fake_username(seed: int) -> str:
    return f"user{seed}"


def fake_address(seed: int) -> str:
    streets = ["Ленина", "Дзержинского", "Кирова", "Орджоникидзе", "Ярославского"]
    return f"ул. {streets[seed % len(streets)]}, д. {(seed % 50) + 1}"


# Таблица.колонка → функция (id_or_seed, current_value) -> new_value.
# Если таблицы нет в БД, шаг просто пропускается.
RULES = {
    "users": {
        "full_name": lambda i, _: fake_full_name(i),
        "username": lambda i, _: fake_username(i),
        "password_hash": lambda *_: "",
    },
    "clients": {
        "full_name": lambda i, _: fake_full_name(i + 1000),
        "phone": lambda i, _: fake_phone(i),
        "notes": lambda *_: "",
    },
    "apartments": {
        "address": lambda i, _: fake_address(i),
        "title": lambda i, cur: f"Квартира {i} — посуточная аренда",
        "source_url": lambda *_: None,
        "apt_number": lambda i, _: str((i % 200) + 1),
        "entrance": lambda i, _: str((i % 5) + 1),
        "intercom_code": lambda *_: "0000",
        "safe_code": lambda *_: "0000",
        "utility_account": lambda *_: "",
    },
    "bookings": {
        "notes": lambda *_: "",
    },
    "expenses": {
        "description": lambda *_: "",
    },
}

# Таблицы, содержимое которых вырезаем целиком (тяжёлые blob'ы — паспорта-фотки и пр.).
WIPE_TABLES = [
    # Заполнить при реализации, проверив схему. Пример:
    # "client_documents",
    # "passport_scans",
]


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _column_exists(conn: sqlite3.Connection, table: str, col: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == col for r in rows)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: demo_make_seed.py <path-to-prod-dump.sqlite3>", file=sys.stderr)
        return 2

    src = Path(argv[1]).expanduser().resolve()
    if not src.exists():
        print(f"ERROR: {src} not found", file=sys.stderr)
        return 1

    root = Path(__file__).resolve().parent.parent
    dst = root / "docs" / "demo-seed.sqlite3"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    print(f"copied {src} -> {dst}")

    conn = sqlite3.connect(str(dst))
    try:
        # WIPE целиком
        for tbl in WIPE_TABLES:
            if _table_exists(conn, tbl):
                conn.execute(f"DELETE FROM {tbl}")
                print(f"wiped table {tbl}")

        # Применяем RULES построчно по id
        for tbl, cols in RULES.items():
            if not _table_exists(conn, tbl):
                print(f"skip table {tbl} (отсутствует)")
                continue
            valid_cols = {c: fn for c, fn in cols.items() if _column_exists(conn, tbl, c)}
            if not valid_cols:
                continue
            ids = [r[0] for r in conn.execute(f"SELECT id FROM {tbl} ORDER BY id").fetchall()]
            for row_id in ids:
                row = conn.execute(
                    f"SELECT {', '.join(valid_cols.keys())} FROM {tbl} WHERE id=?", (row_id,)
                ).fetchone()
                new_values = []
                for (col, fn), cur in zip(valid_cols.items(), row):
                    new_values.append(fn(row_id, cur))
                set_clause = ", ".join(f"{c}=?" for c in valid_cols.keys())
                conn.execute(
                    f"UPDATE {tbl} SET {set_clause} WHERE id=?",
                    (*new_values, row_id),
                )
            print(f"updated {tbl}: {len(ids)} rows, cols={list(valid_cols)}")

        conn.commit()
    finally:
        conn.close()

    print(f"\nDone. Фикстур: {dst}")
    print("Дальше: глазами проверь sqlite3 docs/demo-seed.sqlite3, и подготовь docs/demo-media/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
