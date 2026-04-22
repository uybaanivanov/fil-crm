# MoreLogin-парсер объявлений + URL-only добавление квартиры — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Автоматизировать создание квартиры из ссылки doska.ykt.ru/youla.ru через парсер в MoreLogin-профиле; убрать ручную форму; запретить админу создавать квартиры.

**Architecture:** Синхронный эндпоинт `POST /apartments/parse-url` (owner-only) резолвит редирект, стартует MoreLogin-профиль (id=1) через локальный API, коннектится к Chromium через CDP (Playwright), грузит страницу, отдаёт HTML в парсер конкретного источника, возвращает структурированный `ParsedListing` фронту. Фронт `/apartments/new` — единственный URL-инпут → превью → сохранение.

**Tech Stack:** Python 3.13, FastAPI, httpx, Playwright (chromium), SvelteKit 5 (runes), sqlite raw SQL, pytest.

Спек: `docs/superpowers/specs/2026-04-22-morelogin-parser-design.md`.

---

## Структура файлов

**Создаются:**
- `backend/morelogin.py` — клиент MoreLogin API (httpx-based, async)
- `backend/parsers/__init__.py` — фасад `parse(url) -> ParsedListing`
- `backend/parsers/types.py` — `ParsedListing` dataclass
- `backend/parsers/doska_ykt.py` — парсер doska.ykt.ru
- `backend/parsers/youla.py` — парсер youla.ru
- `backend/migrations/003_apartment_source.sql`
- `tests/fixtures/doska_ykt_sample.html` — снимок одной страницы
- `tests/fixtures/youla_sample.html` — снимок одной страницы
- `tests/test_parser_doska.py`
- `tests/test_parser_youla.py`
- `tests/test_parsers_router.py` — резолв редиректа + выбор парсера
- `tests/e2e_morelogin_open.py` — интерактивный smoke MoreLogin-клиента
- `tests/e2e_capture_html.py` — интерактивный скрипт, сохраняет HTML страницы в `tests/fixtures/`
- `tests/e2e_parse_url.py` — интерактивный полный пайплайн

**Изменяются:**
- `backend/routes/apartments.py` — новый эндпоинт, ограничение прав на create, source/source_url в модели
- `backend/main.py` — ничего (роут уже включён через apartments_routes)
- `pyproject.toml` — добавить зависимости `httpx` (prod), `playwright`, `beautifulsoup4`
- `tests/test_authz.py` — кейсы для apartment create
- `tests/test_apartments.py` — тесты новых полей + 409 на дубль source_url
- `frontend/src/routes/apartments/+page.svelte` — скрыть AddBtn у admin
- `frontend/src/routes/apartments/new/+page.svelte` — полная переделка

**Удаляются в конце:**
- `tests/e2e_listing_urls.txt` — после успешного прогона 14 ссылок через новый UX
- `scripts/fetch_links.py` — разовый скрипт, больше не нужен

---

## Task 1: Клиент MoreLogin

**Files:**
- Create: `backend/morelogin.py`
- Modify: `pyproject.toml` — добавить playwright, beautifulsoup4 (httpx уже добавлен)
- Modify: `.env` — добавить `MORELOGIN_API_URL`, `MORELOGIN_ENV_ID`

Контракт API подтверждён curl-прощупыванием:
- `POST /api/env/start {"envId": "<19-digit>"}` → `{"code":0,"data":{"envId":"...","debugPort":"61384","type":"chrome","version":144,"webdriver":"..."}}`
- `POST /api/env/close {"envId":"..."}` → `{"code":0,"data":{"envId":"...","debugPort":""}}`
- CDP подключение: `http://127.0.0.1:<debugPort>` — там DevTools endpoint, Playwright принимает такой URL в `connect_over_cdp`.
- Success criterion: `code == 0`.

**Важно**: `MORELOGIN_ENV_ID` — это не визуальный «P-1», а 19-значный `id` из `/api/env/page`. Получить можно `curl -X POST http://127.0.0.1:40000/api/env/page -H "Content-Type: application/json" -d '{"pageNo":1,"pageSize":20}'` и взять `data.dataList[0].id`. У разработчика это уже лежит в `.env`.

- [ ] **Step 1: Добавить зависимости**

Modify `pyproject.toml`:
```toml
dependencies = [
    "fastapi>=0.136.0",
    "uvicorn>=0.30.0",
    "httpx>=0.27.0",
    "playwright>=1.49.0",
    "beautifulsoup4>=4.12.0",
]
```

```bash
uv sync
uv run playwright install chromium
```

- [ ] **Step 2: Написать клиент `backend/morelogin.py`**

