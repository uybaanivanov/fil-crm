# Cleaning Schedule Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Расширить кнопку «Требует уборки» диалогом ввода datetime `cleaning_due_at`; хранить, сортировать, показывать, подсвечивать просрочку.

**Architecture:** Одна новая колонка `apartments.cleaning_due_at TEXT NULL`, одно изменённое тело `POST /mark-dirty`, одна сортировка `/apartments/cleaning`, один svelte-диалог, два тронутых фронт-роута. `needs_cleaning` остаётся источником истины «надо убирать».

**Tech Stack:** FastAPI + Pydantic + SQLite (raw SQL) · Svelte 5 runes · pytest+TestClient. Миграции auto-apply при старте приложения.

**Spec:** `docs/superpowers/specs/2026-04-22-cleaning-schedule-design.md`

---

## Файловая структура

**Создаём:**
- `backend/migrations/004_cleaning_due_at.sql` — ALTER TABLE.
- `frontend/src/lib/ui/CleaningDueDialog.svelte` — модалка с datetime-local.
- `tests/test_cleaning_schedule.py` — pytest-тесты контракта.

**Модифицируем:**
- `backend/routes/apartments.py` — `SELECT_FIELDS` + `CleaningDueIn` pydantic-модель + body в `mark-dirty` + NULL в `mark-clean` + сортировка `/cleaning`.
- `frontend/src/lib/format.js` — добавить `fmtDateTime`, `defaultCleaningDueAt`.
- `frontend/src/routes/apartments/[id]/+page.svelte` — диалог, лейбл кнопки, секция времени.
- `frontend/src/routes/cleaning/+page.svelte` — время и просрочка в карточке.

---

## Task 1: Миграция колонки

**Files:**
- Create: `backend/migrations/004_cleaning_due_at.sql`

- [ ] **Step 1: Написать миграцию**

Создать `backend/migrations/004_cleaning_due_at.sql`:

```sql
ALTER TABLE apartments ADD COLUMN cleaning_due_at TEXT;
```

- [ ] **Step 2: Убедиться, что миграция подхватывается**

`backend/db.py:41` читает `MIGRATIONS_DIR.glob("*.sql")` сортированно и применяет новые. Ручной запуск:

```bash
rm -f /tmp/fil_test.sqlite3
FIL_DB_PATH=/tmp/fil_test.sqlite3 uv run --project /home/uybaan/fil-crm python -c "from backend.db import apply_migrations; apply_migrations(); import sqlite3; c = sqlite3.connect('/tmp/fil_test.sqlite3'); print([r[1] for r in c.execute('PRAGMA table_info(apartments)').fetchall()])"
```

Expected: в выводе есть `cleaning_due_at` (последним элементом).

- [ ] **Step 3: Коммит**

```bash
git add backend/migrations/004_cleaning_due_at.sql
git commit -m "feat(db): migration 004 — apartments.cleaning_due_at"
```

---

## Task 2: Pydantic-модель и тесты контракта `mark-dirty`

**Files:**
- Modify: `backend/routes/apartments.py` (добавить модель; поведение меняется в Task 3)
- Create: `tests/test_cleaning_schedule.py`

- [ ] **Step 1: Написать падающие тесты**

Создать `tests/test_cleaning_schedule.py`:

