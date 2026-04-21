# fil-crm Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать прототип CRM для посуточной аренды в Якутске — FastAPI-бэкенд на SQLite (raw queries) и SvelteKit-фронтенд с тремя ролями (owner/admin/maid) и сущностями квартира/клиент/бронь, плюс флаг "требует уборки".

**Architecture:** Монорепо `backend/` (FastAPI, stateless REST, auth через заголовок `X-User-Id`) + `frontend/` (SvelteKit, file-based routing, localStorage-сессия). БД — один `db.sqlite3`, схема применяется миграцией при старте бэка. Тесты не пишем (YAGNI для прототипа) — проверка каждого шага через curl или UI.

**Tech Stack:** Python 3.13 · FastAPI · uvicorn · sqlite3 (stdlib) · uv · SvelteKit · ванильный CSS

**Спецификация:** [`docs/superpowers/specs/2026-04-21-fil-crm-prototype-design.md`](../specs/2026-04-21-fil-crm-prototype-design.md)

---

## Карта файлов

**Бэк:**
- `backend/__init__.py` — пустой, делает пакет
- `backend/main.py` — FastAPI app, CORS, применение миграций при startup, подключение роутеров
- `backend/db.py` — `get_conn()` контекст-менеджер, `Row` factory, `PRAGMA foreign_keys=ON`
- `backend/auth.py` — `require_role(*roles)` FastAPI dependency через заголовок `X-User-Id`
- `backend/migrations/001_init.sql` — DDL всех таблиц
- `backend/routes/__init__.py` — пустой
- `backend/routes/auth.py` — `GET /auth/users`, `POST /auth/login`
- `backend/routes/users.py` — `GET/POST/DELETE /users` (owner only)
- `backend/routes/apartments.py` — CRUD + `/cleaning` + `/mark-dirty` + `/mark-clean`
- `backend/routes/clients.py` — CRUD
- `backend/routes/bookings.py` — CRUD с проверкой пересечения дат
- `backend/seed.py` — одноразовый скрипт, удаляется после запуска
- `pyproject.toml` — добавляем `uvicorn`
- `.env` — пустой файл (для `uv run --env-file .env`)

**Фронт:** (генерируется `npm create svelte@latest`)
- `frontend/src/app.css` — минимальные стили
- `frontend/src/lib/api.js` — fetch-хелпер + `ApiError`
- `frontend/src/lib/auth.js` — работа с `localStorage`
- `frontend/src/routes/+layout.svelte` — навбар + auth-guard
- `frontend/src/routes/+page.svelte` — редирект в зависимости от роли
- `frontend/src/routes/login/+page.svelte`
- `frontend/src/routes/apartments/+page.svelte`
- `frontend/src/routes/clients/+page.svelte`
- `frontend/src/routes/bookings/+page.svelte`
- `frontend/src/routes/users/+page.svelte`
- `frontend/src/routes/cleaning/+page.svelte`

**Удаляем:** старый `main.py` в корне (заглушка). `seed.py` — после успешного запуска (спека требует).

**.gitignore:** добавить `db.sqlite3`, `frontend/node_modules`, `frontend/.svelte-kit`, `frontend/build`.

---

## Task 1: Скелет бэкенда и БД

**Files:**
- Delete: `main.py` (в корне)
- Create: `backend/__init__.py`
- Create: `backend/db.py`
- Create: `backend/migrations/001_init.sql`
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `.env`

- [ ] **Step 1.1: Удалить заглушку в корне**

```bash
rm /home/uybaan/fil-crm/main.py
```

- [ ] **Step 1.2: Добавить uvicorn в зависимости**

Отредактировать `pyproject.toml`, заменить блок `dependencies`:

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
```

- [ ] **Step 1.3: Обновить lockfile**

Run: `cd /home/uybaan/fil-crm && uv sync`
Expected: установится uvicorn, создастся/обновится `uv.lock` без ошибок.

- [ ] **Step 1.4: Создать `.env` (пустой, нужен для uv run --env-file)**

Run: `touch /home/uybaan/fil-crm/.env`

- [ ] **Step 1.5: Дополнить .gitignore**

Добавить в `/home/uybaan/fil-crm/.gitignore` строки (в конец файла):

```
db.sqlite3
frontend/node_modules
frontend/.svelte-kit
frontend/build
.env
```

- [ ] **Step 1.6: Создать `backend/__init__.py` (пустой)**

```bash
mkdir -p /home/uybaan/fil-crm/backend && touch /home/uybaan/fil-crm/backend/__init__.py
```

- [ ] **Step 1.7: Создать SQL-миграцию `backend/migrations/001_init.sql`**

```bash
mkdir -p /home/uybaan/fil-crm/backend/migrations
```

Файл `backend/migrations/001_init.sql`:

```sql
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'maid')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS apartments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    address TEXT NOT NULL,
    price_per_night INTEGER NOT NULL,
    needs_cleaning INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL REFERENCES apartments(id),
    client_id INTEGER NOT NULL REFERENCES clients(id),
    check_in TEXT NOT NULL,
    check_out TEXT NOT NULL,
    total_price INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','cancelled','completed')),
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_bookings_apartment_dates
    ON bookings(apartment_id, check_in, check_out);
```

- [ ] **Step 1.8: Создать `backend/db.py`**

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
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with get_conn() as conn:
        for f in files:
            conn.executescript(f.read_text(encoding="utf-8"))
```

- [ ] **Step 1.9: Коммит**

```bash
cd /home/uybaan/fil-crm
git add .gitignore pyproject.toml uv.lock backend/ docs/ 2>/dev/null || true
git rm main.py
git add -A
git commit -m "feat(backend): каркас — db.py, миграция schema, зависимость uvicorn"
```

---

## Task 2: FastAPI-приложение и CORS

**Files:**
- Create: `backend/main.py`

- [ ] **Step 2.1: Создать `backend/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import apply_migrations


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


@app.get("/health")
def health():
    return {"ok": True}
```

- [ ] **Step 2.2: Запустить бэк и проверить**

Run в отдельном терминале:
```bash
cd /home/uybaan/fil-crm && uv run --env-file .env uvicorn backend.main:app --reload --port 8000
```

В другом терминале:
```bash
curl -s http://localhost:8000/health
```

Expected: `{"ok":true}`. В корне должен появиться `db.sqlite3`. Проверить что таблицы создались:

```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 ".tables"
```

Expected: `apartments  bookings    clients     users`.

- [ ] **Step 2.3: Остановить сервер (Ctrl+C) и закоммитить**

```bash
cd /home/uybaan/fil-crm
git add backend/main.py
git commit -m "feat(backend): FastAPI app + CORS + миграции на startup"
```

---

## Task 3: Auth dependency

**Files:**
- Create: `backend/auth.py`

- [ ] **Step 3.1: Создать `backend/auth.py`**

