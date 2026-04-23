# Источники броней, шахматка-адреса, кликабельные сводки, кнопка договора — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перенести `source` с клиента на бронь (с расширением списка каналов), показать сокращённые адреса в шахматке, сделать брони кликабельными в карточке квартиры и /finance, добавить кнопку «Сделать договор» с двухшаговой модалкой-заглушкой.

**Architecture:** Тонкая миграция БД с переносом данных. Бэкенд — точечные правки SELECT/INSERT/Pydantic-моделей в `bookings.py` и `clients.py`. Фронт — точечные правки шести Svelte-страниц + новый компонент модалки + одна утилита формата + один константный модуль. Бэкенд для генерации договора в скоуп НЕ входит.

**Tech Stack:** SQLite (raw SQL, без ORM), FastAPI + Pydantic, SvelteKit (Svelte 5 runes), pytest.

**Spec:** `docs/superpowers/specs/2026-04-23-bookings-source-and-contract-design.md`

---

## File Structure

**Создаём:**

- `backend/migrations/010_booking_source.sql` — миграция БД.
- `frontend/src/lib/sources.js` — канонический список каналов броней.
- `frontend/src/lib/ui/ContractModal.svelte` — двухшаговая модалка «Сделать договор».

**Модифицируем:**

- `backend/routes/bookings.py` — добавить `source` в Pydantic, SELECT, INSERT.
- `backend/routes/clients.py` — убрать `source` из Pydantic, SELECT, INSERT.
- `frontend/src/lib/format.js` — функция `shortAddress`.
- `frontend/src/routes/bookings/new/+page.svelte` — секция «Источник», убрать `newSource` из inline-формы клиента.
- `frontend/src/routes/bookings/[id]/+page.svelte` — chip и подзаголовок source, секция «Договор» + ContractModal.
- `frontend/src/routes/clients/[id]/+page.svelte` — убрать строку `source`.
- `frontend/src/routes/calendar/+page.svelte` — сокращённый адрес в name-col, убрать второй запрос, удалить `.cs`-стиль.
- `frontend/src/routes/apartments/[id]/+page.svelte` — сделать `.guest-range` кликабельной кнопкой.
- `frontend/src/routes/finance/+page.svelte` — кликабельные строки feed.

**Тесты:**

- `tests/test_bookings.py` — добавить тесты на `source`.
- `tests/test_clients.py` — обновить (убрать асёрты на `source`, если есть).

---

## Task 1: Миграция БД — `bookings.source` + перенос + drop `clients.source`

**Files:**
- Create: `backend/migrations/010_booking_source.sql`
- Test: ручная проверка через pytest существующих тестов (миграции применяются автоматически в `apply_migrations()`)

- [ ] **Step 1: Создать файл миграции**

Файл `backend/migrations/010_booking_source.sql`:

```sql
ALTER TABLE bookings ADD COLUMN source TEXT;

UPDATE bookings
SET source = (SELECT source FROM clients WHERE clients.id = bookings.client_id)
WHERE source IS NULL;

ALTER TABLE clients DROP COLUMN source;
```

- [ ] **Step 2: Проверить версию SQLite на dev**

Run:
```bash
uv run --env-file .env python -c "import sqlite3; print(sqlite3.sqlite_version)"
```

Expected: `3.35` или выше (нужно для `DROP COLUMN`). Если ниже — стоп, спросить пользователя; иначе — продолжаем.

- [ ] **Step 3: Применить миграцию через pytest (косвенно — apply_migrations при старте app)**

Run:
```bash
uv run --env-file .env pytest tests/test_smoke.py -v
```

Expected: PASS. Все existing-тесты выполняются с пустой временной БД, миграция применяется в `apply_migrations()` при старте приложения. На этом этапе ожидается, что часть тестов в `test_clients.py` и `test_bookings.py` упадут — это норма (фиксим в следующих тасках).

- [ ] **Step 4: Применить миграцию на dev-БД (db.sqlite3)**

Run:
```bash
uv run --env-file .env python -c "from backend.db import apply_migrations; apply_migrations()"
```

Expected: молча отработать. Проверить:
```bash
uv run --env-file .env python -c "from backend.db import get_conn;
with get_conn() as c:
    print('bookings cols:', [r[1] for r in c.execute('PRAGMA table_info(bookings)').fetchall()])
    print('clients cols:', [r[1] for r in c.execute('PRAGMA table_info(clients)').fetchall()])"
```

Expected: `bookings` содержит `source`, `clients` НЕ содержит `source`.

- [ ] **Step 5: Commit**

```bash
git add backend/migrations/010_booking_source.sql
git commit -m "feat(db): bookings.source + drop clients.source"
```

---

## Task 2: Backend — `bookings.source` (Pydantic, SELECT, INSERT)

**Files:**
- Modify: `backend/routes/bookings.py`
- Test: `tests/test_bookings.py`

- [ ] **Step 1: Написать упавший тест на создание брони с source**

Добавить в `tests/test_bookings.py`:

```python
def test_create_booking_with_source(client):
    u, a, c = _prep(client)
    r = client.post(
        "/bookings",
        headers=auth(u["id"]),
        json={
            "apartment_id": a["id"],
            "client_id": c["id"],
            "check_in": "2026-04-21",
            "check_out": "2026-04-24",
            "total_price": 12840,
            "source": "Авито",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["source"] == "Авито"


def test_get_booking_returns_source(client):
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
            "source": "Островок",
        },
    ).json()
    r = client.get(f"/bookings/{b['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    assert r.json()["source"] == "Островок"


def test_patch_booking_source(client):
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
    r = client.patch(
        f"/bookings/{b['id']}",
        headers=auth(u["id"]),
        json={"source": "Суточно.ру"},
    )
    assert r.status_code == 200
    assert r.json()["source"] == "Суточно.ру"
```

- [ ] **Step 2: Запустить тесты — должны упасть**

Run:
```bash
uv run --env-file .env pytest tests/test_bookings.py::test_create_booking_with_source tests/test_bookings.py::test_get_booking_returns_source tests/test_bookings.py::test_patch_booking_source -v
```

Expected: FAIL — поле `source` отсутствует в Pydantic / SELECT.

- [ ] **Step 3: Добавить `source` в `BookingIn` и `BookingPatch`**

В `backend/routes/bookings.py:16-23` (`BookingIn`):

```python
class BookingIn(BaseModel):
    apartment_id: int
    client_id: int
    check_in: date
    check_out: date
    total_price: int = Field(gt=0)
    source: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out должна быть позже check_in")
        return self
```

В `backend/routes/bookings.py:31-38` (`BookingPatch`):

```python
class BookingPatch(BaseModel):
    apartment_id: int | None = None
    client_id: int | None = None
    check_in: date | None = None
    check_out: date | None = None
    total_price: int | None = Field(default=None, gt=0)
    status: str | None = None
    source: str | None = None
    notes: str | None = None
```

- [ ] **Step 4: Добавить `b.source` в `_row()` SELECT**

В `backend/routes/bookings.py:54-69`, заменить SELECT в `_row`:

```python
def _row(conn, booking_id: int):
    return conn.execute(
        """
        SELECT b.id, b.apartment_id, b.client_id, b.check_in, b.check_out,
               b.total_price, b.status, b.source, b.notes, b.created_at,
               a.title AS apartment_title,
               a.cover_url AS apartment_cover_url,
               a.callsign AS apartment_callsign,
               c.full_name AS client_name
        FROM bookings b
        JOIN apartments a ON a.id = b.apartment_id
        JOIN clients c ON c.id = b.client_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()
```

- [ ] **Step 5: Добавить `b.source` в `list_bookings()` SELECT**

В `backend/routes/bookings.py:111-123`, заменить SQL на:

```python
    sql = f"""
        SELECT b.id, b.apartment_id, b.client_id, b.check_in, b.check_out,
               b.total_price, b.status, b.source, b.notes, b.created_at,
               a.title AS apartment_title,
               a.cover_url AS apartment_cover_url,
               a.callsign AS apartment_callsign,
               c.full_name AS client_name
        FROM bookings b
        JOIN apartments a ON a.id = b.apartment_id
        JOIN clients c ON c.id = b.client_id
        {"WHERE " + " AND ".join(where) if where else ""}
        ORDER BY {order_by}
    """
```

- [ ] **Step 6: Передать `source` в INSERT в `create_booking`**

В `backend/routes/bookings.py:168-179`, заменить блок INSERT:

```python
            cur = conn.execute(
                "INSERT INTO bookings (apartment_id, client_id, check_in, check_out, total_price, source, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    payload.apartment_id,
                    payload.client_id,
                    ci,
                    co,
                    payload.total_price,
                    payload.source,
                    payload.notes,
                ),
            )
```

- [ ] **Step 7: Запустить тесты — должны пройти**

Run:
```bash
uv run --env-file .env pytest tests/test_bookings.py -v
```

Expected: все тесты PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/routes/bookings.py tests/test_bookings.py
git commit -m "feat(api): bookings.source — POST/PATCH/GET"
```

---

## Task 3: Backend — убрать `source` из `clients`

**Files:**
- Modify: `backend/routes/clients.py`
- Test: `tests/test_clients.py`

- [ ] **Step 1: Прочитать существующий test_clients.py и обновить**

Run:
```bash
cat tests/test_clients.py
```

Найти любые упоминания `"source"` в asserts/payloads. Если есть — заменить (убрать `source` из payload, убрать assert на `source` в response).

Например, если в тесте:
```python
client.post("/clients", json={"full_name": "X", "phone": "+7", "source": "Авито"})
```
заменить на:
```python
client.post("/clients", json={"full_name": "X", "phone": "+7"})
```

И если есть `assert body["source"] == ...` — удалить эти строки.

- [ ] **Step 2: Запустить тесты — должны упасть на новых правках**

Run:
```bash
uv run --env-file .env pytest tests/test_clients.py -v
```

Expected: FAIL (если в существующем коде `clients.py` ещё есть SELECT `source`, после миграции это сломает запрос — `no such column: source`).

- [ ] **Step 3: Убрать `source` из `ClientIn` и `ClientPatch`**

В `backend/routes/clients.py:13-24`:

```python
class ClientIn(BaseModel):
    full_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    notes: str | None = None


class ClientPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, min_length=1)
    notes: str | None = None
```

- [ ] **Step 4: Убрать `source` из `_row()` и `list_clients()` SELECT**

В `backend/routes/clients.py:27-31`:

```python
def _row(conn, client_id: int):
    return conn.execute(
        "SELECT id, full_name, phone, notes, created_at FROM clients WHERE id = ?",
        (client_id,),
    ).fetchone()
```

В `backend/routes/clients.py:34-40`:

```python
@router.get("")
def list_clients(_: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, phone, notes, created_at FROM clients ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 5: Убрать `source` из INSERT в `create_client`**

В `backend/routes/clients.py:43-53`:

```python
@router.post("", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (full_name, phone, notes) VALUES (?, ?, ?)",
            (payload.full_name, payload.phone, payload.notes),
        )
        row = _row(conn, cur.lastrowid)
    return dict(row)
```

- [ ] **Step 6: Запустить полный тест-сьют**

Run:
```bash
uv run --env-file .env pytest -v
```

Expected: все тесты PASS. Если что-то падает по `source` — исправить.

- [ ] **Step 7: Commit**

```bash
git add backend/routes/clients.py tests/test_clients.py
git commit -m "refactor(api): убрать clients.source"
```

---

## Task 4: Frontend — общий список каналов

**Files:**
- Create: `frontend/src/lib/sources.js`

- [ ] **Step 1: Создать файл `frontend/src/lib/sources.js`**

```js
export const BOOKING_SOURCES = [
    'Авито',
    'Островок',
    'Суточно.ру',
    'Доска.якт',
    'Юла',
    'Фил',
];
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/sources.js
git commit -m "feat(frontend): канонический список источников броней"
```

---

## Task 5: Frontend — `/bookings/new` секция «Источник»

**Files:**
- Modify: `frontend/src/routes/bookings/new/+page.svelte`

- [ ] **Step 1: Импортировать BOOKING_SOURCES и завести state**

В `<script>` блоке (после остальных импортов из `$lib/`):

```js
import { BOOKING_SOURCES } from '$lib/sources.js';
```

Добавить state (рядом с `let notes = $state('');`):

```js
let bookingSource = $state('');
```

- [ ] **Step 2: Убрать поле «Источник» из inline-формы создания клиента**

В `frontend/src/routes/bookings/new/+page.svelte:35` удалить строку:
```js
let newSource = $state('Прямая');
```

В блоке создания клиента (`{#if createOpen}`, строки 193–209) — удалить `<label>` с селектом «Источник» (строки 198–205):

```svelte
<label>
    <span>Источник</span>
    <select bind:value={newSource}>
        <option>Доска.якт</option>
        <option>Юла</option>
        <option>Прямая</option>
    </select>
</label>
```

В функции `createClient` (строки 78–97) убрать `source: newSource || null` из POST-запроса. Итог:

```js
async function createClient() {
    if (!newName || !newPhone) {
        error = 'Имя и телефон обязательны';
        return;
    }
    try {
        const c = await api.post('/clients', {
            full_name: newName,
            phone: newPhone
        });
        clients = [...clients, c];
        clientId = c.id;
        createOpen = false;
        newName = '';
        newPhone = '';
    } catch (e) {
        error = e.message;
    }
}
```

- [ ] **Step 3: Добавить новую секцию «Источник» в шаблон**

Вставить **между** секцией `<!-- Guest picker -->` (`</Section>` на строке 212) и блоком `<!-- Сумма -->` (строка 215):

```svelte
<!-- Источник брони -->
<Section title="Источник">
    <div class="wrap">
        <select class="source-sel" bind:value={bookingSource}>
            <option value="" disabled>Выбрать канал…</option>
            {#each BOOKING_SOURCES as src}
                <option value={src}>{src}</option>
            {/each}
        </select>
    </div>
</Section>
```

- [ ] **Step 4: Добавить валидацию в `save()` и передать `source` в POST**

В `frontend/src/routes/bookings/new/+page.svelte:99-124`, расширить функцию `save()`:

```js
async function save() {
    error = null;
    if (!apartmentId) return (error = 'Выбери квартиру');
    if (!clientId) return (error = 'Выбери гостя');
    if (!checkIn || !checkOut) return (error = 'Укажи даты');
    if (!bookingSource) return (error = 'Выбери источник');
    const price = parseInt(totalPrice, 10);
    if (!price || price <= 0) return (error = 'Сумма должна быть > 0');
    if (new Date(checkOut) <= new Date(checkIn)) return (error = 'Выезд должен быть позже заезда');

    saving = true;
    try {
        const result = await api.post('/bookings', {
            apartment_id: apartmentId,
            client_id: clientId,
            check_in: checkIn,
            check_out: checkOut,
            total_price: price,
            source: bookingSource,
            notes: notes || null
        });
        goto(`/bookings/${result.id}`);
    } catch (e) {
        error = e.message;
    } finally {
        saving = false;
    }
}
```

- [ ] **Step 5: Добавить стили для селекта**

В `<style>` блоке добавить:

```css
.source-sel {
    width: 100%;
    height: 42px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 0 10px;
    color: var(--ink);
    font-size: 14px;
    font-family: inherit;
}
```

- [ ] **Step 6: Запустить дев-сервер и проверить вручную**

Run:
```bash
cd frontend && npm run dev
```

Открыть `/bookings/new`, проверить:
- Секция «Источник» появилась между «Гость» и «Сумма».
- В селекте 6 опций (Авито, Островок, Суточно.ру, Доска.якт, Юла, Фил).
- Без выбора источника — сабмит выдаёт ошибку «Выбери источник».
- В inline-форме создания клиента поля «Источник» больше нет.
- Создание брони с выбранным источником успешно (редирект на карточку).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/routes/bookings/new/+page.svelte
git commit -m "feat(bookings/new): секция «Источник», убрать source из формы клиента"
```

---

## Task 6: Frontend — карточка брони показывает source

**Files:**
- Modify: `frontend/src/routes/bookings/[id]/+page.svelte`

- [ ] **Step 1: Заменить `client?.source` на `booking?.source` в подзаголовке**

В `frontend/src/routes/bookings/[id]/+page.svelte:87-89`:

```svelte
<PageHead title={booking ? `Бронь #${booking.id}` : 'Бронь'}
    sub={booking ? (booking.source || 'Без источника') : ''}
    back="Брони" backOnClick={() => goto('/bookings')} />
```

- [ ] **Step 2: Добавить chip с источником в chip-row**

В `frontend/src/routes/bookings/[id]/+page.svelte:99-102`, расширить `.chip-row`:

```svelte
<div class="chip-row">
    <Chip tone={statusTone(booking.status)}>{statusLabel(booking.status)}</Chip>
    {#if booking.source}
        <Chip tone="info">{booking.source}</Chip>
    {/if}
    <span class="nights">{fmtNights(booking.check_in, booking.check_out)}</span>
</div>
```

CSS `.chip-row` (`justify-content: space-between`) — оставляем; если визуально окажется тесно, поменять на `gap: 8px; flex-wrap: wrap;` и убрать `justify-content`. Решение принять при ручной проверке.

- [ ] **Step 3: Запустить дев-сервер и проверить**

Run: `cd frontend && npm run dev` (если ещё не запущен).

Открыть карточку брони, у которой есть `source`. Проверить:
- Подзаголовок страницы — название канала (например, «Авито»).
- Рядом со статусом — chip с источником.
- Карточка брони без `source` показывает «Без источника» в подзаголовке, chip отсутствует.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/bookings/[id]/+page.svelte
git commit -m "feat(bookings/[id]): показывать booking.source вместо client.source"
```

---

## Task 7: Frontend — убрать `source` со страницы клиента

**Files:**
- Modify: `frontend/src/routes/clients/[id]/+page.svelte`

- [ ] **Step 1: Удалить строку с источником**

В `frontend/src/routes/clients/[id]/+page.svelte:57`, удалить:

```svelte
{#if data.source}<div class="src">источник: {data.source}</div>{/if}
```

- [ ] **Step 2: Удалить неиспользуемый стиль `.src`**

В `frontend/src/routes/clients/[id]/+page.svelte:143`, удалить строку:

```css
.src { font-family: var(--font-mono); font-size: 10px; color: var(--muted); margin-top: 2px; }
```

- [ ] **Step 3: Проверить вручную**

Открыть `/clients/<id>`. Убедиться, что карточка клиента отображается без строки «источник: …», ничего не сломалось.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/clients/[id]/+page.svelte
git commit -m "refactor(clients/[id]): убрать строку source"
```

---

## Task 8: Утилита `shortAddress` + тесты

**Files:**
- Modify: `frontend/src/lib/format.js`
- Test: ручная проверка через консоль / smoke в браузере

- [ ] **Step 1: Добавить функцию в `frontend/src/lib/format.js`**

В конец файла:

```js
// Сокращённый адрес для шахматки. "ул. Петра Алексеева, 50, кв. 34" → "Петра Алексеева, 50".
export function shortAddress(addr) {
    if (!addr) return '';
    let s = addr;
    s = s.replace(/^(ул\.?|улица|пр\.?|проспект|пер\.?|переулок|пл\.?|площадь|ш\.?|шоссе|б-р|бульвар)\s+/i, '');
    s = s.replace(/,?\s*(кв\.?|квартира)\s*\d+\S*/i, '');
    s = s.replace(/,?\s*(под\.?|подъезд)\s*\d+/i, '');
    s = s.replace(/\s+/g, ' ').trim();
    return s;
}
```

- [ ] **Step 2: Smoke-проверка через node**

Run:
```bash
node --input-type=module -e "
import('./frontend/src/lib/format.js').then(m => {
  const cases = [
    ['ул. Петра Алексеева, 50, кв. 34', 'Петра Алексеева, 50'],
    ['пр. Ленина 10/2 кв 18', 'Ленина 10/2'],
    ['Ойунского 7', 'Ойунского 7'],
    ['', ''],
    [null, ''],
  ];
  let ok = true;
  for (const [inp, want] of cases) {
    const got = m.shortAddress(inp);
    const pass = got === want;
    ok = ok && pass;
    console.log(pass ? 'PASS' : 'FAIL', JSON.stringify(inp), '->', JSON.stringify(got), '(want', JSON.stringify(want) + ')');
  }
  process.exit(ok ? 0 : 1);
});
"
```

Expected: все строки `PASS`, exit code 0. (Импорт `$lib/currency.js` сорвёт прямой ESM-резолв в node — если так, заменить smoke на запуск через `vite-node`: `cd frontend && npx vite-node -e "import { shortAddress } from './src/lib/format.js'; …"`. Если не получается — пропустить smoke и проверить вручную в браузере на следующем таске.)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/format.js
git commit -m "feat(format): shortAddress для шахматки"
```

---

## Task 9: Backend — добавить `address` в `/bookings/calendar`

**Files:**
- Modify: `backend/routes/bookings.py`
- Test: `tests/test_bookings.py`

- [ ] **Step 1: Расширить тест `test_bookings_calendar_returns_groups`**

В `tests/test_bookings.py:46-68` дописать assert на `apartment_address`:

```python
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
    assert apt_entry["apartment_address"] == "addr"
    assert len(apt_entry["bookings"]) == 1
    assert apt_entry["bookings"][0]["status"] == "active"
```

- [ ] **Step 2: Запустить тест — должен упасть**

Run:
```bash
uv run --env-file .env pytest tests/test_bookings.py::test_bookings_calendar_returns_groups -v
```

Expected: FAIL — `KeyError: 'apartment_address'` или подобное.

- [ ] **Step 3: Добавить `a.address` в SELECT и в bucket**

В `backend/routes/bookings.py:268-292`, заменить блок:

```python
    with get_conn() as conn:
        apartments = conn.execute(
            "SELECT id, title, callsign, address FROM apartments ORDER BY id"
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
    buckets = {
        a["id"]: {
            "apartment_id": a["id"],
            "apartment_title": a["title"],
            "apartment_callsign": a["callsign"],
            "apartment_address": a["address"],
            "bookings": [],
        }
        for a in apartments
    }
```

- [ ] **Step 4: Запустить тест — должен пройти**

Run:
```bash
uv run --env-file .env pytest tests/test_bookings.py::test_bookings_calendar_returns_groups -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/routes/bookings.py tests/test_bookings.py
git commit -m "feat(api): /bookings/calendar отдаёт apartment_address"
```

---

## Task 10: Frontend — шахматка показывает сокращённый адрес

**Files:**
- Modify: `frontend/src/routes/calendar/+page.svelte`

- [ ] **Step 1: Импортировать `shortAddress` и убрать второй запрос**

В `<script>` блоке `frontend/src/routes/calendar/+page.svelte`:

```js
import { onMount } from 'svelte';
import { goto } from '$app/navigation';
import { api } from '$lib/api.js';
import { shortAddress } from '$lib/format.js';
import PageHead from '$lib/ui/PageHead.svelte';

let apartments = $state([]);
let calendar = $state([]);
let error = $state(null);
let loading = $state(true);

const today = new Date();
const from = today.toISOString().slice(0, 10);
const toDate = new Date(today);
toDate.setDate(toDate.getDate() + 14);
const to = toDate.toISOString().slice(0, 10);

const days = Array.from({ length: 14 }, (_, i) => {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    return d;
});

onMount(async () => {
    try {
        const cal = await api.get(`/bookings/calendar?from=${from}&to=${to}`);
        calendar = cal;
        apartments = cal.map(c => ({
            id: c.apartment_id,
            title: c.apartment_title,
            callsign: c.apartment_callsign,
            address: c.apartment_address,
        }));
    } catch (e) {
        error = e.message;
    } finally {
        loading = false;
    }
});
```

- [ ] **Step 2: В name-col показывать сокращённый адрес, в title — полный**

В шаблоне (строки 88–96), заменить `<div class="name-col">`:

```svelte
<div class="name-col" title={a.address || a.title}>
    {shortAddress(a.address) || a.title}
</div>
```

- [ ] **Step 3: Удалить неиспользуемый стиль `.cs`**

В `<style>` (строки 219–224), удалить:

```css
.cs {
    font-family: var(--font-mono);
    color: var(--accent);
    font-weight: 600;
    font-size: 11px;
}
```

- [ ] **Step 4: Проверить вручную в браузере**

Открыть `/calendar`. Убедиться:
- В левой колонке — сокращённые адреса (например, «Петра Алексеева, 50» вместо «ул. Петра Алексеева, 50, кв. 34»).
- При наведении (на десктопе) — tooltip с полным адресом.
- Сетка не уехала, ширина 110px.
- Брони на барах по-прежнему ведут на карточку (клик).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/calendar/+page.svelte
git commit -m "feat(calendar): сокращённые адреса в name-col, убрать дубль-запрос /apartments"
```

---

## Task 11: Frontend — кликабельная зона брони в `/apartments/[id]`

**Files:**
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`

- [ ] **Step 1: Сделать `.guest-range` кнопкой со ссылкой на бронь**

В `frontend/src/routes/apartments/[id]/+page.svelte:200-219`, заменить блок «Гость»:

```svelte
{#if currentGuest}
    <Section title="Гость">
        <div class="wrap">
            <Card pad={14}>
                <button class="guest" type="button" onclick={() => currentGuest.client && goto(`/clients/${currentGuest.client.id}`)}>
                    <Avatar name={currentGuest.client?.full_name || '?'} size={44} accent="var(--accent)" />
                    <div class="guest-body">
                        <div class="guest-name">{currentGuest.client?.full_name || '—'}</div>
                        <div class="guest-phone">{currentGuest.client?.phone || ''}</div>
                    </div>
                </button>
                <button class="guest-range" type="button" onclick={() => goto(`/bookings/${currentGuest.booking.id}`)}>
                    <span>{fmtDate(currentGuest.booking.check_in)} → {fmtDate(currentGuest.booking.check_out)}</span>
                    <span class="guest-sum">{fmtNights(currentGuest.booking.check_in, currentGuest.booking.check_out)} · {fmtRub(currentGuest.booking.total_price)}</span>
                </button>
            </Card>
        </div>
    </Section>
{/if}
```

- [ ] **Step 2: Обновить CSS для `.guest-range`**

Найти существующий стиль `.guest-range` в `<style>` блоке этого же файла. Заменить (или добавить, если нет такого селектора) на:

```css
.guest-range {
    width: 100%;
    margin-top: 12px;
    padding: 10px 12px;
    background: transparent;
    border: none;
    border-top: 1px solid var(--border-soft);
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    text-align: left;
    color: var(--ink);
    font-size: 13px;
    font-family: inherit;
}
.guest-range:hover { background: var(--card-hi); }
.guest-sum {
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--faint);
}
```

(если в файле уже есть селектор `.guest-sum` или `.guest-range` — проверить и привести к этому виду; если другие свойства уже определены — оставить только нужные изменения.)

- [ ] **Step 3: Проверить вручную**

Открыть `/apartments/<id>` для квартиры с активным заездом. Проверить:
- Клик по верхней зоне (аватар + имя) → переход на `/clients/<client_id>`.
- Клик по нижней зоне (даты + сумма) → переход на `/bookings/<booking_id>`.
- При hover — обе зоны меняют фон.
- Без активного заезда — секция «Гость» не отображается (как было).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/apartments/[id]/+page.svelte
git commit -m "feat(apartments/[id]): даты в блоке «Гость» → клик на бронь"
```

---

## Task 12: Frontend — кликабельные строки feed в `/finance`

**Files:**
- Modify: `frontend/src/routes/finance/+page.svelte`

- [ ] **Step 1: Сделать `feed-row` кликабельной кнопкой / делегатом**

В `frontend/src/routes/finance/+page.svelte:206-233`, заменить блок «Последние движения»:

```svelte
<Section title="Последние движения">
    <div class="wrap">
        {#if data.feed.length === 0}
            <Card pad={16}><div class="empty">Движений нет</div></Card>
        {:else}
            <Card pad={0}>
                {#each data.feed.filter(f => {
                    if (filterApt === 'all') return true;
                    if (filterApt === 'general') return f.type === 'income' || f.apartment_id == null;
                    return f.type === 'income' ? false : String(f.apartment_id) === filterApt;
                }) as item, i}
                    {@const targetHref = item.ref?.booking_id
                        ? `/bookings/${item.ref.booking_id}`
                        : (item.ref?.expense_id && item.apartment_id
                            ? `/apartments/${item.apartment_id}`
                            : null)}
                    {#if targetHref}
                        <button
                            class="feed-row clickable"
                            class:last={i === data.feed.length - 1}
                            type="button"
                            onclick={() => goto(targetHref)}
                        >
                            <div class="feed-icon" class:income={item.type === 'income'} class:expense={item.type === 'expense'}>
                                {item.type === 'income' ? '+' : '−'}
                            </div>
                            <div class="feed-body">
                                <div class="feed-label">{item.label}</div>
                                <div class="feed-date">{item.dt}</div>
                            </div>
                            <div class="feed-amt" class:pos={item.type === 'income'}>
                                {item.type === 'income' ? '+' : '−'} {fmtShortRub(item.amount)}
                            </div>
                        </button>
                    {:else}
                        <div class="feed-row" class:last={i === data.feed.length - 1}>
                            <div class="feed-icon" class:income={item.type === 'income'} class:expense={item.type === 'expense'}>
                                {item.type === 'income' ? '+' : '−'}
                            </div>
                            <div class="feed-body">
                                <div class="feed-label">{item.label}</div>
                                <div class="feed-date">{item.dt}</div>
                            </div>
                            <div class="feed-amt" class:pos={item.type === 'income'}>
                                {item.type === 'income' ? '+' : '−'} {fmtShortRub(item.amount)}
                            </div>
                        </div>
                    {/if}
                {/each}
            </Card>
        {/if}
    </div>
</Section>
```

Импортировать `goto` если ещё не импортирован: `import { goto } from '$app/navigation';` в `<script>` блоке (проверить — обычно уже есть).

- [ ] **Step 2: Добавить стили для кликабельной строки**

В `<style>` блоке найти селектор `.feed-row` и убедиться, что есть `display: flex` (или grid). Дополнительно добавить:

```css
.feed-row {
    width: 100%;
    box-sizing: border-box;
    background: transparent;
    border: none;
    text-align: left;
    font: inherit;
    color: inherit;
}
.feed-row.clickable {
    cursor: pointer;
}
.feed-row.clickable:hover {
    background: var(--card-hi);
}
```

(не дублировать свойства, которые уже есть на `.feed-row` — добавить только новые. `<button>` по-умолчанию имеет свои padding/font — нужно сбросить через `font: inherit;` чтобы выглядел как `<div>`.)

- [ ] **Step 3: Проверить вручную**

Открыть `/finance` за месяц с движениями. Проверить:
- Income-строки (доход от брони) — кликабельны, ведут на `/bookings/<id>`.
- Expense-строки с привязкой к квартире — кликабельны, ведут на `/apartments/<id>`.
- Expense-строки без квартиры (общие расходы) — не кликабельны, hover-эффекта нет.
- Layout строки не сломан после смены `<div>` → `<button>`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/finance/+page.svelte
git commit -m "feat(finance): кликабельные строки feed (income → бронь, expense → квартира)"
```

---

## Task 13: ContractModal — компонент

**Files:**
- Create: `frontend/src/lib/ui/ContractModal.svelte`

- [ ] **Step 1: Создать компонент**

```svelte
<script>
    let {
        open = false,
        onClose
    } = $props();

    let step = $state('choose'); // 'choose' | 'wip'

    $effect(() => {
        if (!open) {
            step = 'choose';
        }
    });

    function pick(_kind) {
        // _kind: 'business' | 'personal' — пока не используется (бэк появится позже)
        step = 'wip';
    }
</script>

{#if open}
    <div class="backdrop" onclick={onClose} role="presentation"></div>
    <div class="dialog" role="dialog" aria-modal="true" aria-label="Сделать договор">
        <button class="close" type="button" onclick={onClose} aria-label="Закрыть">×</button>
        {#if step === 'choose'}
            <div class="title">Для кого делаем договор?</div>
            <div class="choices">
                <button class="choice" type="button" onclick={() => pick('business')}>
                    Командированный
                </button>
                <button class="choice" type="button" onclick={() => pick('personal')}>
                    Не командированный
                </button>
            </div>
        {:else}
            <div class="title">Скоро</div>
            <div class="wip">
                Генерация договора скоро появится. Сейчас эта кнопка — заглушка:
                выбор сохранён, сам документ подтянем позже.
            </div>
            <div class="actions">
                <button type="button" class="primary" onclick={onClose}>Понятно</button>
            </div>
        {/if}
    </div>
{/if}

<style>
    .backdrop {
        position: fixed; inset: 0;
        background: rgba(0,0,0,0.4);
        z-index: 1000;
    }
    .dialog {
        position: fixed;
        top: 50%; left: 50%;
        transform: translate(-50%, -50%);
        width: min(360px, calc(100vw - 40px));
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 18px 16px 16px;
        z-index: 1001;
        display: flex;
        flex-direction: column;
        gap: 14px;
    }
    .close {
        position: absolute;
        top: 6px; right: 8px;
        background: transparent;
        border: none;
        color: var(--faint);
        font-size: 22px;
        line-height: 1;
        cursor: pointer;
        padding: 4px 8px;
    }
    .close:hover { color: var(--ink); }
    .title {
        font-size: 15px;
        font-weight: 600;
        color: var(--ink);
        padding-right: 24px;
    }
    .choices {
        display: flex;
        flex-direction: column;
        gap: 10px;
    }
    .choice {
        padding: 16px 12px;
        background: var(--bg);
        border: 1px solid var(--border);
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        color: var(--ink);
        cursor: pointer;
        font-family: inherit;
    }
    .choice:hover {
        background: var(--card-hi);
        border-color: var(--accent);
    }
    .wip {
        font-size: 13px;
        line-height: 1.5;
        color: var(--ink2);
    }
    .actions {
        display: flex;
        justify-content: flex-end;
    }
    .primary {
        padding: 10px 18px;
        font-size: 13px;
        font-weight: 600;
        border-radius: 6px;
        background: var(--accent);
        color: #fff;
        border: none;
        cursor: pointer;
    }
    .primary:hover { background: var(--accent2); }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/ui/ContractModal.svelte
git commit -m "feat(ui): ContractModal — двухшаговая модалка-заглушка"
```

---

## Task 14: Frontend — секция «Договор» в карточке брони

**Files:**
- Modify: `frontend/src/routes/bookings/[id]/+page.svelte`

- [ ] **Step 1: Импортировать ContractModal и завести state**

В `<script>` блоке `frontend/src/routes/bookings/[id]/+page.svelte` (после остальных импортов):

```js
import ContractModal from '$lib/ui/ContractModal.svelte';
```

Добавить state (рядом с `let booking = $state(null);`):

```js
let contractOpen = $state(false);
```

И производное от роли (рядом с `const canDelete = me?.role === 'owner';`):

```js
const canMakeContract = me?.role === 'owner' || me?.role === 'admin';
```

- [ ] **Step 2: Добавить секцию «Договор» в шаблон**

Вставить **между** блоком `{#if booking.notes}` (заканчивается на `{/if}`, строка 174) и блоком `<!-- Actions -->` (строка 177):

```svelte
{#if canMakeContract}
    <Section title="Договор">
        <div class="wrap">
            <button class="contract-btn" type="button" onclick={() => contractOpen = true}>
                Сделать договор
            </button>
        </div>
    </Section>
{/if}
```

- [ ] **Step 3: Подключить ContractModal в конец шаблона**

Перед закрывающим `{/if}` блока `{#if error}…{:else if loading…}{:else}…{/if}` (последняя `{/if}` файла, после `danger-zone` блока), добавить:

```svelte
<ContractModal open={contractOpen} onClose={() => contractOpen = false} />
```

- [ ] **Step 4: Стили для `contract-btn`**

В `<style>` блоке файла добавить:

```css
.contract-btn {
    width: 100%;
    height: 44px;
    background: var(--card);
    color: var(--ink);
    border: 1px solid var(--border);
    border-radius: 6px;
    font-size: 13px;
    font-weight: 600;
    font-family: inherit;
    cursor: pointer;
}
.contract-btn:hover {
    background: var(--card-hi);
    border-color: var(--accent);
}
```

- [ ] **Step 5: Проверить вручную**

Открыть карточку брони:
- Под ролью owner или admin: видна секция «Договор» с кнопкой.
- Клик → открывается модалка с заголовком «Для кого делаем договор?» и двумя кнопками.
- Клик по любой кнопке → переключение на WIP-экран с текстом и кнопкой «Понятно».
- «Понятно» или «×» → модалка закрывается.
- Повторное открытие → снова шаг «choose» (а не WIP).
- Под ролью maid (если такая роль возможна на странице) — секция не видна.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/routes/bookings/[id]/+page.svelte
git commit -m "feat(bookings/[id]): кнопка «Сделать договор» + ContractModal"
```

---

## Task 15: Финальная проверка — весь тест-сьют + smoke в браузере

- [ ] **Step 1: Запустить полный pytest**

Run:
```bash
uv run --env-file .env pytest -v
```

Expected: все тесты PASS.

- [ ] **Step 2: Запустить дев-сервер и проверить золотой путь**

Run (в двух терминалах):
```bash
# терминал 1
uv run --env-file .env uvicorn backend.main:app --reload
# терминал 2
cd frontend && npm run dev
```

Чек-лист в браузере:
- [ ] `/bookings/new` — создать бронь с источником «Авито» → редирект, на карточке источник виден.
- [ ] `/bookings/<id>` — chip с источником, кнопка «Сделать договор», модалка работает.
- [ ] `/calendar` — в левой колонке адрес (сокращённый), tooltip полный.
- [ ] `/apartments/<id>` для квартиры с активным заездом — клик на даты ведёт на бронь.
- [ ] `/finance` — клик на income-строку ведёт на бронь, на expense с квартирой — на квартиру.
- [ ] `/clients/<id>` — нет строки «источник», страница не падает.

- [ ] **Step 3: Если всё ОК — финальный «зелёный» коммит не нужен; план завершён**

История коммитов на ветке должна выглядеть как 12 атомарных коммитов (по одному на таск, кроме чисто-проверочных).

---

## Self-Review

Spec coverage:
- §1 (источники) → Tasks 1, 2, 3, 4, 5, 6, 7. Migration + backend + frontend list + form + card + cleanup.
- §2 (шахматка) → Tasks 8, 9, 10. shortAddress + backend address + frontend.
- §3.1 (`/apartments/[id]` гость) → Task 11.
- §3.2 (`/finance` feed) → Task 12.
- §4 (договор) → Tasks 13, 14. Modal + integration.

Placeholder scan: все шаги содержат код или конкретные команды. «Если визуально окажется тесно» в Task 6 — обусловленная инструкция с конкретным fallback-стилем; не TBD.

Type/name consistency: `bookingSource` (Task 5) → `booking.source` в API (Tasks 2, 6). `BOOKING_SOURCES` (Task 4) импортируется в Task 5. `ContractModal` props `open`, `onClose` (Task 13) → именно так используется в Task 14. `apartment_address` (Tasks 9, 10) единообразно. `shortAddress` (Tasks 8, 10) совпадает.

Все требования спека покрыты, тасков 15, основная масса — мелкие правки в одном файле, естественные коммит-границы.
