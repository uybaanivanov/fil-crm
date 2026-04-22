"""Полуручной импорт: ты открываешь URL в браузере, копируешь HTML (view-source:
или Inspect → <html> → Copy → Outer HTML), вставляешь в терминал, закрываешь
строкой `EOF`. Скрипт парсит селекторами doska_ykt/youla и постит в /apartments.
Опционально перед EOF можно задать img_url (перекрывает og:image).

Бэк должен быть поднят (./start.sh).
  uv run --env-file .env python scripts/manual_import.py URL [URL ...]
  uv run --env-file .env python scripts/manual_import.py -f urls.txt

Ввод для каждой квартиры:
  <вставляешь HTML>
  EOF
  img_url (можно пустым)
  [подтверждение save: Enter=save, s=skip]
"""
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

BACKEND = os.environ.get("FIL_BACKEND_URL", "http://127.0.0.1:8000")

_SOURCE_BY_HOST = {
    "doska.ykt.ru": "doska_ykt", "www.doska.ykt.ru": "doska_ykt",
    "youla.ru": "youla", "www.youla.ru": "youla",
    "trk.mail.ru": "youla",
}


def resolve_source(url: str) -> str:
    return _SOURCE_BY_HOST.get(urlparse(url).netloc.lower(), "manual")


def parse_doska(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("div.d-pv_title")
    title = title_el.get_text(strip=True) if title_el else None
    price_el = soup.select_one("div.d-pv_price")
    digits = re.sub(r"\D", "", price_el.get_text()) if price_el else ""
    price = int(digits) if digits else None
    options: dict[str, str] = {}
    for row in soup.select("table.d-pv_options tr"):
        cells = row.select("td")
        for i in range(0, len(cells), 2):
            pair = cells[i:i + 2]
            if len(pair) == 2:
                options[pair[0].get_text(strip=True).rstrip(":").strip()] = pair[1].get_text(strip=True)
    area_raw = options.get("Общая площадь, м²")
    area_m2 = None
    if area_raw:
        d = re.sub(r"\D", "", area_raw)
        area_m2 = int(d) if d else None
    og = soup.select_one("meta[property='og:image']")
    return {
        "source": "doska_ykt",
        "source_url": url,
        "title": title,
        "address": None,
        "price_per_night": price,
        "rooms": options.get("Комнаты"),
        "area_m2": area_m2,
        "floor": options.get("Этаж"),
        "district": options.get("Район"),
        "cover_url": og.get("content") if og else None,
    }


def parse_youla(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one('h2[data-test-block="ProductCaption"]') or soup.select_one("h1")
    title = title_el.get_text(strip=True) if title_el else None
    price_el = soup.select_one('span[data-test-component="Price"]')
    digits = re.sub(r"\D", "", price_el.get_text()) if price_el else ""
    price = int(digits) if digits else None
    address = None
    dd = soup.select_one('li[data-test-component="ProductMap"] dd')
    if dd:
        btn = dd.find("button")
        if btn:
            btn.decompose()
        address = dd.get_text(" ", strip=True) or None
    og = soup.select_one('meta[property="og:image"]')
    rooms = area_m2 = None
    if title:
        rm = re.search(r"(\d+\s*комн[а-яё]*)", title, re.IGNORECASE)
        if rm:
            rooms = rm.group(1).strip()
        am = re.search(r"(\d+)\s*м²", title)
        if am:
            area_m2 = int(am.group(1))
    return {
        "source": "youla",
        "source_url": url,
        "title": title,
        "address": address,
        "price_per_night": price,
        "rooms": rooms,
        "area_m2": area_m2,
        "floor": None,
        "district": None,
        "cover_url": og.get("content") if og else None,
    }


def parse_html(html: str, url: str) -> dict:
    src = resolve_source(url)
    if src == "doska_ykt":
        return parse_doska(html, url)
    if src == "youla":
        return parse_youla(html, url)
    raise SystemExit(f"unsupported host: {url}")


def read_html_block() -> str:
    print("  вставь HTML страницы. Закрой строкой  EOF")
    lines = []
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        if line.rstrip("\n").strip() == "EOF":
            break
        lines.append(line)
    return "".join(lines)


def pick_owner_id(c: httpx.Client) -> int:
    r = c.get(f"{BACKEND}/dev_auth/users", timeout=10.0)
    r.raise_for_status()
    for u in r.json():
        if u["role"] == "owner":
            return u["id"]
    raise SystemExit("no owner in DB")


def read_urls(argv: list[str]) -> list[str]:
    if len(argv) >= 2 and argv[0] == "-f":
        return [u.strip() for u in Path(argv[1]).read_text().splitlines() if u.strip()]
    return [a.strip() for a in argv if a.strip()]


def main() -> int:
    urls = read_urls(sys.argv[1:])
    if not urls:
        print("нет URL")
        return 2

    with httpx.Client(timeout=60.0) as c:
        uid = pick_owner_id(c)
        c.headers["X-User-Id"] = str(uid)

        ok = skip = fail = 0
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}")
            html = read_html_block()
            if not html.strip():
                print("  пусто, скип")
                skip += 1
                continue
            img_override = input("  img_url (пусто = из og:image): ").strip()

            try:
                data = parse_html(html, url)
            except Exception as e:
                print(f"  parse failed: {e}")
                fail += 1
                continue

            if img_override:
                data["cover_url"] = img_override
            if not data.get("title") or not data.get("price_per_night"):
                print(f"  не распарсилось (title={data.get('title')!r} price={data.get('price_per_night')!r}), скип")
                skip += 1
                continue
            data["address"] = data.get("address") or data.get("district") or data["title"]

            print(f"  → {data['title'][:70]} · {data['price_per_night']}₽ · {data.get('rooms')} · {data.get('district')}")
            confirm = input("  Enter=save, s=skip: ").strip().lower()
            if confirm == "s":
                skip += 1
                continue

            payload = {k: v for k, v in data.items() if v is not None}
            rs = c.post(f"{BACKEND}/apartments", json=payload)
            if rs.status_code == 201:
                print(f"  saved id={rs.json()['id']}")
                ok += 1
            elif rs.status_code == 409:
                print("  дубль source_url, скип")
                skip += 1
            else:
                print(f"  save HTTP {rs.status_code}: {rs.text[:300]}")
                fail += 1

        print(f"\n== ok={ok} skip={skip} fail={fail} ==")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