```python
from typing import Iterable

from fastapi import Header, HTTPException, status

from backend.db import get_conn


def _load_user(user_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, full_name, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return dict(row)


def require_role(*roles: str):
    allowed = set(roles)

    def dep(x_user_id: int | None = Header(default=None, alias="X-User-Id")) -> dict:
        if x_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Отсутствует заголовок X-User-Id",
            )
        user = _load_user(x_user_id)
        if user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    return dep
```

- [ ] **Step 3.2: Коммит**

```bash
cd /home/uybaan/fil-crm
git add backend/auth.py
git commit -m "feat(backend): require_role dependency через заголовок X-User-Id"
```

---

## Task 4: Auth-роуты (список юзеров + логин)

**Files:**
- Create: `backend/routes/__init__.py`
- Create: `backend/routes/auth.py`
- Modify: `backend/main.py`

- [ ] **Step 4.1: Создать `backend/routes/__init__.py` (пустой)**

```bash
touch /home/uybaan/fil-crm/backend/routes/__init__.py
```

- [ ] **Step 4.2: Создать `backend/routes/auth.py`**

```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.db import get_conn

router = APIRouter(prefix="/auth", tags=["auth"])


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
            "SELECT id, full_name, role FROM users WHERE id = ?", (payload.user_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return dict(row)
```

- [ ] **Step 4.3: Подключить роутер в `backend/main.py`**

Отредактировать `backend/main.py`, заменить целиком:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db import apply_migrations
from backend.routes import auth as auth_routes


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

app.include_router(auth_routes.router)


@app.get("/health")
def health():
    return {"ok": True}
```

- [ ] **Step 4.4: Верификация через curl**

Запустить сервер: `cd /home/uybaan/fil-crm && uv run --env-file .env uvicorn backend.main:app --reload --port 8000`

В другом терминале — вручную вставить тестового юзера (временно, для смоук-теста):
```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 "INSERT INTO users (full_name, role) VALUES ('Test Owner', 'owner');"
curl -s http://localhost:8000/auth/users
```

Expected: `[{"id":1,"full_name":"Test Owner","role":"owner"}]`

```bash
curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"user_id": 1}'
```

Expected: `{"id":1,"full_name":"Test Owner","role":"owner"}`

```bash
curl -s -X POST http://localhost:8000/auth/login -H "Content-Type: application/json" -d '{"user_id": 999}'
```

Expected: `{"detail":"Пользователь не найден"}` с кодом 404.

Удалить тестового юзера:
```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 "DELETE FROM users;"
```

Остановить сервер (Ctrl+C).

- [ ] **Step 4.5: Коммит**

```bash
cd /home/uybaan/fil-crm
git add backend/routes/ backend/main.py
git commit -m "feat(backend): auth-роуты — список юзеров + login"
```

---

## Task 5: Users-роуты (owner only)

**Files:**
- Create: `backend/routes/users.py`
- Modify: `backend/main.py`

- [ ] **Step 5.1: Создать `backend/routes/users.py`**

```python
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/users", tags=["users"])


class Role(str, Enum):
    owner = "owner"
    admin = "admin"
    maid = "maid"


class UserIn(BaseModel):
    full_name: str = Field(min_length=1)
    role: Role


@router.get("")
def list_users(_: dict = Depends(require_role("owner"))):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, role, created_at FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserIn, _: dict = Depends(require_role("owner"))):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (full_name, role) VALUES (?, ?)",
            (payload.full_name, payload.role.value),
        )
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT id, full_name, role, created_at FROM users WHERE id = ?",
            (new_id,),
        ).fetchone()
    return dict(row)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, current: dict = Depends(require_role("owner"))):
    if user_id == current["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственную учётную запись",
        )
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if cur.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return None
```

- [ ] **Step 5.2: Подключить роутер**

В `backend/main.py` после `from backend.routes import auth as auth_routes` добавить:

```python
from backend.routes import users as users_routes
```

И после `app.include_router(auth_routes.router)`:

```python
app.include_router(users_routes.router)
```

- [ ] **Step 5.3: Верификация**

Поднять сервер. Создать в БД owner'а вручную:
```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 "INSERT INTO users (full_name, role) VALUES ('Owner', 'owner');"
```

Проверить защиту:
```bash
curl -s -i http://localhost:8000/users
```
Expected: 401 (нет заголовка).

```bash
curl -s -i http://localhost:8000/users -H "X-User-Id: 1"
```
Expected: 200, список из одного owner'а.

Создать admin'а:
```bash
curl -s -i http://localhost:8000/users -X POST \
  -H "Content-Type: application/json" \
  -H "X-User-Id: 1" \
  -d '{"full_name":"Admin","role":"admin"}'
```
Expected: 201, возвращён созданный юзер.

Проверить что admin не может листать users:
```bash
curl -s -i http://localhost:8000/users -H "X-User-Id: 2"
```
Expected: 403.

Попытка self-delete:
```bash
curl -s -i -X DELETE http://localhost:8000/users/1 -H "X-User-Id: 1"
```
Expected: 400 с текстом про "собственную учётную запись".

Очистка: `sqlite3 /home/uybaan/fil-crm/db.sqlite3 "DELETE FROM users;"`. Остановить сервер.

- [ ] **Step 5.4: Коммит**

```bash
cd /home/uybaan/fil-crm
git add backend/routes/users.py backend/main.py
git commit -m "feat(backend): users routes (owner only)"
```

---

## Task 6: Apartments-роуты

**Files:**
- Create: `backend/routes/apartments.py`
- Modify: `backend/main.py`

- [ ] **Step 6.1: Создать `backend/routes/apartments.py`**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/apartments", tags=["apartments"])


class ApartmentIn(BaseModel):
    title: str = Field(min_length=1)
    address: str = Field(min_length=1)
    price_per_night: int = Field(gt=0)


class ApartmentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    price_per_night: int | None = Field(default=None, gt=0)


def _row(conn, apt_id: int):
    return conn.execute(
        "SELECT id, title, address, price_per_night, needs_cleaning, created_at "
        "FROM apartments WHERE id = ?",
        (apt_id,),
    ).fetchone()


@router.get("")
def list_apartments(_: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, address, price_per_night, needs_cleaning, created_at "
            "FROM apartments ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/cleaning")
def list_apartments_needing_cleaning(
    _: dict = Depends(require_role("owner", "admin", "maid")),
):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, title, address, price_per_night, needs_cleaning, created_at "
            "FROM apartments WHERE needs_cleaning = 1 ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_apartment(
    payload: ApartmentIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO apartments (title, address, price_per_night) VALUES (?, ?, ?)",
            (payload.title, payload.address, payload.price_per_night),
        )
        row = _row(conn, cur.lastrowid)
    return dict(row)


@router.patch("/{apt_id}")
def update_apartment(
    apt_id: int,
    payload: ApartmentPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
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

- [ ] **Step 6.2: Подключить роутер**

В `backend/main.py` добавить импорт и `include_router` по аналогии с users — после `from backend.routes import users as users_routes` добавить `from backend.routes import apartments as apartments_routes`, после `app.include_router(users_routes.router)` — `app.include_router(apartments_routes.router)`.

- [ ] **Step 6.3: Верификация**

Создать owner и admin:
```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 "INSERT INTO users (full_name, role) VALUES ('Owner','owner'),('Admin','admin'),('Maid','maid');"
```

Запустить сервер. Проверки:

```bash
# admin создаёт квартиру
curl -s -X POST http://localhost:8000/apartments \
  -H "Content-Type: application/json" -H "X-User-Id: 2" \
  -d '{"title":"2к на Ленина 10","address":"Ленина 10","price_per_night":4500}'
