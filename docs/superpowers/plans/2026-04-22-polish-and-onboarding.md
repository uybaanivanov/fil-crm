# Polish + Онбординг + Мульти-валюта — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Довести прототип fil-crm до боевого вида — отполировать карточку квартиры, добавить ручной режим создания и форму создания юзеров, заменить уродский select квартиры в брони на combobox с поиском, ввести мульти-валюту.

**Architecture:** Изменения локализованы в существующих модулях. Новые компоненты на фронте: `HelpTip`, `CoverPicker`, `ApartmentPicker`, валютный свитч. Новые эндпоинты на бэке: загрузка/удаление обложки, создание юзера с паролем, поиск квартир с занятостью, курсы валют. Хранение медиа — локальная FS под `backend/media/`, на проде раздаёт nginx.

**Tech Stack:** Python 3.13 + FastAPI + raw SQL по sqlite (`backend/db.py`). Фронт — SvelteKit 5 (runes-style `$state`/`$props`). Тесты — pytest с TestClient (см. `tests/conftest.py`). Валюты — `open.er-api.com`. Хеширование пароля — `hashlib.scrypt` из stdlib (без новых зависимостей). Загрузка файлов — `python-multipart` (новая dep).

---

## Спека

`docs/superpowers/specs/2026-04-22-polish-and-onboarding-design.md`. Если в ходе имплементации что-то расходится со спекой — править план/спеку, не игнорить.

## Глобальные правила

- Раздельные коммиты по логически осмысленным шагам (после каждого зелёного теста — коммит). Сообщения коммитов — короткие, на русском, в стиле существующих (`feat(...)`, `fix(...)`).
- Все БД-операции — raw SQL через `with get_conn() as conn` (см. `backend/db.py`), никакого ORM.
- Все новые pytest-тесты — рядом в `tests/test_*.py`. Standalone `e2e_*.py` создавать НЕ нужно — для этих фич достаточно in-process TestClient.
- Не менять существующие тесты, если их падение не вызвано целевыми изменениями. Если падение легитимное — поправить и описать в коммите.
- Перед каждой задачей запускать весь тестовый прогон (`uv run pytest -q`) — должны быть зелёные. После задачи — тоже. Если что-то поломалось вне скоупа задачи — стоп, сначала чинить.
- Никаких эмодзи в коде/коммитах (CLAUDE.md), но в UI допустимы там, где это часть дизайна (`📷` плейсхолдер).

---

## Task 0: Инфраструктура — миграции, deps, media-папка

**Files:**
- Create: `backend/migrations/008_users_credentials.sql`
- Create: `backend/migrations/009_currency.sql`
- Modify: `pyproject.toml`
- Modify: `backend/main.py`
- Modify: `.gitignore`
- Create: `backend/media/.gitkeep`

- [ ] **Step 0.1: Добавить `python-multipart` в зависимости**

В `pyproject.toml`, секция `dependencies` — добавить строкой:

```toml
    "python-multipart>=0.0.9",
```

Запустить `uv sync` — проверить что устанавливается.

- [ ] **Step 0.2: Миграция 008 — username + password_hash в users**

Создать `backend/migrations/008_users_credentials.sql`:

```sql
ALTER TABLE users ADD COLUMN username TEXT;
ALTER TABLE users ADD COLUMN password_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
```

(Колонки делаем nullable, чтобы не ломать существующие dev-юзеров без логина/пароля.)

- [ ] **Step 0.3: Миграция 009 — currency_rates**

Создать `backend/migrations/009_currency.sql`:

```sql
CREATE TABLE IF NOT EXISTS currency_rates (
    date TEXT NOT NULL,
    code TEXT NOT NULL,
    rate_to_rub REAL NOT NULL,
    PRIMARY KEY (date, code)
);
```

- [ ] **Step 0.4: Подготовить media-папку**

Создать `backend/media/.gitkeep` (пустой файл).

В `.gitignore` добавить (отдельной строкой, после существующих):

```
backend/media/apartments/
```

(Сама `backend/media/` остаётся в репо благодаря `.gitkeep`, но содержимое `apartments/` игнорируется.)

- [ ] **Step 0.5: Mount StaticFiles в `backend/main.py`**

В `backend/main.py` после импортов и перед `app = FastAPI(...)` добавить импорт:

```python
from fastapi.staticfiles import StaticFiles
```

После `app.add_middleware(CORSMiddleware, ...)` блока (≈строка 30) добавить:

```python
from pathlib import Path

_MEDIA_DIR = Path(__file__).resolve().parent / "media"
_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_MEDIA_DIR)), name="media")
```

- [ ] **Step 0.6: Запустить миграции и smoke**

```bash
uv run --env-file .env python -c "from backend.db import apply_migrations; apply_migrations()"
uv run pytest tests/test_smoke.py -q
```

Ожидание: 2 миграции применились без ошибок, smoke зелёный.

- [ ] **Step 0.7: Commit**

```bash
git add pyproject.toml uv.lock backend/migrations/008_users_credentials.sql backend/migrations/009_currency.sql backend/main.py .gitignore backend/media/.gitkeep
git commit -m "chore: миграции credentials/currency + media static + python-multipart"
```

---

## Task 1: EditableField — единый визуальный стиль (снять required)

**Files:**
- Modify: `frontend/src/lib/ui/EditableField.svelte`

**Контекст:** сейчас обязательные поля рисуются с primary-пунктиром, звёздочкой и хинтом «Обязательно для сохранения». Юзер хочет, чтобы все поля выглядели одинаково — и в характеристиках, и в расходах. Параметр `required` оставляем (логика страниц на него опирается), но ничего визуального он больше не делает.

- [ ] **Step 1.1: Убрать визуальные индикаторы required**

Открыть `frontend/src/lib/ui/EditableField.svelte`. Текущий шаблон:

```svelte
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
```

Заменить на:

```svelte
<label class="field" class:has-error={!!error}>
    <span class="lbl">{label}</span>
    <div class="slot">
        {@render children()}
    </div>
    {#if error}
        <span class="err">{error}</span>
    {:else if hint}
        <span class="hint">{hint}</span>
    {/if}
</label>
```

В `<style>` удалить правила:

```css
.field.required { border-bottom-color: var(--primary, var(--accent)); }
.req { color: var(--primary, var(--accent)); margin-left: 2px; }
```

Параметр `required` в `$props()` не трогать — он остаётся для consumers (но визуально неактивен). Добавить однострочный комментарий `// required — оставлен для совместимости, визуально не влияет` рядом с пропсом.

- [ ] **Step 1.2: Проверка в браузере (ручная)**

```bash
# терминал 1: бэк
uv run --env-file .env uvicorn backend.main:app --port 8000 --reload
# терминал 2: фронт
cd frontend && npm run dev
```

Зайти на `/apartments/<любая_id>` → блок «Обязательные суммы». Поля «Аренда (₽/мес)» и «ЖКХ (₽/мес)» должны выглядеть так же, как поля в «Характеристиках» — никакого primary-пунктира, никакой звёздочки, никакого хинта про «обязательно».

- [ ] **Step 1.3: Commit**

```bash
git add frontend/src/lib/ui/EditableField.svelte
git commit -m "feat(frontend): единый стиль EditableField — required без визуальной разметки"
```

---

## Task 2: ЖКХ опционально + аренда обязательна

**Files:**
- Modify: `backend/routes/apartments.py:280-295`
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`
- Modify: `scripts/generate_baseline_expenses.py`
- Modify: `tests/test_apartments.py` (если там есть кейс на utilities-required)
- Create: `tests/test_apartments_baseline.py` (новые кейсы)

- [ ] **Step 2.1: Тест — PATCH без utilities проходит**

В `tests/test_apartments_baseline.py`:

```python
from tests.conftest import seed_user, auth


def test_patch_without_utilities_ok(client):
    owner = seed_user(client, role="owner")
    create = client.post(
        "/apartments",
        json={
            "title": "Test", "address": "ул. Тест, 1",
            "price_per_night": 3000,
            "monthly_rent": 50000,
        },
        headers=auth(owner["id"]),
    )
    assert create.status_code in (200, 201), create.text
    apt_id = create.json()["id"]

    r = client.patch(
        f"/apartments/{apt_id}",
        json={"area_m2": 42},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 200, r.text
    assert r.json()["area_m2"] == 42
    assert r.json()["monthly_utilities"] is None


def test_patch_without_rent_fails(client):
    owner = seed_user(client, role="owner")
    create = client.post(
        "/apartments",
        json={"title": "T", "address": "a", "price_per_night": 1000},
        headers=auth(owner["id"]),
    )
    apt_id = create.json()["id"]
    r = client.patch(
        f"/apartments/{apt_id}",
        json={"area_m2": 30},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 400
    assert "monthly_rent" in r.json()["detail"]
```

- [ ] **Step 2.2: Запустить тесты — должны падать**

```bash
uv run pytest tests/test_apartments_baseline.py -q
```

Ожидание: оба падают (текущая логика требует и rent, и utilities).

- [ ] **Step 2.3: Поправить PATCH в `backend/routes/apartments.py`**

Найти блок (≈строки 286–292):

```python
        merged_rent = fields.get("monthly_rent", current["monthly_rent"])
        merged_util = fields.get("monthly_utilities", current["monthly_utilities"])
        if merged_rent is None or merged_util is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="monthly_rent и monthly_utilities обязательны",
            )
```

Заменить на:

```python
        merged_rent = fields.get("monthly_rent", current["monthly_rent"])
        if merged_rent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="monthly_rent обязателен",
            )