```python
"""Клиент локального MoreLogin API (http://127.0.0.1:40000).

Дока: https://guide.morelogin.com/api-reference/local-api/local-api
Контракт ответа: {"code": 0, "msg": null, "data": {...}, "requestId": "..."}.
Ошибка — любой code != 0 или HTTP != 200.
"""
import os
from dataclasses import dataclass

import httpx

API_URL = os.environ.get("MORELOGIN_API_URL", "http://127.0.0.1:40000")
ENV_ID = os.environ.get("MORELOGIN_ENV_ID", "")
TIMEOUT = httpx.Timeout(60.0)


class MoreLoginError(RuntimeError):
    pass


@dataclass
class ProfileSession:
    env_id: str
    debug_port: int
    cdp_url: str  # http://127.0.0.1:<debug_port>


def _unwrap(r: httpx.Response) -> dict:
    if r.status_code != 200:
        raise MoreLoginError(f"http {r.status_code}: {r.text}")
    body = r.json()
    if body.get("code") != 0:
        raise MoreLoginError(f"api error: {body}")
    return body.get("data") or {}


async def start_profile(env_id: str | None = None) -> ProfileSession:
    eid = env_id or ENV_ID
    if not eid:
        raise MoreLoginError("MORELOGIN_ENV_ID не задан")
    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as c:
        data = _unwrap(await c.post("/api/env/start", json={"envId": eid}))
    port = int(data["debugPort"])
    return ProfileSession(env_id=eid, debug_port=port, cdp_url=f"http://127.0.0.1:{port}")


async def stop_profile(env_id: str | None = None) -> None:
    eid = env_id or ENV_ID
    if not eid:
        raise MoreLoginError("MORELOGIN_ENV_ID не задан")
    async with httpx.AsyncClient(base_url=API_URL, timeout=TIMEOUT) as c:
        _unwrap(await c.post("/api/env/close", json={"envId": eid}))
```

- [ ] **Step 3: Commit**

```bash
git add backend/morelogin.py pyproject.toml uv.lock .env
git commit -m "feat(morelogin): клиент локального API"
```

Примечание: `.env` коммитить нормально т.к. у нас прототип и там нет секретов (telethon — свои API id/hash, они ниже секретные, но файл и так в репе).

---

## Task 2: E2E smoke MoreLogin

**Files:**
- Create: `tests/e2e_morelogin_open.py`

- [ ] **Step 1: Написать интерактивный smoke**

```python
"""Smoke MoreLogin: запусти, увидишь окно MoreLogin-профиля, Enter — закроется."""
import asyncio
import os

from backend.morelogin import PROFILE_ID, start_profile, stop_profile


async def main():
    pid = int(os.environ.get("MORELOGIN_PROFILE_ID", PROFILE_ID))
    input(f"Стартовать профиль {pid}? [Enter]")
    session = await start_profile(pid)
    print(f"CDP URL: {session.cdp_url}")
    input("Профиль открыт. Enter для закрытия...")
    await stop_profile(pid)
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Проверить вручную**

```bash
uv run --env-file .env python tests/e2e_morelogin_open.py
```
Ожидается: в MoreLogin открылся профиль 1, CDP URL распечатан, после Enter профиль закрылся. Если нет — вернуться в Task 1, поправить эндпоинты.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e_morelogin_open.py
git commit -m "feat(tests): e2e_morelogin_open — smoke старт/стоп профиля"
```

---

## Task 3: Миграция схемы apartments

**Files:**
- Create: `backend/migrations/003_apartment_source.sql`
- Modify: `backend/routes/apartments.py`
- Modify: `tests/test_apartments.py`

- [ ] **Step 1: Написать падающий тест на дубль source_url**

Append в `tests/test_apartments.py`:
```python
def test_apartment_source_url_unique(client):
    u = seed_user(client, role="owner", name="Айсен")
    h = auth(u["id"])
    payload = {
        "title": "Т1", "address": "А1", "price_per_night": 1000,
        "source": "doska_ykt",
        "source_url": "https://doska.ykt.ru/12345",
    }
    r1 = client.post("/apartments", json=payload, headers=h)
    assert r1.status_code == 201
    assert r1.json()["source"] == "doska_ykt"
    assert r1.json()["source_url"] == "https://doska.ykt.ru/12345"
    r2 = client.post("/apartments", json=payload, headers=h)
    assert r2.status_code == 409


def test_apartment_without_source_url_ok(client):
    u = seed_user(client, role="owner", name="Айсен")
    h = auth(u["id"])
    # два без source_url не должны конфликтовать
    r1 = client.post("/apartments", json={"title": "X", "address": "Y", "price_per_night": 100}, headers=h)
    r2 = client.post("/apartments", json={"title": "X2", "address": "Y2", "price_per_night": 200}, headers=h)
    assert r1.status_code == 201 and r2.status_code == 201
```

- [ ] **Step 2: Запустить — должны упасть**

```bash
uv run pytest tests/test_apartments.py::test_apartment_source_url_unique tests/test_apartments.py::test_apartment_without_source_url_ok -v
```
Ожидается: FAIL (нет колонок source/source_url).

- [ ] **Step 3: Написать миграцию**

`backend/migrations/003_apartment_source.sql`:
```sql
ALTER TABLE apartments ADD COLUMN source TEXT;
ALTER TABLE apartments ADD COLUMN source_url TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS apartments_source_url_uniq
    ON apartments(source_url) WHERE source_url IS NOT NULL;
```

- [ ] **Step 4: Обновить `ApartmentIn`, `ApartmentPatch`, `SELECT_FIELDS`, `create_apartment`**

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
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None


class ApartmentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    price_per_night: int | None = Field(default=None, gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None


SELECT_FIELDS = (
    "id, title, address, price_per_night, needs_cleaning, "
    "cover_url, rooms, area_m2, floor, district, source, source_url, created_at"
)
```

В `create_apartment` обернуть вставку в try/except IntegrityError:
```python
@router.post("", status_code=status.HTTP_201_CREATED)
def create_apartment(
    payload: ApartmentIn, _: dict = Depends(require_role("owner", "admin"))
):
    import sqlite3

    fields = payload.model_dump()
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO apartments ({cols}) VALUES ({placeholders})",
                list(fields.values()),
            )
            row = _row(conn, cur.lastrowid)
    except sqlite3.IntegrityError as e:
        if "apartments_source_url_uniq" in str(e):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Квартира с такой ссылкой уже есть")
        raise
    return dict(row)