```
Expected: 201, json с `needs_cleaning: 0`.

```bash
# maid не может листать все квартиры
curl -s -i http://localhost:8000/apartments -H "X-User-Id: 3"
```
Expected: 403.

```bash
# но может видеть cleaning-список
curl -s http://localhost:8000/apartments/cleaning -H "X-User-Id: 3"
```
Expected: `[]`.

```bash
# admin ставит dirty
curl -s -X POST http://localhost:8000/apartments/1/mark-dirty -H "X-User-Id: 2"
```
Expected: `needs_cleaning: 1`.

```bash
# maid видит квартиру и снимает флаг
curl -s http://localhost:8000/apartments/cleaning -H "X-User-Id: 3"
curl -s -X POST http://localhost:8000/apartments/1/mark-clean -H "X-User-Id: 3"
```
Expected: первый — список с одной квартирой; второй — `needs_cleaning: 0`.

```bash
# PATCH
curl -s -X PATCH http://localhost:8000/apartments/1 \
  -H "Content-Type: application/json" -H "X-User-Id: 2" \
  -d '{"price_per_night":5000}'
```
Expected: обновлённая квартира.

Очистка: `sqlite3 /home/uybaan/fil-crm/db.sqlite3 "DELETE FROM apartments; DELETE FROM users;"`. Остановить сервер.

- [ ] **Step 6.4: Коммит**

```bash
cd /home/uybaan/fil-crm
git add backend/routes/apartments.py backend/main.py
git commit -m "feat(backend): apartments CRUD + mark-dirty/mark-clean"
```

---

## Task 7: Clients-роуты

**Files:**
- Create: `backend/routes/clients.py`
- Modify: `backend/main.py`

- [ ] **Step 7.1: Создать `backend/routes/clients.py`**

```python
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientIn(BaseModel):
    full_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    source: str | None = None
    notes: str | None = None


class ClientPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, min_length=1)
    source: str | None = None
    notes: str | None = None


def _row(conn, client_id: int):
    return conn.execute(
        "SELECT id, full_name, phone, source, notes, created_at FROM clients WHERE id = ?",
        (client_id,),
    ).fetchone()


@router.get("")
def list_clients(_: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, phone, source, notes, created_at FROM clients ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (full_name, phone, source, notes) VALUES (?, ?, ?, ?)",
            (payload.full_name, payload.phone, payload.source, payload.notes),
        )
        row = _row(conn, cur.lastrowid)
    return dict(row)


@router.patch("/{client_id}")
def update_client(
    client_id: int,
    payload: ClientPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления"
        )
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [client_id]
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE clients SET {set_clause} WHERE id = ?", values
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден"
            )
        row = _row(conn, client_id)
    return dict(row)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, _: dict = Depends(require_role("owner", "admin"))):
    try:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден"
                )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить клиента с привязанными бронями",
        )
    return None
```

- [ ] **Step 7.2: Подключить роутер в `backend/main.py`** (аналогично предыдущим — импорт `from backend.routes import clients as clients_routes`, затем `app.include_router(clients_routes.router)`).

- [ ] **Step 7.3: Верификация**

```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 "INSERT INTO users (full_name, role) VALUES ('Owner','owner');"
```
Поднять сервер. Проверки:

```bash
curl -s -X POST http://localhost:8000/clients -H "Content-Type: application/json" -H "X-User-Id: 1" \
  -d '{"full_name":"Иван Иванов","phone":"+79991234567","source":"avito"}'
curl -s http://localhost:8000/clients -H "X-User-Id: 1"
curl -s -X PATCH http://localhost:8000/clients/1 -H "Content-Type: application/json" -H "X-User-Id: 1" \
  -d '{"notes":"постоянный клиент"}'
curl -s -i -X DELETE http://localhost:8000/clients/1 -H "X-User-Id: 1"
```
Expected: 201, список с клиентом, обновлённый клиент, 204.

Очистка: `sqlite3 /home/uybaan/fil-crm/db.sqlite3 "DELETE FROM clients; DELETE FROM users;"`. Остановить сервер.

- [ ] **Step 7.4: Коммит**

```bash
cd /home/uybaan/fil-crm
git add backend/routes/clients.py backend/main.py
git commit -m "feat(backend): clients CRUD"
```

---

## Task 8: Bookings-роуты с детектом пересечений

**Files:**
- Create: `backend/routes/bookings.py`
- Modify: `backend/main.py`

- [ ] **Step 8.1: Создать `backend/routes/bookings.py`**

```python
import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/bookings", tags=["bookings"])


BOOKING_STATUSES = {"active", "cancelled", "completed"}


class BookingIn(BaseModel):
    apartment_id: int
    client_id: int
    check_in: date
    check_out: date
    total_price: int = Field(gt=0)
    notes: str | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out должна быть позже check_in")
        return self


class BookingPatch(BaseModel):
    apartment_id: int | None = None
    client_id: int | None = None
    check_in: date | None = None
    check_out: date | None = None
    total_price: int | None = Field(default=None, gt=0)
    status: str | None = None
    notes: str | None = None


def _find_conflict(conn, apartment_id: int, check_in: str, check_out: str, exclude_id: int | None):
    sql = (
        "SELECT id FROM bookings WHERE apartment_id = ? AND status = 'active' "
        "AND check_in < ? AND check_out > ?"
    )
    params: list = [apartment_id, check_out, check_in]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    row = conn.execute(sql, params).fetchone()
    return row["id"] if row else None


