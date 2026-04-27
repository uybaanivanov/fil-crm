import importlib

import pytest
from fastapi.testclient import TestClient


def _build_app(monkeypatch, tmp_path, env: dict[str, str]):
    """Перезагружает backend.main с заданным окружением и возвращает app."""
    monkeypatch.setenv("FIL_DB_PATH", str(tmp_path / "db.sqlite3"))
    for key in ("DEBUG", "FIL_DEV_AUTH_ONLY"):
        monkeypatch.delenv(key, raising=False)
    for key, val in env.items():
        monkeypatch.setenv(key, val)
    import backend.main as main
    importlib.reload(main)
    return main.app


def test_auth_login_present_by_default(monkeypatch, tmp_path):
    app = _build_app(monkeypatch, tmp_path, {})
    with TestClient(app) as client:
        # Нет такого юзера -> 401, а не 404 — значит роут существует.
        r = client.post("/auth/login", json={"username": "x", "password": "y"})
        assert r.status_code == 401


def test_auth_login_disabled_when_dev_auth_only(monkeypatch, tmp_path):
    app = _build_app(monkeypatch, tmp_path, {"FIL_DEV_AUTH_ONLY": "1"})
    with TestClient(app) as client:
        # Роут не подключён вовсе -> 404.
        r = client.post("/auth/login", json={"username": "x", "password": "y"})
        assert r.status_code == 404


def test_dev_auth_present_when_debug(monkeypatch, tmp_path):
    app = _build_app(monkeypatch, tmp_path, {"DEBUG": "1", "FIL_DEV_AUTH_ONLY": "1"})
    with TestClient(app) as client:
        r = client.get("/dev_auth/users")
        assert r.status_code == 200
