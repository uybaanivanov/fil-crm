import re

from bs4 import BeautifulSoup

from backend.parsers.types import ParsedListing


_ROOMS_RE = re.compile(r"(\d+\s*комн[а-яё]*)", re.IGNORECASE)
_AREA_RE = re.compile(r"(\d+)\s*м²")


def parse_html(html: str, url: str) -> ParsedListing:
    soup = BeautifulSoup(html, "html.parser")

    title_el = soup.select_one('h2[data-test-block="ProductCaption"]')
    title = title_el.get_text(strip=True) if title_el else None

    price_el = soup.select_one('span[data-test-component="Price"]')
    digits = re.sub(r"\D", "", price_el.get_text()) if price_el else ""
    price_per_night = int(digits) if digits else None

    address = None
    dd = soup.select_one('li[data-test-component="ProductMap"] dd')
    if dd:
        btn = dd.find("button")
        if btn:
            btn.decompose()
        address = dd.get_text(" ", strip=True) or None

    og = soup.select_one('meta[property="og:image"]')
    cover_url = og.get("content") if og else None

    rooms = None
    area_m2 = None
    if title:
        rm = _ROOMS_RE.search(title)
        if rm:
            rooms = rm.group(1).strip()
        am = _AREA_RE.search(title)
        if am:
            area_m2 = int(am.group(1))

    return ParsedListing(
        source="youla",
        source_url=url,
        title=title,
        address=address,
        price_per_night=price_per_night,
        rooms=rooms,
        area_m2=area_m2,
        floor=None,
        district=None,
        cover_url=cover_url,
    )
