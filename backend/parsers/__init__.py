from urllib.parse import urlparse

import httpx

from backend.parsers.types import ParsedListing


class UnsupportedSource(ValueError):
    pass


class ParseError(ValueError):
    pass


_SOURCE_BY_HOST = {
    "doska.ykt.ru": "doska_ykt",
    "www.doska.ykt.ru": "doska_ykt",
    "youla.ru": "youla",
    "www.youla.ru": "youla",
}


def resolve_source(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host in _SOURCE_BY_HOST:
        return _SOURCE_BY_HOST[host]
    raise UnsupportedSource(f"unsupported host: {host}")


def resolve_final_url(url: str) -> str:
    """HEAD с follow_redirects — отдаёт финальный URL (для trk.mail.ru → youla.ru)."""
    with httpx.Client(follow_redirects=True, timeout=15.0) as c:
        r = c.head(url)
        return str(r.url)


def parse_html(html: str, final_url: str) -> ParsedListing:
    source = resolve_source(final_url)
    if source == "doska_ykt":
        from backend.parsers.doska_ykt import parse_html as impl
    elif source == "youla":
        from backend.parsers.youla import parse_html as impl
    else:
        raise UnsupportedSource(source)
    return impl(html, final_url)
