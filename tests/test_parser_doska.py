from pathlib import Path

from backend.parsers.doska_ykt import parse_html

FIX = Path(__file__).parent / "fixtures" / "doska_ykt_sample.html"


def test_parse_doska_sample():
    html = FIX.read_text(encoding="utf-8")
    url = "https://doska.ykt.ru/15838371"
    r = parse_html(html, url)
    assert r.source == "doska_ykt"
    assert r.source_url == url
    assert r.title == "37 м², квартиры, сдаю в посуточную аренду"
    assert r.price_per_night == 3500
    assert r.rooms == "1 комн."
    assert r.district == "Сайсары"
    assert r.floor == "4"
    assert r.area_m2 == 37
    assert r.cover_url == "https://doska.ykt2.ru/files/2025-04-18/c3rhI9lCa1O.jpeg"
    assert r.address is None
