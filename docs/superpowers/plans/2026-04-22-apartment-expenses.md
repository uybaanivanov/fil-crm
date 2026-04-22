# Apartment Expenses Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Привязать расходы к квартирам, ввести обязательный baseline (аренда + ЖКХ) на каждой квартире, автоматически генерировать ежемесячные записи расходов из baseline.

**Architecture:** Одна таблица `expenses` с nullable `apartment_id` (NULL = общий расход фирмы). Поля `monthly_rent` / `monthly_utilities` на `apartments` — обязательны при PATCH (мягкая миграция существующих). Скрипт `scripts/generate_baseline_expenses.py` раз в месяц создаёт авто-записи с `source='auto'`, идемпотентно через частичный UNIQUE-индекс.

**Tech Stack:** Python (FastAPI, raw sqlite3 без ORM), SvelteKit 5 (runes `$state`/`$derived`), pytest.

**Spec:** `docs/superpowers/specs/2026-04-22-apartment-expenses-design.md`

---

## File Structure

**Backend:**
- Create: `backend/migrations/006_apartment_expenses.sql` — миграция
- Modify: `backend/routes/apartments.py` — добавить поля baseline в модели + валидация в PATCH
- Modify: `backend/routes/expenses.py` — добавить `apartment_id`/`source` + новые фильтры
- Modify: `backend/routes/finance.py` — добавить `by_apartment` в summary

**Скрипт:**
- Create: `scripts/generate_baseline_expenses.py` — самодостаточный, sqlite3 stdlib, без импорта `backend`

**Фронт:**
- Create: `frontend/src/lib/expenseCategories.js` — мапа value↔label
- Create: `frontend/src/lib/ui/EditableField.svelte` — обёртка с пунктиром под полем (обычный / primary)
- Create: `frontend/src/lib/ui/ApartmentExpenses.svelte` — секция расходов на карточке квартиры
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte` — добавить baseline-поля и секцию расходов
- Modify: `frontend/src/routes/apartments/+page.svelte` — значок ⚠ у квартир без baseline
- Modify: `frontend/src/routes/finance/+page.svelte` — фильтр по квартире + блок «По квартирам»

**Тесты:**
- Modify: `tests/test_apartments.py` — PATCH с/без baseline
- Modify: `tests/test_expenses.py` — фильтры apartment_id / only_general
- Create: `tests/test_baseline_script.py` — прогоняет скрипт на тестовой БД
- Modify: `tests/test_finance.py` — `by_apartment` в summary

---

## Task 1: Миграция БД

**Files:**
- Create: `backend/migrations/006_apartment_expenses.sql`

- [ ] **Step 1: Создать миграцию**

```sql
-- 006_apartment_expenses.sql

ALTER TABLE apartments ADD COLUMN monthly_rent INTEGER;
ALTER TABLE apartments ADD COLUMN monthly_utilities INTEGER;

ALTER TABLE expenses ADD COLUMN apartment_id INTEGER REFERENCES apartments(id);
ALTER TABLE expenses ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('manual', 'auto'));

CREATE INDEX idx_expenses_apartment ON expenses(apartment_id);

-- Идемпотентность авто-генерации: одна запись rent/utilities на квартиру в месяц
CREATE UNIQUE INDEX idx_expenses_auto_unique
    ON expenses(apartment_id, category, substr(occurred_at, 1, 7))
    WHERE source = 'auto';
```

- [ ] **Step 2: Применить миграцию локально и проверить схему**

Run:
```bash
uv run --env-file .env python -c "from backend.db import apply_migrations; apply_migrations()"
sqlite3 db.sqlite3 ".schema apartments" | grep -E "monthly_(rent|utilities)"
sqlite3 db.sqlite3 ".schema expenses" | grep -E "apartment_id|source"
sqlite3 db.sqlite3 ".indexes expenses"
```

Expected: видим `monthly_rent`, `monthly_utilities` в apartments; `apartment_id`, `source` в expenses; индексы `idx_expenses_apartment` и `idx_expenses_auto_unique`.

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/006_apartment_expenses.sql
git commit -m "feat(db): миграция 006 — apartment baseline + expenses.apartment_id/source"
```

---

## Task 2: Backend — GET /apartments отдаёт baseline-поля

**Files:**
- Modify: `backend/routes/apartments.py` (константа `SELECT_FIELDS`)
- Modify: `tests/test_apartments.py` (новый тест)

- [ ] **Step 1: Написать падающий тест**

Добавить в `tests/test_apartments.py`:

```python
def test_get_apartment_returns_baseline_fields(client):
    u = seed_user(client, role="owner")
    r = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    )
    apt = r.json()
    assert "monthly_rent" in apt
    assert "monthly_utilities" in apt
    assert apt["monthly_rent"] is None
    assert apt["monthly_utilities"] is None
```

- [ ] **Step 2: Прогнать тест — упадёт**

Run: `uv run pytest tests/test_apartments.py::test_get_apartment_returns_baseline_fields -v`
Expected: FAIL (поля отсутствуют в ответе).

- [ ] **Step 3: Расширить SELECT_FIELDS**

В `backend/routes/apartments.py` заменить константу:

```python
SELECT_FIELDS = (
    "id, title, address, price_per_night, needs_cleaning, cleaning_due_at, "
    "cover_url, rooms, area_m2, floor, district, callsign, source, source_url, "
    "monthly_rent, monthly_utilities, created_at"
)
```

- [ ] **Step 4: Прогнать — проходит**

Run: `uv run pytest tests/test_apartments.py::test_get_apartment_returns_baseline_fields -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/apartments.py tests/test_apartments.py
git commit -m "feat(apartments): отдаём monthly_rent/utilities в API"
```

---

## Task 3: Backend — POST /apartments принимает baseline (опционально)

**Files:**
- Modify: `backend/routes/apartments.py` (`ApartmentIn`)
- Modify: `tests/test_apartments.py`

- [ ] **Step 1: Падающий тест**

```python
def test_create_apartment_with_baseline(client):
    u = seed_user(client, role="owner")
    r = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "A", "address": "X", "price_per_night": 1000,
            "monthly_rent": 50000, "monthly_utilities": 7000,
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["monthly_rent"] == 50000
    assert body["monthly_utilities"] == 7000
```

- [ ] **Step 2: Прогнать — упадёт**

Run: `uv run pytest tests/test_apartments.py::test_create_apartment_with_baseline -v`
Expected: FAIL — Pydantic игнорирует поля либо возвращает NULL.

