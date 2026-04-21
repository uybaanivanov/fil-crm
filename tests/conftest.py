import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def tmp_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".sqlite3")
    os.close(fd)
    monkeypatch.setenv("FIL_DB_PATH", path)
    yield Path(path)
    Path(path).unlink(missing_ok=True)


@pytest.fixture
def app(tmp_db, monkeypatch):
    # DEBUG включаем, чтобы регистрировался dev_auth
    monkeypatch.setenv("DEBUG", "1")
    # Пересобираем импорт, чтобы подхватить env
    import importlib

    import backend.main as main_mod

    importlib.reload(main_mod)
    return main_mod.app


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def seed_user(client: TestClient, role: str = "owner", name: str = "Айсен") -> dict:
    # Пробуем создать через dev_auth, если он есть; иначе — INSERT напрямую
    from backend.db import get_conn

    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users(full_name, role) VALUES (?, ?)", (name, role)
        )
        return {"id": cur.lastrowid, "full_name": name, "role": role}


def auth(user_id: int) -> dict:
    return {"X-User-Id": str(user_id)}
