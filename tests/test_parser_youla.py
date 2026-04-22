from pathlib import Path

from backend.parsers.youla import parse_html

FIX = Path(__file__).parent / "fixtures" / "youla_sample.html"


def test_parse_youla_sample():
    html = FIX.read_text(encoding="utf-8")
    url = "https://youla.ru/yakutsk/nedvijimost/arenda-kvartiri-posutochno/kvartira-2-komnaty-50-m2-69b96c08f2c5078bbf081ad4"
    r = parse_html(html, url)
    assert r.source == "youla"
    assert r.source_url == url
    assert r.title == "Квартира, 2 комнаты, 50 м²"
    assert r.address == "Якутск, улица Свердлова, 16"
    assert r.price_per_night == 5000
    assert r.rooms == "2 комнаты"
    assert r.area_m2 == 50
    assert r.floor is None
    assert r.district is None
    assert r.cover_url == "https://cdn1.youla.io/files/images/780_780/69/b9/69b96ad1c49dd7569f0bd4d0-2.jpg"