- [ ] **Step 3: Добавить поля в `ApartmentIn`**

В `backend/routes/apartments.py`:

```python
class ApartmentIn(BaseModel):
    title: str = Field(min_length=1)
    address: str = Field(min_length=1)
    price_per_night: int = Field(gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    callsign: str | None = None
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None
    monthly_rent: int | None = Field(default=None, ge=0)
    monthly_utilities: int | None = Field(default=None, ge=0)
```

- [ ] **Step 4: Прогнать — проходит**

Run: `uv run pytest tests/test_apartments.py::test_create_apartment_with_baseline -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/apartments.py tests/test_apartments.py
git commit -m "feat(apartments): принимаем baseline при создании (опционально)"
```

---

## Task 4: Backend — PATCH /apartments валидирует обязательность baseline

**Files:**
- Modify: `backend/routes/apartments.py` (`ApartmentPatch`, `update_apartment`)
- Modify: `tests/test_apartments.py`

- [ ] **Step 1: Падающие тесты**

```python
def test_patch_apartment_fails_without_baseline(client):
    """У существующей квартиры без baseline любой PATCH падает 400."""
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"price_per_night": 1500},
    )
    assert r.status_code == 400
    assert "monthly_rent" in r.json()["detail"]


def test_patch_apartment_ok_with_baseline_in_payload(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"monthly_rent": 50000, "monthly_utilities": 7000},
    )
    assert r.status_code == 200
    assert r.json()["monthly_rent"] == 50000


def test_patch_apartment_ok_when_baseline_already_in_db(client):
    """Если baseline уже в БД, можно патчить другое поле без него."""
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={
            "title": "A", "address": "X", "price_per_night": 1000,
            "monthly_rent": 40000, "monthly_utilities": 5000,
        },
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"price_per_night": 1500},
    )
    assert r.status_code == 200


def test_patch_apartment_fails_with_only_one_baseline_when_db_empty(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.patch(
        f"/apartments/{apt['id']}",
        headers=auth(u["id"]),
        json={"monthly_rent": 50000},
    )
    assert r.status_code == 400
```

- [ ] **Step 2: Прогнать — все четыре падают**

Run: `uv run pytest tests/test_apartments.py -v -k "baseline"`
Expected: все четыре теста FAIL.

- [ ] **Step 3: Расширить `ApartmentPatch` и `update_apartment`**

В `backend/routes/apartments.py`:

```python
class ApartmentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    price_per_night: int | None = Field(default=None, gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    callsign: str | None = None
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None
    monthly_rent: int | None = Field(default=None, ge=0)
    monthly_utilities: int | None = Field(default=None, ge=0)
```

Заменить тело `update_apartment`:

```python
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
    with get_conn() as conn:
        current = _row(conn, apt_id)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        # После применения patch оба baseline-поля должны быть не-NULL.
        merged_rent = fields.get("monthly_rent", current["monthly_rent"])
        merged_util = fields.get("monthly_utilities", current["monthly_utilities"])
        if merged_rent is None or merged_util is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="monthly_rent и monthly_utilities обязательны",
            )
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [apt_id]
        conn.execute(
            f"UPDATE apartments SET {set_clause} WHERE id = ?", values
        )
        row = _row(conn, apt_id)
    return dict(row)
```

- [ ] **Step 4: Прогнать — проходят**

Run: `uv run pytest tests/test_apartments.py -v -k "baseline or patch_apartment"`
Expected: все проходят. Убедиться что старые PATCH-тесты тоже зелёные (они создают квартиру с baseline уже или патчат с ним).

- [ ] **Step 5: Прогнать весь test_apartments.py — все старые тесты должны пройти**

Run: `uv run pytest tests/test_apartments.py -v`
Expected: все PASS. Если старые PATCH-тесты падают — нужно поправить их: либо сразу создавать с baseline, либо патчить добавляя оба поля. Исправления в тестах делаются в том же шаге.

- [ ] **Step 6: Commit**

```bash
git add backend/routes/apartments.py tests/test_apartments.py
git commit -m "feat(apartments): обязательный baseline при PATCH"
```

---

## Task 5: Backend — `expenses.apartment_id` и `source` в API

**Files:**
- Modify: `backend/routes/expenses.py`
- Modify: `tests/test_expenses.py`

- [ ] **Step 1: Падающие тесты**

```python
def test_create_expense_with_apartment_id(client):
    u = seed_user(client, role="owner")
    apt = client.post(
        "/apartments",
        headers=auth(u["id"]),
        json={"title": "A", "address": "X", "price_per_night": 1000},
    ).json()
    r = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={
            "amount": 1500, "category": "internet",
            "occurred_at": "2026-04-10", "apartment_id": apt["id"],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["apartment_id"] == apt["id"]
    assert body["source"] == "manual"


def test_create_expense_with_invalid_apartment_id(client):
    u = seed_user(client, role="owner")
    r = client.post(
        "/expenses",
        headers=auth(u["id"]),
        json={
            "amount": 1500, "category": "x",
            "occurred_at": "2026-04-10", "apartment_id": 99999,
        },
    )
    assert r.status_code == 400
```

- [ ] **Step 2: Прогнать — FAIL**

Run: `uv run pytest tests/test_expenses.py -v -k "apartment_id"`
Expected: FAIL (поле не принимается / не валидируется).

- [ ] **Step 3: Расширить expenses.py**

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
    apartment_id: int | None = None


class ExpensePatch(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1)
    description: str | None = None
    occurred_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    apartment_id: int | None = None


FIELDS = (
    "id, amount, category, description, occurred_at, "
    "apartment_id, source, created_at"
)


def _row(conn, eid: int):
    return conn.execute(f"SELECT {FIELDS} FROM expenses WHERE id = ?", (eid,)).fetchone()


