# Backend design-adapt — Implementation Plan (1/3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Расширить FastAPI+SQLite бэкенд fil-crm под требования мобильного дизайна: миграция схемы, `/dev_auth/*` под DEBUG-гейтом, расширение CRUD-эндпоинтов (apartments / bookings / clients), новые `/dashboard/summary`, `/reports`, `/expenses`, `/finance/summary`, `/*/stats`. Покрыть всё pytest-тестами через FastAPI `TestClient`.

**Architecture:** Каждый новый endpoint получает свой файл-роутер в `backend/routes/`. Общие расчёты (ночи, занятость, ADR/RevPAR, диапазон месяца) вынесены в `backend/lib/stats.py`. Миграции становятся идемпотентными через таблицу `_schema_migrations`. Тестовое окружение использует временную sqlite-БД через фикстуру pytest.

**Tech Stack:** Python 3.13 · FastAPI · SQLite (raw queries) · pytest + httpx (TestClient) · uv для запуска.

**Спека:** `docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md` разделы 2, 3.

---

## Файловая структура

### Создать
- `backend/lib/__init__.py` — пустой
- `backend/lib/stats.py` — общие расчёты
- `backend/routes/dev_auth.py` — dev-picker, регистрируется только если `DEBUG`
- `backend/routes/dashboard.py` — `/dashboard/summary`
- `backend/routes/reports.py` — `/reports`
- `backend/routes/expenses.py` — CRUD
- `backend/routes/finance.py` — `/finance/summary`
- `backend/migrations/002_design_adapt.sql`
- `tests/__init__.py`
- `tests/conftest.py` — фикстура app+client с временной БД
- `tests/test_dev_auth.py`
- `tests/test_apartments.py`
- `tests/test_bookings.py`
- `tests/test_clients.py`
- `tests/test_dashboard.py`
- `tests/test_reports.py`
- `tests/test_expenses.py`
- `tests/test_finance.py`

### Изменить
- `pyproject.toml` — добавить `pytest`, `httpx` в dev-зависимости
- `backend/db.py` — track migrations через таблицу, идемпотентный applier
- `backend/main.py` — условная регистрация `dev_auth`, снять `auth`
- `backend/routes/apartments.py` — новые поля, `GET /{id}`, `GET /{id}/stats`, `?with_stats=1`
- `backend/routes/bookings.py` — `GET /{id}`, `GET /calendar`
- `backend/routes/clients.py` — `GET /{id}` с агрегатами

### Удалить
- `backend/routes/auth.py` — полностью (код переезжает в `dev_auth.py`)

---

## Phase 1 — Test infrastructure & идемпотентная миграция

### Task 1: Установить pytest + httpx

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Дописать dev-зависимости**

Заменить секцию `[project]` в `pyproject.toml`, добавить `[dependency-groups]`:

```toml
[project]
name = "fil-crm"
version = "0.1.0"
description = "CRM для посуточной аренды в Якутске"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "fastapi>=0.136.0",
    "uvicorn>=0.30.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.27.0",
]
```

- [ ] **Step 2: Синхронизировать**

Run: `uv sync --group dev`
Expected: устанавливает pytest и httpx без ошибок.

- [ ] **Step 3: Коммит**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: pytest + httpx в dev-группе"
```

---

### Task 2: Сделать `apply_migrations()` идемпотентным

**Files:**
- Modify: `backend/db.py`

- [ ] **Step 1: Переписать `db.py`**

```python
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_migrations() -> None:
    with get_conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_migrations ("
            "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
        )
        applied = {
            r["name"]
            for r in conn.execute("SELECT name FROM _schema_migrations").fetchall()
        }
        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if f.name in applied:
                continue
            conn.executescript(f.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO _schema_migrations(name) VALUES (?)", (f.name,)
            )
```

- [ ] **Step 2: Записать существующую `001_init.sql` как уже применённую**

Если у тебя локально есть `db.sqlite3`, то после миграции в нём не будет таблицы `_schema_migrations` и `001_init.sql` попытается применится повторно. Так как в ней `CREATE TABLE IF NOT EXISTS` — это безопасно, просто прогреется и запишется в трекинг.

Ничего делать не надо — следующий запуск сервера сам всё подтянет.

- [ ] **Step 3: Коммит**

```bash
git add backend/db.py
git commit -m "feat(db): идемпотентный applier миграций через _schema_migrations"
```

---

### Task 3: Миграция 002 — apartments-поля + expenses

**Files:**
- Create: `backend/migrations/002_design_adapt.sql`

- [ ] **Step 1: Создать файл миграции**

```sql
-- Расширение apartments: декоративные/классификационные поля
ALTER TABLE apartments ADD COLUMN cover_url TEXT;
ALTER TABLE apartments ADD COLUMN rooms TEXT;
ALTER TABLE apartments ADD COLUMN area_m2 INTEGER;
ALTER TABLE apartments ADD COLUMN floor TEXT;
ALTER TABLE apartments ADD COLUMN district TEXT;

-- Расходы — отдельная сущность для /finance
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount INTEGER NOT NULL,
    category TEXT NOT NULL,
    description TEXT,
    occurred_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_expenses_occurred ON expenses(occurred_at);
```

- [ ] **Step 2: Убедиться, что миграция применяется**

Run: `rm -f /tmp/fil_crm_test.sqlite3 && FIL_DB_PATH=/tmp/fil_crm_test.sqlite3 uv run --env-file .env python -c "from backend.db import apply_migrations; apply_migrations()" 2>&1`

Expected: тишина (нет исключений). (Примечание: Task 4 добавит поддержку `FIL_DB_PATH`; пока можно просто удалить основной `db.sqlite3` и дать новому создаться заново).

Более простая проверка:
Run: `rm -f db.sqlite3 && uv run --env-file .env python -c "from backend.db import apply_migrations; apply_migrations()"`
Expected: создаёт `db.sqlite3` без исключений.

- [ ] **Step 3: Проверить колонки и таблицу**

Run: `uv run --env-file .env python -c "import sqlite3; c = sqlite3.connect('db.sqlite3'); print(c.execute('PRAGMA table_info(apartments)').fetchall()); print(c.execute('PRAGMA table_info(expenses)').fetchall())"`

Expected: в `apartments` есть cover_url, rooms, area_m2, floor, district; таблица `expenses` есть с нужными полями.

- [ ] **Step 4: Коммит**

```bash
git add backend/migrations/002_design_adapt.sql
git commit -m "feat(db): миграция 002 — apartments-обогащение + expenses"
```

---

### Task 4: Поддержка `FIL_DB_PATH` для тестов

**Files:**
- Modify: `backend/db.py`

- [ ] **Step 1: Разрешить переопределение пути БД через env**

Заменить начало файла:

```python
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

_DEFAULT_DB = Path(__file__).resolve().parent.parent / "db.sqlite3"


