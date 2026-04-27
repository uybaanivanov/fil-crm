import importlib
import os

import pytest
from fastapi.testclient import TestClient


def _build_app(env: dict[str, str]):
    """Перезагружает backend.main с заданным окружением и возвращает app."""
    for key in ("DEBUG", "FIL_DEV_AUTH_ONLY"):
        os.environ.pop(key, None)
    os.environ.update(env)
    import backend.main as main
    importlib.reload(main)
    return main.app


@pytest.fixture
def tmp_db_env(tmp_path, monkeypatch):
    monkeypatch.setenv("FIL_DB_PATH", str(tmp_path / "db.sqlite3"))


def test_auth_login_present_by_default(tmp_db_env):
    app = _build_app({})
    with TestClient(app) as client:
        # Нет такого юзера -> 401, а не 404 — значит роут существует.
        r = client.post("/auth/login", json={"username": "x", "password": "y"})
        assert r.status_code == 401


def test_auth_login_disabled_when_dev_auth_only(tmp_db_env):
    app = _build_app({"FIL_DEV_AUTH_ONLY": "1"})
    with TestClient(app) as client:
        # Роут не подключён вовсе -> 404.
        r = client.post("/auth/login", json={"username": "x", "password": "y"})
        assert r.status_code == 404


def test_dev_auth_present_when_debug(tmp_db_env):
    app = _build_app({"DEBUG": "1", "FIL_DEV_AUTH_ONLY": "1"})
    with TestClient(app) as client:
        r = client.get("/dev_auth/users")
        assert r.status_code == 200