def _assert_apartment_exists(conn, apt_id: int | None):
    if apt_id is None:
        return
    row = conn.execute("SELECT 1 FROM apartments WHERE id = ?", (apt_id,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Квартира {apt_id} не найдена",
        )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        _assert_apartment_exists(conn, payload.apartment_id)
        cur = conn.execute(
            "INSERT INTO expenses(amount, category, description, occurred_at, apartment_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                payload.amount, payload.category, payload.description,
                payload.occurred_at, payload.apartment_id,
            ),
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления")
    with get_conn() as conn:
        if "apartment_id" in fields:
            _assert_apartment_exists(conn, fields["apartment_id"])
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        cur = conn.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?",
            list(fields.values()) + [eid],
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расход не найден")
        row = _row(conn, eid)
    return dict(row)


@router.delete("/{eid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(eid: int, _: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (eid,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расход не найден")
    return None
```

(Функция `list_expenses` пока оставить как есть — её допишем в Task 6.)

- [ ] **Step 4: Прогнать все тесты expenses — и убедиться что старые ок**

Run: `uv run pytest tests/test_expenses.py -v`
Expected: все PASS, включая новые 2 теста.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/expenses.py tests/test_expenses.py
git commit -m "feat(expenses): apartment_id + source в create/patch/get"
```

---

## Task 6: Backend — GET /expenses фильтры apartment_id / only_general

**Files:**
- Modify: `backend/routes/expenses.py` (`list_expenses`)
- Modify: `tests/test_expenses.py`

- [ ] **Step 1: Падающие тесты**

```python
def test_list_expenses_filter_by_apartment(client):
    u = seed_user(client, role="owner")
    a1 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A1", "address": "x", "price_per_night": 1000}).json()
    a2 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A2", "address": "x", "price_per_night": 1000}).json()
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 100, "category": "x", "occurred_at": "2026-04-01", "apartment_id": a1["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 200, "category": "x", "occurred_at": "2026-04-02", "apartment_id": a2["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 300, "category": "x", "occurred_at": "2026-04-03"})  # общий
    r = client.get(f"/expenses?apartment_id={a1['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["amount"] == 100


def test_list_expenses_only_general(client):
    u = seed_user(client, role="owner")
    a = client.post("/apartments", headers=auth(u["id"]),
                    json={"title": "A", "address": "x", "price_per_night": 1000}).json()
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 100, "category": "x", "occurred_at": "2026-04-01", "apartment_id": a["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 200, "category": "x", "occurred_at": "2026-04-02"})
    r = client.get("/expenses?only_general=true", headers=auth(u["id"]))
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["amount"] == 200


def test_list_expenses_mutually_exclusive_filters(client):
    u = seed_user(client, role="owner")
    r = client.get("/expenses?apartment_id=1&only_general=true", headers=auth(u["id"]))
    assert r.status_code == 400
```

- [ ] **Step 2: Прогнать — FAIL**

Run: `uv run pytest tests/test_expenses.py -v -k "filter_by_apartment or only_general or mutually"`
Expected: FAIL.

- [ ] **Step 3: Переписать `list_expenses`**

В `backend/routes/expenses.py`:

```python
@router.get("")
def list_expenses(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    apartment_id: int | None = Query(None),
    only_general: bool = Query(False),
    _: dict = Depends(require_role("owner", "admin")),
):
    if apartment_id is not None and only_general:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="apartment_id и only_general взаимоисключающие",
        )
    where = []
    params: list = []
    if month:
        where.append("substr(occurred_at, 1, 7) = ?")
        params.append(month)
    if apartment_id is not None:
        where.append("apartment_id = ?")
        params.append(apartment_id)
    if only_general:
        where.append("apartment_id IS NULL")
    sql = f"SELECT {FIELDS} FROM expenses"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY occurred_at DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 4: Прогнать — проходят**

Run: `uv run pytest tests/test_expenses.py -v`
Expected: все PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/expenses.py tests/test_expenses.py
git commit -m "feat(expenses): фильтры apartment_id / only_general"
```

---

## Task 7: Backend — /finance/summary + by_apartment

**Files:**
- Modify: `backend/routes/finance.py`
- Modify: `tests/test_finance.py`

- [ ] **Step 1: Падающий тест**

Добавить в `tests/test_finance.py`:

```python
def test_summary_includes_by_apartment(client):
    u = seed_user(client, role="owner")
    a1 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A1", "address": "x", "price_per_night": 1000}).json()
    a2 = client.post("/apartments", headers=auth(u["id"]),
                     json={"title": "A2", "address": "x", "price_per_night": 1000}).json()
    # расход по квартире и общий
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 5000, "category": "rent", "occurred_at": "2026-04-01",
        "apartment_id": a1["id"]})
    client.post("/expenses", headers=auth(u["id"]), json={
        "amount": 9999, "category": "общий", "occurred_at": "2026-04-02"})
    r = client.get("/finance/summary?month=2026-04", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert "by_apartment" in body
    assert "general_expenses_total" in body
    assert body["general_expenses_total"] == 9999
    # найдём строку с a1
    rows = {x["apartment_id"]: x for x in body["by_apartment"]}
    assert a1["id"] in rows
    assert rows[a1["id"]]["expenses_total"] == 5000
    assert rows[a1["id"]]["title"] == "A1"
    # feed должен содержать apartment_id/apartment_title
    for item in body["feed"]:
        if item["type"] == "expense":
            assert "apartment_id" in item
            assert "apartment_title" in item
```

- [ ] **Step 2: Прогнать — FAIL**

Run: `uv run pytest tests/test_finance.py::test_summary_includes_by_apartment -v`
Expected: FAIL (поле отсутствует).

- [ ] **Step 3: Переписать `summary`**

В `backend/routes/finance.py` заменить функцию `summary`:

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
                "SELECT id, apartment_id, check_in, check_out, total_price, status, "
                "(SELECT full_name FROM clients WHERE clients.id = bookings.client_id) AS client_name "
                "FROM bookings "
                "WHERE check_out > ? AND check_in < ? AND status != 'cancelled'",
                (p_start.isoformat(), p_end.isoformat()),
            ).fetchall()
        ]
        expenses = [
            dict(r) for r in conn.execute(
                "SELECT e.id, e.amount, e.category, e.description, e.occurred_at, "
                "e.apartment_id, e.source, a.title AS apartment_title "
                "FROM expenses e LEFT JOIN apartments a ON a.id = e.apartment_id "
                "WHERE substr(e.occurred_at, 1, 7) = ? ORDER BY e.occurred_at DESC",
                (ym,),
            ).fetchall()
        ]
        apartments = [
            dict(r) for r in conn.execute(
                "SELECT id, title FROM apartments"
            ).fetchall()
        ]
    agg = aggregate_bookings_in_period(bookings, p_start, p_end)
    revenue = agg["revenue"]
    expenses_total = sum(e["amount"] for e in expenses)
    general_expenses_total = sum(e["amount"] for e in expenses if e["apartment_id"] is None)
    by_category: dict[str, int] = {}
    for e in expenses:
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]

    # Разбивка по квартирам
    by_apt_map: dict[int, dict] = {}
    for a in apartments:
        by_apt_map[a["id"]] = {
            "apartment_id": a["id"], "title": a["title"],
            "revenue": 0, "expenses_total": 0, "net": 0,
        }
    # Revenue по квартирам — через aggregate на их подмножестве броней
    for apt_id, row in by_apt_map.items():
        apt_bookings = [b for b in bookings if b["apartment_id"] == apt_id]
        apt_agg = aggregate_bookings_in_period(apt_bookings, p_start, p_end)
        row["revenue"] = apt_agg["revenue"]
    for e in expenses:
        if e["apartment_id"] is not None and e["apartment_id"] in by_apt_map:
            by_apt_map[e["apartment_id"]]["expenses_total"] += e["amount"]
    for row in by_apt_map.values():
        row["net"] = row["revenue"] - row["expenses_total"]
    by_apartment = sorted(by_apt_map.values(), key=lambda x: x["net"], reverse=True)

    feed = []
    for b in bookings:
        feed.append({
            "type": "income",
            "amount": b["total_price"],
            "label": f"Бронь {b['client_name'] or ''}".strip(),
            "dt": b["check_out"],
            "ref": {"booking_id": b["id"]},
        })
    for e in expenses:
        feed.append({
            "type": "expense",
            "amount": e["amount"],
            "label": f"{e['category']}"
                + (f" · {e['description']}" if e["description"] else ""),
            "dt": e["occurred_at"],
            "ref": {"expense_id": e["id"]},
            "apartment_id": e["apartment_id"],
            "apartment_title": e["apartment_title"],
            "source": e["source"],
        })
    feed.sort(key=lambda x: x["dt"], reverse=True)

    return {
        "month": ym,
        "revenue": revenue,
        "expenses_total": expenses_total,
        "general_expenses_total": general_expenses_total,
        "net": revenue - expenses_total,
        "by_category": by_category,
        "by_apartment": by_apartment,
        "feed": feed,
    }
