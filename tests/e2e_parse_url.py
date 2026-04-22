"""Полный пайплайн через HTTP: бэк должен быть запущен.

Префлайт: пик первого owner из /dev_auth/users; шлёт POST /apartments/parse-url;
печатает ответ.

Запуск:
    # терминал 1:  uv run --env-file .env uvicorn backend.main:app --port 8000
    # терминал 2:  uv run --env-file .env python tests/e2e_parse_url.py
"""
import json
import os
import sys

import httpx

BACKEND = os.environ.get("FIL_BACKEND_URL", "http://127.0.0.1:8000")


def pick_owner_id() -> int:
    r = httpx.get(f"{BACKEND}/dev_auth/users", timeout=10.0)
    r.raise_for_status()
    for u in r.json():
        if u["role"] == "owner":
            return u["id"]
    raise SystemExit("в базе нет owner — создай через UI или seed вручную")


def main():
    url = input("URL: ").strip()
    if not url:
        sys.exit("URL пустой")
    uid = pick_owner_id()
    r = httpx.post(
        f"{BACKEND}/apartments/parse-url",
        json={"url": url},
        headers={"X-User-Id": str(uid)},
        timeout=180.0,
    )
    print(f"HTTP {r.status_code}")
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)


if __name__ == "__main__":
    main()