def _db_path() -> Path:
    return Path(os.environ.get("FIL_DB_PATH", str(_DEFAULT_DB)))


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
```

`apply_migrations()` оставить как есть.

- [ ] **Step 2: Проверить, что сервер по-прежнему пишет в основной файл**

Run: `ls -la db.sqlite3`
Expected: файл не пустой.

- [ ] **Step 3: Коммит**

```bash
git add backend/db.py
git commit -m "feat(db): переопределение пути БД через FIL_DB_PATH"
```

---

### Task 5: Создать `tests/conftest.py` и «dim-тест»

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: `tests/__init__.py`**

Пустой файл.

- [ ] **Step 2: `tests/conftest.py`**

```python
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
```

- [ ] **Step 3: `tests/test_smoke.py`**

```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_tmp_db_isolated(client, tmp_db):
    assert tmp_db.exists()
    # Seed и проверка — БД пустая изначально
    import sqlite3

    with sqlite3.connect(str(tmp_db)) as conn:
        rows = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        assert rows[0] == 0
```

- [ ] **Step 4: Запустить**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: 2 passed.

- [ ] **Step 5: Коммит**

```bash
git add tests/__init__.py tests/conftest.py tests/test_smoke.py
git commit -m "test: conftest — tmp-db + client, smoke-тест /health"
```

---

## Phase 2 — Dev auth

### Task 6: Red — тест на `/dev_auth/*`

**Files:**
- Create: `tests/test_dev_auth.py`

- [ ] **Step 1: Написать провальные тесты**

```python
from tests.conftest import seed_user


def test_dev_auth_users_lists(client):
    seed_user(client, role="owner", name="Айсен")
    seed_user(client, role="maid", name="Анна")
    r = client.get("/dev_auth/users")
    assert r.status_code == 200
    data = r.json()
    assert {u["full_name"] for u in data} == {"Айсен", "Анна"}
    assert all("role" in u and "id" in u for u in data)


def test_dev_auth_login_ok(client):
    u = seed_user(client, role="admin", name="Дарья")
    r = client.post("/dev_auth/login", json={"user_id": u["id"]})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Дарья"
    assert r.json()["role"] == "admin"


def test_dev_auth_login_not_found(client):
    r = client.post("/dev_auth/login", json={"user_id": 9999})
    assert r.status_code == 404


def test_dev_auth_gated_by_debug(monkeypatch, tmp_db):
    monkeypatch.delenv("DEBUG", raising=False)
    import importlib

    import backend.main as main_mod

    importlib.reload(main_mod)
    from fastapi.testclient import TestClient

    with TestClient(main_mod.app) as c:
        r = c.get("/dev_auth/users")
        assert r.status_code == 404
```

- [ ] **Step 2: Запустить — убедиться, что падает**

Run: `uv run pytest tests/test_dev_auth.py -v`
Expected: FAIL (все тесты — путь `/dev_auth/*` не найден).

- [ ] **Step 3: Не коммитим**

Красные тесты остаются в рабочей копии, коммитим вместе с реализацией.

---

### Task 7: Green — реализовать `backend/routes/dev_auth.py`

**Files:**
- Create: `backend/routes/dev_auth.py`
- Modify: `backend/main.py`
- Delete: `backend/routes/auth.py`

- [ ] **Step 1: Создать `dev_auth.py`**

```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.db import get_conn

router = APIRouter(prefix="/dev_auth", tags=["dev_auth"])


class LoginIn(BaseModel):
    user_id: int


@router.get("/users")
def list_users_for_login():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, role FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/login")
def login(payload: LoginIn):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, full_name, role FROM users WHERE id = ?",
            (payload.user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return dict(row)
```

- [ ] **Step 2: Обновить `backend/main.py`**

```python
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import apply_migrations
from backend.routes import users as users_routes
from backend.routes import apartments as apartments_routes
from backend.routes import clients as clients_routes
from backend.routes import bookings as bookings_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    apply_migrations()
    yield


app = FastAPI(title="fil-crm", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.environ.get("DEBUG"):
    from backend.routes import dev_auth as dev_auth_routes

    app.include_router(dev_auth_routes.router)

app.include_router(users_routes.router)
app.include_router(apartments_routes.router)
app.include_router(clients_routes.router)
app.include_router(bookings_routes.router)


@app.get("/health")
def health():
    return {"ok": True}
```

- [ ] **Step 3: Удалить старый `auth.py`**

Run: `rm backend/routes/auth.py`

- [ ] **Step 4: Запустить тесты**

Run: `uv run pytest tests/test_dev_auth.py -v`
Expected: 4 passed.

- [ ] **Step 5: Коммит**

```bash
git add backend/routes/dev_auth.py backend/routes/auth.py backend/main.py tests/test_dev_auth.py
git commit -m "feat(auth): /dev_auth под DEBUG-гейтом; удалён публичный /auth"
```

---

## Phase 3 — Apartments

### Task 8: Red — тест: новые поля в `/apartments` CRUD

**Files:**
- Create: `tests/test_apartments.py`

- [ ] **Step 1: Тест создания/патча с новыми полями**

```python
from tests.conftest import auth, seed_user


def _owner(client):
    return seed_user(client, role="owner", name="Айсен")


def test_create_apartment_with_new_fields(client):
    u = _owner(client)
    r = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "Лермонтова 58/24",
            "address": "ул. Лермонтова, 58, кв. 24",
            "price_per_night": 4280,
            "rooms": "2-комн",
            "area_m2": 52,
            "floor": "3/5",
            "district": "Сайсары",
            "cover_url": "https://example.com/cover.jpg",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["rooms"] == "2-комн"
    assert body["area_m2"] == 52
    assert body["floor"] == "3/5"
    assert body["district"] == "Сайсары"
    assert body["cover_url"] == "https://example.com/cover.jpg"


def test_patch_apartment_updates_new_fields(client):
    u = _owner(client)
    created = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "A",
            "address": "addr",
            "price_per_night": 1000,
        },
    ).json()
    r = client.patch(
        f"/apartments/{created['id']}",
        headers=auth(u["id"]),
        json={"rooms": "Студия", "area_m2": 28, "district": "центр"},
    )
    assert r.status_code == 200
    assert r.json()["rooms"] == "Студия"
    assert r.json()["area_m2"] == 28
    assert r.json()["district"] == "центр"


def test_get_apartment_by_id(client):
    u = _owner(client)
    created = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 1000},
    ).json()
    r = client.get(f"/apartments/{created['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_apartment_by_id_404(client):
    u = _owner(client)
    r = client.get("/apartments/9999", headers=auth(u["id"]))
    assert r.status_code == 404
```

- [ ] **Step 2: Запустить — убедиться, что падают**

Run: `uv run pytest tests/test_apartments.py -v`
Expected: 3 fails (новые поля не принимаются / игнорируются; `GET /{id}` отсутствует).

---

### Task 9: Green — расширить `routes/apartments.py`

**Files:**
- Modify: `backend/routes/apartments.py`

- [ ] **Step 1: Обновить pydantic-модели и добавить `GET /{id}`**

Полностью заменить файл:

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/apartments", tags=["apartments"])


class ApartmentIn(BaseModel):
    title: str = Field(min_length=1)
    address: str = Field(min_length=1)
    price_per_night: int = Field(gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    cover_url: str | None = None


class ApartmentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    price_per_night: int | None = Field(default=None, gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    cover_url: str | None = None


SELECT_FIELDS = (
    "id, title, address, price_per_night, needs_cleaning, "
    "cover_url, rooms, area_m2, floor, district, created_at"
)


def _row(conn, apt_id: int):
    return conn.execute(
        f"SELECT {SELECT_FIELDS} FROM apartments WHERE id = ?", (apt_id,)
    ).fetchone()


@router.get("")
def list_apartments(_: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {SELECT_FIELDS} FROM apartments ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/cleaning")
def list_apartments_needing_cleaning(
    _: dict = Depends(require_role("owner", "admin", "maid")),
):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {SELECT_FIELDS} FROM apartments WHERE needs_cleaning = 1 ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{apt_id}")
def get_apartment(
    apt_id: int, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        row = _row(conn, apt_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Квартира не найдена")
    return dict(row)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_apartment(
    payload: ApartmentIn, _: dict = Depends(require_role("owner", "admin"))
):
    fields = payload.model_dump()
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    with get_conn() as conn:
        cur = conn.execute(
            f"INSERT INTO apartments ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )
        row = _row(conn, cur.lastrowid)
    return dict(row)


@router.patch("/{apt_id}")
def update_apartment(
    apt_id: int,
    payload: ApartmentPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления"
        )
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [apt_id]
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE apartments SET {set_clause} WHERE id = ?", values
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)


@router.delete("/{apt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_apartment(apt_id: int, _: dict = Depends(require_role("owner", "admin"))):
    import sqlite3

    try:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM apartments WHERE id = ?", (apt_id,))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
                )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить квартиру с привязанными бронями",
        )
    return None


@router.post("/{apt_id}/mark-dirty")
def mark_dirty(apt_id: int, _: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 1 WHERE id = ?", (apt_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)


@router.post("/{apt_id}/mark-clean")
def mark_clean(apt_id: int, _: dict = Depends(require_role("owner", "admin", "maid"))):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 0 WHERE id = ?", (apt_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)
```

- [ ] **Step 2: Запустить тесты**

Run: `uv run pytest tests/test_apartments.py -v`
Expected: 4 passed.

- [ ] **Step 3: Коммит**

```bash
git add backend/routes/apartments.py tests/test_apartments.py
git commit -m "feat(apartments): новые поля + GET /{id}"
```

---

### Task 10: Общие расчёты — `backend/lib/stats.py`

**Files:**
- Create: `backend/lib/__init__.py`
- Create: `backend/lib/stats.py`
- Create: `tests/test_stats.py`

- [ ] **Step 1: `backend/lib/__init__.py`** — пустой.

- [ ] **Step 2: Red — тесты помощников**

```python
# tests/test_stats.py
from datetime import date

from backend.lib.stats import (
    month_bounds,
    overlap_nights,
    aggregate_bookings_in_period,
)


def test_month_bounds_april():
    ci, co = month_bounds("2026-04")
    assert ci == date(2026, 4, 1)
    assert co == date(2026, 5, 1)


def test_month_bounds_december():
    ci, co = month_bounds("2026-12")
    assert ci == date(2026, 12, 1)
    assert co == date(2027, 1, 1)


def test_overlap_full_inside():
    # booking 10.04 → 13.04, period апрель
    n = overlap_nights(
        date(2026, 4, 10), date(2026, 4, 13),
        date(2026, 4, 1), date(2026, 5, 1),
    )
    assert n == 3


def test_overlap_partial_before_period():
    # booking 30.03 → 03.04, period апрель
    n = overlap_nights(
        date(2026, 3, 30), date(2026, 4, 3),
        date(2026, 4, 1), date(2026, 5, 1),
    )
    assert n == 2


def test_overlap_no_intersection():
    n = overlap_nights(
        date(2026, 3, 1), date(2026, 3, 31),
        date(2026, 4, 1), date(2026, 5, 1),
    )
    assert n == 0


def test_aggregate_bookings_basic():
    # Одна бронь 3 ночи, одна 2 ночи — все в апреле
    bookings = [
        {"check_in": "2026-04-10", "check_out": "2026-04-13", "total_price": 12840, "status": "active"},
        {"check_in": "2026-04-20", "check_out": "2026-04-22", "total_price": 9600, "status": "completed"},
    ]
    agg = aggregate_bookings_in_period(bookings, date(2026, 4, 1), date(2026, 5, 1))
    assert agg["nights"] == 5
    assert agg["revenue"] == 12840 + 9600
    assert agg["adr"] == round((12840 + 9600) / 5)


def test_aggregate_skips_cancelled():
    bookings = [
        {"check_in": "2026-04-10", "check_out": "2026-04-13", "total_price": 12840, "status": "cancelled"},
    ]
    agg = aggregate_bookings_in_period(bookings, date(2026, 4, 1), date(2026, 5, 1))
    assert agg["nights"] == 0
    assert agg["revenue"] == 0
    assert agg["adr"] == 0
```

- [ ] **Step 3: Убедиться, что падает**

Run: `uv run pytest tests/test_stats.py -v`
Expected: ModuleNotFoundError / failures.

- [ ] **Step 4: Green — реализовать `backend/lib/stats.py`**

```python
from calendar import monthrange
from datetime import date, datetime


def month_bounds(month: str) -> tuple[date, date]:
    """'2026-04' → (date(2026,4,1), date(2026,5,1))"""
    y, m = (int(x) for x in month.split("-"))
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, m + 1, 1)
    return start, end


def parse_date(d: str | date) -> date:
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(d).date()


def overlap_nights(ci: str | date, co: str | date, p_start: date, p_end: date) -> int:
    ci_d, co_d = parse_date(ci), parse_date(co)
    start = max(ci_d, p_start)
    end = min(co_d, p_end)
    delta = (end - start).days
    return max(0, delta)


def aggregate_bookings_in_period(bookings, p_start: date, p_end: date) -> dict:
    nights = 0
    revenue = 0
    for b in bookings:
        if b.get("status") == "cancelled":
            continue
        total_nights_full = (parse_date(b["check_out"]) - parse_date(b["check_in"])).days
        if total_nights_full <= 0:
            continue
        night_in_period = overlap_nights(
            b["check_in"], b["check_out"], p_start, p_end
        )
        if night_in_period == 0:
            continue
        nights += night_in_period
        # Пропорциональная выручка
        revenue += round(b["total_price"] * night_in_period / total_nights_full)
    adr = round(revenue / nights) if nights else 0
    return {"nights": nights, "revenue": revenue, "adr": adr}


def days_in_month(month: str) -> int:
    y, m = (int(x) for x in month.split("-"))
    return monthrange(y, m)[1]
```

- [ ] **Step 5: Убедиться, что всё зелёное**

Run: `uv run pytest tests/test_stats.py -v`
Expected: 7 passed.

- [ ] **Step 6: Коммит**

```bash
git add backend/lib/__init__.py backend/lib/stats.py tests/test_stats.py
git commit -m "feat(lib): stats helpers — month_bounds, overlap_nights, aggregate"
```

---

### Task 11: Red+Green — `GET /apartments/{id}/stats` и `?with_stats=1`

**Files:**
- Modify: `backend/routes/apartments.py`
- Modify: `tests/test_apartments.py`

- [ ] **Step 1: Red — добавить тесты**

В конец `tests/test_apartments.py`:

```python
def _apt_with_price(client, u_id: int, price: int) -> dict:
    return client.post(
        "/apartments",
        headers=auth(u_id),
        json={"title": "A", "address": "addr", "price_per_night": price},
    ).json()


def _client_and_booking(client, u_id: int, apt_id: int, ci: str, co: str, total: int, status_: str = "active"):
    cl = client.post(
        "/clients",
        headers=auth(u_id),
        json={"full_name": "Гость", "phone": "+7 000"},
    ).json()
    b = client.post(
        "/bookings",
        headers=auth(u_id),
        json={
            "apartment_id": apt_id,
            "client_id": cl["id"],
            "check_in": ci,
            "check_out": co,
            "total_price": total,
        },
    ).json()
    if status_ != "active":
        client.patch(f"/bookings/{b['id']}", headers=auth(u_id), json={"status": status_})
    return b


def test_apartment_stats_empty_month(client):
    u = _owner(client)
    apt = _apt_with_price(client, u["id"], 4000)
    r = client.get(
        f"/apartments/{apt['id']}/stats?month=2026-04", headers=auth(u["id"])
    )
    assert r.status_code == 200
    body = r.json()
    assert body["nights"] == 0
    assert body["revenue"] == 0
    assert body["adr"] == 0
    assert body["utilization"] == 0.0


def test_apartment_stats_one_booking(client):
    u = _owner(client)
    apt = _apt_with_price(client, u["id"], 4000)
    _client_and_booking(client, u["id"], apt["id"], "2026-04-10", "2026-04-13", 12000)
    r = client.get(
        f"/apartments/{apt['id']}/stats?month=2026-04", headers=auth(u["id"])
    )
    body = r.json()
    assert body["nights"] == 3
    assert body["revenue"] == 12000
    assert body["adr"] == 4000
    # 3 / 30 = 0.1
    assert abs(body["utilization"] - 0.1) < 1e-6


def test_list_with_stats_includes_utilization_and_status(client):
    u = _owner(client)
    apt = _apt_with_price(client, u["id"], 4000)
    _client_and_booking(client, u["id"], apt["id"], "2026-04-10", "2026-04-13", 12000)
    r = client.get(
        "/apartments?with_stats=1&month=2026-04", headers=auth(u["id"])
    )
    assert r.status_code == 200
    row = next(a for a in r.json() if a["id"] == apt["id"])
    assert row["utilization"] > 0
    assert row["status"] in ("occupied", "free", "needs_cleaning")
```

- [ ] **Step 2: Запустить (падает)**

Run: `uv run pytest tests/test_apartments.py -v`
Expected: 3 new fails.

- [ ] **Step 3: Green — дописать `apartments.py`**

В `list_apartments` заменить сигнатуру и тело на:

```python
@router.get("")
def list_apartments(
    with_stats: int = Query(0),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {SELECT_FIELDS} FROM apartments ORDER BY id"
        ).fetchall()
        apts = [dict(r) for r in rows]
        if not with_stats:
            return apts
        from datetime import date

        from backend.lib.stats import (
            aggregate_bookings_in_period,
            days_in_month,
            month_bounds,
        )

        month = month or date.today().strftime("%Y-%m")
        p_start, p_end = month_bounds(month)
        dim = days_in_month(month)
        today = date.today().isoformat()
        for a in apts:
            bookings = conn.execute(
                "SELECT check_in, check_out, total_price, status FROM bookings WHERE apartment_id = ?",
                (a["id"],),
            ).fetchall()
            bookings = [dict(b) for b in bookings]
            agg = aggregate_bookings_in_period(bookings, p_start, p_end)
            a["nights"] = agg["nights"]
            a["revenue"] = agg["revenue"]
            a["adr"] = agg["adr"]
            a["utilization"] = round(agg["nights"] / dim, 4) if dim else 0.0
            # Статус: если есть бронь где check_in<=today<check_out и status='active' — occupied;
            # иначе если needs_cleaning=1 — needs_cleaning; иначе free.
            is_occupied = any(
                b["status"] == "active"
                and b["check_in"] <= today < b["check_out"]
                for b in bookings
            )
            if is_occupied:
                a["status"] = "occupied"
            elif a["needs_cleaning"]:
                a["status"] = "needs_cleaning"
            else:
                a["status"] = "free"
    return apts
```

Добавить ниже новый endpoint `/stats`:

```python
@router.get("/{apt_id}/stats")
def apartment_stats(
    apt_id: int,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    from datetime import date

    from backend.lib.stats import (
        aggregate_bookings_in_period,
        days_in_month,
        month_bounds,
    )

    month = month or date.today().strftime("%Y-%m")
    p_start, p_end = month_bounds(month)
    dim = days_in_month(month)
    with get_conn() as conn:
        if _row(conn, apt_id) is None:
            raise HTTPException(status_code=404, detail="Квартира не найдена")
        rows = conn.execute(
            "SELECT check_in, check_out, total_price, status FROM bookings WHERE apartment_id = ?",
            (apt_id,),
        ).fetchall()
    bookings = [dict(r) for r in rows]
    agg = aggregate_bookings_in_period(bookings, p_start, p_end)
    agg["utilization"] = round(agg["nights"] / dim, 4) if dim else 0.0
    return agg
```

- [ ] **Step 4: Зелёные тесты**

Run: `uv run pytest tests/test_apartments.py -v`
Expected: 7 passed.

- [ ] **Step 5: Коммит**

```bash
git add backend/routes/apartments.py tests/test_apartments.py
git commit -m "feat(apartments): /{id}/stats + ?with_stats=1 на списке"
```

---

## Phase 4 — Bookings

### Task 12: Red+Green — `GET /bookings/{id}`

**Files:**
- Modify: `backend/routes/bookings.py`
- Create: `tests/test_bookings.py`

- [ ] **Step 1: Создать `tests/test_bookings.py`**

```python
from tests.conftest import auth, seed_user


def _prep(client):
    u = seed_user(client, role="owner", name="Айсен")
    a = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    c = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7 000"},
    ).json()
    return u, a, c


def test_get_booking_by_id(client):
    u, a, c = _prep(client)
    b = client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
        },
    ).json()
    r = client.get(f"/bookings/{b['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == b["id"]
    assert body["apartment_title"] == "A"
    assert body["client_name"] == "Смирнов"


def test_get_booking_404(client):
    u, _, _ = _prep(client)
    r = client.get("/bookings/9999", headers=auth(u["id"]))
    assert r.status_code == 404


def test_bookings_calendar_returns_groups(client):
    u, a, c = _prep(client)
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
        },
    )
    r = client.get(
        "/bookings/calendar?from=2026-04-21&to=2026-05-05",
        headers=auth(u["id"]),
    )
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    apt_entry = next(e for e in body if e["apartment_id"] == a["id"])
    assert len(apt_entry["bookings"]) == 1
    assert apt_entry["bookings"][0]["status"] == "active"
```

- [ ] **Step 2: Red**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: 3 fails.

- [ ] **Step 3: Дописать `backend/routes/bookings.py`**

Добавить в конец файла:

```python
@router.get("/calendar")
def bookings_calendar(
    from_: str = Query(..., alias="from", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    to: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        apartments = conn.execute(
            "SELECT id, title FROM apartments ORDER BY id"
        ).fetchall()
        bookings = conn.execute(
            """
            SELECT b.id, b.apartment_id, b.check_in, b.check_out, b.status,
                   c.full_name AS client_name
            FROM bookings b
            JOIN clients c ON c.id = b.client_id
            WHERE b.status != 'cancelled'
              AND b.check_in < ? AND b.check_out > ?
            ORDER BY b.check_in
            """,
            (to, from_),
        ).fetchall()
    buckets = {a["id"]: {"apartment_id": a["id"], "apartment_title": a["title"], "bookings": []}
               for a in apartments}
    for b in bookings:
        buckets[b["apartment_id"]]["bookings"].append(
            {
                "id": b["id"],
                "client_name": b["client_name"],
                "check_in": b["check_in"],
                "check_out": b["check_out"],
                "status": b["status"],
            }
        )
    return list(buckets.values())


@router.get("/{booking_id}")
def get_booking(
    booking_id: int, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        row = _row(conn, booking_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    return dict(row)
```

В шапке файла добавить `Query` в импорт:
```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
```

- [ ] **Step 4: Зелёные тесты**

Run: `uv run pytest tests/test_bookings.py -v`
Expected: 3 passed.

Примечание: `/calendar` должен быть зарегистрирован **до** `/{booking_id}` чтобы не попасть в catch-all. FastAPI принимает в порядке определения, поэтому `GET /calendar` идёт **перед** `GET /{booking_id}` в коде.

- [ ] **Step 5: Коммит**

```bash
git add backend/routes/bookings.py tests/test_bookings.py
git commit -m "feat(bookings): GET /{id} и GET /calendar"
```

---

## Phase 5 — Clients

### Task 13: Red+Green — `GET /clients/{id}` с историей

**Files:**
- Modify: `backend/routes/clients.py`
- Create: `tests/test_clients.py`

- [ ] **Step 1: Тесты**

```python
# tests/test_clients.py
from tests.conftest import auth, seed_user


def test_get_client_with_history(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7 914 330 05 12"},
    ).json()
    for ci, co, total in [
        ("2026-01-10", "2026-01-12", 8000),
        ("2026-02-15", "2026-02-18", 12000),
        ("2026-04-21", "2026-04-24", 12840),
    ]:
        client.post(
            "/bookings",
            headers=auth(u["id"]),
            json={
                "apartment_id": apt["id"],
                "client_id": cl["id"],
                "check_in": ci,
                "check_out": co,
                "total_price": total,
            },
        )
    r = client.get(f"/clients/{cl['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == cl["id"]
    assert body["full_name"] == "Смирнов"
    assert body["stats"]["count"] == 3
    assert body["stats"]["nights"] == 2 + 3 + 3
    assert body["stats"]["revenue"] == 8000 + 12000 + 12840
    assert len(body["bookings"]) == 3
    assert body["bookings"][0]["apartment_title"] == "A"


def test_get_client_404(client):
    u = seed_user(client, role="owner")
    r = client.get("/clients/9999", headers=auth(u["id"]))
    assert r.status_code == 404
```

- [ ] **Step 2: Red**

Run: `uv run pytest tests/test_clients.py -v`
Expected: 2 fails (endpoint отсутствует).

- [ ] **Step 3: Дописать `backend/routes/clients.py`**

Добавить в конец:

```python
@router.get("/{client_id}")
def get_client(
    client_id: int, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        row = _row(conn, client_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Клиент не найден")
        bookings = conn.execute(
            """
            SELECT b.id, b.check_in, b.check_out, b.total_price, b.status,
                   a.title AS apartment_title, a.id AS apartment_id
            FROM bookings b JOIN apartments a ON a.id = b.apartment_id
            WHERE b.client_id = ?
            ORDER BY b.check_in DESC
            """,
            (client_id,),
        ).fetchall()
    bookings = [dict(b) for b in bookings]
    active_count = sum(1 for b in bookings if b["status"] != "cancelled")
    nights = sum(
        (_date(b["check_out"]) - _date(b["check_in"])).days
        for b in bookings
        if b["status"] != "cancelled"
    )
    revenue = sum(b["total_price"] for b in bookings if b["status"] != "cancelled")
    return {
        **dict(row),
        "bookings": bookings,
        "stats": {"count": active_count, "nights": nights, "revenue": revenue},
    }
```

В шапке файла добавить импорт:
```python
from backend.lib.stats import parse_date as _date
```

- [ ] **Step 4: Зелёные тесты**

Run: `uv run pytest tests/test_clients.py -v`
Expected: 2 passed.

- [ ] **Step 5: Коммит**

```bash
git add backend/routes/clients.py tests/test_clients.py
git commit -m "feat(clients): GET /{id} с историей броней и агрегатами"
```

---

## Phase 6 — Dashboard / Reports / Expenses / Finance

### Task 14: Red+Green — `GET /dashboard/summary`

**Files:**
- Create: `backend/routes/dashboard.py`
- Modify: `backend/main.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Тест**

```python
# tests/test_dashboard.py
from tests.conftest import auth, seed_user


def test_dashboard_summary_shape(client):
    u = seed_user(client, role="owner")
    r = client.get("/dashboard/summary", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    # Shape: occupancy, revenue_mtd, revenue_prev_month, daily_series, today_events
    assert "occupancy" in body
    assert set(body["occupancy"]) == {"occupied", "total"}
    assert "revenue_mtd" in body
    assert "revenue_prev_month" in body
    assert isinstance(body["daily_series"], list)
    assert isinstance(body["today_events"], list)


def test_dashboard_summary_with_data(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7 000"},
    ).json()
    # В текущем тестовом контексте today ≈ реальное время. Создадим бронь на «сегодня».
    from datetime import date, timedelta

    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=3)).isoformat()
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": apt["id"],
            "client_id": cl["id"],
            "check_in": today,
            "check_out": tomorrow,
            "total_price": 12000,
        },
    )
    r = client.get("/dashboard/summary", headers=auth(u["id"]))
    body = r.json()
    assert body["occupancy"]["total"] == 1
    assert body["occupancy"]["occupied"] == 1
    # Сегодня есть заезд
    assert any(e["kind"] == "check_in" for e in body["today_events"])
```

- [ ] **Step 2: Red**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: 2 fails (404).

- [ ] **Step 3: `backend/routes/dashboard.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends

from backend.auth import require_role
from backend.db import get_conn
from backend.lib.stats import (
    aggregate_bookings_in_period,
    days_in_month,
    month_bounds,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _prev_month(ym: str) -> str:
    y, m = (int(x) for x in ym.split("-"))
    if m == 1:
        return f"{y - 1}-12"
    return f"{y}-{m - 1:02d}"


@router.get("/summary")
def summary(_: dict = Depends(require_role("owner", "admin"))):
    today = date.today()
    ym = today.strftime("%Y-%m")
    p_start, p_end = month_bounds(ym)
    prev_start, prev_end = month_bounds(_prev_month(ym))
    with get_conn() as conn:
        apt_total = conn.execute("SELECT COUNT(*) FROM apartments").fetchone()[0]
        occupied = conn.execute(
            "SELECT COUNT(DISTINCT apartment_id) FROM bookings "
            "WHERE status='active' AND check_in <= ? AND check_out > ?",
            (today.isoformat(), today.isoformat()),
        ).fetchone()[0]
        # Вытаскиваем все брони, которые могут попасть в текущий или прошлый месяц
        rows = conn.execute(
            "SELECT check_in, check_out, total_price, status FROM bookings "
            "WHERE check_out > ? AND check_in < ?",
            (prev_start.isoformat(), p_end.isoformat()),
        ).fetchall()
        bookings = [dict(r) for r in rows]
        events_rows = conn.execute(
            """
            SELECT b.id, b.check_in, b.check_out, b.total_price, b.status,
                   c.full_name AS client_name, a.title AS apartment_title, a.address AS apartment_address
            FROM bookings b
            JOIN clients c ON c.id = b.client_id
            JOIN apartments a ON a.id = b.apartment_id
            WHERE b.status != 'cancelled'
              AND (b.check_in = ? OR b.check_out = ?)
            ORDER BY b.check_in
            """,
            (today.isoformat(), today.isoformat()),
        ).fetchall()

    revenue_mtd = aggregate_bookings_in_period(bookings, p_start, p_end)["revenue"]
    revenue_prev = aggregate_bookings_in_period(bookings, prev_start, prev_end)["revenue"]

    # Дневной ряд — выручка по дням месяца
    dim = days_in_month(ym)
    daily = [0] * dim
    for b in bookings:
        if b["status"] == "cancelled":
            continue
        from backend.lib.stats import parse_date

        ci, co = parse_date(b["check_in"]), parse_date(b["check_out"])
        nights_full = (co - ci).days
        if nights_full <= 0:
            continue
        per_night = b["total_price"] / nights_full
        # Распределяем per_night по дням, входящим в месяц
        d = ci
        while d < co:
            if p_start <= d < p_end:
                daily[d.day - 1] += round(per_night)
            d = date.fromordinal(d.toordinal() + 1)
        # (parse_date для check_in/check_out уже вызвана выше)

    today_events = []
    for r in events_rows:
        if r["check_in"] == today.isoformat():
            today_events.append(
                {
                    "booking_id": r["id"],
                    "kind": "check_in",
                    "time": "14:00",
                    "client_name": r["client_name"],
                    "apartment_title": r["apartment_title"],
                    "apartment_address": r["apartment_address"],
                    "total_price": r["total_price"],
                    "status": r["status"],
                }
            )
        if r["check_out"] == today.isoformat():
            today_events.append(
                {
                    "booking_id": r["id"],
                    "kind": "check_out",
                    "time": "12:00",
                    "client_name": r["client_name"],
                    "apartment_title": r["apartment_title"],
                    "apartment_address": r["apartment_address"],
                    "total_price": r["total_price"],
                    "status": r["status"],
                }
            )

    return {
        "occupancy": {"occupied": occupied, "total": apt_total},
        "revenue_mtd": revenue_mtd,
        "revenue_prev_month": revenue_prev,
        "daily_series": daily,
        "today_events": today_events,
        "month": ym,
    }
```

- [ ] **Step 4: Зарегистрировать в `main.py`**

Добавить:
```python
from backend.routes import dashboard as dashboard_routes
app.include_router(dashboard_routes.router)
```

- [ ] **Step 5: Green**

Run: `uv run pytest tests/test_dashboard.py -v`
Expected: 2 passed.

- [ ] **Step 6: Коммит**

```bash
git add backend/routes/dashboard.py backend/main.py tests/test_dashboard.py
git commit -m "feat(dashboard): GET /dashboard/summary"
```

---

### Task 15: Red+Green — `GET /reports`

**Files:**
- Create: `backend/routes/reports.py`
- Modify: `backend/main.py`
- Create: `tests/test_reports.py`

- [ ] **Step 1: Тест**

```python
# tests/test_reports.py
from datetime import date, timedelta

from tests.conftest import auth, seed_user


def test_reports_month_empty(client):
    u = seed_user(client, role="owner")
    r = client.get("/reports?period=month", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert set(body) >= {
        "period",
        "from",
        "to",
        "occupancy",
        "adr",
        "revpar",
        "avg_nights",
        "per_apartment",
    }
    assert body["period"] == "month"


def test_reports_month_with_data(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "Смирнов", "phone": "+7"},
    ).json()
    today = date.today()
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": apt["id"],
            "client_id": cl["id"],
            "check_in": today.isoformat(),
            "check_out": (today + timedelta(days=3)).isoformat(),
            "total_price": 12000,
        },
    )
    r = client.get("/reports?period=month", headers=auth(u["id"]))
    body = r.json()
    assert body["adr"] > 0
    per = body["per_apartment"]
    assert per[0]["apartment_id"] == apt["id"]
    assert per[0]["util"] > 0
```

- [ ] **Step 2: Red**

Run: `uv run pytest tests/test_reports.py -v`
Expected: fails (404).

- [ ] **Step 3: `backend/routes/reports.py`**

```python
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from backend.auth import require_role
from backend.db import get_conn
from backend.lib.stats import aggregate_bookings_in_period

router = APIRouter(prefix="/reports", tags=["reports"])


def _period_bounds(period: str) -> tuple[date, date]:
    today = date.today()
    if period == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
    elif period == "quarter":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        start = date(today.year, q_start_month, 1)
        end_m = q_start_month + 3
        end_y = today.year + (1 if end_m > 12 else 0)
        end = date(end_y, ((end_m - 1) % 12) + 1, 1)
    elif period == "year":
        start = date(today.year, 1, 1)
        end = date(today.year + 1, 1, 1)
    else:  # month (default)
        start = date(today.year, today.month, 1)
        if today.month == 12:
            end = date(today.year + 1, 1, 1)
        else:
            end = date(today.year, today.month + 1, 1)
    return start, end


@router.get("")
def reports(
    period: str = Query("month", pattern=r"^(week|month|quarter|year)$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    p_start, p_end = _period_bounds(period)
    days = (p_end - p_start).days
    with get_conn() as conn:
        apts = conn.execute("SELECT id, title FROM apartments ORDER BY id").fetchall()
        all_bookings = conn.execute(
            "SELECT apartment_id, check_in, check_out, total_price, status FROM bookings "
            "WHERE check_out > ? AND check_in < ? AND status != 'cancelled'",
            (p_start.isoformat(), p_end.isoformat()),
        ).fetchall()
    by_apt: dict[int, list] = {}
    for b in all_bookings:
        by_apt.setdefault(b["apartment_id"], []).append(dict(b))

    total_nights = 0
    total_revenue = 0
    total_bookings = 0
    nights_sum_for_avg = 0
    per_apartment = []
    total_avail = len(apts) * days
    for a in apts:
        bookings = by_apt.get(a["id"], [])
        agg = aggregate_bookings_in_period(bookings, p_start, p_end)
        util = round(agg["nights"] / days, 4) if days else 0.0
        per_apartment.append(
            {
                "apartment_id": a["id"],
                "title": a["title"],
                "util": util,
                "nights": agg["nights"],
                "revenue": agg["revenue"],
            }
        )
        total_nights += agg["nights"]
        total_revenue += agg["revenue"]
        total_bookings += len(bookings)
        nights_sum_for_avg += sum(
            (
                (_parse_d(b["check_out"]) - _parse_d(b["check_in"])).days
                for b in bookings
            )
        )
    occupancy = round(total_nights / total_avail, 4) if total_avail else 0.0
    adr = round(total_revenue / total_nights) if total_nights else 0
    revpar = round(total_revenue / total_avail) if total_avail else 0
    avg_nights = round(nights_sum_for_avg / total_bookings, 2) if total_bookings else 0.0

    return {
        "period": period,
        "from": p_start.isoformat(),
        "to": p_end.isoformat(),
        "occupancy": occupancy,
        "adr": adr,
        "revpar": revpar,
        "avg_nights": avg_nights,
        "per_apartment": per_apartment,
    }


def _parse_d(s: str):
    from datetime import datetime

    return datetime.fromisoformat(s).date()
```

- [ ] **Step 4: Регистрация в `main.py`**

```python
from backend.routes import reports as reports_routes
app.include_router(reports_routes.router)
```

- [ ] **Step 5: Green**

Run: `uv run pytest tests/test_reports.py -v`
Expected: 2 passed.

- [ ] **Step 6: Коммит**

```bash
git add backend/routes/reports.py backend/main.py tests/test_reports.py
git commit -m "feat(reports): GET /reports с period=week|month|quarter|year"
```

---

### Task 16: Red+Green — `/expenses` CRUD

**Files:**
- Create: `backend/routes/expenses.py`
- Modify: `backend/main.py`
- Create: `tests/test_expenses.py`

- [ ] **Step 1: Тесты**

```python
# tests/test_expenses.py
from tests.conftest import auth, seed_user


def _owner(client):
    return seed_user(client, role="owner", name="O")


def test_create_expense(client):
    u = _owner(client)
    r = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={
            "amount": 4200,
            "category": "Уборка",
            "description": "Лермонтова 58",
            "occurred_at": "2026-04-20",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["amount"] == 4200
    assert body["category"] == "Уборка"


def test_list_expenses_filter_by_month(client):
    u = _owner(client)
    for ym, amt in [("2026-03-10", 1000), ("2026-04-15", 2000), ("2026-04-20", 500)]:
        client.post(
            "/expenses",
            headers=auth(u["id"]),
            json={"amount": amt, "category": "X", "occurred_at": ym},
        )
    r = client.get("/expenses?month=2026-04", headers=auth(u["id"]))
    assert r.status_code == 200
    data = r.json()
    assert sum(e["amount"] for e in data) == 2500
    assert len(data) == 2


def test_patch_expense(client):
    u = _owner(client)
    e = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 100, "category": "X", "occurred_at": "2026-04-01"},
    ).json()
    r = client.patch(
        f"/expenses/{e['id']}",
        headers=auth(u["id"]),
        json={"amount": 150},
    )
    assert r.status_code == 200
    assert r.json()["amount"] == 150


def test_delete_expense(client):
    u = _owner(client)
    e = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 100, "category": "X", "occurred_at": "2026-04-01"},
    ).json()
    r = client.delete(f"/expenses/{e['id']}", headers=auth(u["id"]))
    assert r.status_code == 204
    r = client.get("/expenses", headers=auth(u["id"]))
    assert r.json() == []
```

- [ ] **Step 2: Red**

Run: `uv run pytest tests/test_expenses.py -v`
Expected: fails (404).

- [ ] **Step 3: `backend/routes/expenses.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/expenses", tags=["expenses"])


class ExpenseIn(BaseModel):
    amount: int = Field(gt=0)
    category: str = Field(min_length=1)
    description: str | None = None
    occurred_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class ExpensePatch(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1)
    description: str | None = None
    occurred_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


FIELDS = "id, amount, category, description, occurred_at, created_at"


def _row(conn, eid: int):
    return conn.execute(f"SELECT {FIELDS} FROM expenses WHERE id = ?", (eid,)).fetchone()


@router.get("")
def list_expenses(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        if month:
            rows = conn.execute(
                f"SELECT {FIELDS} FROM expenses "
                "WHERE substr(occurred_at, 1, 7) = ? "
                "ORDER BY occurred_at DESC",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {FIELDS} FROM expenses ORDER BY occurred_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO expenses(amount, category, description, occurred_at) "
            "VALUES (?, ?, ?, ?)",
            (payload.amount, payload.category, payload.description, payload.occurred_at),
        )
        row = _row(conn, cur.lastrowid)
    return dict(row)


@router.patch("/{eid}")
def update_expense(
    eid: int,
    payload: ExpensePatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=400, detail="Нет полей для обновления")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?",
            list(fields.values()) + [eid],
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Расход не найден")
        row = _row(conn, eid)
    return dict(row)


@router.delete("/{eid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(eid: int, _: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (eid,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Расход не найден")
    return None
```

- [ ] **Step 4: Регистрация**

В `main.py`:
```python
from backend.routes import expenses as expenses_routes
app.include_router(expenses_routes.router)
```

- [ ] **Step 5: Green**

Run: `uv run pytest tests/test_expenses.py -v`
Expected: 4 passed.

- [ ] **Step 6: Коммит**

```bash
git add backend/routes/expenses.py backend/main.py tests/test_expenses.py
git commit -m "feat(expenses): CRUD + фильтр по месяцу"
```

---

### Task 17: Red+Green — `GET /finance/summary`

**Files:**
- Create: `backend/routes/finance.py`
- Modify: `backend/main.py`
- Create: `tests/test_finance.py`

- [ ] **Step 1: Тест**

```python
# tests/test_finance.py
from tests.conftest import auth, seed_user


def test_finance_summary_combines_revenue_and_expenses(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "addr", "price_per_night": 4000},
    ).json()
    cl = client.post(
        "/clients",
        headers=auth(u["id"]),
        json={"full_name": "X", "phone": "+7"},
    ).json()
    client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": apt["id"],
            "client_id": cl["id"],
            "check_in": "2026-04-10",
            "check_out": "2026-04-13",
            "total_price": 12000,
        },
    )
    client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 4200, "category": "Уборка", "occurred_at": "2026-04-15"},
    )
    client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={"amount": 3000, "category": "ЖКХ", "occurred_at": "2026-04-18"},
    )
    r = client.get("/finance/summary?month=2026-04", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["revenue"] == 12000
    assert body["expenses_total"] == 7200
    assert body["net"] == 4800
    assert body["by_category"] == {"Уборка": 4200, "ЖКХ": 3000}
    assert len(body["feed"]) == 3
    # feed отсортирован по дате убывающе
    dates = [f["dt"] for f in body["feed"]]
    assert dates == sorted(dates, reverse=True)
```

- [ ] **Step 2: Red**

Run: `uv run pytest tests/test_finance.py -v`
Expected: fail (404).

- [ ] **Step 3: `backend/routes/finance.py`**

```python
from datetime import date

from fastapi import APIRouter, Depends, Query

from backend.auth import require_role
from backend.db import get_conn
from backend.lib.stats import aggregate_bookings_in_period, month_bounds

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary")
def summary(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    ym = month or date.today().strftime("%Y-%m")
    p_start, p_end = month_bounds(ym)
    with get_conn() as conn:
        bookings = [
            dict(r) for r in conn.execute(
                "SELECT id, check_in, check_out, total_price, status, "
                "(SELECT full_name FROM clients WHERE clients.id = bookings.client_id) AS client_name "
                "FROM bookings "
                "WHERE check_out > ? AND check_in < ? AND status != 'cancelled'",
                (p_start.isoformat(), p_end.isoformat()),
            ).fetchall()
        ]
        expenses = [
            dict(r) for r in conn.execute(
                "SELECT id, amount, category, description, occurred_at FROM expenses "
                "WHERE substr(occurred_at, 1, 7) = ? ORDER BY occurred_at DESC",
                (ym,),
            ).fetchall()
        ]
    agg = aggregate_bookings_in_period(bookings, p_start, p_end)
    revenue = agg["revenue"]
    expenses_total = sum(e["amount"] for e in expenses)
    by_category: dict[str, int] = {}
    for e in expenses:
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]

    feed = []
    for b in bookings:
        feed.append(
            {
                "type": "income",
                "amount": b["total_price"],
                "label": f"Бронь {b['client_name'] or ''}".strip(),
                "dt": b["check_out"],
                "ref": {"booking_id": b["id"]},
            }
        )
    for e in expenses:
        feed.append(
            {
                "type": "expense",
                "amount": e["amount"],
                "label": f"{e['category']}"
                + (f" · {e['description']}" if e["description"] else ""),
                "dt": e["occurred_at"],
                "ref": {"expense_id": e["id"]},
            }
        )
    feed.sort(key=lambda x: x["dt"], reverse=True)

    return {
        "month": ym,
        "revenue": revenue,
        "expenses_total": expenses_total,
        "net": revenue - expenses_total,
        "by_category": by_category,
        "feed": feed,
    }
```

- [ ] **Step 4: Регистрация в `main.py`**

```python
from backend.routes import finance as finance_routes
app.include_router(finance_routes.router)
```

- [ ] **Step 5: Green**

Run: `uv run pytest tests/test_finance.py -v`
Expected: 1 passed.

- [ ] **Step 6: Коммит**

```bash
git add backend/routes/finance.py backend/main.py tests/test_finance.py
git commit -m "feat(finance): GET /finance/summary"
```

---

## Phase 7 — Финал

### Task 18: Прогнать полный набор тестов + запуск сервера

- [ ] **Step 1: Все тесты разом**

Run: `uv run pytest -v`
Expected: все тесты зелёные (~25 тестов).

- [ ] **Step 2: Обновить `.env` — добавить `DEBUG=1` для локальной разработки**

Run: `echo 'DEBUG=1' >> .env && cat .env`
Expected: `.env` теперь содержит строку `DEBUG=1`.

- [ ] **Step 3: Быстрый smoke-запуск сервера и проверка**

В первом терминале:
Run: `uv run --env-file .env uvicorn backend.main:app --port 8000`

Во втором терминале (не закрывая):
Run: `curl -s http://localhost:8000/health && echo && curl -s http://localhost:8000/dev_auth/users`
Expected:
```json
{"ok": true}
[]
```
(пустой список юзеров — это ок, БД только что мигрирована; руками создадим юзера для ручной проверки в следующем шаге)

Run: `curl -s -X POST http://localhost:8000/users -H 'X-User-Id: 0' -H 'Content-Type: application/json' -d '{"full_name":"test","role":"owner"}' -w "\n%{http_code}\n"`
Expected: `401` (нет текущего юзера) — ожидаемо. Создать руками через sqlite:
Run: `uv run --env-file .env python -c "from backend.db import get_conn; c = get_conn().__enter__(); c.execute(\"INSERT INTO users(full_name, role) VALUES ('Owner', 'owner')\"); c.commit(); print('OK')"`
Expected: `OK`.

Run: `curl -s http://localhost:8000/dev_auth/users`
Expected: список из одного объекта.

Убить сервер (Ctrl+C).

- [ ] **Step 4: Коммит (если была правка .env — .env в .gitignore, но если нет — не пушим секреты)**

Run: `cat .gitignore`
Expected: `.env` в списке. Если да — ничего не коммитим (ок, backend готов).

Если `.env` не в `.gitignore` — добавить и коммит:
```bash
echo '.env' >> .gitignore
git add .gitignore
git commit -m "chore: .env в gitignore"
```

- [ ] **Step 5: Финальный коммит — заметка в спеке, что бэк готов**

В конец `docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md` добавить строку:
```markdown
---

## Status

- [x] Backend (план 1/3) — готов `2026-04-21`
- [ ] Frontend foundation + core screens (план 2/3)
- [ ] Frontend remaining screens (план 3/3)
```

```bash
git add docs/superpowers/specs/2026-04-21-mobile-design-adapt-design.md
git commit -m "docs(spec): отметка о завершении backend-части"
```

---

## Готово

После выполнения этого плана:

- Миграции идемпотентны, схема расширена.
- `/dev_auth/*` работает только при `DEBUG=1`; старый `/auth/*` удалён.
- Все CRUD-эндпоинты apartments/bookings/clients обогащены.
- Добавлены `/dashboard/summary`, `/reports`, `/expenses` CRUD, `/finance/summary`, `/apartments/{id}/stats`, `/bookings/calendar`, `/clients/{id}`.
- `pytest -v` проходит полностью (~25 тестов).
- Сервер отвечает на curl-пробе.

Следующий шаг — написать **план 2/3** (frontend foundation + 6 базовых экранов) после прогона и ревью этого плана.