```

- [ ] **Step 2.4: Запустить тесты — должны пройти**

```bash
uv run pytest tests/test_apartments_baseline.py -q
uv run pytest tests/test_apartments.py -q
```

Если `tests/test_apartments.py` содержит кейс `monthly_utilities обязателен` — переписать его под новое сообщение `monthly_rent обязателен` (или удалить, если кейс становится бессмысленным; в новом файле он уже покрыт).

- [ ] **Step 2.5: Поправить `scripts/generate_baseline_expenses.py`**

Открыть скрипт. Найти место, где формируется список baseline-расходов (rent + utilities). Сделать так, чтобы строка ЖКХ добавлялась только при `monthly_utilities is not None`. Минимальный патч (концептуально):

```python
items = [("Аренда", row["monthly_rent"])]
if row["monthly_utilities"] is not None:
    items.append(("ЖКХ", row["monthly_utilities"]))
```

(Точная форма зависит от текущего кода; обрабатывающий шаги — открыть файл, найти аналогичную секцию и сохранить общий стиль.)

- [ ] **Step 2.6: Тест на скрипт**

В `tests/test_baseline_script.py` добавить кейс «квартира без utilities — генерируется только аренда». Если в файле уже есть похожие тесты, скопировать паттерн. Запустить:

```bash
uv run pytest tests/test_baseline_script.py -q
```

- [ ] **Step 2.7: Поправить фронт — баннер только про аренду**

В `frontend/src/routes/apartments/[id]/+page.svelte`:

Текст баннера (≈строка 223):

```svelte
<div class="baseline-banner">
    Сначала заполни обязательные суммы (аренда/ЖКХ) ниже — без них нельзя редактировать другие поля.
</div>
```

Заменить на:

```svelte
<div class="baseline-banner">
    Сначала заполни аренду в месяц ниже — без неё нельзя редактировать другие поля.