```python
from tests.conftest import auth, seed_user


def _owner(client):
    return seed_user(client, role="owner", name="Айсен")


def _apt(client, u_id):
    return client.post(
        "/apartments",
        headers=auth(u_id),
        json={"title": "A", "address": "addr", "price_per_night": 1000},
    ).json()


def test_mark_dirty_requires_body(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(f"/apartments/{a['id']}/mark-dirty", headers=auth(u["id"]))
    assert r.status_code == 422


def test_mark_dirty_requires_cleaning_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(f"/apartments/{a['id']}/mark-dirty", headers=auth(u["id"]), json={})
    assert r.status_code == 422


def test_mark_dirty_rejects_invalid_datetime(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "not-a-date"},
    )
    assert r.status_code == 422


def test_mark_dirty_sets_flag_and_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    r = client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["needs_cleaning"] == 1
    assert body["cleaning_due_at"] == "2026-04-24T14:00:00"


def test_mark_dirty_overwrites_existing_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    r = client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T16:30:00"},
    )
    assert r.status_code == 200
    assert r.json()["cleaning_due_at"] == "2026-04-24T16:30:00"


def test_mark_clean_clears_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    r = client.post(f"/apartments/{a['id']}/mark-clean", headers=auth(u["id"]))
    assert r.status_code == 200
    body = r.json()
    assert body["needs_cleaning"] == 0
    assert body["cleaning_due_at"] is None


def test_cleaning_list_includes_due_at_and_sorts(client):
    u = _owner(client)
    a1 = _apt(client, u["id"])
    a2 = _apt(client, u["id"])
    # a1 позже, a2 раньше — a2 должен идти первым
    client.post(
        f"/apartments/{a1['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T16:30:00"},
    )
    client.post(
        f"/apartments/{a2['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T10:00:00"},
    )
    r = client.get("/apartments/cleaning", headers=auth(u["id"]))
    assert r.status_code == 200
    rows = r.json()
    ids = [x["id"] for x in rows]
    assert ids == [a2["id"], a1["id"]]
    assert rows[0]["cleaning_due_at"] == "2026-04-24T10:00:00"


def test_get_apartment_returns_cleaning_due_at(client):
    u = _owner(client)
    a = _apt(client, u["id"])
    client.post(
        f"/apartments/{a['id']}/mark-dirty",
        headers=auth(u["id"]),
        json={"cleaning_due_at": "2026-04-24T14:00:00"},
    )
    r = client.get(f"/apartments/{a['id']}", headers=auth(u["id"]))
    assert r.status_code == 200
    assert r.json()["cleaning_due_at"] == "2026-04-24T14:00:00"
```

- [ ] **Step 2: Убедиться, что тесты падают**

Run:
```bash
uv run --project /home/uybaan/fil-crm pytest tests/test_cleaning_schedule.py -v
```

Expected: все 8 тестов FAIL (body отсутствует — 405/400/200 без ожидаемого поля, в зависимости от теста).

---

## Task 3: Реализация `mark-dirty`, `mark-clean`, `/cleaning` на бэке

**Files:**
- Modify: `backend/routes/apartments.py:37-40, 101-109, 281-306`

- [ ] **Step 1: Расширить `SELECT_FIELDS`**

Заменить `apartments.py:37-40`:

```python
SELECT_FIELDS = (
    "id, title, address, price_per_night, needs_cleaning, cleaning_due_at, "
    "cover_url, rooms, area_m2, floor, district, source, source_url, created_at"
)
```

- [ ] **Step 2: Добавить Pydantic-модель**

Вставить после `ApartmentPatch` (примерно `apartments.py:35`):

```python
class CleaningDueIn(BaseModel):
    cleaning_due_at: datetime.datetime
```

И добавить импорт в начало файла (после существующих импортов):

```python
import datetime
```

Обоснование: Pydantic парсит ISO-8601 строки в `datetime.datetime`. Наивный datetime (без TZ) он допускает — это наш контракт. Невалидная строка → `422` автоматически.

- [ ] **Step 3: Переписать `mark-dirty`**

Заменить `apartments.py:281-292`:

```python
@router.post("/{apt_id}/mark-dirty")
def mark_dirty(
    apt_id: int,
    payload: CleaningDueIn,
    _: dict = Depends(require_role("owner", "admin")),
):
    due_iso = payload.cleaning_due_at.isoformat(timespec="seconds")
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 1, cleaning_due_at = ? WHERE id = ?",
            (due_iso, apt_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)
```

- [ ] **Step 4: Переписать `mark-clean`**

Заменить `apartments.py:295-306`:

```python
@router.post("/{apt_id}/mark-clean")
def mark_clean(apt_id: int, _: dict = Depends(require_role("owner", "admin", "maid"))):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 0, cleaning_due_at = NULL WHERE id = ?",
            (apt_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)
```

