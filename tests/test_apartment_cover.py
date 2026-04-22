from pathlib import Path

import pytest

from tests.conftest import seed_user, auth


@pytest.fixture
def media_dir(tmp_path, monkeypatch):
    d = tmp_path / "media"
    monkeypatch.setenv("FIL_MEDIA_DIR", str(d))
    return d


def _png_bytes() -> bytes:
    # минимальный валидный PNG (1x1 прозрачный пиксель)
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )


def _make_apartment(client, owner_id):
    r = client.post(
        "/apartments",
        json={"title": "T", "address": "a", "price_per_night": 1000},
        headers=auth(owner_id),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def test_upload_cover_ok(media_dir, client):
    owner = seed_user(client, role="owner")
    apt_id = _make_apartment(client, owner["id"])
    r = client.post(
        f"/apartments/{apt_id}/cover",
        files={"file": ("c.png", _png_bytes(), "image/png")},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["cover_url"].startswith(f"/media/apartments/{apt_id}/cover.")
    saved = media_dir / "apartments" / str(apt_id)
    assert any(p.name.startswith("cover.") for p in saved.iterdir())


def test_upload_cover_rejects_text(media_dir, client):
    owner = seed_user(client, role="owner")
    apt_id = _make_apartment(client, owner["id"])
    r = client.post(
        f"/apartments/{apt_id}/cover",
        files={"file": ("c.txt", b"hello", "text/plain")},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 415


def test_upload_cover_replaces_old(media_dir, client):
    owner = seed_user(client, role="owner")
    apt_id = _make_apartment(client, owner["id"])
    client.post(
        f"/apartments/{apt_id}/cover",
        files={"file": ("c.png", _png_bytes(), "image/png")},
        headers=auth(owner["id"]),
    )
    # повторная загрузка с другим расширением — старый файл удаляется
    client.post(
        f"/apartments/{apt_id}/cover",
        files={"file": ("c.jpg", _png_bytes(), "image/jpeg")},
        headers=auth(owner["id"]),
    )
    saved = media_dir / "apartments" / str(apt_id)
    files = sorted(p.name for p in saved.iterdir())
    assert files == ["cover.jpg"]


def test_delete_cover(media_dir, client):
    owner = seed_user(client, role="owner")
    apt_id = _make_apartment(client, owner["id"])
    client.post(
        f"/apartments/{apt_id}/cover",
        files={"file": ("c.png", _png_bytes(), "image/png")},
        headers=auth(owner["id"]),
    )
    r = client.delete(f"/apartments/{apt_id}/cover", headers=auth(owner["id"]))
    assert r.status_code == 204
    apt = client.get(f"/apartments/{apt_id}", headers=auth(owner["id"])).json()
    assert apt["cover_url"] is None
