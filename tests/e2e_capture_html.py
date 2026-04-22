"""Захват HTML страницы через MoreLogin+Playwright для парсер-фикстур.
Самодостаточный: httpx + playwright, без импортов из backend/.

Запуск:
    uv run --env-file .env python tests/e2e_capture_html.py

Сохраняет в tests/fixtures/<name>.html.
"""
import asyncio
import os
import sys
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

API_URL = os.environ.get("MORELOGIN_API_URL", "http://127.0.0.1:40000")
FIXTURES = Path(__file__).parent / "fixtures"


def call(path: str, payload: dict) -> dict:
    r = httpx.post(f"{API_URL}{path}", json=payload, timeout=60.0)
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 0:
        raise SystemExit(f"{path} → api error: {body}")
    return body.get("data") or {}


async def main():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    eid = os.environ.get("MORELOGIN_ENV_ID") or input("envId: ").strip()
    url = input("URL: ").strip()
    name = input("имя фикстуры (без .html), например doska_ykt_sample: ").strip()
    if not (eid and url and name):
        sys.exit("envId, URL и имя — обязательны")
    out = FIXTURES / f"{name}.html"

    data = call("/api/env/start", {"envId": eid})
    port = data.get("debugPort")
    if not port:
        sys.exit(f"debugPort пустой: {data}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)
            html = await page.content()
            out.write_text(html, encoding="utf-8")
            print(f"saved {len(html)} bytes -> {out}")
            await page.close()
    finally:
        call("/api/env/close", {"envId": eid})


if __name__ == "__main__":
    asyncio.run(main())