- [ ] **Step 5: Отсортировать `/apartments/cleaning`**

Заменить `apartments.py:101-109`:

```python
@router.get("/cleaning")
def list_apartments_needing_cleaning(
    _: dict = Depends(require_role("owner", "admin", "maid")),
):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {SELECT_FIELDS} FROM apartments "
            "WHERE needs_cleaning = 1 "
            "ORDER BY cleaning_due_at IS NULL, cleaning_due_at ASC, id"
        ).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 6: Запустить тесты**

Run:
```bash
uv run --project /home/uybaan/fil-crm pytest tests/test_cleaning_schedule.py -v
```

Expected: все 8 тестов PASS.

- [ ] **Step 7: Прогнать всю test-suite**

Run:
```bash
uv run --project /home/uybaan/fil-crm pytest -q
```

Expected: весь набор PASS (важно: `test_apartments.py` содержит assert про `status in ("occupied", "free", "needs_cleaning")` — не ломаем).

- [ ] **Step 8: Коммит**

```bash
git add backend/routes/apartments.py tests/test_cleaning_schedule.py
git commit -m "feat(apartments): mark-dirty требует cleaning_due_at; /cleaning сортирует по времени"
```

---

## Task 4: Хелперы даты/времени на фронте

**Files:**
- Modify: `frontend/src/lib/format.js`

- [ ] **Step 1: Добавить `fmtDateTime`**

В конец `frontend/src/lib/format.js` (перед закрывающей) добавить:

```javascript
// ISO local "YYYY-MM-DDTHH:MM:SS" → "23 апр., 14:00". Null → ''.
export function fmtDateTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    return d.getDate() + ' ' + MONTHS_SHORT[d.getMonth()] + ', ' +
        String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
}
```

- [ ] **Step 2: Добавить `defaultCleaningDueAt`**

После `fmtDateTime` в том же файле:

```javascript
// Возвращает строку для <input type="datetime-local"> ("YYYY-MM-DDTHH:MM").
// Если есть активная бронь → день её checkout в 12:00 local. Иначе → now, округлённое вверх до часа.
export function defaultCleaningDueAt(currentGuest) {
    let d;
    if (currentGuest?.booking?.check_out) {
        d = new Date(currentGuest.booking.check_out + 'T12:00:00');
    } else {
        d = new Date();
        d.setMinutes(0, 0, 0);
        d.setHours(d.getHours() + 1);
    }
    return d.getFullYear() + '-' +
        String(d.getMonth() + 1).padStart(2, '0') + '-' +
        String(d.getDate()).padStart(2, '0') + 'T' +
        String(d.getHours()).padStart(2, '0') + ':' +
        String(d.getMinutes()).padStart(2, '0');
}

// "YYYY-MM-DDTHH:MM" (из datetime-local) → "YYYY-MM-DDTHH:MM:00" (для API).
export function datetimeLocalToIso(value) {
    if (!value) return null;
    return value.length === 16 ? value + ':00' : value;
}

// ISO "YYYY-MM-DDTHH:MM:SS" → "YYYY-MM-DDTHH:MM" (для prefill datetime-local).
export function isoToDatetimeLocal(iso) {
    if (!iso) return '';
    return iso.length >= 16 ? iso.slice(0, 16) : iso;
}
```

- [ ] **Step 3: Визуально убедиться, что ничего не сломалось**

Run:
```bash
cd /home/uybaan/fil-crm/frontend && source "$HOME/.nvm/nvm.sh" && nvm use node >/dev/null && npm run build 2>&1 | tail -5
```

Expected: `✓ built` без ошибок.

- [ ] **Step 4: Коммит**

```bash
git add frontend/src/lib/format.js
git commit -m "feat(frontend): helpers fmtDateTime / defaultCleaningDueAt / iso<->datetime-local"
```

---

## Task 5: Компонент `CleaningDueDialog.svelte`

**Files:**
- Create: `frontend/src/lib/ui/CleaningDueDialog.svelte`

- [ ] **Step 1: Написать компонент**

Создать `frontend/src/lib/ui/CleaningDueDialog.svelte`:

```svelte
<script>
    let {
        open = false,
        defaultValue = '',
        errorText = null,
        title = 'Когда требуется уборка?',
        onSubmit,
        onCancel
    } = $props();

    let value = $state(defaultValue);
    let inputEl;

    $effect(() => {
        if (open) {
            value = defaultValue;
            queueMicrotask(() => inputEl?.focus());
        }
    });

    function submit() {
        if (!value) return;
        onSubmit?.(value);
    }

    function onKey(e) {
        if (e.key === 'Enter') { e.preventDefault(); submit(); }
        else if (e.key === 'Escape') { e.preventDefault(); onCancel?.(); }
    }