```

- [ ] **Step 5: Запустить тесты**

```bash
uv run pytest tests/test_apartments.py -v
```
Ожидается: все тесты зелёные.

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/003_apartment_source.sql backend/routes/apartments.py tests/test_apartments.py
git commit -m "feat(apartments): source/source_url + 409 на дубль"
```

---

## Task 4: ParsedListing + парсеры-фасад + резолв редиректа

**Files:**
- Create: `backend/parsers/types.py`
- Create: `backend/parsers/__init__.py`
- Create: `tests/test_parsers_router.py`

- [ ] **Step 1: Написать падающий тест роутера**

`tests/test_parsers_router.py`:
```python
from backend.parsers import resolve_source, UnsupportedSource
import pytest


def test_resolve_source_doska():
    assert resolve_source("https://doska.ykt.ru/15838371") == "doska_ykt"


def test_resolve_source_youla():
    assert resolve_source("https://youla.ru/yakutsk/nedvizhimost/123") == "youla"


def test_resolve_source_unknown_raises():
    with pytest.raises(UnsupportedSource):
        resolve_source("https://example.com/listing/1")
```

- [ ] **Step 2: Запустить — FAIL**

```bash
uv run pytest tests/test_parsers_router.py -v
```

- [ ] **Step 3: Написать `backend/parsers/types.py`**

```python
from dataclasses import asdict, dataclass


@dataclass
class ParsedListing:
    source: str
    source_url: str
    title: str | None = None
    address: str | None = None
    price_per_night: int | None = None
    rooms: str | None = None
    area_m2: int | None = None
    floor: str | None = None
    district: str | None = None
    cover_url: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
```

- [ ] **Step 4: Написать `backend/parsers/__init__.py`**

```python
from urllib.parse import urlparse

import httpx

from backend.parsers.types import ParsedListing


class UnsupportedSource(ValueError):
    pass


class ParseError(ValueError):
    pass


_SOURCE_BY_HOST = {
    "doska.ykt.ru": "doska_ykt",
    "www.doska.ykt.ru": "doska_ykt",
    "youla.ru": "youla",
    "www.youla.ru": "youla",
}


def resolve_source(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host in _SOURCE_BY_HOST:
        return _SOURCE_BY_HOST[host]
    raise UnsupportedSource(f"unsupported host: {host}")


def resolve_final_url(url: str) -> str:
    """HEAD с follow_redirects — отдаёт финальный URL (для trk.mail.ru → youla.ru)."""
    with httpx.Client(follow_redirects=True, timeout=15.0) as c:
        r = c.head(url)
        return str(r.url)


def parse_html(html: str, final_url: str) -> ParsedListing:
    source = resolve_source(final_url)
    if source == "doska_ykt":
        from backend.parsers.doska_ykt import parse_html as impl
    elif source == "youla":
        from backend.parsers.youla import parse_html as impl
    else:
        raise UnsupportedSource(source)
    return impl(html, final_url)
```

- [ ] **Step 5: Запустить тесты**

```bash
uv run pytest tests/test_parsers_router.py -v
```
Ожидается: все зелёные.

- [ ] **Step 6: Commit**

```bash
git add backend/parsers/ tests/test_parsers_router.py
git commit -m "feat(parsers): ParsedListing + резолв источника по хосту"
```

---

## Task 5: Захват HTML-фикстур (интерактивный)

**Files:**
- Create: `tests/e2e_capture_html.py`
- Create: `tests/fixtures/doska_ykt_sample.html` (результат прогона)
- Create: `tests/fixtures/youla_sample.html` (результат прогона)

- [ ] **Step 1: Написать интерактивный скрипт захвата**

```python
"""Захват HTML страницы через MoreLogin+Playwright для парсер-фикстур.
Запускать интерактивно, по одной ссылке за раз.
Самодостаточный — никаких импортов из backend/, только httpx + playwright.
"""
import asyncio
import os
import sys
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

API_URL = os.environ.get("MORELOGIN_API_URL", "http://127.0.0.1:40000")
FIXTURES = Path(__file__).parent / "fixtures"


def call(path: str, payload: dict) -> dict:
    r = httpx.post(f"{API_URL}{path}", json=payload, timeout=60.0)
    r.raise_for_status()
    body = r.json()
    if body.get("code") != 0:
        raise SystemExit(f"{path} → api error: {body}")
    return body.get("data") or {}


async def main():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    eid = os.environ.get("MORELOGIN_ENV_ID") or input("envId: ").strip()
    url = input("URL: ").strip()
    name = input("имя фикстуры (без .html), например doska_ykt_sample: ").strip()
    out = FIXTURES / f"{name}.html"

    data = call("/api/env/start", {"envId": eid})
    port = data.get("debugPort")
    if not port:
        sys.exit(f"debugPort пустой: {data}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=60000)
            html = await page.content()
            out.write_text(html, encoding="utf-8")
            print(f"saved {len(html)} bytes -> {out}")
            await page.close()
    finally:
        call("/api/env/close", {"envId": eid})


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Прогнать на одной doska-ссылке**

```bash
uv run --env-file .env python tests/e2e_capture_html.py
# URL: https://doska.ykt.ru/15838371
# имя: doska_ykt_sample
```

- [ ] **Step 3: Прогнать на одной youla-ссылке (из trk.mail.ru резолвится)**

Сначала резолвим редирект вручную:
```bash
uv run python -c "import httpx; r = httpx.head('https://trk.mail.ru/c/phjpd1?id=69b96c08f2c5078bbf081ad4', follow_redirects=True); print(r.url)"
```
Затем прогнать `e2e_capture_html.py` с финальным youla-URL, имя `youla_sample`.

- [ ] **Step 4: Зафиксировать фикстуры**

Если HTML огромный (>500КБ), ок — фикстур-файлы не часть API. Инженер имеет право вручную укоротить `<script>`-блоки если они мешают.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e_capture_html.py tests/fixtures/doska_ykt_sample.html tests/fixtures/youla_sample.html
git commit -m "chore(tests): скрипт захвата HTML + первичные фикстуры"
```

