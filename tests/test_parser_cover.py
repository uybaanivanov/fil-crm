from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from backend.parsers.types import ParsedListing
from tests.conftest import seed_user, auth


@pytest.fixture
def media_dir(tmp_path, monkeypatch):
    d = tmp_path / "media"
    monkeypatch.setenv("FIL_MEDIA_DIR", str(d))
    return d


def _png_bytes() -> bytes:
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )


def _fake_listing() -> ParsedListing:
    return ParsedListing(
        source="doska_ykt",
        source_url="http://doska.ykt.ru/x",
        title="Y",
        address="a",
        price_per_night=1500,
        cover_url="http://example.com/img.png",
    )


async def _async_fake_fetch(url: str) -> ParsedListing:
    return _fake_listing()


def test_parse_localizes_cover(media_dir, client):
    owner = seed_user(client, role="owner")

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.headers = {"content-type": "image/png"}
    fake_resp.content = _png_bytes()
    fake_resp.raise_for_status = lambda: None

    with patch(
        "backend.routes.apartments._fetch_listing",
        new=_async_fake_fetch,
    ), patch("backend.routes.apartments.httpx.Client") as cli_cls:
        cli_cls.return_value.__enter__.return_value.get.return_value = fake_resp
        r = client.post(
            "/apartments/parse-url",
            json={"url": "http://doska.ykt.ru/x"},
            headers=auth(owner["id"]),
        )
    assert r.status_code == 200, r.text
    cover = r.json()["cover_url"]
    assert cover.startswith("/media/apartments/_pending/")
    pending_file = media_dir / "apartments" / "_pending" / Path(cover).name
    assert pending_file.exists()


def test_create_moves_pending_cover(media_dir, client):
    owner = seed_user(client, role="owner")
    pending_dir = media_dir / "apartments" / "_pending"
    pending_dir.mkdir(parents=True)
    fname = "abc.png"
    (pending_dir / fname).write_bytes(b"x")

    r = client.post(
        "/apartments",
        json={
            "title": "T", "address": "a", "price_per_night": 1000,
            "cover_url": f"/media/apartments/_pending/{fname}",
        },
        headers=auth(owner["id"]),
    )
    assert r.status_code in (200, 201), r.text
    apt_id = r.json()["id"]
    new_cover = r.json()["cover_url"]
    assert new_cover == f"/media/apartments/{apt_id}/cover.png"
    assert (media_dir / "apartments" / str(apt_id) / "cover.png").exists()
    assert not (pending_dir / fname).exists()
