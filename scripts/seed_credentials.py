"""Сиды username/password для существующих юзеров без password_hash.

Самодостаточен (sqlite3 + hashlib + secrets) — не импортит backend.

Запуск:
    uv run --env-file .env python scripts/seed_credentials.py

Поведение:
- Овнерам ставится OWNER_PASSWORD ниже (захардкожено).
- Остальным — random 16-символьный пароль.
- Username — транслит full_name в [a-z0-9_]; при коллизиях добавляется суффикс.
- Юзеры с уже заполненным password_hash пропускаются.
- В конце печатается markdown-таблица для записи в docs/prod_credentials.md.
"""
import datetime as dt
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import string
import sys
from pathlib import Path


OWNER_PASSWORD = "NhaTrang2026!"

DB = Path(os.environ.get("FIL_DB_PATH") or (Path(__file__).resolve().parent.parent / "db.sqlite3"))


_RU_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "",
    "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}


def transliterate(s: str) -> str:
    out = []
    for ch in s.lower():
        out.append(_RU_TO_LAT.get(ch, ch))
    res = "".join(out)
    res = re.sub(r"[^a-z0-9]+", "_", res).strip("_")
    if not res:
        res = "user"
    return res[:32]


def make_unique_username(conn, base: str) -> str:
    cand = base
    i = 1
    while True:
        row = conn.execute("SELECT 1 FROM users WHERE username = ?", (cand,)).fetchone()
        if row is None:
            return cand
        i += 1
        suf = str(i)
        cand = (base[: 32 - len(suf) - 1] + "_" + suf)


def random_password(n: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


_N = 2 ** 14
_R = 8
_P = 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${key.hex()}"


def main():
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT id, full_name, role, username, password_hash FROM users ORDER BY id"
        ).fetchall()
        seeded: list[tuple[str, str, str, str]] = []  # (full_name, role, username, password)
        for r in rows:
            if r["password_hash"]:
                continue  # уже есть
            base = transliterate(r["full_name"]) if r["full_name"] else f"user_{r['id']}"
            username = r["username"] or make_unique_username(conn, base)
            password = OWNER_PASSWORD if r["role"] == "owner" else random_password()
            pw_hash = hash_password(password)
            conn.execute(
                "UPDATE users SET username = ?, password_hash = ? WHERE id = ?",
                (username, pw_hash, r["id"]),
            )
            seeded.append((r["full_name"], r["role"], username, password))
        conn.commit()
    finally:
        conn.close()

    if not seeded:
        print("Нечего сидить — у всех юзеров уже есть password_hash.")
        return

    print(f"# fil-crm — credentials\n\nСгенерировано: {dt.datetime.now().isoformat(timespec='seconds')}\n")
    print("| ФИО | Роль | Username | Пароль |")
    print("|---|---|---|---|")
    for full_name, role, username, password in seeded:
        print(f"| {full_name} | {role} | `{username}` | `{password}` |")


if __name__ == "__main__":
    main()