---

## Task 6: Парсер doska.ykt.ru

**Files:**
- Create: `backend/parsers/doska_ykt.py`
- Create: `tests/test_parser_doska.py`

- [ ] **Step 1: Написать падающий тест**

Сначала инженер смотрит `tests/fixtures/doska_ykt_sample.html` руками и выписывает эталонные значения title/address/price/rooms/area/floor/district/cover_url для конкретного объявления.

`tests/test_parser_doska.py`:
```python
from pathlib import Path

from backend.parsers.doska_ykt import parse_html

FIX = Path(__file__).parent / "fixtures" / "doska_ykt_sample.html"


def test_parse_doska_sample():
    html = FIX.read_text(encoding="utf-8")
    url = "https://doska.ykt.ru/15838371"
    r = parse_html(html, url)
    assert r.source == "doska_ykt"
    assert r.source_url == url
    assert r.title  # непустой
    assert r.address
    assert r.price_per_night and r.price_per_night > 0
    # Остальные поля могут быть None — проверяем только что они корректно типизированы
    assert r.area_m2 is None or isinstance(r.area_m2, int)
    assert r.cover_url is None or r.cover_url.startswith("http")
```

(Если у инженера есть точные значения из HTML, заменить `непустой`-проверки на `== "Ожидаемый заголовок"`.)

- [ ] **Step 2: Запустить — FAIL**

```bash
uv run pytest tests/test_parser_doska.py -v
```

- [ ] **Step 3: Написать парсер**

`backend/parsers/doska_ykt.py`:
```python
"""Парсер doska.ykt.ru. Селекторы подобраны по HTML-фикстуре; при изменении
сайта упадут юнит-тесты и потребуется обновление.
"""
import re

from bs4 import BeautifulSoup

from backend.parsers.types import ParsedListing


_PRICE_RE = re.compile(r"([\d\s]+)\s*₽")
_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*м²")


def _clean_int(s: str | None) -> int | None:
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    return int(digits) if digits else None


def _text(el) -> str | None:
    return el.get_text(strip=True) if el else None


def parse_html(html: str, url: str) -> ParsedListing:
    soup = BeautifulSoup(html, "html.parser")

    # Инженер: адаптировать селекторы под текущий HTML doska.ykt.ru.
    # Ниже — стартовый вариант по распространённым классам/атрибутам;
    # если класс изменился — правь по фикстуре.
    title = _text(soup.select_one("h1"))
    address = _text(soup.select_one("[class*=address]")) or _text(soup.select_one("[itemprop=address]"))

    price = None
    price_el = soup.select_one("[class*=price]")
    if price_el:
        m = _PRICE_RE.search(price_el.get_text(" ", strip=True))
        if m:
            price = _clean_int(m.group(1))

    area = None
    body_text = soup.get_text(" ", strip=True)
    m = _AREA_RE.search(body_text)
    if m:
        area = int(float(m.group(1).replace(",", ".")))

    rooms = None
    rooms_match = re.search(r"(студия|\d+-комн)", body_text, re.IGNORECASE)
    if rooms_match:
        rooms = rooms_match.group(1).capitalize()

    floor = None
    floor_match = re.search(r"этаж[:\s]*(\d+/\d+|\d+)", body_text, re.IGNORECASE)
    if floor_match:
        floor = floor_match.group(1)

    district = None
    # doska.ykt.ru часто кладёт район в breadcrumbs или в блоке «характеристики»
    for el in soup.select("[class*=district], [class*=region]"):
        if _text(el):
            district = _text(el)
            break

    cover_url = None
    og = soup.select_one("meta[property='og:image']")
    if og and og.get("content"):
        cover_url = og["content"]

    return ParsedListing(
        source="doska_ykt",
        source_url=url,
        title=title,
        address=address,
        price_per_night=price,
        rooms=rooms,
        area_m2=area,
        floor=floor,
        district=district,
        cover_url=cover_url,
    )
```

- [ ] **Step 4: Запустить тест, подкрутить селекторы пока не зелёный**

```bash
uv run pytest tests/test_parser_doska.py -v
```

Если `title/address/price` — None, вскрыть фикстуру, найти реальные теги, поправить селекторы, повторить.

- [ ] **Step 5: Commit**

```bash
git add backend/parsers/doska_ykt.py tests/test_parser_doska.py
git commit -m "feat(parsers): doska.ykt.ru"
```

---