```

- [ ] **Step 4: Прогнать все тесты finance**

Run: `uv run pytest tests/test_finance.py -v`
Expected: все PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/finance.py tests/test_finance.py
git commit -m "feat(finance): by_apartment + general_expenses_total + apartment в feed"
```

---

## Task 8: Скрипт generate_baseline_expenses.py

**Files:**
- Create: `scripts/generate_baseline_expenses.py`
- Create: `tests/test_baseline_script.py`

- [ ] **Step 1: Падающий тест**

Создать `tests/test_baseline_script.py`:

```python
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "generate_baseline_expenses.py"


def _init_schema(db_path: Path) -> None:
    from backend.db import MIGRATIONS_DIR
    conn = sqlite3.connect(str(db_path))
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.executescript(f.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()


def _run_script(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DB_PATH": str(db_path)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env, capture_output=True, text=True, check=False,
    )


def _setup_db(tmp_path):
    db = tmp_path / "t.sqlite3"
    _init_schema(db)
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        INSERT INTO apartments(title, address, price_per_night, monthly_rent, monthly_utilities)
        VALUES ('A1', 'x', 1000, 50000, 7000);
        INSERT INTO apartments(title, address, price_per_night, monthly_rent, monthly_utilities)
        VALUES ('A2', 'y', 1000, 30000, 5000);
        INSERT INTO apartments(title, address, price_per_night)
        VALUES ('A3 no baseline', 'z', 1000);
        """
    )
    conn.commit()
    conn.close()
    return db


def test_script_creates_two_records_per_apartment(tmp_path):
    db = _setup_db(tmp_path)
    r = _run_script(db, "--month", "2026-04")
    assert r.returncode == 0, r.stderr
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT apartment_id, category, amount, source, occurred_at FROM expenses"
    ).fetchall()
    conn.close()
    # Две квартиры × 2 записи
    assert len(rows) == 4
    for row in rows:
        assert row[3] == "auto"
        assert row[4] == "2026-04-01"
    cats = sorted({r[1] for r in rows})
    assert cats == ["rent", "utilities"]


def test_script_skips_apartments_without_baseline(tmp_path):
    db = _setup_db(tmp_path)
    r = _run_script(db, "--month", "2026-04")
    assert r.returncode == 0
    conn = sqlite3.connect(str(db))
    apt_ids = {row[0] for row in conn.execute("SELECT apartment_id FROM expenses").fetchall()}
    conn.close()
    # A3 (id=3) не должен попасть
    assert 3 not in apt_ids


def test_script_is_idempotent(tmp_path):
    db = _setup_db(tmp_path)
    _run_script(db, "--month", "2026-04")
    _run_script(db, "--month", "2026-04")
    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    assert count == 4


def test_script_month_flag(tmp_path):
    db = _setup_db(tmp_path)
    _run_script(db, "--month", "2026-03")
    _run_script(db, "--month", "2026-04")
    conn = sqlite3.connect(str(db))
    months = {row[0] for row in conn.execute(
        "SELECT substr(occurred_at,1,7) FROM expenses").fetchall()}
    conn.close()
    assert months == {"2026-03", "2026-04"}


def test_script_dry_run_writes_nothing(tmp_path):
    db = _setup_db(tmp_path)
    r = _run_script(db, "--month", "2026-04", "--dry-run")
    assert r.returncode == 0
    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    assert count == 0
```

- [ ] **Step 2: Прогнать — FAIL (скрипта нет)**

Run: `uv run pytest tests/test_baseline_script.py -v`
Expected: все тесты FAIL.

- [ ] **Step 3: Создать скрипт**

`scripts/generate_baseline_expenses.py`:

```python
#!/usr/bin/env python3
"""Генерирует ежемесячные авто-записи расходов (rent/utilities) из baseline-полей квартир.

Самодостаточный, не импортирует backend. Идемпотентен через UNIQUE-индекс
expenses.idx_expenses_auto_unique.
"""
import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path


def run(db_path: Path, month: str, dry_run: bool) -> int:
    occurred_at = f"{month}-01"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        apartments = conn.execute(
            "SELECT id, monthly_rent, monthly_utilities FROM apartments "
            "WHERE monthly_rent IS NOT NULL AND monthly_utilities IS NOT NULL"
        ).fetchall()
        created = 0
        skipped = 0
        for apt_id, rent, util in apartments:
            for category, amount in (("rent", rent), ("utilities", util)):
                if dry_run:
                    created += 1
                    continue
                cur = conn.execute(
                    "INSERT INTO expenses(amount, category, description, occurred_at, "
                    "apartment_id, source) "
                    "VALUES (?, ?, 'auto-generated', ?, ?, 'auto') "
                    "ON CONFLICT DO NOTHING",
                    (amount, category, occurred_at, apt_id),
                )
                if cur.rowcount == 1:
                    created += 1
                else:
                    skipped += 1
        if not dry_run:
            conn.commit()
        prefix = "[DRY RUN] " if dry_run else ""
        print(f"{prefix}baseline-expenses for {month}: created={created} skipped={skipped}")
        return 0
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--month", default=date.today().strftime("%Y-%m"),
        help="YYYY-MM; по умолчанию текущий",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db_path = Path(os.environ.get("DB_PATH", "db.sqlite3"))
    if not db_path.exists():
        print(f"DB not found: {db_path}", file=sys.stderr)
        return 1
    if len(args.month) != 7 or args.month[4] != "-":
        print(f"--month must be YYYY-MM, got {args.month!r}", file=sys.stderr)
        return 1
    return run(db_path, args.month, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Прогнать тесты**

Run: `uv run pytest tests/test_baseline_script.py -v`
Expected: все 5 тестов PASS.

- [ ] **Step 5: Проверить вручную на деве**

```bash
uv run --env-file .env scripts/generate_baseline_expenses.py --month 2026-04 --dry-run
```

Expected: вывод `[DRY RUN] baseline-expenses for 2026-04: created=N skipped=0` (N = кол-во квартир с заполненным baseline).

- [ ] **Step 6: Commit**

```bash
git add scripts/generate_baseline_expenses.py tests/test_baseline_script.py
git commit -m "feat(scripts): generate_baseline_expenses + тесты"
```

---

## Task 9: Фронт — библиотека категорий

**Files:**
- Create: `frontend/src/lib/expenseCategories.js`

- [ ] **Step 1: Создать модуль**

```javascript
// value = то что летит в БД; label = отображается в UI.
export const EXPENSE_CATEGORIES = [
    { value: 'rent',      label: 'Аренда' },
    { value: 'utilities', label: 'ЖКХ' },
    { value: 'internet',  label: 'Интернет' },
    { value: 'repair',    label: 'Ремонт' },
    { value: 'furniture', label: 'Мебель' },
    { value: 'supplies',  label: 'Расходники' },
    { value: 'other',     label: 'Прочее' },
];

