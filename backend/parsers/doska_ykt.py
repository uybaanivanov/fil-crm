import re

from bs4 import BeautifulSoup

from backend.parsers.types import ParsedListing


def parse_html(html: str, url: str) -> ParsedListing:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one("div.d-pv_title")
    title = title_el.get_text(strip=True) if title_el else None

    price_el = soup.select_one("div.d-pv_price")
    digits = re.sub(r"\D", "", price_el.get_text()) if price_el else ""
    price_per_night = int(digits) if digits else None

    options: dict[str, str] = {}
    for row in soup.select("table.d-pv_options tr"):
        cells = row.select("td")
        for i in range(0, len(cells), 2):
            pair = cells[i:i + 2]
            if len(pair) == 2:
                name = pair[0].get_text(strip=True).rstrip(":").strip()
                value = pair[1].get_text(strip=True)
                options[name] = value

    rooms = options.get("Комнаты")
    district = options.get("Район")
    floor = options.get("Этаж")
    area_raw = options.get("Общая площадь, м²")
    area_m2 = None
    if area_raw:
        area_digits = re.sub(r"\D", "", area_raw)
        area_m2 = int(area_digits) if area_digits else None

    og = soup.select_one("meta[property='og:image']")
    cover_url = og.get("content") if og else None

    return ParsedListing(
        source="doska_ykt",
        source_url=url,
        title=title,
        address=None,
        price_per_night=price_per_night,
        rooms=rooms,
        area_m2=area_m2,
        floor=floor,
        district=district,
        cover_url=cover_url,
    )