## Task 7: Парсер youla.ru

**Files:**
- Create: `backend/parsers/youla.py`
- Create: `tests/test_parser_youla.py`

- [ ] **Step 1: Написать падающий тест**

`tests/test_parser_youla.py` — зеркало `test_parser_doska.py` с youla-фикстурой и URL:
```python
from pathlib import Path

from backend.parsers.youla import parse_html

FIX = Path(__file__).parent / "fixtures" / "youla_sample.html"


def test_parse_youla_sample():
    html = FIX.read_text(encoding="utf-8")
    url = "https://youla.ru/yakutsk/nedvizhimost/arenda-kvartir/some-id"
    r = parse_html(html, url)
    assert r.source == "youla"
    assert r.source_url == url
    assert r.title
    assert r.address
    assert r.price_per_night and r.price_per_night > 0
```

- [ ] **Step 2: Запустить — FAIL**

- [ ] **Step 3: Написать парсер**

`backend/parsers/youla.py` — структура как у `doska_ykt.py`, но селекторы под youla. Опора — JSON-LD (youla часто отдаёт schema.org `Product`/`Offer`):

```python
import json
import re

from bs4 import BeautifulSoup

from backend.parsers.types import ParsedListing

_AREA_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*м²")


def _json_ld(soup: BeautifulSoup) -> list[dict]:
    out = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        if isinstance(data, list):
            out.extend(d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            out.append(data)
    return out


def parse_html(html: str, url: str) -> ParsedListing:
    soup = BeautifulSoup(html, "html.parser")
    title = address = cover_url = None
    price = None

    for d in _json_ld(soup):
        if d.get("@type") in ("Product", "Offer"):
            title = title or d.get("name")
            offers = d.get("offers") or {}
            if isinstance(offers, dict) and offers.get("price"):
                try:
                    price = int(float(offers["price"]))
                except ValueError:
                    pass
            img = d.get("image")
            if isinstance(img, list):
                cover_url = cover_url or (img[0] if img else None)
            elif isinstance(img, str):
                cover_url = cover_url or img

    if not title:
        h1 = soup.select_one("h1")
        title = h1.get_text(strip=True) if h1 else None

    # адрес — частый паттерн: блок с data-testid="address" или itemprop=address
    for sel in ["[data-testid=address]", "[itemprop=address]", "[class*=address]"]:
        el = soup.select_one(sel)
        if el:
            address = el.get_text(strip=True)
            break

    body = soup.get_text(" ", strip=True)
    area = None
    m = _AREA_RE.search(body)
    if m:
        area = int(float(m.group(1).replace(",", ".")))

    rooms = None
    rm = re.search(r"(студия|\d+-комн)", body, re.IGNORECASE)
    if rm:
        rooms = rm.group(1).capitalize()

    floor = None
    fm = re.search(r"этаж[:\s]*(\d+/\d+|\d+)", body, re.IGNORECASE)
    if fm:
        floor = fm.group(1)

    if not cover_url:
        og = soup.select_one("meta[property='og:image']")
        if og and og.get("content"):
            cover_url = og["content"]

    return ParsedListing(
        source="youla",
        source_url=url,
        title=title,
        address=address,
        price_per_night=price,
        rooms=rooms,
        area_m2=area,
        floor=floor,
        district=None,
        cover_url=cover_url,
    )
```

- [ ] **Step 4: Запустить тест, подкрутить пока не зелёный**

```bash
uv run pytest tests/test_parser_youla.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/parsers/youla.py tests/test_parser_youla.py
git commit -m "feat(parsers): youla.ru"
```

---

## Task 8: Эндпоинт `POST /apartments/parse-url` + authz

**Files:**
- Modify: `backend/routes/apartments.py`
- Modify: `tests/test_authz.py`
- Create: test внутри `tests/test_apartments.py` (mocked parser)

- [ ] **Step 1: Написать падающий тест authz**

Append в `tests/test_authz.py`:
```python
def test_admin_cannot_parse_url(client):
    u = seed_user(client, role="admin", name="Дарья")
    r = client.post("/apartments/parse-url", json={"url": "https://doska.ykt.ru/1"}, headers=auth(u["id"]))
    assert r.status_code == 403


def test_admin_cannot_create_apartment(client):
    u = seed_user(client, role="admin", name="Дарья")
    payload = {"title": "T", "address": "A", "price_per_night": 100}
    r = client.post("/apartments", json=payload, headers=auth(u["id"]))
    assert r.status_code == 403


def test_owner_can_create_apartment(client):
    u = seed_user(client, role="owner", name="Айсен")
    payload = {"title": "T", "address": "A", "price_per_night": 100}
    r = client.post("/apartments", json=payload, headers=auth(u["id"]))
    assert r.status_code == 201
```

