"""Импорт listing-URL'ов через прямой httpx fetch (без MoreLogin / Playwright).
Используем когда MoreLogin отвалился.

URL-ы идут аргументами; если их нет — берём дефолтный список ниже.
Бэк должен быть запущен (см. ./start.sh). По умолчанию http://127.0.0.1:8000.

Парсеры — для doska_ykt и youla. Для doska читаем DOM-селекторы (прод-разметка).
Для youla SSR-HTML без data-атрибутов (Vue-SPA), достаём всё из og-meta + <title>.

  uv run --env-file .env python scripts/import_via_httpx.py
  uv run --env-file .env python scripts/import_via_httpx.py URL [URL ...]
  FIL_BACKEND_URL=http://127.0.0.1:8000 uv run python scripts/import_via_httpx.py
"""
import os
import re
import sys
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


DEFAULT_URLS = [
    "https://doska.ykt.ru/15852055",
    "https://doska.ykt.ru/16390698",
    "https://doska.ykt.ru/16123896",
    "https://trk.mail.ru/c/phjpd1?id=69b96c08f2c5078bbf081ad4",
    "https://trk.mail.ru/c/phjpd1?id=69b96f6d669ab377050bcf04",
    "https://trk.mail.ru/c/phjpd1?id=68bc38a356554dd8e70245df",
]

BACKEND = os.environ.get("FIL_BACKEND_URL", "http://127.0.0.1:8000")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}


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


def parse_youla(html: str, final_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    og_title = soup.select_one('meta[property="og:title"]')
    og_image = soup.select_one('meta[property="og:image"]')
    og_url = soup.select_one('meta[property="og:url"]')
    title = og_title.get("content").strip() if og_title and og_title.get("content") else None

    price = rooms = area_m2 = None
    if title:
        # "Квартира, 2 комнаты, 50 м² – аренда в Якутске, цена 5 000 руб., дата размещения: ..."
        m = re.search(r"цена\s+([\d\s ]+)\s*руб", title)
        if m:
            d = re.sub(r"\D", "", m.group(1))
            price = int(d) if d else None
        if re.search(r"студи[яи]", title, re.IGNORECASE):
            rooms = "Студия"
        else:
            rm = re.search(r"(\d+)\s*комнат[а-яё]*", title, re.IGNORECASE)
            if rm:
                n = rm.group(1)
                rooms = f"{n} комн."
        am = re.search(r"(\d+)\s*м²", title)
        if am:
            area_m2 = int(am.group(1))

    canonical = (og_url.get("content") if og_url and og_url.get("content") else final_url)
    return {
        "source": "youla",
        "source_url": canonical,
        "title": title,
        "address": None,
        "price_per_night": price,
        "rooms": rooms,
        "area_m2": area_m2,
        "floor": None,
        "district": "Якутск",
        "cover_url": og_image.get("content") if og_image and og_image.get("content") else None,
    }


def detect_parser(final_host: str):
    h = final_host.lower()
    if h.endswith("doska.ykt.ru"):
        return "doska_ykt", parse_doska
    if h.endswith("youla.ru"):
        return "youla", parse_youla
    return None, None


def fetch(client: httpx.Client, url: str) -> tuple[str, str]:
    r = client.get(url, follow_redirects=True, timeout=30.0)
    r.raise_for_status()
    return r.text, str(r.url)


def pick_owner_id(client: httpx.Client) -> int:
    r = client.get(f"{BACKEND}/dev_auth/users", timeout=10.0)
    r.raise_for_status()
    for u in r.json():
        if u["role"] == "owner":
            return u["id"]
    raise SystemExit("no owner in DB — нужен dev_auth с владельцем")


def main() -> int:
    urls = sys.argv[1:] or DEFAULT_URLS
    print(f"backend = {BACKEND}")
    print(f"{len(urls)} URLs")

    fetch_client = httpx.Client(headers=HEADERS, timeout=30.0)
    api = httpx.Client(base_url=BACKEND, timeout=60.0)
    try:
        uid = pick_owner_id(api)
        api.headers["X-User-Id"] = str(uid)

        ok = skip = fail = 0
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}")
            try:
                html, final_url = fetch(fetch_client, url)
            except Exception as e:
                print(f"  fetch failed: {e}")
                fail += 1
                continue
            host = urlparse(final_url).netloc
            src, parser = detect_parser(host)
            if not parser:
                print(f"  unsupported host after redirect: {host}")
                fail += 1
                continue
            try:
                data = parser(html, final_url)
            except Exception as e:
                print(f"  parse failed: {e}")
                fail += 1
                continue
            if not data.get("title") or not data.get("price_per_night"):
                print(f"  no title/price (title={data.get('title')!r} price={data.get('price_per_night')!r}), скип")
                skip += 1
                continue
            data["address"] = data.get("address") or data.get("district") or data["title"]
            payload = {k: v for k, v in data.items() if v is not None}
            print(f"  → {data['title'][:80]} · {data['price_per_night']}₽ · {data.get('rooms')} · {data.get('district')}")

            rs = api.post("/apartments", json=payload)
            if rs.status_code == 201:
                apt_id = rs.json()["id"]
                print(f"  saved id={apt_id}")
                ok += 1
            elif rs.status_code == 409:
                print("  дубль source_url, скип")
                skip += 1
            else:
                print(f"  save HTTP {rs.status_code}: {rs.text[:300]}")
                fail += 1
        print(f"\n== ok={ok} skip={skip} fail={fail} ==")
        return 0 if fail == 0 else 1
    finally:
        fetch_client.close()
        api.close()


if __name__ == "__main__":
    raise SystemExit(main())