def _row(conn, booking_id: int):
    return conn.execute(
        """
        SELECT b.id, b.apartment_id, b.client_id, b.check_in, b.check_out,
               b.total_price, b.status, b.notes, b.created_at,
               a.title AS apartment_title, c.full_name AS client_name
        FROM bookings b
        JOIN apartments a ON a.id = b.apartment_id
        JOIN clients c ON c.id = b.client_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()


@router.get("")
def list_bookings(_: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT b.id, b.apartment_id, b.client_id, b.check_in, b.check_out,
                   b.total_price, b.status, b.notes, b.created_at,
                   a.title AS apartment_title, c.full_name AS client_name
            FROM bookings b
            JOIN apartments a ON a.id = b.apartment_id
            JOIN clients c ON c.id = b.client_id
            ORDER BY b.check_in DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingIn, _: dict = Depends(require_role("owner", "admin"))
):
    ci = payload.check_in.isoformat()
    co = payload.check_out.isoformat()
    try:
        with get_conn() as conn:
            conflict = _find_conflict(conn, payload.apartment_id, ci, co, None)
            if conflict is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Даты пересекаются с бронью #{conflict}",
                )
            cur = conn.execute(
                "INSERT INTO bookings (apartment_id, client_id, check_in, check_out, total_price, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    payload.apartment_id,
                    payload.client_id,
                    ci,
                    co,
                    payload.total_price,
                    payload.notes,
                ),
            )
            row = _row(conn, cur.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указаны несуществующие apartment_id или client_id",
        )
    return dict(row)


@router.patch("/{booking_id}")
def update_booking(
    booking_id: int,
    payload: BookingPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления"
        )
    if "status" in fields and fields["status"] not in BOOKING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status должен быть одним из: {sorted(BOOKING_STATUSES)}",
        )
    # нормализация дат -> строки
    for k in ("check_in", "check_out"):
        if k in fields and fields[k] is not None:
            fields[k] = fields[k].isoformat() if hasattr(fields[k], "isoformat") else fields[k]

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT apartment_id, check_in, check_out, status FROM bookings WHERE id = ?",
            (booking_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена"
            )

        new_apt = fields.get("apartment_id", existing["apartment_id"])
        new_ci = fields.get("check_in", existing["check_in"])
        new_co = fields.get("check_out", existing["check_out"])
        new_status = fields.get("status", existing["status"])

        if new_co <= new_ci:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="check_out должна быть позже check_in",
            )

        if new_status == "active":
            conflict = _find_conflict(conn, new_apt, new_ci, new_co, booking_id)
            if conflict is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Даты пересекаются с бронью #{conflict}",
                )

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [booking_id]
        try:
            conn.execute(f"UPDATE bookings SET {set_clause} WHERE id = ?", values)
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указаны несуществующие apartment_id или client_id",
            )
        row = _row(conn, booking_id)
    return dict(row)


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(booking_id: int, _: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    if cur.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена"
        )
    return None
```

- [ ] **Step 8.2: Подключить роутер в `backend/main.py`** (импорт `from backend.routes import bookings as bookings_routes` и `app.include_router(bookings_routes.router)`).

- [ ] **Step 8.3: Верификация**

Подготовка (одна команда, мульти-insert):
```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 "
INSERT INTO users (full_name, role) VALUES ('Owner','owner');
INSERT INTO apartments (title, address, price_per_night) VALUES ('Apt 1','Addr 1',3000);
INSERT INTO clients (full_name, phone) VALUES ('Ivan','+7'),('Petr','+7');
"
```

Запустить сервер. Проверки:

```bash
# создаём первую бронь
curl -s -X POST http://localhost:8000/bookings -H "Content-Type: application/json" -H "X-User-Id: 1" \
  -d '{"apartment_id":1,"client_id":1,"check_in":"2026-05-01","check_out":"2026-05-05","total_price":12000}'
```
Expected: 201.

```bash
# пытаемся пересечь — должно быть 409
curl -s -i -X POST http://localhost:8000/bookings -H "Content-Type: application/json" -H "X-User-Id: 1" \
  -d '{"apartment_id":1,"client_id":2,"check_in":"2026-05-04","check_out":"2026-05-07","total_price":9000}'
```
Expected: HTTP 409, detail "Даты пересекаются с бронью #1".

```bash
# касание датой (check_in=check_out предыдущей) — должно пройти
curl -s -i -X POST http://localhost:8000/bookings -H "Content-Type: application/json" -H "X-User-Id: 1" \
  -d '{"apartment_id":1,"client_id":2,"check_in":"2026-05-05","check_out":"2026-05-08","total_price":9000}'
```
Expected: 201 (check_out exclusive).

```bash
# список с join-полями
curl -s http://localhost:8000/bookings -H "X-User-Id: 1"
```
Expected: массив с `apartment_title`, `client_name`.

```bash
# отменяем первую бронь — после этого пересечение с её датами должно быть разрешено
curl -s -X PATCH http://localhost:8000/bookings/1 -H "Content-Type: application/json" -H "X-User-Id: 1" -d '{"status":"cancelled"}'
```
Expected: status = cancelled.

Очистка: `sqlite3 /home/uybaan/fil-crm/db.sqlite3 "DELETE FROM bookings; DELETE FROM clients; DELETE FROM apartments; DELETE FROM users;"`. Остановить сервер.

- [ ] **Step 8.4: Коммит**

```bash
cd /home/uybaan/fil-crm
git add backend/routes/bookings.py backend/main.py
git commit -m "feat(backend): bookings CRUD с детектом пересечения дат"
```

---

## Task 9: Seed-скрипт

**Files:**
- Create: `backend/seed.py`

- [ ] **Step 9.1: Создать `backend/seed.py`**

```python
"""One-shot seed: создаёт трёх тестовых юзеров. После успешного запуска файл удаляется вручную."""

from backend.db import apply_migrations, get_conn


USERS = [
    ("Хозяин Иван", "owner"),
    ("Админ Анна", "admin"),
    ("Горничная Мария", "maid"),
]


def main() -> None:
    apply_migrations()
    with get_conn() as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if existing > 0:
            print(f"В таблице users уже {existing} записей — сид пропущен.")
            return
        for full_name, role in USERS:
            conn.execute(
                "INSERT INTO users (full_name, role) VALUES (?, ?)",
                (full_name, role),
            )
    print("Сид выполнен: Owner/Admin/Maid созданы. Теперь удали backend/seed.py.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 9.2: Запустить seed**

```bash
cd /home/uybaan/fil-crm && uv run --env-file .env python -m backend.seed
```
Expected: `Сид выполнен: Owner/Admin/Maid созданы. Теперь удали backend/seed.py.`

Проверка:
```bash
sqlite3 /home/uybaan/fil-crm/db.sqlite3 "SELECT id, full_name, role FROM users ORDER BY id;"
```
Expected: 3 строки.

- [ ] **Step 9.3: Коммит seed-файла**

```bash
cd /home/uybaan/fil-crm
git add backend/seed.py
git commit -m "feat(backend): seed-скрипт (owner/admin/maid, одноразовый)"
```

Примечание: файл удалим отдельным коммитом в Task 18, после того как фронт будет проверен и мы убедимся что сид-данные живы.

---

## Task 10: Инициализация SvelteKit

**Files:**
- Create: `frontend/` (через `npm create svelte@latest`)

- [ ] **Step 10.1: Создать проект SvelteKit**

Запустить (минимальный скелет, без TypeScript/ESLint, Svelte 5):
```bash
cd /home/uybaan/fil-crm && npx sv create frontend --template minimal --types none --no-add-ons --install npm
```

Если `sv` интерактивит — принять дефолты: `Skeleton project` / `No` для всех опций типов/линтеров.

Ожидается: создана директория `frontend/` со стандартной структурой SvelteKit, установлены node_modules.

- [ ] **Step 10.2: Проверить что dev-сервер стартует**

```bash
cd /home/uybaan/fil-crm/frontend && npm run dev -- --port 5173
```
Открыть `http://localhost:5173` — должен отобразиться welcome-стартер SvelteKit. Остановить (Ctrl+C).

- [ ] **Step 10.3: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/
git commit -m "feat(frontend): инициализация SvelteKit"
```

---

## Task 11: Библиотека `lib/` (auth, api)

**Files:**
- Create: `frontend/src/lib/auth.js`
- Create: `frontend/src/lib/api.js`
- Create: `frontend/src/app.css`
- Modify: `frontend/src/routes/+layout.svelte` (если нет — создаём на Task 12)

- [ ] **Step 11.1: Создать `frontend/src/lib/auth.js`**

```javascript
const KEY = 'fil_crm_user';

export function getUser() {
    if (typeof localStorage === 'undefined') return null;
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
}

export function setUser(user) {
    localStorage.setItem(KEY, JSON.stringify(user));
}

export function clearUser() {
    localStorage.removeItem(KEY);
}
```

- [ ] **Step 11.2: Создать `frontend/src/lib/api.js`**

```javascript
import { getUser } from './auth.js';

const BASE = 'http://localhost:8000';

export class ApiError extends Error {
    constructor(status, detail) {
        super(detail || `HTTP ${status}`);
        this.status = status;
        this.detail = detail;
    }
}

async function request(method, path, body, { auth = true } = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (auth) {
        const user = getUser();
        if (user) headers['X-User-Id'] = String(user.id);
    }
    const res = await fetch(`${BASE}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body)
    });
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(res.status, data.detail || `HTTP ${res.status}`);
    return data;
}

export const api = {
    get:    (path, opts)       => request('GET',    path, undefined, opts),
    post:   (path, body, opts) => request('POST',   path, body,      opts),
    patch:  (path, body, opts) => request('PATCH',  path, body,      opts),
    delete: (path, opts)       => request('DELETE', path, undefined, opts)
};
```

- [ ] **Step 11.3: Создать `frontend/src/app.css`**

```css
:root {
    --bg: #f6f7f9;
    --surface: #ffffff;
    --border: #e3e6eb;
    --text: #1b1f24;
    --muted: #6b7280;
    --accent: #2b6cb0;
    --accent-hover: #245a94;
    --danger: #c0392b;
    --danger-hover: #962f24;
    --warn: #d97706;
    --ok: #059669;
}

* { box-sizing: border-box; }

html, body { margin: 0; padding: 0; background: var(--bg); color: var(--text);
    font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px; }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

.container { max-width: 1100px; margin: 0 auto; padding: 16px; }

nav.topbar { background: var(--surface); border-bottom: 1px solid var(--border);
    padding: 10px 16px; display: flex; align-items: center; gap: 18px; }
nav.topbar .brand { font-weight: 600; }
nav.topbar .spacer { flex: 1; }
nav.topbar a { color: var(--text); padding: 6px 10px; border-radius: 6px; }
nav.topbar a.active { background: var(--bg); }

button { font: inherit; padding: 7px 12px; border-radius: 6px; border: 1px solid var(--border);
    background: var(--surface); cursor: pointer; }
button:hover { background: var(--bg); }
button.primary { background: var(--accent); color: #fff; border-color: var(--accent); }
button.primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
button.danger { color: var(--danger); border-color: var(--danger); }
button.danger:hover { background: var(--danger); color: #fff; }

input, select, textarea { font: inherit; padding: 7px 10px; border-radius: 6px;
    border: 1px solid var(--border); background: var(--surface); width: 100%; }

table { width: 100%; border-collapse: collapse; background: var(--surface);
    border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--border); }
th { background: var(--bg); font-weight: 600; color: var(--muted); }
tr:last-child td { border-bottom: none; }

.card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 16px; margin-bottom: 12px; }

.row { display: flex; gap: 8px; align-items: center; }
.stack { display: flex; flex-direction: column; gap: 10px; }
.grid-form { display: grid; grid-template-columns: 160px 1fr; gap: 10px 12px; align-items: center; }

.badge { display: inline-block; padding: 2px 8px; border-radius: 999px;
    font-size: 12px; background: var(--bg); color: var(--muted); }
.badge.ok    { background: #d1fae5; color: #065f46; }
.badge.warn  { background: #fef3c7; color: #92400e; }

.error-banner { background: #fee2e2; color: #7f1d1d; border: 1px solid #fecaca;
    padding: 10px 12px; border-radius: 6px; margin-bottom: 12px; }

h1 { font-size: 22px; margin: 0 0 12px; }
h2 { font-size: 16px; margin: 0 0 8px; }
```

- [ ] **Step 11.4: Подключить `app.css` глобально — создать/перезаписать `frontend/src/routes/+layout.js`**

```javascript
import '../app.css';
```

- [ ] **Step 11.5: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/src/
git commit -m "feat(frontend): lib/auth, lib/api, app.css и глобальный import"
```

---

## Task 12: `+layout.svelte` с навбаром и auth-guard

**Files:**
- Create/overwrite: `frontend/src/routes/+layout.svelte`

- [ ] **Step 12.1: Создать `frontend/src/routes/+layout.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/stores';
    import { getUser, clearUser } from '$lib/auth.js';

    let user = $state(null);
    let ready = $state(false);

    onMount(() => {
        user = getUser();
        const path = $page.url.pathname;
        if (!user && path !== '/login') {
            goto('/login');
            return;
        }
        if (user && path === '/login') {
            goto(user.role === 'maid' ? '/cleaning' : '/apartments');
            return;
        }
        ready = true;
    });

    function logout() {
        clearUser();
        user = null;
        goto('/login');
    }

    const NAV = {
        owner: [
            { href: '/apartments', label: 'Квартиры' },
            { href: '/clients',    label: 'Клиенты'  },
            { href: '/bookings',   label: 'Брони'    },
            { href: '/users',      label: 'Пользователи' }
        ],
        admin: [
            { href: '/apartments', label: 'Квартиры' },
            { href: '/clients',    label: 'Клиенты'  },
            { href: '/bookings',   label: 'Брони'    }
        ],
        maid: [
            { href: '/cleaning',   label: 'Уборка' }
        ]
    };

    let items = $derived(user ? NAV[user.role] || [] : []);
</script>

{#if ready}
    {#if user}
        <nav class="topbar">
            <span class="brand">fil-crm</span>
            {#each items as item}
                <a href={item.href} class:active={$page.url.pathname === item.href}>{item.label}</a>
            {/each}
            <span class="spacer"></span>
            <span class="badge">{user.full_name} · {user.role}</span>
            <button onclick={logout}>Выход</button>
        </nav>
    {/if}
    <div class="container">
        <slot />
    </div>
{/if}
```

- [ ] **Step 12.2: Создать `frontend/src/routes/+page.svelte` — корневой редирект**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { getUser } from '$lib/auth.js';

    onMount(() => {
        const user = getUser();
        if (!user) goto('/login');
        else goto(user.role === 'maid' ? '/cleaning' : '/apartments');
    });
</script>
```

- [ ] **Step 12.3: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/src/routes/+layout.svelte frontend/src/routes/+page.svelte
git commit -m "feat(frontend): +layout с навбаром по роли и auth-guard"
```

---

## Task 13: Страница `/login`

**Files:**
- Create: `frontend/src/routes/login/+page.svelte`

- [ ] **Step 13.1: Создать `frontend/src/routes/login/+page.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { setUser } from '$lib/auth.js';

    let users = $state([]);
    let error = $state('');

    onMount(async () => {
        try {
            users = await api.get('/auth/users', { auth: false });
        } catch (e) {
            error = e instanceof ApiError ? e.detail : 'Не удалось загрузить список пользователей';
        }
    });

    async function login(u) {
        try {
            const me = await api.post('/auth/login', { user_id: u.id }, { auth: false });
            setUser(me);
            goto(me.role === 'maid' ? '/cleaning' : '/apartments');
        } catch (e) {
            error = e instanceof ApiError ? e.detail : 'Ошибка входа';
        }
    }
</script>

<h1>Вход</h1>

{#if error}
    <div class="error-banner">{error}</div>
{/if}

<div class="stack">
    {#each users as u}
        <button class="card" onclick={() => login(u)}>
            <div class="row">
                <strong style="flex:1">{u.full_name}</strong>
                <span class="badge">{u.role}</span>
            </div>
        </button>
    {/each}
    {#if users.length === 0 && !error}
        <div class="card">Нет пользователей. Запусти seed-скрипт.</div>
    {/if}
</div>
```

- [ ] **Step 13.2: Верификация**

Запустить бэк (`uv run --env-file .env uvicorn backend.main:app --port 8000`) и фронт (`cd frontend && npm run dev -- --port 5173`). Открыть `http://localhost:5173/login`. Должно быть 3 карточки (Owner/Admin/Maid). Клик по "Хозяин Иван" → редирект на `/apartments`, в localStorage лежит `fil_crm_user`. Клик по "Горничная Мария" (сначала разлогинившись через DevTools → Application → localStorage, удалить ключ) → редирект на `/cleaning`.

- [ ] **Step 13.3: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/src/routes/login/
git commit -m "feat(frontend): страница /login со списком юзеров"
```

---

## Task 14: Страница `/apartments`

**Files:**
- Create: `frontend/src/routes/apartments/+page.svelte`

- [ ] **Step 14.1: Создать `frontend/src/routes/apartments/+page.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let editingId = $state(null);
    let form = $state({ title: '', address: '', price_per_night: 0 });

    async function load() {
        try { items = await api.get('/apartments'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        editingId = null;
        form = { title: '', address: '', price_per_night: 0 };
        showForm = true; error = '';
    }
    function openEdit(a) {
        editingId = a.id;
        form = { title: a.title, address: a.address, price_per_night: a.price_per_night };
        showForm = true; error = '';
    }
    async function save() {
        try {
            if (editingId === null) await api.post('/apartments', form);
            else await api.patch(`/apartments/${editingId}`, form);
            showForm = false;
            await load();
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(a) {
        if (!confirm(`Удалить квартиру «${a.title}»?`)) return;
        try { await api.delete(`/apartments/${a.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }
    async function markDirty(a) {
        try { await api.post(`/apartments/${a.id}/mark-dirty`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка'; }
    }
    async function markClean(a) {
        try { await api.post(`/apartments/${a.id}/mark-clean`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка'; }
    }
</script>

<h1>Квартиры</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новая квартира</button>
</div>

{#if showForm}
    <div class="card">
        <h2>{editingId === null ? 'Новая квартира' : `Редактировать #${editingId}`}</h2>
        <div class="grid-form">
            <label>Название</label>    <input bind:value={form.title} />
            <label>Адрес</label>       <input bind:value={form.address} />
            <label>Цена за ночь, ₽</label><input type="number" min="1" bind:value={form.price_per_night} />
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead>
        <tr><th>Название</th><th>Адрес</th><th>₽/ночь</th><th>Статус</th><th></th></tr>
    </thead>
    <tbody>
        {#each items as a}
            <tr>
                <td>{a.title}</td>
                <td>{a.address}</td>
                <td>{a.price_per_night.toLocaleString('ru-RU')}</td>
                <td>
                    {#if a.needs_cleaning}
                        <span class="badge warn">требует уборки</span>
                    {:else}
                        <span class="badge ok">чисто</span>
                    {/if}
                </td>
                <td>
                    <div class="row" style="justify-content:flex-end">
                        {#if a.needs_cleaning}
                            <button onclick={() => markClean(a)}>Отметить убрано</button>
                        {:else}
                            <button onclick={() => markDirty(a)}>Пометить грязно</button>
                        {/if}
                        <button onclick={() => openEdit(a)}>Редактировать</button>
                        <button class="danger" onclick={() => remove(a)}>Удалить</button>
                    </div>
                </td>
            </tr>
        {/each}
        {#if items.length === 0}
            <tr><td colspan="5" style="text-align:center; color:var(--muted)">Пока нет квартир</td></tr>
        {/if}
    </tbody>
</table>
```

- [ ] **Step 14.2: Верификация**

Залогиниться как Owner, открыть `/apartments`. Создать квартиру через форму — должна появиться в таблице. Пометить грязно → статус-бейдж меняется. Нажать "Отметить убрано" → меняется обратно. Редактировать → поля подхватываются, сохраняется. Удалить пустую → удаляется.

- [ ] **Step 14.3: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/src/routes/apartments/
git commit -m "feat(frontend): страница /apartments (CRUD + mark dirty/clean)"
```

---

## Task 15: Страница `/clients`

**Files:**
- Create: `frontend/src/routes/clients/+page.svelte`

- [ ] **Step 15.1: Создать `frontend/src/routes/clients/+page.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let editingId = $state(null);
    let form = $state({ full_name: '', phone: '', source: '', notes: '' });

    async function load() {
        try { items = await api.get('/clients'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        editingId = null;
        form = { full_name: '', phone: '', source: '', notes: '' };
        showForm = true; error = '';
    }
    function openEdit(c) {
        editingId = c.id;
        form = { full_name: c.full_name, phone: c.phone, source: c.source || '', notes: c.notes || '' };
        showForm = true; error = '';
    }
    async function save() {
        const payload = { ...form };
        if (!payload.source) delete payload.source;
        if (!payload.notes)  delete payload.notes;
        try {
            if (editingId === null) await api.post('/clients', payload);
            else await api.patch(`/clients/${editingId}`, payload);
            showForm = false;
            await load();
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(c) {
        if (!confirm(`Удалить клиента «${c.full_name}»?`)) return;
        try { await api.delete(`/clients/${c.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }
</script>

<h1>Клиенты</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новый клиент</button>
</div>

{#if showForm}
    <div class="card">
        <h2>{editingId === null ? 'Новый клиент' : `Редактировать #${editingId}`}</h2>
        <div class="grid-form">
            <label>ФИО</label>      <input bind:value={form.full_name} />
            <label>Телефон</label>  <input bind:value={form.phone} />
            <label>Источник</label>
            <select bind:value={form.source}>
                <option value="">—</option>
                <option value="avito">Avito</option>
                <option value="booking">Booking</option>
                <option value="прямой">Прямой</option>
                <option value="другое">Другое</option>
            </select>
            <label>Заметки</label>  <textarea rows="3" bind:value={form.notes}></textarea>
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead><tr><th>ФИО</th><th>Телефон</th><th>Источник</th><th>Заметки</th><th></th></tr></thead>
    <tbody>
        {#each items as c}
            <tr>
                <td>{c.full_name}</td>
                <td>{c.phone}</td>
                <td>{c.source || '—'}</td>
                <td style="max-width:320px; color:var(--muted)">{c.notes || ''}</td>
                <td>
                    <div class="row" style="justify-content:flex-end">
                        <button onclick={() => openEdit(c)}>Редактировать</button>
                        <button class="danger" onclick={() => remove(c)}>Удалить</button>
                    </div>
                </td>
            </tr>
        {/each}
        {#if items.length === 0}
            <tr><td colspan="5" style="text-align:center; color:var(--muted)">Пока нет клиентов</td></tr>
        {/if}
    </tbody>
</table>
```

- [ ] **Step 15.2: Верификация**

Создать клиента с источником "Avito", заметкой. Проверить что отображается. Отредактировать, удалить. Всё работает.

- [ ] **Step 15.3: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/src/routes/clients/
git commit -m "feat(frontend): страница /clients (CRUD)"
```

---

## Task 16: Страница `/bookings`

**Files:**
- Create: `frontend/src/routes/bookings/+page.svelte`

- [ ] **Step 16.1: Создать `frontend/src/routes/bookings/+page.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let apartments = $state([]);
    let clients = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let editingId = $state(null);
    let form = $state({
        apartment_id: '', client_id: '', check_in: '', check_out: '',
        total_price: 0, status: 'active', notes: ''
    });

    async function load() {
        try {
            [items, apartments, clients] = await Promise.all([
                api.get('/bookings'), api.get('/apartments'), api.get('/clients')
            ]);
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        editingId = null;
        form = { apartment_id: '', client_id: '', check_in: '', check_out: '',
                 total_price: 0, status: 'active', notes: '' };
        showForm = true; error = '';
    }
    function openEdit(b) {
        editingId = b.id;
        form = {
            apartment_id: b.apartment_id, client_id: b.client_id,
            check_in: b.check_in, check_out: b.check_out,
            total_price: b.total_price, status: b.status, notes: b.notes || ''
        };
        showForm = true; error = '';
    }
    async function save() {
        const payload = { ...form };
        payload.apartment_id = Number(payload.apartment_id);
        payload.client_id    = Number(payload.client_id);
        payload.total_price  = Number(payload.total_price);
        if (!payload.notes) delete payload.notes;
        try {
            if (editingId === null) {
                delete payload.status;
                await api.post('/bookings', payload);
            } else {
                await api.patch(`/bookings/${editingId}`, payload);
            }
            showForm = false;
            await load();
        } catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(b) {
        if (!confirm(`Удалить бронь #${b.id}?`)) return;
        try { await api.delete(`/bookings/${b.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }

    const statusLabel = { active: 'активна', cancelled: 'отменена', completed: 'завершена' };
    const statusClass = { active: 'ok', cancelled: 'warn', completed: '' };
</script>

<h1>Брони</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новая бронь</button>
</div>

{#if showForm}
    <div class="card">
        <h2>{editingId === null ? 'Новая бронь' : `Редактировать #${editingId}`}</h2>
        <div class="grid-form">
            <label>Квартира</label>
            <select bind:value={form.apartment_id}>
                <option value="">—</option>
                {#each apartments as a}<option value={a.id}>{a.title}</option>{/each}
            </select>
            <label>Клиент</label>
            <select bind:value={form.client_id}>
                <option value="">—</option>
                {#each clients as c}<option value={c.id}>{c.full_name}</option>{/each}
            </select>
            <label>Заезд</label>    <input type="date" bind:value={form.check_in} />
            <label>Выезд</label>    <input type="date" bind:value={form.check_out} />
            <label>Сумма, ₽</label> <input type="number" min="1" bind:value={form.total_price} />
            {#if editingId !== null}
                <label>Статус</label>
                <select bind:value={form.status}>
                    <option value="active">активна</option>
                    <option value="cancelled">отменена</option>
                    <option value="completed">завершена</option>
                </select>
            {/if}
            <label>Заметки</label>  <textarea rows="3" bind:value={form.notes}></textarea>
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead>
        <tr><th>Квартира</th><th>Клиент</th><th>Заезд</th><th>Выезд</th><th>Сумма</th><th>Статус</th><th></th></tr>
    </thead>
    <tbody>
        {#each items as b}
            <tr>
                <td>{b.apartment_title}</td>
                <td>{b.client_name}</td>
                <td>{b.check_in}</td>
                <td>{b.check_out}</td>
                <td>{b.total_price.toLocaleString('ru-RU')} ₽</td>
                <td><span class="badge {statusClass[b.status] || ''}">{statusLabel[b.status] || b.status}</span></td>
                <td>
                    <div class="row" style="justify-content:flex-end">
                        <button onclick={() => openEdit(b)}>Редактировать</button>
                        <button class="danger" onclick={() => remove(b)}>Удалить</button>
                    </div>
                </td>
            </tr>
        {/each}
        {#if items.length === 0}
            <tr><td colspan="7" style="text-align:center; color:var(--muted)">Пока нет броней</td></tr>
        {/if}
    </tbody>
</table>
```

- [ ] **Step 16.2: Верификация**

Создать квартиру и двух клиентов (если не созданы). Создать бронь 2026-05-01 → 2026-05-05, сумма 12000 — появилась. Попробовать создать пересекающуюся бронь 2026-05-03 → 2026-05-07 на ту же квартиру → должна показаться красная плашка с "Даты пересекаются с бронью #N". Отредактировать, поставить статус "отменена" — бейдж меняется. Удалить. Всё работает.

- [ ] **Step 16.3: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/src/routes/bookings/
git commit -m "feat(frontend): страница /bookings (CRUD + отображение конфликта дат)"
```

---

## Task 17: Страницы `/users` и `/cleaning`

**Files:**
- Create: `frontend/src/routes/users/+page.svelte`
- Create: `frontend/src/routes/cleaning/+page.svelte`

- [ ] **Step 17.1: Создать `frontend/src/routes/users/+page.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';

    let items = $state([]);
    let error = $state('');
    let showForm = $state(false);
    let form = $state({ full_name: '', role: 'admin' });
    const me = getUser();

    async function load() {
        try { items = await api.get('/users'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    function openCreate() {
        form = { full_name: '', role: 'admin' };
        showForm = true; error = '';
    }
    async function save() {
        try { await api.post('/users', form); showForm = false; await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка сохранения'; }
    }
    async function remove(u) {
        if (!confirm(`Удалить пользователя «${u.full_name}»?`)) return;
        try { await api.delete(`/users/${u.id}`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка удаления'; }
    }
</script>

<h1>Пользователи</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

<div class="row" style="margin-bottom:12px">
    <button class="primary" onclick={openCreate}>+ Новый пользователь</button>
</div>

{#if showForm}
    <div class="card">
        <h2>Новый пользователь</h2>
        <div class="grid-form">
            <label>ФИО</label>  <input bind:value={form.full_name} />
            <label>Роль</label>
            <select bind:value={form.role}>
                <option value="owner">owner</option>
                <option value="admin">admin</option>
                <option value="maid">maid</option>
            </select>
        </div>
        <div class="row" style="margin-top:12px; justify-content:flex-end">
            <button onclick={() => showForm = false}>Отмена</button>
            <button class="primary" onclick={save}>Сохранить</button>
        </div>
    </div>
{/if}

<table>
    <thead><tr><th>ФИО</th><th>Роль</th><th></th></tr></thead>
    <tbody>
        {#each items as u}
            <tr>
                <td>{u.full_name}</td>
                <td><span class="badge">{u.role}</span></td>
                <td style="text-align:right">
                    {#if me && me.id !== u.id}
                        <button class="danger" onclick={() => remove(u)}>Удалить</button>
                    {:else}
                        <span class="badge">вы</span>
                    {/if}
                </td>
            </tr>
        {/each}
    </tbody>
</table>
```

- [ ] **Step 17.2: Создать `frontend/src/routes/cleaning/+page.svelte`**

```svelte
<script>
    import { onMount } from 'svelte';
    import { api, ApiError } from '$lib/api.js';

    let items = $state([]);
    let error = $state('');

    async function load() {
        try { items = await api.get('/apartments/cleaning'); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка загрузки'; }
    }
    onMount(load);

    async function markClean(a) {
        try { await api.post(`/apartments/${a.id}/mark-clean`); await load(); }
        catch (e) { error = e instanceof ApiError ? e.detail : 'Ошибка'; }
    }
</script>

<h1>Уборка</h1>

{#if error}<div class="error-banner">{error}</div>{/if}

{#if items.length === 0}
    <div class="card" style="text-align:center">Всё чисто 🎉</div>
{:else}
    <div class="stack">
        {#each items as a}
            <div class="card">
                <div class="row">
                    <div style="flex:1">
                        <strong>{a.title}</strong><br/>
                        <span style="color:var(--muted)">{a.address}</span>
                    </div>
                    <button class="primary" onclick={() => markClean(a)}>Отметить убрано</button>
                </div>
            </div>
        {/each}
    </div>
{/if}
```

- [ ] **Step 17.3: Верификация**

Owner: открыть `/users` — видит всех троих, у себя бейдж "вы", остальных можно удалить. Создать нового админа — появляется в списке.

Переключиться на Admin — в навбаре нет пункта "Пользователи".

Переключиться на Maid: прямой переход на `/cleaning`. Если какая-то квартира помечена "грязно" (через owner/admin на `/apartments`) — она появится карточкой. Кнопка "Отметить убрано" → карточка исчезает. Когда пусто — "Всё чисто 🎉".

Попытка maid зайти на `/apartments` через URL → бэк вернёт 403, фронт покажет error-banner.

- [ ] **Step 17.4: Коммит**

```bash
cd /home/uybaan/fil-crm
git add frontend/src/routes/users/ frontend/src/routes/cleaning/
git commit -m "feat(frontend): страницы /users (owner) и /cleaning (maid)"
```

---

## Task 18: Финальный прогон, README и удаление seed

**Files:**
- Create: `README.md`
- Delete: `backend/seed.py`

- [ ] **Step 18.1: Сквозной прогон**

Поднять бэк и фронт одновременно (два терминала). Пройтись по сценариям:
1. Логин как Хозяин Иван → создать квартиру → создать клиента → создать бронь → увидеть в таблице с join-именами.
2. Пометить квартиру грязной. Выйти.
3. Логин как Горничная Мария → квартира видна в `/cleaning` → "Отметить убрано" → пропадает → "Всё чисто".
4. Логин как Админ Анна → не видит пункт "Пользователи", но видит квартиры/клиентов/брони.
5. Попытка создать пересекающуюся бронь → красная плашка с номером конфликтующей брони.
6. Попытка удалить квартиру с активной бронью → красная плашка "Нельзя удалить…".

Любой найденный баг — пофиксить отдельным коммитом и перепрогнать.

- [ ] **Step 18.2: Написать `README.md`**

Перезаписать `README.md` в корне:

```markdown
# fil-crm

CRM-прототип для посуточной аренды в Якутске. Три роли (owner/admin/maid), сущности квартира/клиент/бронь, флаг "требует уборки".

Стек: Python 3.13 + FastAPI + SQLite (raw queries, без ORM) · SvelteKit · uv · npm.

## Запуск

```bash
# 1. зависимости бэка
uv sync

# 2. зависимости фронта
cd frontend && npm install && cd ..

# 3. бэк на :8000
uv run --env-file .env uvicorn backend.main:app --reload --port 8000

# 4. фронт на :5173 (в другом терминале)
cd frontend && npm run dev -- --port 5173
```

Открыть `http://localhost:5173`.

## Структура

- `backend/` — FastAPI, SQLite, миграции
- `frontend/` — SvelteKit
- `db.sqlite3` — БД (создаётся автоматически при первом запуске)
- `docs/superpowers/` — spec и план реализации

## Примечания

Это прототип. Аутентификации по паролю нет — юзер просто выбирается из списка. Не для продакшена.
```

- [ ] **Step 18.3: Удалить seed-скрипт**

```bash
cd /home/uybaan/fil-crm
rm backend/seed.py
```

- [ ] **Step 18.4: Финальный коммит**

```bash
cd /home/uybaan/fil-crm
git add README.md
git rm backend/seed.py
git commit -m "docs: README + удаление одноразового seed-скрипта"
```

---

## Self-Review (выполнено автором плана)

**Spec coverage:** все разделы спеки покрыты задачами — роли (Task 3), auth (Task 4), users/apartments/clients/bookings (5-8), seed (9), frontend со всеми страницами (10-17), error handling встроен в каждую задачу. Стилизация — минимальная (Task 11.3), соответствует "Стилизация: минимальная".

**Placeholder scan:** нет TBD/TODO, все шаги с кодом содержат реальный код, тестовых плейсхолдеров нет (тестов не пишем по спеке).

**Type consistency:** проверены имена — `require_role` одинаковый во всех роутах, `get_conn` везде, `api.get/post/patch/delete` консистентны на фронте, `ApiError` одинаково используется, поля в JSON-ответах (`apartment_title`, `client_name`) названы одинаково в бэке (bookings.py) и фронте (bookings/+page.svelte).

**Знание Svelte 5:** рун-синтаксис (`$state`, `$derived`, `onclick`) — актуальный для SvelteKit + Svelte 5.