Плюс в `tests/test_apartments.py` — тест парсинга с мок-парсером:
```python
def test_parse_url_returns_listing(client, monkeypatch):
    from backend.parsers.types import ParsedListing
    import backend.routes.apartments as apts_mod

    async def fake_fetch(url):
        return ParsedListing(
            source="doska_ykt", source_url=url,
            title="Flat", address="Addr", price_per_night=3000,
        )
    monkeypatch.setattr(apts_mod, "_fetch_and_parse", fake_fetch)

    u = seed_user(client, role="owner", name="Айсен")
    r = client.post(
        "/apartments/parse-url",
        json={"url": "https://doska.ykt.ru/1"},
        headers=auth(u["id"]),
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Flat" and data["source"] == "doska_ykt"


def test_parse_url_unsupported_is_422(client):
    u = seed_user(client, role="owner", name="Айсен")
    r = client.post(
        "/apartments/parse-url",
        json={"url": "https://example.com/1"},
        headers=auth(u["id"]),
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Запустить — FAIL**

```bash
uv run pytest tests/test_authz.py tests/test_apartments.py -v
```

- [ ] **Step 3: Изменить права на create + добавить эндпоинт**

В `backend/routes/apartments.py`:

Поменять `create_apartment`:
```python
@router.post("", status_code=status.HTTP_201_CREATED)
def create_apartment(
    payload: ApartmentIn, _: dict = Depends(require_role("owner"))
):
    # ... тело как раньше
```

Добавить эндпоинт и helper:
```python
class ParseUrlIn(BaseModel):
    url: str = Field(min_length=1)


async def _fetch_and_parse(url: str):
    """Резолв редиректа, старт MoreLogin, Playwright CDP, парсер. Вынесено
    чтобы тесты могли подменить через monkeypatch."""
    from playwright.async_api import async_playwright

    from backend import morelogin
    from backend.parsers import parse_html, resolve_final_url, resolve_source

    final_url = resolve_final_url(url)
    resolve_source(final_url)  # рейзит UnsupportedSource → 422 снаружи

    session = await morelogin.start_profile()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(session.cdp_url)
            ctx = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await ctx.new_page()
            await page.goto(final_url, wait_until="networkidle", timeout=60000)
            html = await page.content()
            await page.close()
        return parse_html(html, final_url)
    finally:
        await morelogin.stop_profile()


@router.post("/parse-url")
async def parse_url(
    payload: ParseUrlIn, _: dict = Depends(require_role("owner"))
):
    from backend.parsers import ParseError, UnsupportedSource

    try:
        listing = await _fetch_and_parse(payload.url)
    except UnsupportedSource as e:
        raise HTTPException(status_code=422, detail=f"unsupported_source: {e}")
    except ParseError as e:
        raise HTTPException(status_code=422, detail=f"parse_failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"fetch_failed: {e}")
    return listing.to_dict()
```

Важно: `parse-url` — GET-роут нет; эндпоинт зарегистрирован ПОСЛЕ `POST ""` (они не конфликтуют). Но `parse-url` как path — должен быть ДО `@router.get("/{apt_id}")` если бы был GET; у нас POST — ок, path-конфликт не страшит.

- [ ] **Step 4: Запустить тесты**

```bash
uv run pytest tests/test_authz.py tests/test_apartments.py -v
```

- [ ] **Step 5: Полный прогон тестов**

```bash
uv run pytest -v
```
Проверить, что не сломали existing authz (admin всё ещё видит list, может делать mark-dirty и т.д.).

- [ ] **Step 6: Commit**

```bash
git add backend/routes/apartments.py tests/test_authz.py tests/test_apartments.py
git commit -m "feat(apartments): POST /parse-url (owner) + create теперь только owner"
```

---

## Task 9: Интерактивный e2e полного пайплайна

**Files:**
- Create: `tests/e2e_parse_url.py`

- [ ] **Step 1: Написать скрипт**

```python
"""Полный пайплайн через HTTP: бэк должен быть запущен (start.sh или uvicorn).
Скрипт — внешний клиент, без импортов из backend/.

Префлайт: seed овнера через dev_auth, затем POST /apartments/parse-url.
"""
import json
import os
import sys

import httpx

BACKEND = os.environ.get("FIL_BACKEND_URL", "http://127.0.0.1:8000")


def seed_owner() -> int:
    """Возвращает X-User-Id овнера. Через dev_auth (DEBUG=1)."""
    r = httpx.post(f"{BACKEND}/dev_auth/seed",
                   json={"full_name": "E2E Owner", "role": "owner"},
                   timeout=10.0)
    r.raise_for_status()
    return r.json()["id"]


def main():
    url = input("URL: ").strip()
    if not url:
        sys.exit("URL пустой")
    uid = seed_owner()
    r = httpx.post(
        f"{BACKEND}/apartments/parse-url",
        json={"url": url},
        headers={"X-User-Id": str(uid)},
        timeout=120.0,
    )
    print(f"HTTP {r.status_code}")
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)


if __name__ == "__main__":
    main()
```

**Замечание:** этот e2e требует реально запущенного бэка (`./start.sh` или `uv run --env-file .env uvicorn backend.main:app --port 8000`) и `DEBUG=1` в env (чтобы dev_auth seed работал). Посмотри `backend/routes/dev_auth.py` и адаптируй путь/поля seed-эндпоинта, если контракт отличается.

- [ ] **Step 2: Прогнать на 3+ ссылках из `tests/e2e_listing_urls.txt`**

```bash
# терминал 1
uv run --env-file .env uvicorn backend.main:app --port 8000
# терминал 2
uv run --env-file .env python tests/e2e_parse_url.py
```

Если парсер для какой-то ссылки даёт всё None — вернуться в Task 6/7 и подкрутить селекторы.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e_parse_url.py
git commit -m "feat(tests): e2e_parse_url — интерактивный полный пайплайн"
```

---

## Task 10: Фронт — скрыть AddBtn админу

**Files:**
- Modify: `frontend/src/routes/apartments/+page.svelte`