</script>

{#if open}
    <div class="backdrop" onclick={onCancel} role="presentation"></div>
    <div class="dialog" role="dialog" aria-modal="true" aria-label={title}>
        <div class="title">{title}</div>
        <input
            bind:this={inputEl}
            bind:value
            type="datetime-local"
            class="input"
            onkeydown={onKey}
        />
        {#if errorText}<div class="err">{errorText}</div>{/if}
        <div class="actions">
            <button type="button" class="ghost" onclick={onCancel}>Отмена</button>
            <button type="button" class="primary" disabled={!value} onclick={submit}>Сохранить</button>
        </div>
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
        padding: 16px;
        z-index: 1001;
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    .title { font-size: 15px; font-weight: 600; color: var(--ink); }
    .input {
        width: 100%;
        box-sizing: border-box;
        padding: 10px 12px;
        font-size: 14px;
        font-family: inherit;
        border: 1px solid var(--border);
        border-radius: 6px;
        background: var(--bg);
        color: var(--ink);
    }
    .err {
        font-size: 12px;
        color: var(--danger);
    }
    .actions {
        display: flex; gap: 10px; justify-content: flex-end;
    }
    .primary, .ghost {
        padding: 8px 14px;
        font-size: 13px;
        font-weight: 600;
        border-radius: 6px;
        cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ghost { background: transparent; color: var(--ink); border: 1px solid var(--border); }
</style>
```

- [ ] **Step 2: Проверить билд**

Run:
```bash
cd /home/uybaan/fil-crm/frontend && source "$HOME/.nvm/nvm.sh" && nvm use node >/dev/null && npm run build 2>&1 | tail -5
```

Expected: `✓ built`.

- [ ] **Step 3: Коммит**

```bash
git add frontend/src/lib/ui/CleaningDueDialog.svelte
git commit -m "feat(frontend): CleaningDueDialog — модалка с datetime-local"
```

---

## Task 6: Интеграция диалога в карточку квартиры

**Files:**
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`

- [ ] **Step 1: Импорты и стейт**

Заменить в `+page.svelte:5-12` (блок импортов):

```javascript
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { page } from '$app/state';
    import { api, ApiError } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';
    import Chip from '$lib/ui/Chip.svelte';
    import Avatar from '$lib/ui/Avatar.svelte';
    import CleaningDueDialog from '$lib/ui/CleaningDueDialog.svelte';
    import {
        fmtRub, fmtShortRub, fmtDate, fmtNights, fmtMonth,
        fmtDateTime, defaultCleaningDueAt, datetimeLocalToIso, isoToDatetimeLocal
    } from '$lib/format.js';
```

- [ ] **Step 2: Добавить стейт диалога и derived-значения**

После строки `let loading = $state(true);` (было `:21`) добавить:

```javascript
    let dialogOpen = $state(false);
    let dialogDefault = $state('');
    let dialogError = $state(null);

    const isOverdue = $derived(
        apt?.cleaning_due_at && new Date(apt.cleaning_due_at) < new Date()
    );
```

- [ ] **Step 3: Заменить `markDirty` на открытие диалога + submit**

Заменить текущую `async function markDirty()` (`:64-71`) на:

```javascript
    function openCleaningDialog() {
        dialogDefault = apt.needs_cleaning && apt.cleaning_due_at
            ? isoToDatetimeLocal(apt.cleaning_due_at)
            : defaultCleaningDueAt(currentGuest);
        dialogError = null;
        dialogOpen = true;
    }

    async function submitCleaning(value) {
        try {
            await api.post(`/apartments/${aptId}/mark-dirty`, {
                cleaning_due_at: datetimeLocalToIso(value)
            });
            dialogOpen = false;
            await load();
        } catch (e) {
            dialogError = e.message;
        }
    }
```

- [ ] **Step 4: Обновить секцию «Характеристики» — показать время**

Заменить строку `['Нужна уборка', apt.needs_cleaning ? 'Да' : 'Нет']` (`:146`) на две строки (пунктами `{#each}`) — проще заменить сам `{#each}` блок. Вариант: переделаем строку уборки, добавив условный элемент.

Заменить блок `{#each [ ... ] as [k, v], i}` (примерно `:140-152`):

```svelte
                {@const rows = [
                    ['Тип', apt.rooms || '—'],
                    ['Площадь', apt.area_m2 ? apt.area_m2 + ' м²' : '—'],
                    ['Этаж', apt.floor || '—'],
                    ['Район', apt.district || '—'],
                    ['Цена/ночь', fmtRub(apt.price_per_night)],
                    ['Нужна уборка', apt.needs_cleaning
                        ? (apt.cleaning_due_at ? 'К ' + fmtDateTime(apt.cleaning_due_at) : 'Да')
                        : 'Нет']
                ]}
                {#each rows as [k, v], i}
                    <div class="ch-row" class:last={i === rows.length - 1}>
                        <span class="ch-key">{k}</span>
                        <span class="ch-val">{v}</span>
                        {#if k === 'Нужна уборка' && isOverdue}
                            <span class="overdue"><Chip tone="late">Просрочено</Chip></span>
                        {/if}
                    </div>
                {/each}
```

Добавить в `<style>` в конец:

```css
    .overdue { margin-left: 8px; }
```

- [ ] **Step 5: Заменить кнопку «Пометить грязной» на двухрежимную + добавить диалог в конец шаблона**

Заменить блок `<div class="actions">...</div>` (`:158-164`):

```svelte
    <div class="actions">
        {#if apt.needs_cleaning}
            <button class="ghost" type="button" onclick={openCleaningDialog}>Изменить время уборки</button>
            <button class="primary" type="button" onclick={markClean}>Закрыть уборку ✓</button>
        {:else}
            <button class="ghost" type="button" onclick={openCleaningDialog}>Требует уборки</button>
        {/if}
    </div>

    <CleaningDueDialog
        open={dialogOpen}
        defaultValue={dialogDefault}
        errorText={dialogError}
        onSubmit={submitCleaning}
        onCancel={() => (dialogOpen = false)}
    />
```

- [ ] **Step 6: Собрать и проверить**

Run:
```bash
cd /home/uybaan/fil-crm/frontend && source "$HOME/.nvm/nvm.sh" && nvm use node >/dev/null && npm run build 2>&1 | tail -5
```

Expected: `✓ built`.

- [ ] **Step 7: Коммит**

```bash
git add frontend/src/routes/apartments/[id]/+page.svelte
git commit -m "feat(frontend): диалог cleaning_due_at в карточке квартиры"
```

---

## Task 7: Время и просрочка в `/cleaning`

**Files:**
- Modify: `frontend/src/routes/cleaning/+page.svelte`

- [ ] **Step 1: Импорты**

Заменить `frontend/src/routes/cleaning/+page.svelte:8`:

```javascript
    import { fmtRub, fmtDateTime } from '$lib/format.js';
```

- [ ] **Step 2: Отрисовать время и чип «Просрочено»**

Заменить блок `<div class="top">...</div>` (`:59-65`):

```svelte
                <div class="top">
                    <div class="addr-wrap">
                        <div class="title">{a.title}</div>
                        <div class="addr">{a.address}</div>
                        {#if a.cleaning_due_at}
                            <div class="due" class:overdue={new Date(a.cleaning_due_at) < new Date()}>
                                К {fmtDateTime(a.cleaning_due_at)}
                            </div>
                        {/if}
                    </div>
                    {#if a.cleaning_due_at && new Date(a.cleaning_due_at) < new Date()}
                        <Chip tone="late">Просрочено</Chip>
                    {:else}
                        <Chip tone="due">Требует уборки</Chip>
                    {/if}
                </div>
```

Добавить в `<style>`:

```css
    .due {
        font-family: var(--font-mono);
        font-size: 11px;
        color: var(--muted);
        margin-top: 4px;
    }
    .due.overdue { color: var(--danger); font-weight: 600; }
```

- [ ] **Step 3: Сборка**

Run:
```bash
cd /home/uybaan/fil-crm/frontend && source "$HOME/.nvm/nvm.sh" && nvm use node >/dev/null && npm run build 2>&1 | tail -5
```

Expected: `✓ built`.

- [ ] **Step 4: Коммит**

```bash
git add frontend/src/routes/cleaning/+page.svelte
git commit -m "feat(cleaning): время уборки и чип 'Просрочено' в списке"
```

---

## Task 8: Ручной дымовой тест (локально)

- [ ] **Step 1: Поднять локально**

Run:
```bash
cd /home/uybaan/fil-crm && bash start.sh
```

Expected: tmux `fil-crm` с окнами `backend` (:8000) и `frontend` (:5173).

- [ ] **Step 2: Открыть в браузере и пройти сценарий**

Открыть `http://localhost:5173`.

Checklist (каждый пункт отметить в PR-описании):
- Зайти как owner. Открыть свободную квартиру. Нажать «Требует уборки» → диалог с дефолтом «следующий час».
- Сохранить → чип в обложке «Требует уборки», в «Характеристиках» строка «Нужна уборка: К HH:MM, DD МММ».
- Нажать «Изменить время уборки» → диалог с текущим значением. Поменять на прошедшее время → Сохранить → чип «Просрочено» появился рядом.
- Открыть `/cleaning` → карточка с временем, у просроченной — красный чип «Просрочено» и красный текст.
- Создать вторую грязную с более поздним временем — она идёт ниже.
- Вход `/dev_auth` как maid → автопереход на `/cleaning`, видно то же.
- Нажать «Закрыть уборку ✓» → пропадает из списка; в карточке квартиры чип «Свободна», строка «Нужна уборка: Нет».

Expected: все пункты прошли.

- [ ] **Step 3: Отчёт**

Если что-то не так — откатиться к задаче, где это сломалось, и починить. Если всё ок — двигаться к деплою.

---

## Task 9: Деплой на прод

- [ ] **Step 1: Запушить**

Run:
```bash
cd /home/uybaan/fil-crm && git push origin feat/prototype
```

- [ ] **Step 2: Подтянуть и перебилдить на проде**

Run:
```bash
ssh cms-gen-bot '
set -e
cd /opt/fil-crm
git pull --ff-only origin feat/prototype
cd frontend
. "$HOME/.nvm/nvm.sh" && nvm use node >/dev/null
npm install --silent 2>&1 | tail -3
npm run build 2>&1 | tail -5

# Перезапуск бэка (подхватит новую миграцию на startup)
tmux send-keys -t fil-crm:backend C-c
sleep 2
tmux send-keys -t fil-crm:backend "cd /opt/fil-crm && uv run --env-file .env uvicorn backend.main:app --reload --port 8000" C-m
sleep 4

# Sanity
curl -sS http://127.0.0.1:8000/health
echo
curl -sSI https://sakha.gay/ | head -1
curl -sS https://sakha.gay/api/health
'
```

Expected: `{"ok":true}` и `HTTP/1.1 200 OK`. Миграция автоматически накатилась при старте.

- [ ] **Step 3: Визуальный smoke на проде**

Открыть `https://sakha.gay/`. Повторить сокращённый чеклист из Task 8 Step 2 (сценарий с диалогом + `/cleaning` + mark-clean). Одной квартире реально назначить время, проверить, что чип есть, закрыть уборку.

Expected: всё работает.

- [ ] **Step 4: Финальный коммит не нужен**

Все коммиты уже в master. Этап деплоя только выкатывает.