</div>
```

В функции сабмита baseline (где сейчас валидация `if (!Number.isInteger(util) || util < 0)`) — убрать это требование. Оставить только проверку рента. Не отправлять `monthly_utilities` если поле пустое (оставить `null`/не добавлять в payload).

В блоке отлова ошибки (≈строка 110) условие:

```js
if (msg.includes('monthly_rent') || msg.includes('monthly_utilities')) {
    baselineRequired = true;
```

Заменить на:

```js
if (msg.includes('monthly_rent')) {
    baselineRequired = true;
```

`required={true}` на поле «ЖКХ» — заменить на `required={false}` (или просто убрать пропс).

- [ ] **Step 2.8: Ручная проверка**

Бэк + фронт. На карточке квартиры с заполненной арендой и пустым ЖКХ — должно сохраняться без ошибки. Если очистить аренду — баннер появляется, остальные поля не редактируются.

- [ ] **Step 2.9: Commit**

```bash
git add backend/routes/apartments.py scripts/generate_baseline_expenses.py tests/test_apartments_baseline.py tests/test_baseline_script.py tests/test_apartments.py frontend/src/routes/apartments/[id]/+page.svelte
git commit -m "feat: ЖКХ опционально, обязателен только monthly_rent"
```

---

## Task 3: Glossary + HelpTip

**Files:**
- Create: `frontend/src/lib/glossary.js`
- Create: `frontend/src/lib/ui/HelpTip.svelte`
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`
- Modify: `frontend/src/routes/reports/+page.svelte`

- [ ] **Step 3.1: Создать словарь**

`frontend/src/lib/glossary.js`:

```js
export const GLOSSARY = {
    adr: {
        title: 'ADR',
        body: 'Average Daily Rate — средняя цена за проданную ночь. Считается как выручка / количество забронированных ночей.'
    },
    revpar: {
        title: 'RevPAR',
        body: 'Revenue per Available Room — выручка на доступную комнату-ночь. Считается как выручка / общее количество ночей в периоде.'
    }
};
```

- [ ] **Step 3.2: Создать `HelpTip.svelte`**

`frontend/src/lib/ui/HelpTip.svelte`:

```svelte
<script>
    import { GLOSSARY } from '$lib/glossary.js';

    let { term } = $props();
    let open = $state(false);
    let btn = $state(null);

    const entry = $derived(GLOSSARY[term]);

    function toggle(e) {
        e.stopPropagation();
        open = !open;
    }

    function onWindowClick(e) {
        if (!open) return;
        if (btn && btn.contains(e.target)) return;
        open = false;
    }

    function onKey(e) {
        if (e.key === 'Escape') open = false;
    }

    $effect(() => {
        if (typeof window === 'undefined') return;
        window.addEventListener('click', onWindowClick);
        window.addEventListener('keydown', onKey);
        return () => {
            window.removeEventListener('click', onWindowClick);
            window.removeEventListener('keydown', onKey);
        };
    });
</script>

{#if entry}
    <span class="wrap">
        <button
            type="button"
            class="ico"
            bind:this={btn}
            onclick={toggle}
            aria-label="Что это?"
        >ⓘ</button>
        {#if open}
            <span class="pop">
                <b>{entry.title}</b>
                <span class="body">{entry.body}</span>
            </span>
        {/if}
    </span>
{/if}

<style>
    .wrap { position: relative; display: inline-flex; align-items: center; gap: 4px; }
    .ico {
        font-size: 12px;
        color: var(--faint);
        background: transparent;
        border: none;
        padding: 0 2px;
        cursor: pointer;
        line-height: 1;
    }
    .ico:hover { color: var(--ink); }
    .pop {
        position: absolute;
        top: calc(100% + 4px);
        left: 0;
        z-index: 50;
        min-width: 200px;
        max-width: 260px;
        padding: 8px 10px;
        background: var(--bg, #fff);
        color: var(--ink);
        border: 1px solid var(--border);
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        font-size: 12px;
        line-height: 1.4;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }
    .pop b { font-size: 11px; }
    .body { color: var(--faint); }
</style>
```

- [ ] **Step 3.3: Применить в карточке квартиры**

В `frontend/src/routes/apartments/[id]/+page.svelte`:

Импорт сверху (`<script>`):

```js
import HelpTip from '$lib/ui/HelpTip.svelte';
```

В блоке KPI (≈строки 187-198) текущее:

```svelte
{#each [
    ['Ночей', stats.nights, fmtMonth(currentMonth)],
    ['ADR', fmtShortRub(stats.adr), ''],
    ['Выручка', fmtShortRub(stats.revenue), Math.round((stats.utilization || 0) * 100) + '%']
] as [lbl, val, meta]}
    <div class="kpi">
        <div class="kpi-lbl">{lbl}</div>
        ...
    </div>
{/each}
```

Заменить структуру на однотипную с поддержкой `term`:

```svelte
{#each [
    { lbl: 'Ночей', val: stats.nights, meta: fmtMonth(currentMonth), term: null },
    { lbl: 'ADR', val: fmtShortRub(stats.adr), meta: '', term: 'adr' },
    { lbl: 'Выручка', val: fmtShortRub(stats.revenue), meta: Math.round((stats.utilization || 0) * 100) + '%', term: null }
] as k}
    <div class="kpi">
        <div class="kpi-lbl">
            {k.lbl}
            {#if k.term}<HelpTip term={k.term}/>{/if}
        </div>
        <div class="kpi-val">{k.val}</div>
        {#if k.meta}<div class="kpi-meta">{k.meta}</div>{/if}
    </div>
{/each}
```

- [ ] **Step 3.4: Применить в `/reports`**

В `frontend/src/routes/reports/+page.svelte` сверху импорт:

```js
import HelpTip from '$lib/ui/HelpTip.svelte';
```

Найти блок где `['ADR', fmtShortRub(data.adr)]` и `['RevPAR', fmtShortRub(data.revpar)]` — переделать аналогично, добавив `term: 'adr'` / `term: 'revpar'` и рендер `<HelpTip>` рядом с лейблом.

(Точные строки — `frontend/src/routes/reports/+page.svelte:55-56`. Если структура отличается, найти место рендера лейбла KPI и добавить туда `<HelpTip term="...">`.)

- [ ] **Step 3.5: Ручная проверка**

`/apartments/<id>`: рядом с надписью «ADR» — иконка `ⓘ`. Клик → попап с расшифровкой. Esc / клик вне — закрывается.

`/reports`: то же для ADR и RevPAR.

- [ ] **Step 3.6: Commit**

```bash
git add frontend/src/lib/glossary.js frontend/src/lib/ui/HelpTip.svelte frontend/src/routes/apartments/\[id\]/+page.svelte frontend/src/routes/reports/+page.svelte
git commit -m "feat(frontend): glossary + HelpTip для ADR/RevPAR"
```

---

## Task 4: Cover upload — backend

**Files:**
- Modify: `backend/routes/apartments.py`
- Create: `tests/test_apartment_cover.py`

- [ ] **Step 4.1: Тесты — POST/DELETE cover**

`tests/test_apartment_cover.py`:

```python
import io
from pathlib import Path

from tests.conftest import seed_user, auth


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
    return r.json()["id"]


def test_upload_cover_ok(client, tmp_path, monkeypatch):
    monkeypatch.setenv("FIL_MEDIA_DIR", str(tmp_path))
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
    saved = Path(tmp_path) / "apartments" / str(apt_id)
    assert any(p.name.startswith("cover.") for p in saved.iterdir())


def test_upload_cover_rejects_text(client, tmp_path, monkeypatch):
    monkeypatch.setenv("FIL_MEDIA_DIR", str(tmp_path))
    owner = seed_user(client, role="owner")
    apt_id = _make_apartment(client, owner["id"])
    r = client.post(
        f"/apartments/{apt_id}/cover",
        files={"file": ("c.txt", b"hello", "text/plain")},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 415


def test_upload_cover_replaces_old(client, tmp_path, monkeypatch):
    monkeypatch.setenv("FIL_MEDIA_DIR", str(tmp_path))
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
    saved = Path(tmp_path) / "apartments" / str(apt_id)
    files = sorted(p.name for p in saved.iterdir())
    assert files == ["cover.jpg"]


def test_delete_cover(client, tmp_path, monkeypatch):
    monkeypatch.setenv("FIL_MEDIA_DIR", str(tmp_path))
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
```

- [ ] **Step 4.2: Прогнать — должны падать**

```bash
uv run pytest tests/test_apartment_cover.py -q
```

Ожидание: `404` (эндпоинтов нет).

- [ ] **Step 4.3: Сделать `FIL_MEDIA_DIR` настраиваемым**

В `backend/main.py` блок mount-а заменить:

```python
_MEDIA_DIR = Path(os.environ.get("FIL_MEDIA_DIR") or (Path(__file__).resolve().parent / "media"))
_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_MEDIA_DIR)), name="media")
```

(`os` уже импортирован.)

В `backend/routes/apartments.py` сверху — добавить хелпер:

```python
import os
from pathlib import Path


def _media_root() -> Path:
    return Path(os.environ.get("FIL_MEDIA_DIR") or (Path(__file__).resolve().parent.parent / "media"))
```

- [ ] **Step 4.4: Реализовать POST cover**

В `backend/routes/apartments.py`. Импорты сверху:

```python
from fastapi import UploadFile, File
```

В конец файла (перед `delete_apartment` или после — неважно, в одной группе с другими роутами):

```python
_ALLOWED_COVER_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_MAX_COVER_SIZE = 5 * 1024 * 1024


@router.post("/{apt_id}/cover")
async def upload_cover(
    apt_id: int,
    file: UploadFile = File(...),
    _: dict = Depends(require_role("owner", "admin")),
):
    ext = _ALLOWED_COVER_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Поддерживаются только jpeg/png/webp",
        )
    data = await file.read()
    if len(data) > _MAX_COVER_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Файл больше 5 МБ",
        )
    with get_conn() as conn:
        if _row(conn, apt_id) is None:
            raise HTTPException(status_code=404, detail="Квартира не найдена")
        target_dir = _media_root() / "apartments" / str(apt_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        for old in target_dir.glob("cover.*"):
            try:
                old.unlink()
            except OSError:
                pass
        target = target_dir / f"cover.{ext}"
        target.write_bytes(data)
        url = f"/media/apartments/{apt_id}/cover.{ext}"
        conn.execute("UPDATE apartments SET cover_url = ? WHERE id = ?", (url, apt_id))
    return {"cover_url": url}


@router.delete("/{apt_id}/cover", status_code=status.HTTP_204_NO_CONTENT)
def delete_cover(
    apt_id: int,
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        if _row(conn, apt_id) is None:
            raise HTTPException(status_code=404, detail="Квартира не найдена")
        target_dir = _media_root() / "apartments" / str(apt_id)
        if target_dir.exists():
            for old in target_dir.glob("cover.*"):
                try:
                    old.unlink()
                except OSError:
                    pass
        conn.execute("UPDATE apartments SET cover_url = NULL WHERE id = ?", (apt_id,))
    return None
```

- [ ] **Step 4.5: Прогнать — должны пройти**

```bash
uv run pytest tests/test_apartment_cover.py -q
```

- [ ] **Step 4.6: Commit**

```bash
git add backend/main.py backend/routes/apartments.py tests/test_apartment_cover.py
git commit -m "feat(backend): загрузка/удаление обложки квартиры через multipart"
```

---

## Task 5: Локализация cover в парсере

**Files:**
- Modify: `backend/routes/apartments.py` (parse-url + create)
- Modify: `tests/test_parsers_router.py` или новый `tests/test_parser_cover.py`

**Контекст:** парсер сейчас отдаёт внешний `cover_url` (с doska.ykt.ru / youla.ru). После Task 4 у нас есть локальное хранилище. Хотим: после парсинга бэк сразу качает картинку в `media/apartments/_pending/<uuid>.<ext>`, и при `POST /apartments` (если payload содержит такой `_pending`-путь) перемещает её в каталог квартиры.

- [ ] **Step 5.1: Тест — после парсинга cover_url локальный**

`tests/test_parser_cover.py`:

```python
from pathlib import Path
from unittest.mock import patch

from tests.conftest import seed_user, auth


def test_parse_localizes_cover(client, tmp_path, monkeypatch):
    monkeypatch.setenv("FIL_MEDIA_DIR", str(tmp_path))
    owner = seed_user(client, role="owner")

    # подменяем парсер целиком, чтобы не дёргать реальный URL/MoreLogin
    fake_listing = type("L", (), {
        "title": "Y", "address": "a", "price_per_night": 1500,
        "rooms": None, "area_m2": None, "floor": None, "district": None,
        "cover_url": "http://example.com/img.png",
        "source": "doska_ykt",
        "source_url": "http://doska.ykt.ru/x",
    })()

    png = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
        "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
    )

    class FakeResp:
        status_code = 200
        headers = {"content-type": "image/png"}
        content = png
        def raise_for_status(self): pass

    with patch("backend.routes.apartments._fetch_listing", return_value=fake_listing), \
         patch("httpx.Client.get", return_value=FakeResp()):
        r = client.post(
            "/apartments/parse-url",
            json={"url": "http://doska.ykt.ru/x"},
            headers=auth(owner["id"]),
        )
    assert r.status_code == 200, r.text
    cover = r.json()["cover_url"]
    assert cover.startswith("/media/apartments/_pending/")
    pending_file = Path(tmp_path) / "apartments" / "_pending" / Path(cover).name
    assert pending_file.exists()


def test_create_moves_pending_cover(client, tmp_path, monkeypatch):
    monkeypatch.setenv("FIL_MEDIA_DIR", str(tmp_path))
    owner = seed_user(client, role="owner")
    pending_dir = Path(tmp_path) / "apartments" / "_pending"
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
    assert (Path(tmp_path) / "apartments" / str(apt_id) / "cover.png").exists()
    assert not (pending_dir / fname).exists()
```

- [ ] **Step 5.2: Запуск — упасть**

```bash
uv run pytest tests/test_parser_cover.py -q
```

- [ ] **Step 5.3: Рефактор — выделить `_fetch_listing`**

В `backend/routes/apartments.py` найти `parse_url` (≈строка 251). Сейчас там вся логика старт→парсинг inline. Вынести «получить ParsedListing по URL» в отдельную функцию `async def _fetch_listing(url: str) -> ParsedListing` — без изменения поведения. Это нужно, чтобы тесты могли её мокать одной точкой.

- [ ] **Step 5.4: Скачать обложку после парсинга**

После того как `_fetch_listing` вернул объект, добавить блок:

```python
if listing.cover_url:
    listing.cover_url = _localize_cover(listing.cover_url)
```

Сам хелпер (рядом с `_media_root`):

```python
import uuid

import httpx

_COVER_EXT_BY_CT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def _localize_cover(src_url: str) -> str | None:
    pending = _media_root() / "apartments" / "_pending"
    pending.mkdir(parents=True, exist_ok=True)
    # GC: удаляем файлы старше 24 ч
    import time
    cutoff = time.time() - 24 * 3600
    for old in pending.iterdir():
        try:
            if old.stat().st_mtime < cutoff:
                old.unlink()
        except OSError:
            pass
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as c:
            r = c.get(src_url)
            r.raise_for_status()
            ext = _COVER_EXT_BY_CT.get((r.headers.get("content-type") or "").split(";")[0].strip())
            if ext is None:
                return None
            name = f"{uuid.uuid4().hex}.{ext}"
            (pending / name).write_bytes(r.content)
            return f"/media/apartments/_pending/{name}"
    except Exception:
        return None
```

- [ ] **Step 5.5: Перемещение pending → квартира при создании**

Найти `create_apartment` (`POST /apartments`). После INSERT и получения `new_id` добавить:

```python
        if payload.cover_url and payload.cover_url.startswith("/media/apartments/_pending/"):
            from_path = _media_root() / "apartments" / "_pending" / Path(payload.cover_url).name
            ext = from_path.suffix.lstrip(".")
            if from_path.exists() and ext:
                target_dir = _media_root() / "apartments" / str(new_id)
                target_dir.mkdir(parents=True, exist_ok=True)
                for old in target_dir.glob("cover.*"):
                    try: old.unlink()
                    except OSError: pass
                target = target_dir / f"cover.{ext}"
                from_path.rename(target)
                new_url = f"/media/apartments/{new_id}/cover.{ext}"
                conn.execute("UPDATE apartments SET cover_url = ? WHERE id = ?", (new_url, new_id))
```

(Размещение — сразу после INSERT, перед `row = ...` или внутри транзакции; зависит от структуры функции. Файловые операции вне SQL-транзакции допустимы — это единственный consumer.)

Импорт `Path` уже есть.

- [ ] **Step 5.6: Тесты — пройти**

```bash
uv run pytest tests/test_parser_cover.py tests/test_parsers_router.py tests/test_apartments.py tests/test_apartment_cover.py -q
```

Если что-то из существующего падает — изучить причину; вероятно мок `_fetch_listing` потребует адаптации под реальную сигнатуру.

- [ ] **Step 5.7: Commit**

```bash
git add backend/routes/apartments.py tests/test_parser_cover.py
git commit -m "feat(backend): парсер скачивает cover локально, create перемещает из _pending"
```

---

## Task 6: CoverPicker компонент + интеграция

**Files:**
- Create: `frontend/src/lib/ui/CoverPicker.svelte`
- Modify: `frontend/src/routes/apartments/[id]/+page.svelte`
- Modify: `frontend/src/routes/apartments/new/+page.svelte` (опционально — если в форме есть поле cover_url)

- [ ] **Step 6.1: Создать `CoverPicker.svelte`**

`frontend/src/lib/ui/CoverPicker.svelte`:

```svelte
<script>
    import { api } from '$lib/api.js';

    let { apartmentId, cover, onChange } = $props();

    let busy = $state(false);
    let err = $state(null);
    let inputEl = $state(null);

    function pick() { inputEl?.click(); }

    async function onFile(e) {
        const f = e.target.files?.[0];
        e.target.value = '';
        if (!f) return;
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) {
            err = 'Только jpeg/png/webp'; return;
        }
        if (f.size > 5 * 1024 * 1024) {
            err = 'Файл больше 5 МБ'; return;
        }
        busy = true; err = null;
        try {
            const fd = new FormData();
            fd.append('file', f);
            const r = await api.postForm(`/apartments/${apartmentId}/cover`, fd);
            onChange(r.cover_url);
        } catch (e) {
            err = e.message || 'Ошибка загрузки';
        } finally {
            busy = false;
        }
    }

    async function remove() {
        if (!confirm('Удалить обложку?')) return;
        busy = true; err = null;
        try {
            await api.del(`/apartments/${apartmentId}/cover`);
            onChange(null);
        } catch (e) {
            err = e.message || 'Ошибка удаления';
        } finally {
            busy = false;
        }
    }
</script>

<div class="cover">
    {#if cover}
        <div
            class="thumb"
            style="background-image:url({cover})"
            role="button"
            tabindex="0"
        >
            <div class="ovr">
                <button type="button" onclick={pick} disabled={busy}>Заменить</button>
                <button type="button" class="danger" onclick={remove} disabled={busy}>Удалить</button>
            </div>
        </div>
    {:else}
        <button type="button" class="placeholder" onclick={pick} disabled={busy}>
            <span class="icon">📷</span>
            <span>Загрузить обложку</span>
        </button>
    {/if}
    <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        bind:this={inputEl}
        onchange={onFile}
        hidden
    />
    {#if busy}<div class="hint">Загрузка…</div>{/if}
    {#if err}<div class="err">{err}</div>{/if}
</div>

<style>
    .cover { display: flex; flex-direction: column; gap: 6px; align-items: flex-start; }
    .thumb {
        width: 160px; height: 160px;
        border-radius: 10px;
        background-size: cover; background-position: center;
        position: relative;
        overflow: hidden;
        border: 1px solid var(--border);
    }
    .ovr {
        position: absolute; inset: 0;
        background: rgba(0,0,0,0.5);
        opacity: 0;
        transition: opacity 120ms ease;
        display: flex; align-items: center; justify-content: center; gap: 8px;
    }
    .thumb:hover .ovr, .thumb:focus-within .ovr { opacity: 1; }
    .ovr button {
        background: #fff; border: none; padding: 6px 10px; border-radius: 6px;
        font-size: 12px; cursor: pointer;
    }
    .ovr .danger { color: #c33; }
    .placeholder {
        width: 160px; height: 160px;
        border: 1px dashed var(--border);
        border-radius: 10px;
        background: transparent;
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        gap: 8px;
        color: var(--faint);
        font-size: 12px;
        cursor: pointer;
    }
    .placeholder:hover { color: var(--ink); border-color: var(--ink); }
    .icon { font-size: 22px; }
    .hint { font-size: 11px; color: var(--faint); }
    .err { font-size: 11px; color: #c33; }
</style>
```

- [ ] **Step 6.2: Добавить хелперы в `api.js`**

В `frontend/src/lib/api.js` если нет — добавить:

```js
async postForm(path, formData) {
    return this._req(path, { method: 'POST', body: formData });
},
async del(path) {
    return this._req(path, { method: 'DELETE' });
},
```

(Структура `api` в проекте — ориентируйся на существующие методы `get`/`post`/`patch`. Если уже есть эквиваленты под другими именами — переиспользуй.)

В обработчике `_req` — НЕ ставить `Content-Type: application/json` если `body instanceof FormData` (браузер сам поставит multipart с boundary).

- [ ] **Step 6.3: Подключить `CoverPicker` в карточке квартиры**

В `frontend/src/routes/apartments/[id]/+page.svelte`:

Импорт:

```js
import CoverPicker from '$lib/ui/CoverPicker.svelte';
```

Найти секцию, где сейчас рендерится `EditableField` для `cover_url` (это делается через общий `<InlineEdit field="cover_url"/>` или явный `<EditableField>`). Заменить эту строку на:

```svelte
<CoverPicker
    apartmentId={apt.id}
    cover={apt.cover_url}
    onChange={(u) => { apt.cover_url = u; }}
/>
```

Если поле было внутри секции «Обложка» — секция остаётся (с тем же `<Section title="Обложка">`).

- [ ] **Step 6.4: Ручная проверка**

Зайти на карточку квартиры. Без обложки — видим dashed-плейсхолдер «📷 Загрузить обложку». Клик → выбор файла → загружается → видим thumbnail. Hover → оверлей с «Заменить»/«Удалить». «Удалить» → плейсхолдер.

- [ ] **Step 6.5: Commit**

```bash
git add frontend/src/lib/ui/CoverPicker.svelte frontend/src/lib/api.js frontend/src/routes/apartments/\[id\]/+page.svelte
git commit -m "feat(frontend): CoverPicker — кнопка-загрузчик обложки квартиры"
```

---

## Task 7: Юзеры — username/password + форма создания

**Files:**
- Create: `backend/security.py` (хеширование пароля)
- Modify: `backend/routes/users.py`
- Create: `tests/test_users_create.py`
- Create: `frontend/src/routes/users/new/+page.svelte`
- Modify: `frontend/src/routes/users/+page.svelte` (кнопка «+»)

- [ ] **Step 7.1: `backend/security.py` — scrypt-хеш**

```python
"""Хеширование паролей через hashlib.scrypt (stdlib).

Формат строки: scrypt$<n>$<r>$<p>$<salt_hex>$<hash_hex>
"""
import hashlib
import os


_N = 2 ** 14
_R = 8
_P = 1
_SALT_BYTES = 16
_KEY_LEN = 32


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    key = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=_N, r=_R, p=_P, dklen=_KEY_LEN)
    return f"scrypt${_N}${_R}${_P}${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n_s, r_s, p_s, salt_hex, key_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        n, r, p = int(n_s), int(r_s), int(p_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
    except (ValueError, AttributeError):
        return False
    actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=len(expected))
    return _const_eq(actual, expected)


def _const_eq(a: bytes, b: bytes) -> bool:
    if len(a) != len(b):
        return False
    res = 0
    for x, y in zip(a, b):
        res |= x ^ y
    return res == 0
```

- [ ] **Step 7.2: Тесты на эндпоинт**

`tests/test_users_create.py`:

```python
from tests.conftest import seed_user, auth


def test_owner_creates_user(client):
    owner = seed_user(client, role="owner")
    r = client.post(
        "/users",
        json={
            "username": "kolya",
            "password": "supersecret",
            "full_name": "Коля",
            "role": "admin",
        },
        headers=auth(owner["id"]),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["username"] == "kolya"
    assert body["role"] == "admin"
    assert "password" not in body and "password_hash" not in body


def test_admin_cannot_create_user(client):
    owner = seed_user(client, role="owner")
    admin = seed_user(client, role="admin", name="Админ")
    r = client.post(
        "/users",
        json={"username": "x", "password": "12345678", "full_name": "X", "role": "maid"},
        headers=auth(admin["id"]),
    )
    assert r.status_code == 403


def test_username_conflict(client):
    owner = seed_user(client, role="owner")
    payload = {"username": "alice", "password": "12345678", "full_name": "A", "role": "maid"}
    r1 = client.post("/users", json=payload, headers=auth(owner["id"]))
    assert r1.status_code == 201
    r2 = client.post("/users", json=payload, headers=auth(owner["id"]))
    assert r2.status_code == 409


def test_password_too_short(client):
    owner = seed_user(client, role="owner")
    r = client.post(
        "/users",
        json={"username": "u", "password": "short", "full_name": "U", "role": "maid"},
        headers=auth(owner["id"]),
    )
    assert r.status_code == 422
```

- [ ] **Step 7.3: Прогнать — упасть**

```bash
uv run pytest tests/test_users_create.py -q
```

Ожидание: тесты падают (нет `username`/`password` в API).

- [ ] **Step 7.4: Расширить `POST /users`**

В `backend/routes/users.py`:

```python
import re
import sqlite3

from backend.security import hash_password


_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)
    role: Role


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserIn, _: dict = Depends(require_role("owner"))):
    if not _USERNAME_RE.match(payload.username):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="username должен быть [a-z0-9_]{3,32}",
        )
    pw_hash = hash_password(payload.password)
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (full_name, role, username, password_hash) VALUES (?, ?, ?, ?)",
                (payload.full_name, payload.role.value, payload.username, pw_hash),
            )
            new_id = cur.lastrowid
            row = conn.execute(
                "SELECT id, full_name, role, username, created_at FROM users WHERE id = ?",
                (new_id,),
            ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username занят",
        )
    return dict(row)
```

В `list_users` — также добавить `username` в SELECT:

```python
"SELECT id, full_name, role, username, created_at FROM users ORDER BY id"
```

- [ ] **Step 7.5: Прогнать — пройти**

```bash
uv run pytest tests/test_users_create.py -q
uv run pytest tests/test_smoke.py tests/test_authz.py -q
```

- [ ] **Step 7.6: Frontend — `/users/new`**

`frontend/src/routes/users/new/+page.svelte`:

```svelte
<script>
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { api, ApiError } from '$lib/api.js';
    import { getUser } from '$lib/auth.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';

    let me = $state(null);
    let username = $state('');
    let password = $state('');
    let showPass = $state(false);
    let fullName = $state('');
    let role = $state('admin');
    let saving = $state(false);
    let error = $state(null);

    onMount(() => {
        me = getUser();
        if (!me || me.role !== 'owner') {
            error = 'Доступно только владельцу';
        }
    });

    async function submit() {
        error = null;
        if (!username.trim() || password.length < 8 || !fullName.trim()) {
            error = 'Заполни все поля; пароль ≥ 8 символов'; return;
        }
        saving = true;
        try {
            await api.post('/users', {
                username: username.trim(), password, full_name: fullName.trim(), role,
            });
            goto('/users');
        } catch (e) {
            error = e instanceof ApiError ? e.message : 'Ошибка';
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новый пользователь" back="Команда" backOnClick={() => goto('/users')} />

{#if error && error === 'Доступно только владельцу'}
    <div class="error-banner">{error}</div>
{:else}
    <Section title="Учётные данные">
        <div class="wrap">
            <Card pad={14}>
                <form onsubmit={(e) => { e.preventDefault(); submit(); }}>
                    <label>Username
                        <input type="text" bind:value={username} autocomplete="off" />
                    </label>
                    <label>Пароль
                        <div class="pass">
                            <input type={showPass ? 'text' : 'password'} bind:value={password} />
                            <button type="button" onclick={() => showPass = !showPass}>
                                {showPass ? 'Скрыть' : 'Показать'}
                            </button>
                        </div>
                    </label>
                    <label>Полное имя
                        <input type="text" bind:value={fullName} />
                    </label>
                    <label>Роль
                        <select bind:value={role}>
                            <option value="owner">Владелец</option>
                            <option value="admin">Админ</option>
                            <option value="maid">Горничная</option>
                        </select>
                    </label>
                    {#if error && error !== 'Доступно только владельцу'}
                        <div class="err">{error}</div>
                    {/if}
                    <button type="submit" class="primary" disabled={saving}>
                        {saving ? 'Создание…' : 'Создать'}
                    </button>
                </form>
            </Card>
        </div>
    </Section>
{/if}

<style>
    .wrap { padding: 0 16px; }
    form { display: flex; flex-direction: column; gap: 12px; }
    label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--faint); }
    input, select { padding: 6px 8px; font-size: 14px; border: 1px solid var(--border); border-radius: 6px; }
    .pass { display: flex; gap: 6px; }
    .pass input { flex: 1; }
    .pass button { font-size: 11px; padding: 0 8px; background: transparent; border: 1px solid var(--border); border-radius: 6px; cursor: pointer; }
    .primary { padding: 10px; background: var(--ink); color: #fff; border: none; border-radius: 8px; cursor: pointer; }
    .primary:disabled { opacity: 0.5; }
    .err { font-size: 12px; color: #c33; }
    .error-banner { padding: 12px; color: #c33; }
</style>
```

- [ ] **Step 7.7: Кнопка «+» на `/users`**

В `frontend/src/routes/users/+page.svelte` найти `<PageHead ...>`. Добавить рядом кнопку (только для owner) — простейший вариант: после PageHead в шаблоне:

```svelte
{#if me?.role === 'owner'}
    <div class="add-row">
        <button class="add-btn" onclick={() => goto('/users/new')}>+ Добавить</button>
    </div>
{/if}
```

Стили (в `<style>`):

```css
.add-row { padding: 0 16px 12px; }
.add-btn { padding: 6px 10px; border: 1px solid var(--border); background: transparent; border-radius: 6px; cursor: pointer; font-size: 13px; }
```

(Если в проекте есть готовый `<AddBtn/>` — заменить на него.)

- [ ] **Step 7.8: Ручная проверка**

Owner → `/users` → жмёт «+» → форма → создаёт юзера → возврат на `/users`, новый юзер в списке. Не-owner — кнопки нет, прямой переход показывает «Доступно только владельцу».

- [ ] **Step 7.9: Commit**

```bash
git add backend/security.py backend/routes/users.py tests/test_users_create.py frontend/src/routes/users/new/+page.svelte frontend/src/routes/users/+page.svelte
git commit -m "feat: создание юзеров с username/password (scrypt)"
```

---

## Task 8: Табы на `/apartments/new`

**Files:**
- Modify: `frontend/src/routes/apartments/new/+page.svelte`

- [ ] **Step 8.1: Добавить таб-стейт и переключатель**

В `frontend/src/routes/apartments/new/+page.svelte` сверху скрипта добавить:

```js
let mode = $state('parse'); // 'parse' | 'manual'
```

В шаблоне сразу после `<PageHead ...>` добавить таб-блок:

```svelte
<div class="tabs">
    <button class:active={mode === 'parse'} onclick={() => mode = 'parse'}>По ссылке</button>
    <button class:active={mode === 'manual'} onclick={() => mode = 'manual'}>Вручную</button>
</div>
```

Стили в `<style>`:

```css
.tabs { display: flex; gap: 4px; padding: 0 16px 12px; }
.tabs button {
    flex: 1; padding: 8px;
    background: transparent; border: 1px solid var(--border); border-radius: 8px;
    font-size: 13px; color: var(--faint); cursor: pointer;
}
.tabs button.active { background: var(--ink); color: #fff; border-color: var(--ink); }
```

- [ ] **Step 8.2: Скрыть URL-блок в режиме manual**

Найти секцию ввода URL (input + кнопка «Распарсить» + ошибки парсинга). Обернуть её в:

```svelte
{#if mode === 'parse'}
    ... текущий URL-блок ...
{/if}
```

- [ ] **Step 8.3: Показать форму полей всегда**

Сейчас форма показывается через `{#if listing}`. В ручном режиме `listing` пустой — но форма должна быть. Условие меняем:

Текущее (концептуально):

```svelte
{#if listing}
    ... поля title/address/.../save ...
{/if}
```

На:

```svelte
{#if mode === 'manual' || listing}
    ... поля title/address/.../save ...
{/if}
```

- [ ] **Step 8.4: В save() — выставить source/source_url по режиму**

Найти функцию `save()`. В `payload`:

Текущее:

```js
const payload = {
    title, address,
    price_per_night: priceNum,
    source, source_url: sourceUrl,
};
```

Заменить на:

```js
const payload = {
    title, address,
    price_per_night: priceNum,
    source: mode === 'manual' ? 'manual' : source,
    source_url: mode === 'manual' ? null : sourceUrl,
};
```

- [ ] **Step 8.5: Бэк — пропустить `source: 'manual'`**

Открыть `backend/routes/apartments.py` — модель `ApartmentCreate`. Если там `source` enum с допустимыми значениями `('doska_ykt', 'youla')` — добавить `'manual'`. Если `source: str | None` без валидации — ничего делать не надо (и `source_url=null` тоже допустим).

Если есть UNIQUE-индекс по `(source, source_url)` или подобное — убедиться, что для `source='manual', source_url=NULL` это не сработает (NULL в SQLite не считается равным самому себе → должно быть ок).

Если в `tests/test_apartments.py` есть кейс «source обязателен из набора» — обновить.

- [ ] **Step 8.6: Ручная проверка**

`/apartments/new`:
- Таб «По ссылке» — текущее поведение, парсит и префилит.
- Таб «Вручную» — нет URL-блока, форма пустая, заполнил → сохранил → попал на карточку квартиры с `source='manual'`.

- [ ] **Step 8.7: Commit**

```bash
git add frontend/src/routes/apartments/new/+page.svelte backend/routes/apartments.py
git commit -m "feat(frontend): табы парсер/вручную на /apartments/new"
```

---

## Task 9: Поиск квартир для брони (back) + ApartmentPicker (front)

**Files:**
- Modify: `backend/routes/apartments.py` (`GET /apartments` — q, check_in, check_out)
- Create: `tests/test_apartments_search.py`
- Create: `frontend/src/lib/ui/ApartmentPicker.svelte`
- Modify: `frontend/src/routes/bookings/new/+page.svelte`

- [ ] **Step 9.1: Тесты поиска**

`tests/test_apartments_search.py`:

```python
from tests.conftest import seed_user, auth


def _create(client, owner_id, **kw):
    body = {"title": "T", "address": "ул. Ленина, 1", "price_per_night": 1000, **kw}
    return client.post("/apartments", json=body, headers=auth(owner_id)).json()["id"]


def test_search_by_callsign(client):
    owner = seed_user(client, role="owner")
    a = _create(client, owner["id"], title="Кв 1", callsign="alpha")
    b = _create(client, owner["id"], title="Кв 2", callsign="bravo")
    r = client.get("/apartments?q=alp", headers=auth(owner["id"]))
    assert r.status_code == 200
    ids = [x["id"] for x in r.json()]
    assert a in ids and b not in ids


def test_search_by_address(client):
    owner = seed_user(client, role="owner")
    a = _create(client, owner["id"], address="проспект Мира, 5")
    b = _create(client, owner["id"], address="ул. Кулаковского, 12")
    r = client.get("/apartments?q=кулак", headers=auth(owner["id"]))
    ids = [x["id"] for x in r.json()]
    assert b in ids and a not in ids


def test_next_booked_from(client):
    owner = seed_user(client, role="owner")
    apt_id = _create(client, owner["id"])
    # клиент
    cli = client.post("/clients", json={"full_name": "G", "phone": "+7..."},
                      headers=auth(owner["id"])).json()
    # бронь 2026-05-10 → 2026-05-12
    client.post("/bookings", json={
        "apartment_id": apt_id, "client_id": cli["id"],
        "check_in": "2026-05-10", "check_out": "2026-05-12",
        "total_price": 5000,
    }, headers=auth(owner["id"]))
    r = client.get(
        "/apartments?check_in=2026-05-09&check_out=2026-05-15",
        headers=auth(owner["id"]),
    )
    apt = next(x for x in r.json() if x["id"] == apt_id)
    assert apt["next_booked_from"] == "2026-05-10"


def test_no_dates_no_field(client):
    owner = seed_user(client, role="owner")
    _create(client, owner["id"])
    r = client.get("/apartments", headers=auth(owner["id"]))
    # next_booked_from = null когда диапазон не задан
    assert all(x["next_booked_from"] is None for x in r.json())
```

- [ ] **Step 9.2: Прогон — упасть**

```bash
uv run pytest tests/test_apartments_search.py -q
```

- [ ] **Step 9.3: Расширить `GET /apartments`**

В `backend/routes/apartments.py` найти `list_apartments` (`GET /apartments`). Добавить параметры:

```python
from fastapi import Query


@router.get("")
def list_apartments(
    q: str | None = Query(default=None),
    check_in: str | None = Query(default=None),
    check_out: str | None = Query(default=None),
    _: dict = Depends(require_role("owner", "admin", "maid")),
):
    where = []
    params: list = []
    if q:
        where.append("(LOWER(callsign) LIKE ? OR LOWER(address) LIKE ?)")
        like = f"%{q.lower()}%"
        params.extend([like, like])
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    next_select = "NULL AS next_booked_from"
    next_params: list = []
    if check_in and check_out:
        # ближайшая бронь, пересекающая [check_in, check_out) или начинающаяся внутри окна
        next_select = (
            "(SELECT MIN(b.check_in) FROM bookings b "
            " WHERE b.apartment_id = a.id "
            "   AND b.status = 'active' "
            "   AND b.check_out > ? AND b.check_in < ?) AS next_booked_from"
        )
        next_params.extend([check_in, check_out])

    sql = (
        f"SELECT a.*, {next_select} FROM apartments a {where_sql} "
        f"ORDER BY (next_booked_from IS NULL) DESC, a.id ASC"
    )
    # параметры для next_select идут перед параметрами WHERE — так что переставим
    full_params = next_params + params
    with get_conn() as conn:
        rows = conn.execute(sql, full_params).fetchall()
    return [dict(r) for r in rows]
```

(Внимание: в SQLite параметры подставляются по порядку появления `?`. `next_select` стоит до `WHERE`, поэтому его параметры идут первыми. Сортировка `(next_booked_from IS NULL) DESC` ставит свободные (`NULL`) первыми.)

Если в проекте уже есть кастомный список ролей для `GET /apartments` — переиспользовать.

- [ ] **Step 9.4: Прогон — пройти**

```bash
uv run pytest tests/test_apartments_search.py -q
uv run pytest tests/test_apartments.py tests/test_authz.py -q
```

- [ ] **Step 9.5: Создать `ApartmentPicker.svelte`**

`frontend/src/lib/ui/ApartmentPicker.svelte`:

```svelte
<script>
    import { api } from '$lib/api.js';

    let { value, check_in, check_out, onChange } = $props();

    let query = $state('');
    let items = $state([]);
    let open = $state(false);
    let active = $state(0);
    let selected = $state(null);
    let loading = $state(false);
    let timer = null;

    async function fetchList(q) {
        loading = true;
        const params = new URLSearchParams();
        if (q) params.set('q', q);
        if (check_in) params.set('check_in', check_in);
        if (check_out) params.set('check_out', check_out);
        try {
            items = await api.get(`/apartments?${params}`);
        } finally {
            loading = false;
        }
    }

    function debouncedFetch(q) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => fetchList(q), 200);
    }

    $effect(() => {
        if (value && (!selected || selected.id !== value)) {
            api.get(`/apartments/${value}`).then(a => selected = a).catch(() => {});
        }
        if (!value) selected = null;
    });

    function focus() { open = true; if (items.length === 0) fetchList(''); }
    function pick(it) {
        selected = it;
        onChange(it.id);
        open = false;
        query = '';
    }

    function onKey(e) {
        if (!open) return;
        if (e.key === 'ArrowDown') { e.preventDefault(); active = Math.min(active + 1, items.length - 1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); active = Math.max(active - 1, 0); }
        else if (e.key === 'Enter') { e.preventDefault(); if (items[active]) pick(items[active]); }
        else if (e.key === 'Escape') { open = false; }
    }

    function fmtTo(d) {
        if (!d) return null;
        const [_, m, day] = d.split('-');
        return `${day}.${m}`;
    }
</script>

<div class="picker">
    {#if selected && !open}
        <button type="button" class="selected" onclick={() => { open = true; query = ''; fetchList(''); }}>
            <img class="thumb" src={selected.cover_url || '/placeholder.png'} alt="" />
            <div class="meta">
                <div class="title">{selected.callsign || selected.title}</div>
                <div class="addr">{selected.address}</div>
            </div>
            <span class="change">Сменить</span>
        </button>
    {:else}
        <input
            type="text"
            placeholder="Поиск по позывному или адресу"
            bind:value={query}
            oninput={() => debouncedFetch(query)}
            onfocus={focus}
            onkeydown={onKey}
        />
        {#if open}
            <div class="dropdown">
                {#if loading}<div class="empty">…</div>{/if}
                {#each items as it, i}
                    <button
                        type="button"
                        class="row"
                        class:active={i === active}
                        onmouseenter={() => active = i}
                        onclick={() => pick(it)}
                    >
                        <img class="thumb" src={it.cover_url || '/placeholder.png'} alt="" />
                        <div class="meta">
                            <div class="title">{it.callsign || it.title}</div>
                            <div class="addr">{it.address}</div>
                        </div>
                        {#if it.next_booked_from}
                            <span class="busy">до {fmtTo(it.next_booked_from)}</span>
                        {/if}
                    </button>
                {/each}
                {#if items.length === 0 && !loading}
                    <div class="empty">Ничего не найдено</div>
                {/if}
            </div>
        {/if}
    {/if}
</div>

<style>
    .picker { position: relative; }
    input { width: 100%; padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px; font-size: 14px; }
    .dropdown {
        position: absolute; top: calc(100% + 4px); left: 0; right: 0;
        max-height: 320px; overflow-y: auto; z-index: 30;
        background: #fff; border: 1px solid var(--border); border-radius: 8px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
    }
    .row, .selected {
        display: flex; align-items: center; gap: 10px;
        width: 100%; padding: 8px 10px;
        background: transparent; border: none; cursor: pointer; text-align: left;
    }
    .row.active { background: var(--bg-muted, #f3f3f3); }
    .selected { border: 1px solid var(--border); border-radius: 8px; }
    .thumb { width: 40px; height: 40px; object-fit: cover; border-radius: 6px; background: #eee; }
    .meta { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
    .title { font-weight: 600; font-size: 13px; }
    .addr { font-size: 11px; color: var(--faint); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .busy { font-size: 11px; color: #c33; padding: 2px 6px; background: #fee; border-radius: 4px; }
    .change { font-size: 11px; color: var(--faint); margin-left: auto; }
    .empty { padding: 10px; color: var(--faint); font-size: 12px; }
</style>
```

- [ ] **Step 9.6: Подключить в `/bookings/new`**

В `frontend/src/routes/bookings/new/+page.svelte` импортировать:

```js
import ApartmentPicker from '$lib/ui/ApartmentPicker.svelte';
```

Найти существующий `<select bind:value={apartmentId}>` (или подобный). Заменить на:

```svelte
<ApartmentPicker
    value={apartmentId}
    check_in={checkIn}
    check_out={checkOut}
    onChange={(id) => apartmentId = id}
/>
```

(`checkIn`/`checkOut` — текущие имена стейтов на странице. Если другие — поправить под факт.)

- [ ] **Step 9.7: Ручная проверка**

`/bookings/new`:
- Введи даты заезда/выезда.
- Кликни на пикер — раскрывается список. У занятых на это окно квартир — красная плашка «до DD.MM».
- Введи часть адреса/позывного — список фильтруется. Стрелки + Enter работают.
- Выбрал → пикер сворачивается, видны thumb/название/адрес + ссылка «Сменить».

- [ ] **Step 9.8: Commit**

```bash
git add backend/routes/apartments.py tests/test_apartments_search.py frontend/src/lib/ui/ApartmentPicker.svelte frontend/src/routes/bookings/new/+page.svelte
git commit -m "feat: ApartmentPicker — fuzzy-поиск по адресу/позывному + занятость"
```

---

## Task 10: Мульти-валюта (RUB / USD / VND)

**Files:**
- Create: `backend/currency.py`
- Modify: `backend/main.py` (роут `/currency/rates`)
- Create: `backend/routes/currency.py`
- Create: `scripts/refresh_rates.py`
- Modify: `README.md` (cron-рецепт)
- Create: `tests/test_currency.py`
- Create: `frontend/src/lib/currency.js`
- Modify: `frontend/src/lib/format.js`
- Modify: `frontend/src/routes/+layout.svelte`

- [ ] **Step 10.1: `backend/currency.py`**

```python
"""Курсы валют. Хранит rate_to_rub: сколько единиц валюты за 1 рубль."""
import datetime as dt

import httpx

from backend.db import get_conn

RATES_URL = "https://open.er-api.com/v6/latest/RUB"
SUPPORTED = ("USD", "VND")


async def refresh_rates() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as c:
        r = await c.get(RATES_URL)
        r.raise_for_status()
        body = r.json()
    rates = body.get("rates") or {}
    today = dt.date.today().isoformat()
    out: dict[str, float] = {}
    with get_conn() as conn:
        for code in SUPPORTED:
            v = rates.get(code)
            if v is None:
                continue
            out[code] = float(v)
            conn.execute(
                "INSERT OR REPLACE INTO currency_rates(date, code, rate_to_rub) VALUES (?, ?, ?)",
                (today, code, float(v)),
            )
    return {"date": today, "rates": out}


def get_latest_rates() -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT MAX(date) AS d FROM currency_rates").fetchone()
        d = row["d"]
        if not d:
            return {"updated_at": None, "usd": None, "vnd": None}
        rows = conn.execute(
            "SELECT code, rate_to_rub FROM currency_rates WHERE date = ?", (d,)
        ).fetchall()
    by = {r["code"]: r["rate_to_rub"] for r in rows}
    return {"updated_at": d, "usd": by.get("USD"), "vnd": by.get("VND")}
```

- [ ] **Step 10.2: Роут `/currency/rates`**

`backend/routes/currency.py`:

```python
from fastapi import APIRouter

from backend.currency import get_latest_rates

router = APIRouter(prefix="/currency", tags=["currency"])


@router.get("/rates")
def rates():
    return get_latest_rates()
```

В `backend/main.py` импорт и подключение:

```python
from backend.routes import currency as currency_routes
...
app.include_router(currency_routes.router)
```

- [ ] **Step 10.3: Тесты**

`tests/test_currency.py`:

```python
from unittest.mock import patch, AsyncMock

import pytest

from backend.db import get_conn


@pytest.mark.asyncio
async def test_refresh_writes_rates(tmp_db, monkeypatch):
    from backend import currency as cur

    fake = AsyncMock()
    fake.return_value.__aenter__.return_value.get.return_value.json = lambda: {
        "rates": {"USD": 0.011, "VND": 273.5}
    }
    fake.return_value.__aenter__.return_value.get.return_value.raise_for_status = lambda: None
    with patch("httpx.AsyncClient", fake):
        await cur.refresh_rates()
    with get_conn() as conn:
        rows = {r["code"]: r["rate_to_rub"] for r in conn.execute("SELECT * FROM currency_rates")}
    assert rows["USD"] == pytest.approx(0.011)
    assert rows["VND"] == pytest.approx(273.5)


def test_endpoint_returns_latest(client):
    with get_conn() as conn:
        conn.execute("INSERT INTO currency_rates VALUES ('2026-04-22', 'USD', 0.012)")
        conn.execute("INSERT INTO currency_rates VALUES ('2026-04-22', 'VND', 280.0)")
    r = client.get("/currency/rates")
    assert r.status_code == 200
    body = r.json()
    assert body["usd"] == 0.012 and body["vnd"] == 280.0 and body["updated_at"] == "2026-04-22"


def test_endpoint_empty(client):
    r = client.get("/currency/rates")
    assert r.status_code == 200
    body = r.json()
    assert body == {"updated_at": None, "usd": None, "vnd": None}
```

(Async-тест требует `pytest-asyncio` или `anyio` — если в проекте такой плагин не установлен, заменить async-тест на синхронный вариант, обернув `asyncio.run(cur.refresh_rates())` без mocка httpx, или использовать `httpx.MockTransport`. Проверить наличие в `pyproject.toml`. Если нет — добавить `pytest-asyncio>=0.23` в dev-deps.)

- [ ] **Step 10.4: Прогон**

```bash
uv run pytest tests/test_currency.py -q
```

- [ ] **Step 10.5: Самостоятельный скрипт `scripts/refresh_rates.py`**

По правилам CLAUDE.md — не импортит backend.

```python
"""Обновляет курсы USD/VND в локальной БД из open.er-api.com.

Запуск:
    uv run --env-file .env python scripts/refresh_rates.py

Cron:
    0 6 * * * cd /opt/fil-crm && uv run --env-file .env python scripts/refresh_rates.py
"""
import datetime as dt
import os
import sqlite3
from pathlib import Path

import httpx

DB = Path(os.environ.get("FIL_DB_PATH") or (Path(__file__).resolve().parent.parent / "db.sqlite3"))
URL = "https://open.er-api.com/v6/latest/RUB"
CODES = ("USD", "VND")


def main():
    r = httpx.get(URL, timeout=10.0)
    r.raise_for_status()
    rates = (r.json() or {}).get("rates") or {}
    today = dt.date.today().isoformat()
    conn = sqlite3.connect(str(DB))
    try:
        for code in CODES:
            v = rates.get(code)
            if v is None:
                continue
            conn.execute(
                "INSERT OR REPLACE INTO currency_rates(date, code, rate_to_rub) VALUES (?, ?, ?)",
                (today, code, float(v)),
            )
        conn.commit()
        print(f"OK: {today} {[(c, rates.get(c)) for c in CODES]}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

В `README.md` (раздел про cron, рядом с `generate_baseline_expenses`) добавить рецепт:

```
# обновление курсов RUB→USD/VND раз в сутки
0 6 * * * cd /opt/fil-crm && uv run --env-file .env python scripts/refresh_rates.py
```

- [ ] **Step 10.6: Frontend — store + format**

`frontend/src/lib/currency.js`:

```js
import { writable, get, derived } from 'svelte/store';
import { api } from '$lib/api.js';

const STORAGE_KEY = 'fil_currency';

function initial() {
    if (typeof localStorage === 'undefined') return 'RUB';
    return localStorage.getItem(STORAGE_KEY) || 'RUB';
}

export const currency = writable(initial());

currency.subscribe((v) => {
    if (typeof localStorage !== 'undefined') localStorage.setItem(STORAGE_KEY, v);
});

export const rates = writable({ usd: null, vnd: null, updated_at: null });

let loaded = false;
export async function ensureRates() {
    if (loaded) return;
    loaded = true;
    try {
        const r = await api.get('/currency/rates');
        rates.set(r);
    } catch (e) {
        // молча fallback в RUB
    }
}

export function fmtMoney(amountRub) {
    if (amountRub == null) return '—';
    const code = get(currency);
    const r = get(rates);
    if (code === 'USD' && r.usd) {
        return '$' + (amountRub * r.usd).toFixed(2);
    }
    if (code === 'VND' && r.vnd) {
        return '₫' + Math.round(amountRub * r.vnd).toLocaleString('ru-RU');
    }
    return Math.round(amountRub).toLocaleString('ru-RU') + ' ₽';
}

export function fmtMoneyShort(amountRub) {
    if (amountRub == null) return '—';
    const code = get(currency);
    const r = get(rates);
    if (code === 'USD' && r.usd) {
        const v = amountRub * r.usd;
        return '$' + (v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v.toFixed(0));
    }
    if (code === 'VND' && r.vnd) {
        const v = amountRub * r.vnd;
        return '₫' + (v >= 1_000_000 ? (v / 1_000_000).toFixed(1) + 'M' : Math.round(v / 1000) + 'k');
    }
    if (amountRub >= 1_000_000) return (amountRub / 1_000_000).toFixed(1) + 'M ₽';
    if (amountRub >= 1000) return Math.round(amountRub / 1000) + 'k ₽';
    return Math.round(amountRub) + ' ₽';
}
```

В `frontend/src/lib/format.js` существующие `fmtRub` и `fmtShortRub` — переписать как обёртки:

```js
import { fmtMoney, fmtMoneyShort } from '$lib/currency.js';

export function fmtRub(v) { return fmtMoney(v); }
export function fmtShortRub(v) { return fmtMoneyShort(v); }
```

(Прочие функции — `fmtDate`, `fmtNights` и т.д. — не трогать.)

ВАЖНО: `fmtMoney`/`fmtMoneyShort` используют `get(store)` — это снимок. Чтобы все KPI/секции автоматически переотрисовывались при смене валюты, нужно обернуть форматтеры в derived-стор или использовать `$derived` в местах вывода. Проще всего:

В `frontend/src/lib/format.js` экспортировать derived-стор:

```js
import { derived } from 'svelte/store';
import { currency, rates } from '$lib/currency.js';

export const moneyFmt = derived([currency, rates], () => ({
    full: (v) => fmtMoney(v),
    short: (v) => fmtMoneyShort(v),
}));
```

И в шаблонах заменить `{fmtRub(v)}` на `{$moneyFmt.full(v)}` (где `import { moneyFmt } from '$lib/format.js'`).

Если этот рефактор слишком объёмный — оставить `fmtRub`/`fmtShortRub` как есть и добавить ручное обновление через перезагрузку страницы при смене валюты (acceptable trade-off; зафиксировать в спеке как «для немедленного отображения в KPI после смены валюты — F5»). Принять решение по факту: если использований < 30 — переходим на `$moneyFmt`, если больше — оставляем перезагрузку.

- [ ] **Step 10.7: Свитч в `+layout.svelte`**

`frontend/src/routes/+layout.svelte`:

```svelte
<script>
    import { onMount } from 'svelte';
    import { currency, ensureRates } from '$lib/currency.js';
    let cur = $state('RUB');
    currency.subscribe(v => cur = v);
    onMount(() => { ensureRates(); });
    const SYM = { RUB: '₽', USD: '$', VND: '₫' };
    function setCur(v) { currency.set(v); /* SPA-обновление; если используется F5-fallback — location.reload(); */ }
</script>

<!-- ... существующая разметка layout ... -->
<div class="cur-switch">
    <select value={cur} onchange={(e) => setCur(e.target.value)}>
        <option value="RUB">₽ RUB</option>
        <option value="USD">$ USD</option>
        <option value="VND">₫ VND</option>
    </select>
</div>

<style>
    .cur-switch { position: fixed; top: 8px; right: 8px; z-index: 100; }
    .cur-switch select {
        background: rgba(255,255,255,0.9);
        border: 1px solid var(--border);
        border-radius: 6px;
        padding: 4px 6px;
        font-size: 12px;
        cursor: pointer;
    }
</style>
```

(Точное место вставки переключателя в layout — на усмотрение исполнителя; может быть в шапке, если она существует. Главное — виден на всех страницах.)

Если выбрали путь «derived `$moneyFmt`» — переключение реактивное. Если «fallback с reload» — добавить `location.reload()` в `setCur`.

- [ ] **Step 10.8: Ручная проверка**

- Открыть `/finance` или `/reports` — все суммы в `₽`.
- Сменить свитч на USD → суммы пересчитались в `$xx.xx`. На VND → `₫xxx,xxx`.
- F5 → выбранная валюта сохранилась.

- [ ] **Step 10.9: Commit**

```bash
git add backend/currency.py backend/routes/currency.py backend/main.py scripts/refresh_rates.py README.md tests/test_currency.py frontend/src/lib/currency.js frontend/src/lib/format.js frontend/src/routes/+layout.svelte
git commit -m "feat: мульти-валюта RUB/USD/VND — store, /currency/rates, скрипт обновления"
```

---

## Task 11: Прод — nginx-конфиг + пример

**Files:**
- Create: `docs/nginx-sakha-gay.conf`

- [ ] **Step 11.1: Положить пример конфига**

`docs/nginx-sakha-gay.conf`:

```
server {
    listen 80;
    server_name sakha.gay;

    location /media/ {
        alias /opt/fil-crm/backend/media/;
        expires 7d;
        access_log off;
        try_files $uri =404;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

В `README.md` коротким абзацем сослаться на этот файл («для прод-деплоя — `docs/nginx-sakha-gay.conf`, маппит `/media/` на локальную FS»).

- [ ] **Step 11.2: Commit**

```bash
git add docs/nginx-sakha-gay.conf README.md
git commit -m "docs: пример nginx-конфига для sakha.gay (медиа + бэк)"
```

---

## Финальная проверка

- [ ] **Step F.1: Полный прогон тестов**

```bash
uv run pytest -q
```

Все зелёные. Если есть жёлтые предупреждения от стороннего кода — игнорировать.

- [ ] **Step F.2: Ручной smoke по фичам**

Чек-лист в браузере:

1. `/apartments/<id>` — поля одинаковые (нет primary-пунктира), ⓘ рядом с ADR работает, обложка грузится через CoverPicker.
2. `/apartments/<id>` — можно сохранить квартиру с пустым ЖКХ, но не с пустой арендой.
3. `/apartments/new` — табы «По ссылке»/«Вручную» переключаются.
4. `/users` — owner видит «+», создаёт юзера. Admin не видит.
5. `/bookings/new` — combobox с поиском работает, занятость подсвечивается.
6. Свитч валют в шапке — суммы переключаются.
7. `/reports` — ⓘ у ADR и RevPAR.

- [ ] **Step F.3: Финальный коммит-метка**

Если по ходу что-то осталось без коммита, сделать общий «chore: финал polish-and-onboarding» — иначе шаг пропустить.

---

## Самопроверка (внутри плана)

- **Спека покрыта:** Task 1 → EditableField (спек §«Единый стиль»). Task 2 → ЖКХ (спек §«ЖКХ → опциональный»). Task 3 → glossary/HelpTip (спек §«Тултипы»). Task 4 + Task 6 → cover upload (back+front, спек §«Загрузка обложки» и §«Cover-загрузчик»). Task 5 → парсер локализует cover (спек §«Парсер: локализация cover»). Task 7 → создание юзеров (спек §«Создание юзеров»). Task 8 → табы (спек §«Табы на /apartments/new»). Task 9 → search + ApartmentPicker (спек §«Поиск квартир для брони» и §«Combobox»). Task 10 → валюты (спек §«Курсы валют» и §«Глобальный валютный свитч»). Task 11 → nginx (спек §«Данные / миграции», nginx-конфиг). Task 0 — инфра, в спеке отдельно не выделена, но обеспечивает миграции/deps/media-mount.
- **Открытое из спеки:** «точные тексты глоссария» — реализованы базовые формулировки в Step 3.1, расширяемо. «Ввод сумм всегда в RUB» — UI ввода (`EditableField` числовой) не трогаем; конвертация только в `fmtMoney`/`fmtMoneyShort`.
- **Типы и имена:** `_media_root` используется и в Task 4, и в Task 5 — определена один раз. `next_booked_from` фигурирует в Task 9 (back) и в `ApartmentPicker` (front) — одинаково. `cover_url` — имя поля в БД и в API ответах согласовано.