- [ ] **Step 1: Добавить проверку роли и условный рендер AddBtn**

В `+page.svelte` (`<script>`-блок):
```javascript
import { getUser } from '$lib/auth.js';
const me = getUser();
const canAdd = me?.role === 'owner';
```

В `PageHead`-сниппете:
```svelte
{#snippet right()}
    {#if canAdd}
        <AddBtn onclick={() => goto('/apartments/new')} />
    {/if}
{/snippet}
```

- [ ] **Step 2: Запустить dev-сервер и проверить визуально**

```bash
cd frontend && npm run dev
```
Зайти под owner — кнопка есть. Под admin (через dev_auth) — кнопки нет.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/apartments/+page.svelte
git commit -m "feat(frontend): скрыть 'Добавить квартиру' для не-овнера"
```

---

## Task 11: Переделка `/apartments/new` под URL-only

**Files:**
- Modify: `frontend/src/routes/apartments/new/+page.svelte` (полная перезапись)

- [ ] **Step 1: Полностью переписать страницу**

```svelte
<script>
    import { goto } from '$app/navigation';
    import { api } from '$lib/api.js';
    import PageHead from '$lib/ui/PageHead.svelte';
    import Card from '$lib/ui/Card.svelte';
    import Section from '$lib/ui/Section.svelte';

    const ROOMS_OPTIONS = ['Студия', '1-комн', '2-комн', '3+'];

    let url = $state('');
    let parsing = $state(false);
    let parseError = $state(null);

    // Поля превью — появляются после парсинга
    let listing = $state(null);  // null = ещё не парсили
    let title = $state('');
    let address = $state('');
    let rooms = $state('');
    let area = $state('');
    let floor = $state('');
    let district = $state('');
    let price = $state('');
    let coverUrl = $state('');
    let source = $state('');
    let sourceUrl = $state('');

    let saving = $state(false);
    let saveError = $state(null);

    async function doParse() {
        parseError = null;
        saveError = null;
        if (!url.trim()) { parseError = 'Вставь ссылку'; return; }
        parsing = true;
        try {
            const r = await api.post('/apartments/parse-url', { url: url.trim() });
            listing = r;
            title = r.title || '';
            address = r.address || '';
            rooms = r.rooms || '';
            area = r.area_m2 ? String(r.area_m2) : '';
            floor = r.floor || '';
            district = r.district || '';
            price = r.price_per_night ? String(r.price_per_night) : '';
            coverUrl = r.cover_url || '';
            source = r.source;
            sourceUrl = r.source_url;
        } catch (e) {
            parseError = e.message;
            listing = null;
        } finally {
            parsing = false;
        }
    }

    async function save() {
        saveError = null;
        const priceNum = parseInt(price, 10);
        if (!title || !address || !priceNum || priceNum <= 0) {
            saveError = 'Заполни название, адрес и цену (>0)';
            return;
        }
        saving = true;
        try {
            const payload = {
                title, address,
                price_per_night: priceNum,
                source, source_url: sourceUrl,
            };
            if (rooms) payload.rooms = rooms;
            if (area) payload.area_m2 = parseInt(area, 10);
            if (floor) payload.floor = floor;
            if (district) payload.district = district;
            if (coverUrl) payload.cover_url = coverUrl;
            const result = await api.post('/apartments', payload);
            goto(`/apartments/${result.id}`);
        } catch (e) {
            saveError = e.message;
        } finally {
            saving = false;
        }
    }
</script>

<PageHead title="Новая квартира" sub="Вставь ссылку — разберём и покажем поля"
    back="Отмена" backOnClick={() => goto('/apartments')} />

