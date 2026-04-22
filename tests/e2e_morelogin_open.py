"""Smoke MoreLogin: стартует профиль через локальный API, печатает CDP URL,
ждёт Enter, закрывает. Самодостаточный — только httpx + env.

Запуск:  uv run --env-file .env python tests/e2e_morelogin_open.py
"""
import os
import sys

import httpx

API_URL = os.environ.get("MORELOGIN_API_URL", "http://127.0.0.1:40000")


def call(path: str, payload: dict) -> dict:
    r = httpx.post(f"{API_URL}{path}", json=payload, timeout=60.0)
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 0:
        raise SystemExit(f"{path} → api error: {body}")
    return body.get("data") or {}


def main():
    eid = os.environ.get("MORELOGIN_ENV_ID") or input("envId: ").strip()
    if not eid:
        sys.exit("envId пустой")

    input(f"Стартовать профиль {eid}? [Enter]")
    data = call("/api/env/start", {"envId": eid})
    port = data.get("debugPort")
    if not port:
        sys.exit(f"debugPort пустой: {data}")
    print(f"debug port: {port}")
    print(f"CDP URL:    http://127.0.0.1:{port}")

    input("Профиль открыт. Enter для закрытия...")
    call("/api/env/close", {"envId": eid})
    print("OK")


if __name__ == "__main__":
    main()