export function categoryLabel(value) {
    const found = EXPENSE_CATEGORIES.find(c => c.value === value);
    return found ? found.label : value;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/expenseCategories.js
git commit -m "feat(frontend): expenseCategories — value↔label мапа"
```

---

## Task 10: Фронт — EditableField компонент с пунктиром

**Files:**
- Create: `frontend/src/lib/ui/EditableField.svelte`

- [ ] **Step 1: Создать компонент**

```svelte
<!--
  Обёртка для редактируемого поля.
  Отображает метку сверху и слот с инпутом внутри; под инпутом
  рисуется пунктирная линия (обычная или primary для required).
  Внутри слота ожидается обычный <input>/<select>; border-bottom
  даётся контейнеру, а инпут внутри — transparent без рамки.
-->
<script>
    let {
        label,
        required = false,
        error = null,
        hint = null,
        children,
    } = $props();
</script>

<label class="field" class:required class:has-error={!!error}>
    <span class="lbl">
        {label}
        {#if required}<span class="req">*</span>{/if}
    </span>
    <div class="slot">
        {@render children()}
    </div>
    {#if error}
        <span class="err">{error}</span>
    {:else if hint}
        <span class="hint">{hint}</span>
    {:else if required}
        <span class="hint">Обязательно для сохранения</span>
    {/if}
</label>

<style>
    .field {
        display: flex;
        flex-direction: column;
        gap: 4px;
        padding: 6px 0 4px;
        border-bottom: 1px dashed var(--border);
    }
    .field.required { border-bottom-color: var(--primary, var(--accent)); }
    .field.has-error { border-bottom-color: var(--danger, #c33); }
    .lbl {
        font-family: var(--font-mono);
        font-size: 10px;
        text-transform: uppercase;
        color: var(--faint);
    }
    .req { color: var(--primary, var(--accent)); margin-left: 2px; }
    .slot :global(input),
    .slot :global(select) {
        width: 100%;
        border: none;
        outline: none;
        background: transparent;
        font-size: 13px;
        color: var(--ink);
        padding: 2px 0;
    }
    .slot :global(input:focus),
    .slot :global(select:focus) {
        outline: none;
    }
    .hint {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--faint);
    }
    .err {
        font-family: var(--font-mono);
        font-size: 10px;
        color: var(--danger, #c33);
    }
</style>
```

- [ ] **Step 2: Проверить что билд фронта не ломается**

Run:
```bash
cd frontend && npm run build
```

Expected: успешная сборка без ошибок.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/ui/EditableField.svelte
git commit -m "feat(frontend): EditableField — пунктир под полем, primary для required"
```

---

## Task 11: Фронт — секция расходов на карточке квартиры

**Files:**
- Create: `frontend/src/lib/ui/ApartmentExpenses.svelte`

- [ ] **Step 1: Создать компонент**

```svelte
<!--
  Секция «Расходы по квартире» — список с переключателем месяца и формой добавления.
-->
<script>
    import { api } from '$lib/api.js';
    import { EXPENSE_CATEGORIES, categoryLabel } from '$lib/expenseCategories.js';
    import { fmtRub, fmtDate } from '$lib/format.js';

    let { apartmentId } = $props();

    const today = new Date();
    let month = $state(new Date().toISOString().slice(0, 7));
    let items = $state([]);
    let loading = $state(false);
    let error = $state(null);

    let addOpen = $state(false);
    let addAmount = $state('');
    let addCategory = $state('internet');
    let addDescription = $state('');
    let addDate = $state(new Date().toISOString().slice(0, 10));
    let addError = $state(null);

    async function load() {
        loading = true;
        error = null;
        try {
            items = await api.get(
                `/expenses?apartment_id=${apartmentId}&month=${month}`
            );
        } catch (e) {
            error = e.message;
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        if (apartmentId) load();
    });

    function shiftMonth(delta) {
        const [y, m] = month.split('-').map(Number);
        const d = new Date(y, m - 1 + delta, 1);
        month = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    }

    async function saveExpense() {
        addError = null;
        const amount = parseInt(addAmount, 10);
        if (!amount || amount <= 0) { addError = 'Сумма > 0'; return; }
        try {
            await api.post('/expenses', {
                amount,
                category: addCategory,
                description: addDescription || null,
                occurred_at: addDate,
                apartment_id: apartmentId,
            });
            addOpen = false;
            addAmount = '';
            addDescription = '';
            await load();
        } catch (e) {
            addError = e.message;
        }
    }

    const total = $derived(items.reduce((s, x) => s + x.amount, 0));
</script>

<div class="expenses">
    <header>
        <button type="button" class="nav" onclick={() => shiftMonth(-1)}>‹</button>
        <span class="month">{month}</span>
        <button type="button" class="nav" onclick={() => shiftMonth(1)}>›</button>
        <span class="total">{fmtRub(total)}</span>
        <button type="button" class="add" onclick={() => (addOpen = !addOpen)}>
            {addOpen ? '×' : '+'}
        </button>
    </header>

    {#if addOpen}
        <div class="add-form">
            <input type="number" placeholder="Сумма" bind:value={addAmount} />
            <select bind:value={addCategory}>
                {#each EXPENSE_CATEGORIES as c}
                    <option value={c.value}>{c.label}</option>
                {/each}
            </select>
            <input type="date" bind:value={addDate} />
            <input type="text" placeholder="Описание" bind:value={addDescription} />
            {#if addError}<div class="err">{addError}</div>{/if}
            <button type="button" class="save" onclick={saveExpense}>Сохранить</button>
        </div>
    {/if}

    {#if loading}
        <div class="state">Загрузка…</div>
    {:else if error}
        <div class="state err">{error}</div>
    {:else if items.length === 0}
        <div class="state muted">Нет расходов</div>
    {:else}
        <ul class="list">
            {#each items as e}
                <li class="row">
                    <span class="date">{fmtDate(e.occurred_at)}</span>
                    <span class="cat">
                        {categoryLabel(e.category)}
                        {#if e.source === 'auto'}<span class="auto" title="Авто-генерация">⚙</span>{/if}
                    </span>
                    {#if e.description}<span class="desc">{e.description}</span>{/if}
                    <span class="amt">{fmtRub(e.amount)}</span>
                </li>
            {/each}
        </ul>
    {/if}
</div>

<style>
    .expenses { padding: 0 20px 14px; }
    header {
        display: flex; align-items: center; gap: 8px;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
    }
    .nav {
        background: none; border: none; cursor: pointer;
        font-size: 18px; color: var(--muted);
    }
    .month { font-family: var(--font-mono); font-size: 12px; color: var(--ink); }
    .total { margin-left: auto; font-family: var(--font-mono); font-weight: 600; color: var(--ink); }
    .add {
        margin-left: 8px;
        background: var(--accent); color: #fff; border: none;
        width: 28px; height: 28px; border-radius: 6px; cursor: pointer;
    }
    .add-form {
        display: flex; flex-direction: column; gap: 6px;
        padding: 10px 0;
        border-bottom: 1px solid var(--border-soft);
    }
    .add-form input, .add-form select {
        height: 32px; padding: 0 8px;
        border: 1px solid var(--border); border-radius: 4px;
        background: var(--card); color: var(--ink);
    }
    .save {
        height: 34px; border: none; border-radius: 4px;
        background: var(--accent); color: #fff; font-weight: 600; cursor: pointer;
    }
    .list { list-style: none; padding: 0; margin: 0; }
    .row {
        display: grid;
        grid-template-columns: 68px 1fr auto;
        gap: 6px;
        padding: 8px 0;
        border-bottom: 1px solid var(--border-soft);
        font-size: 13px;
    }
    .date { font-family: var(--font-mono); font-size: 11px; color: var(--faint); }
    .cat { color: var(--ink); }
    .auto { margin-left: 4px; color: var(--faint); }
    .desc { grid-column: 2; font-size: 11px; color: var(--muted); }
    .amt { font-family: var(--font-mono); font-weight: 600; color: var(--ink); }
    .state { padding: 14px 0; text-align: center; color: var(--faint); font-size: 12px; }
    .state.err { color: var(--danger, #c33); }
    .state.muted { color: var(--faint); }
    .err { color: var(--danger, #c33); font-size: 11px; }
</style>
```

- [ ] **Step 2: Проверить билд**

Run: `cd frontend && npm run build`
Expected: успешная сборка.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/ui/ApartmentExpenses.svelte
git commit -m "feat(frontend): ApartmentExpenses — секция расходов с переключателем месяца"
```

---

## Task 12: Фронт — карточка квартиры, baseline-поля + секция расходов

**Files:**
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`

- [ ] **Step 1: Добавить стейт и импорты**

В верх `<script>` блока добавить импорты:

```javascript
import EditableField from '$lib/ui/EditableField.svelte';
import ApartmentExpenses from '$lib/ui/ApartmentExpenses.svelte';
```

И добавить state для baseline:

```javascript
let editingBaseline = $state(false);
let baselineRent = $state('');
let baselineUtilities = $state('');
let baselineError = $state(null);
let baselineErrorField = $state(null); // 'rent' | 'utilities' | null
```

- [ ] **Step 2: Добавить функции инициализации и сохранения baseline**

После `async function load()` добавить:

```javascript
function startEditBaseline() {
    baselineRent = apt.monthly_rent ?? '';
    baselineUtilities = apt.monthly_utilities ?? '';
    baselineError = null;
    baselineErrorField = null;
    editingBaseline = true;
}

async function saveBaseline() {
    baselineError = null;
    baselineErrorField = null;
    const rent = parseInt(baselineRent, 10);
    const util = parseInt(baselineUtilities, 10);
    if (!rent || rent < 0) {
        baselineError = 'Укажи аренду';
        baselineErrorField = 'rent';
        return;
    }
    if (!util || util < 0) {
        baselineError = 'Укажи ЖКХ';
        baselineErrorField = 'utilities';
        return;
    }
    try {
        await api.patch(`/apartments/${aptId}`, {
            monthly_rent: rent,
            monthly_utilities: util,
        });
        editingBaseline = false;
        await load();
    } catch (e) {
        baselineError = e.message;
    }
}
```

- [ ] **Step 3: Добавить блок baseline в разметку перед секцией «Характеристики»**

Вставить **после** блока `{#if currentGuest}...{/if}` и **до** секции `<Section title="Характеристики">`:

```svelte
<Section title="Обязательные суммы">
    <div class="wrap">
        <Card pad={14}>
            {#if editingBaseline}
                <div class="bl-form">
                    <EditableField
                        label="Аренда помещения / мес"
                        required
                        error={baselineErrorField === 'rent' ? baselineError : null}
                    >
                        <input type="number" bind:value={baselineRent} placeholder="₽" />
                    </EditableField>
                    <EditableField
                        label="ЖКХ / мес"
                        required
                        error={baselineErrorField === 'utilities' ? baselineError : null}
                    >
                        <input type="number" bind:value={baselineUtilities} placeholder="₽" />
                    </EditableField>
                    {#if baselineError && !baselineErrorField}
                        <div class="err-banner">{baselineError}</div>
                    {/if}
                    <div class="bl-actions">
                        <button type="button" class="ghost"
                            onclick={() => (editingBaseline = false)}>Отмена</button>
                        <button type="button" class="primary" onclick={saveBaseline}>Сохранить</button>
                    </div>
                </div>
            {:else}
                <div class="bl-row"
                    class:empty={apt.monthly_rent == null}>
                    <span>Аренда / мес</span>
                    <span>{apt.monthly_rent != null ? fmtRub(apt.monthly_rent) : '— не заполнено'}</span>
                </div>
                <div class="bl-row"
                    class:empty={apt.monthly_utilities == null}>
                    <span>ЖКХ / мес</span>
                    <span>{apt.monthly_utilities != null ? fmtRub(apt.monthly_utilities) : '— не заполнено'}</span>
                </div>
                <button type="button" class="ghost bl-edit" onclick={startEditBaseline}>
                    {apt.monthly_rent == null || apt.monthly_utilities == null
                        ? 'Заполнить обязательные'
                        : 'Изменить'}
                </button>
            {/if}
        </Card>
    </div>
</Section>

<Section title="Расходы">
    <ApartmentExpenses apartmentId={aptId} />
</Section>
```

- [ ] **Step 4: Добавить стили в `<style>`**

```css
.bl-form { display: flex; flex-direction: column; gap: 10px; }
.bl-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 6px; }
.bl-row {
    display: flex; justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid var(--border-soft);
    font-size: 13px;
}
.bl-row:last-of-type { border-bottom: none; }
.bl-row.empty { color: var(--danger, #c33); }
.bl-edit { margin-top: 10px; width: 100%; }
.err-banner {
    background: var(--danger-bg, #fde);
    color: var(--danger, #c33);
    padding: 6px 8px; border-radius: 4px;
    font-size: 12px;
}
```

- [ ] **Step 5: Проверить билд**

Run: `cd frontend && npm run build`
Expected: успех.

- [ ] **Step 6: Руками проверить в браузере**

Запустить дев:
```bash
./start.sh
```
(или вручную `uv run --env-file .env uvicorn backend.main:app --reload` + `cd frontend && npm run dev`)

Открыть существующую квартиру → видим «Обязательные суммы» с красным статусом и кнопкой «Заполнить обязательные». Открыть форму, заполнить оба поля, сохранить — карточка обновляется. Попытаться очистить одно поле и сохранить — видим ошибку.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/routes/apartments/\[id\]/+page.svelte
git commit -m "feat(frontend): baseline-поля и секция расходов на карточке квартиры"
```

---

## Task 13: Фронт — значок ⚠ в списке квартир

**Files:**
- Modify: `frontend/src/routes/apartments/+page.svelte`

- [ ] **Step 1: Прочитать текущее состояние файла**

Run: `cat frontend/src/routes/apartments/+page.svelte | head -100`
(Для понимания существующей разметки списка — вставить значок рядом с заголовком квартиры.)

- [ ] **Step 2: Добавить маркер рядом с title**

В шаблон, там где рендерится заголовок квартиры в списке, добавить:

```svelte
{#if apt.monthly_rent == null || apt.monthly_utilities == null}
    <span class="no-baseline" title="Не заполнен baseline (аренда/ЖКХ)">⚠</span>
{/if}
```

И стиль:

```css
.no-baseline { color: var(--caution, #e80); margin-left: 6px; }
```

- [ ] **Step 3: Проверить билд**

Run: `cd frontend && npm run build`
Expected: успех.

- [ ] **Step 4: Проверить в браузере**

Открыть `/apartments` — у квартир без заполненного baseline виден значок ⚠.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/apartments/+page.svelte
git commit -m "feat(frontend): ⚠ у квартир без заполненного baseline"
```

---

## Task 14: Фронт — /finance фильтр по квартире + блок «По квартирам»

**Files:**
- Modify: `frontend/src/routes/finance/+page.svelte`

- [ ] **Step 1: Добавить state и загрузку квартир**

В `<script>` добавить:

```javascript
let apartments = $state([]);
let filterApt = $state('all'); // 'all' | 'general' | <id>
```

Изменить `load()`:

```javascript
async function load() {
    loading = true;
    try {
        const [summary, apts] = await Promise.all([
            api.get(`/finance/summary?month=${currentMonth}`),
            api.get('/apartments')
        ]);
        data = summary;
        apartments = apts;
    } catch (e) {
        error = e.message;
    } finally {
        loading = false;
    }
}
```

- [ ] **Step 2: В разметке добавить фильтр и блок «По квартирам»**

Найти существующий блок сводки и добавить перед feed:

```svelte
{#if data}
    <Section title="Фильтр">
        <div class="wrap">
            <select class="apt-filter" bind:value={filterApt}>
                <option value="all">Все</option>
                <option value="general">Только общие</option>
                {#each apartments as a}
                    <option value={String(a.id)}>{a.title}</option>
                {/each}
            </select>
        </div>
    </Section>

    {#if data.by_apartment?.length}
        <Section title="По квартирам">
            <div class="wrap">
                <Card pad={0}>
                    {#each data.by_apartment as row, i}
                        <div class="apt-row" class:last={i === data.by_apartment.length - 1}>
                            <a class="name" href={`/apartments/${row.apartment_id}`}>{row.title}</a>
                            <span class="rev">{fmtShortRub(row.revenue)}</span>
                            <span class="exp">−{fmtShortRub(row.expenses_total)}</span>
                            <span class="net" class:pos={row.net >= 0} class:neg={row.net < 0}>
                                {fmtShortRub(row.net)}
                            </span>
                        </div>
                    {/each}
                </Card>
            </div>
        </Section>
    {/if}
{/if}
```

Где feed рендерится — оставить как есть, но фильтровать:

```svelte
{#each data.feed.filter(f => {
    if (filterApt === 'all') return true;
    if (filterApt === 'general') return f.type === 'income' || f.apartment_id == null;
    return f.type === 'income' ? false : String(f.apartment_id) === filterApt;
}) as item}
    ...существующая разметка, при этом у expense-строк показать apartment_title если есть...
{/each}
```

(Если вокруг много кода, оставить фильтр простым — можно и без income-фильтра, если «Фильтр квартиры» трактовать только для расходов.)

- [ ] **Step 3: Стили**

```css
.apt-filter {
    width: 100%;
    height: 36px;
    padding: 0 10px;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--card);
    color: var(--ink);
}
.apt-row {
    display: grid;
    grid-template-columns: 1fr 80px 80px 80px;
    gap: 8px;
    padding: 10px 12px;
    border-bottom: 1px solid var(--border-soft);
    align-items: center;
    font-size: 13px;
}
.apt-row.last { border-bottom: none; }
.apt-row .name { color: var(--ink); text-decoration: none; }
.apt-row .rev { color: var(--positive, #2a8); text-align: right; font-family: var(--font-mono); }
.apt-row .exp { color: var(--danger, #c33); text-align: right; font-family: var(--font-mono); }
.apt-row .net { text-align: right; font-family: var(--font-mono); font-weight: 600; }
.apt-row .net.pos { color: var(--positive, #2a8); }
.apt-row .net.neg { color: var(--danger, #c33); }
```

- [ ] **Step 4: Проверить билд**

Run: `cd frontend && npm run build`
Expected: успех.

- [ ] **Step 5: Проверить в браузере**

Открыть `/finance`. Убедиться:
- появился блок «Фильтр» с селектом квартир.
- появился блок «По квартирам» с доход/расход/чистая.
- смена фильтра меняет видимые в feed расходы.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/finance/+page.svelte
git commit -m "feat(frontend): /finance — фильтр по квартире + блок «По квартирам»"
```

---

## Task 15: Форма «+ расход» в /finance — использовать правильные категории и apartment_id

**Files:**
- Modify: `frontend/src/routes/finance/+page.svelte`

- [ ] **Step 1: Заменить локальный массив `CATS` на импорт**

В `<script>`:

```javascript
import { EXPENSE_CATEGORIES } from '$lib/expenseCategories.js';
```

Удалить строку `const CATS = ['Уборка', 'ЖКХ', 'Ремонт', 'Комиссии', 'Прочее'];`.

Инициализировать `addCategory` значением `'other'` (вместо старого `'Уборка'`).

- [ ] **Step 2: Добавить стейт apartment и опциональный селект**

```javascript
let addApartmentId = $state(''); // '' = общий
```

- [ ] **Step 3: В форме заменить селект категорий и добавить селект квартиры**

```svelte
<select bind:value={addCategory}>
    {#each EXPENSE_CATEGORIES as c}
        <option value={c.value}>{c.label}</option>
    {/each}
</select>

<select bind:value={addApartmentId}>
    <option value="">Общий расход</option>
    {#each apartments as a}
        <option value={String(a.id)}>{a.title}</option>
    {/each}
</select>
```

- [ ] **Step 4: Изменить `saveExpense`**

```javascript
await api.post('/expenses', {
    amount,
    category: addCategory,
    description: addDescription || null,
    occurred_at: addDate,
    apartment_id: addApartmentId === '' ? null : parseInt(addApartmentId, 10),
});
```

- [ ] **Step 5: Проверить билд и руками**

Run: `cd frontend && npm run build`
Проверить в браузере: `/finance` → «+ расход» → можно выбрать квартиру или «Общий». После сохранения — расход попадает в фильтр корректно.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/finance/+page.svelte
git commit -m "feat(frontend): /finance — использовать общий список категорий + выбор квартиры"
```

---

## Task 16: Cron-рецепт в README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Добавить раздел «Cron» в README**

В конец README добавить:

```markdown
## Cron на проде

Генерация ежемесячных baseline-расходов (аренда/ЖКХ):

```
0 3 1 * * cd /opt/fil-crm && uv run --env-file .env scripts/generate_baseline_expenses.py >> /var/log/fil-crm/baseline.log 2>&1
```

Скрипт идемпотентен: повторные запуски не дублируют записи. Для догона пропущенного месяца:

```
uv run --env-file .env scripts/generate_baseline_expenses.py --month 2026-04
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs(readme): cron-рецепт для generate_baseline_expenses"
```

---

## Task 17: Полный прогон тестов и чек-смок всего флоу

- [ ] **Step 1: Все тесты**

Run: `uv run pytest -v`
Expected: все PASS. Особое внимание — test_apartments, test_expenses, test_finance, test_baseline_script, test_authz (если там что-то зацепилось).

- [ ] **Step 2: Билд фронта**

Run: `cd frontend && npm run build`
Expected: успех.

- [ ] **Step 3: Ручной смок-тест (в браузере)**

Поднять дев, пройти сценарий:
1. Создать новую квартиру без baseline → открыть её → попробовать PATCH price_per_night → должна падать 400 на бэке, форма baseline обязательна на фронте.
2. Заполнить baseline → сохранить → оба поля отображаются, значок ⚠ в списке пропадает.
3. Добавить расход из карточки квартиры → он появляется в списке с русским лейблом категории.
4. Запустить скрипт: `uv run --env-file .env scripts/generate_baseline_expenses.py --month 2026-04` → открыть карточку, видим 2 авто-записи с ⚙.
5. Открыть `/finance` → блок «По квартирам» показывает эту квартиру с расходами включая авто-записи.
6. Переключить фильтр на «Только общие» → в feed остаются только общие расходы.

- [ ] **Step 4: Финальный commit (если что-то поправилось по ходу смока)**

Если смок нашёл что-то — исправить в том же шаге и закоммитить. Если всё ок — никакого коммита не нужно.

---

## Out of Scope (напоминание из spec)

- История изменения baseline — если аренда поменяется, применится к следующему cron-запуску; старые `auto`-записи не пересчитываются.
- Авто-удаление/пересчёт expenses при удалении квартиры.
- Гранулярные роли на категории расходов.
- Отчёт «план/факт» — план и факт сейчас одно и то же.