<div class="wrap">
    <div class="eyebrow">Ссылка на объявление</div>
    <input class="url-field" bind:value={url}
        placeholder="https://doska.ykt.ru/... или https://youla.ru/..."
        disabled={parsing} />
    <div class="hint">Поддержка: <span class="mono">Доска.якт · Юла</span> (трекер-ссылки mail.ru резолвим).</div>
    <button class="primary wide" type="button" onclick={doParse} disabled={parsing || !url.trim()}>
        {parsing ? 'Разбираю…' : 'Разобрать'}
    </button>
    {#if parseError}<div class="error-banner">{parseError}</div>{/if}
</div>

{#if listing}
    <Section title="Поля квартиры">
        <div class="wrap">
            <Card pad={14}>
                <div class="form">
                    <label>
                        <span>Название*</span>
                        <input bind:value={title} />
                    </label>
                    <label class="full">
                        <span>Адрес*</span>
                        <input bind:value={address} />
                    </label>
                    <label>
                        <span>Тип</span>
                        <select bind:value={rooms}>
                            <option value=""></option>
                            {#each ROOMS_OPTIONS as r}<option value={r}>{r}</option>{/each}
                        </select>
                    </label>
                    <label>
                        <span>Площадь м²</span>
                        <input type="number" bind:value={area} />
                    </label>
                    <label>
                        <span>Этаж</span>
                        <input bind:value={floor} />
                    </label>
                    <label>
                        <span>Район</span>
                        <input bind:value={district} />
                    </label>
                    <label>
                        <span>Цена/ночь ₽*</span>
                        <input type="number" bind:value={price} />
                    </label>
                    <label class="full">
                        <span>URL обложки</span>
                        <input bind:value={coverUrl} />
                    </label>
                </div>
            </Card>
        </div>
    </Section>

    {#if saveError}<div class="error-banner">{saveError}</div>{/if}

    <div class="actions">
        <button class="ghost" type="button" onclick={() => goto('/apartments')} disabled={saving}>Отмена</button>
        <button class="primary" type="button" onclick={save} disabled={saving}>
            {saving ? 'Сохраняю…' : 'Сохранить →'}
        </button>
    </div>
{/if}

<style>
    .wrap { padding: 0 20px 14px; }
    .eyebrow {
        font-family: var(--font-mono); font-size: 10px;
        letter-spacing: 0.1em; text-transform: uppercase;
        color: var(--faint); margin-bottom: 8px;
    }
    .url-field {
        width: 100%; height: 48px;
        border: 1.5px solid var(--accent); background: var(--card);
        border-radius: 8px; padding: 0 14px;
        font-family: var(--font-mono); font-size: 12px; color: var(--ink);
    }
    .url-field:disabled { opacity: 0.6; }
    .hint {
        margin-top: 8px; font-family: var(--font-mono);
        font-size: 10px; color: var(--faint);
    }
    .mono { color: var(--muted); }
    .wide { margin-top: 10px; width: 100%; height: 42px; border-radius: 8px; }
    .form { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
    .form .full { grid-column: 1 / -1; }
    .form label { display: flex; flex-direction: column; gap: 4px; }
    .form label span {
        font-family: var(--font-mono); font-size: 10px;
        letter-spacing: 0.1em; text-transform: uppercase; color: var(--faint);
    }
    .form input, .form select {
        height: 42px; background: var(--bg); border: 1px solid var(--border);
        border-radius: 6px; padding: 0 10px; color: var(--ink); font-size: 14px;
    }
    .actions {
        padding: 8px 20px 24px;
        display: grid; grid-template-columns: 1fr 2fr; gap: 10px;
    }
    .primary, .ghost {
        height: 50px; border-radius: 6px;
        font-size: 14px; font-weight: 600; cursor: pointer;
    }
    .primary { background: var(--accent); color: #fff; border: none; }
    .primary:hover { background: var(--accent2); }
    .primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .ghost { background: var(--card); color: var(--ink); border: 1px solid var(--border); }
    .ghost:hover { background: var(--card-hi); }
</style>
```

- [ ] **Step 2: Прогнать dev-сервером с запущенным бэком и MoreLogin**

```bash
# терминал 1
uv run --env-file .env uvicorn backend.main:app --reload
# терминал 2
cd frontend && npm run dev
```

Под овнером зайти на `/apartments/new`, вставить ссылку из `tests/e2e_listing_urls.txt`, разобрать, сохранить. Убедиться, что квартира появилась в списке.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/apartments/new/+page.svelte
git commit -m "feat(frontend): /apartments/new — URL-only → превью → сохранение"
```

---

## Task 12: Финализация — прогнать 14 ссылок и убрать временные артефакты

- [ ] **Step 1: Прогнать все 14 ссылок через UI**

Открыть `tests/e2e_listing_urls.txt`, по одной вставить в `/apartments/new`, разобрать, сохранить. Дубли (если повторно вставить) должны давать 409 «уже есть».

Если конкретная ссылка падает на парсере — завести правки в `backend/parsers/*.py`, юнит-тест с новой фикстурой (через `e2e_capture_html.py`), коммитить точечно.

- [ ] **Step 2: Удалить временные файлы**

```bash
git rm tests/e2e_listing_urls.txt tests/e2e_morelogin_discover.py scripts/fetch_links.py
```

- [ ] **Step 3: Финальный прогон тестов**

```bash
uv run pytest -v
```
Все зелёные.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore: убрать разовые артефакты (14 ссылок, discovery-скрипт, fetch_links)"
```

---

## Self-review

**Spec coverage:**
- MoreLogin-клиент → Task 1 ✅
- Парсеры doska + youla → Task 6, 7 ✅
- POST /apartments/parse-url (owner only) → Task 8 ✅
- Миграция source/source_url + UNIQUE → Task 3 ✅
- 409 на дубль → Task 3 ✅
- Фронт /apartments/new URL-only → Task 11 ✅
- Админ не создаёт квартиры → Task 8 (бэк) + Task 10 (UI) ✅
- tests/e2e_*.py интерактивные → Task 2, 5, 9 ✅
- tests/e2e/ удалена + fixture переехал → уже сделано в прошлом коммите ✅
- 14 ссылок как временная фикстура, удалить после прогона → Task 12 ✅
- Резолв редиректа trk.mail.ru → Task 4 (resolve_final_url) ✅
- Юнит-тесты парсеров → Task 6, 7 ✅

**Placeholder scan:** Task 1 Step 4 содержит `# TODO заменить на найденный в discovery` — это намеренный маркер, задача инженера именно его заменить после Step 2. Остальное — чистый код.

**Type consistency:** `ParsedListing.source`, `.source_url`, `.price_per_night`, `.area_m2` — одинаково везде. `_fetch_and_parse` определён в Task 8, используется в Task 9 — совпадает.

**Риски:**
- MoreLogin API может вернуть CDP в формате, отличном от ожидаемых ключей. Task 1 Step 2 явно требует валидации и правки `_extract_cdp`.
- Селекторы парсеров могут не совпасть с актуальным HTML. TDD-цикл на фикстурах это ловит, но на остальных 13 ссылках нюансы могут вылезти — Task 12 их вычищает.
