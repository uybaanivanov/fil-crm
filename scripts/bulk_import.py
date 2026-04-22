"""Прогон всех ссылок из tests/e2e_listing_urls.txt:
parse-url → POST /apartments. Печатает прогресс по каждой.

Бэк должен быть запущен (./start.sh).
"""
import json
import os
import sys
from pathlib import Path

import httpx

BACKEND = os.environ.get("FIL_BACKEND_URL", "http://127.0.0.1:8000")
URLS_FILE = Path("tests/e2e_listing_urls.txt")


def pick_owner_id() -> int:
    r = httpx.get(f"{BACKEND}/dev_auth/users", timeout=10.0)
    r.raise_for_status()
    for u in r.json():
        if u["role"] == "owner":
            return u["id"]
    raise SystemExit("no owner in DB")


def main():
    urls = [u.strip() for u in URLS_FILE.read_text().splitlines() if u.strip()]
    print(f"{len(urls)} URLs")
    uid = pick_owner_id()
    h = {"X-User-Id": str(uid)}
    with httpx.Client(base_url=BACKEND, headers=h, timeout=180.0) as c:
        ok = skip = fail = 0
        for i, url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {url}")
            r = c.post("/apartments/parse-url", json={"url": url})
            if r.status_code != 200:
                print(f"  parse: HTTP {r.status_code} {r.text[:300]}")
                fail += 1
                continue
            listing = r.json()
            title = listing.get("title") or ""
            print(f"  parsed: {title[:60]} · {listing.get('price_per_night')}₽ · {listing.get('rooms')}")

            # минимальная валидация
            if not listing.get("title") or not listing.get("price_per_night"):
                print("  ! нет title/price, пропускаю (руками потом)")
                skip += 1
                continue
            address = listing.get("address") or listing.get("district") or title
            payload = {
                "title": title,
                "address": address,
                "price_per_night": listing["price_per_night"],
                "source": listing.get("source"),
                "source_url": listing.get("source_url"),
            }
            for k in ("rooms", "area_m2", "floor", "district", "cover_url"):
                if listing.get(k):
                    payload[k] = listing[k]

            rs = c.post("/apartments", json=payload)
            if rs.status_code == 201:
                apt_id = rs.json()["id"]
                print(f"  saved id={apt_id}")
                ok += 1
            elif rs.status_code == 409:
                print("  дубль source_url, скип")
                skip += 1
            else:
                print(f"  save: HTTP {rs.status_code} {rs.text[:300]}")
                fail += 1
        print(f"\n== ok={ok} skip={skip} fail={fail} ==")


if __name__ == "__main__":
    main()
