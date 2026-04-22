import pytest

from backend.parsers import UnsupportedSource, resolve_source


def test_resolve_source_doska():
    assert resolve_source("https://doska.ykt.ru/15838371") == "doska_ykt"


def test_resolve_source_doska_www():
    assert resolve_source("https://www.doska.ykt.ru/15838371") == "doska_ykt"


def test_resolve_source_youla():
    assert resolve_source("https://youla.ru/yakutsk/nedvizhimost/123") == "youla"


def test_resolve_source_unknown_raises():
    with pytest.raises(UnsupportedSource):
        resolve_source("https://example.com/listing/1")
