# MoreLogin-парсер объявлений + URL-only поток добавления квартиры

## Контекст

Сейчас `/apartments/new` — ручная форма с декоративным полем URL («парсер не реализован»). Админ имеет те же права, что и овнер, включая создание квартир. Нужно:

1. Реализовать реальный парсер объявлений с **doska.ykt.ru** и **youla.ru** (трекер `trk.mail.ru` → редирект на youla).
2. Запускать парсер через **MoreLogin-профиль** (локальный API `http://127.0.0.1:40000`, профиль id=1) — чтобы обходить бот-детект источников, подключаясь к уже залогиненному браузеру через CDP.
3. Убрать ручную форму на `/apartments/new` — остаётся только URL → превью → сохранить.
4. Запретить админу создавать квартиры; оставить за ним только редактирование/операционные действия.
5. Положить в проект 14 ссылок, присланных в телегу, как фикстуру для ручного тестирования парсера.

Спек делается в две фазы, но в одном плане.

## Область и не-область

**В области:**
- Клиент MoreLogin API (start/stop профиля, получение CDP-URL).
- Модульный парсер с единым контрактом, реализациями для doska.ykt.ru и youla.ru.
- Эндпоинт `POST /apartments/parse-url` (owner only).
- Миграция схемы: `apartments.source`, `apartments.source_url` с уникальным индексом.
- Фронт `/apartments/new` — URL → разбор → превью с редактируемыми полями → сохранить. Ручная форма удаляется.
- Ограничение прав: `POST /apartments` и `POST /apartments/parse-url` — только `owner`. На фронте скрывается кнопка «Добавить» у админа.
- Интерактивные e2e-скрипты `tests/e2e_*.py` (без pytest).
- Юнит-тесты парсеров на сохранённых HTML-фикстурах.

**Вне области:**
- Асинхронные парсер-джобы, очередь, поллинг статуса.
- Парсеры для других источников (Авито, домофонд и т.д.).
- Автоматический ре-парсинг или обновление существующих квартир.
- Капча-солверы, прокси-ротация, антидетект поверх MoreLogin.

## Фаза 1: MoreLogin-клиент + парсер

### Модули

```
backend/
  morelogin.py          # клиент локального MoreLogin API
  parsers/
    __init__.py         # parse(url) -> ParsedListing (резолв редиректа + роутинг)
    types.py            # dataclass ParsedListing
    doska_ykt.py        # parse_html(html, url) -> ParsedListing
    youla.py            # parse_html(html, url) -> ParsedListing
  routes/
    apartments.py       # + POST /apartments/parse-url
```

### Контракт `ParsedListing`

Dataclass с полями:
- `title: str | None`
- `address: str | None`
- `price_per_night: int | None`
- `rooms: str | None`
- `area_m2: int | None`
- `floor: str | None`
- `district: str | None`
- `cover_url: str | None`
- `source: str` — `"doska_ykt"` или `"youla"`
- `source_url: str` — финальный URL после редиректа

### Клиент MoreLogin

`backend/morelogin.py`:
- `async start_profile(profile_id: int) -> str` — возвращает CDP URL вида `ws://127.0.0.1:NNNNN/devtools/browser/...`
- `async stop_profile(profile_id: int) -> None`
- Конфиг — через env: `MORELOGIN_API_URL` (default `http://127.0.0.1:40000`), `MORELOGIN_PROFILE_ID` (default `1`).
- Точные эндпоинты API изучаются на этапе имплементации (см. «Открытые вопросы»).

### Поток `POST /apartments/parse-url`

Вход: `{"url": "..."}`. Авторизация: `require_role("owner")`.

1. `httpx` HEAD с `follow_redirects=True` → финальный URL.
2. По хосту финального URL выбирается парсер; если домен не поддержан — `422 unsupported_source`.
3. `cdp_url = await morelogin.start_profile(1)`.
4. `async with async_playwright() as p: browser = await p.chromium.connect_over_cdp(cdp_url)` → открыть страницу → `page.goto(url, wait_until="networkidle")` → `html = await page.content()` → закрыть контекст.
5. `listing = parser.parse_html(html, final_url)`.
6. `await morelogin.stop_profile(1)` в `finally`.
7. Ответ — сериализованный `ParsedListing`.

Ошибки:
- MoreLogin недоступен → `502 morelogin_unavailable`.
- Playwright/навигация упала → `502 fetch_failed` + причина.
- Парсер не смог разобрать HTML (нет минимального `title`) → `422 parse_failed`.

### Миграция схемы

Новый файл миграции добавляет:
```sql
ALTER TABLE apartments ADD COLUMN source TEXT;
ALTER TABLE apartments ADD COLUMN source_url TEXT;
CREATE UNIQUE INDEX apartments_source_url_uniq ON apartments(source_url) WHERE source_url IS NOT NULL;
```

`ApartmentIn` расширяется полями `source`, `source_url` (optional). `create_apartment` — при `IntegrityError` на уникальном индексе → `409 duplicate_source_url`.

### Интерактивные e2e-скрипты

- Папка `tests/e2e/` удаляется (существует от прошлой итерации).
- `tests/e2e_listing_urls.txt` — 14 ссылок из телеги (дамп для ручного copy-paste). **Временный файл**: удаляется из репо на последнем шаге плана, после того как все 14 квартир прогнаны через парсер.
- `tests/e2e_morelogin_open.py` — интерактивно печатает «open profile 1? [y]», стартует профиль, выводит CDP URL, ждёт Enter, стопает. Smoke-проверка клиента.
- `tests/e2e_parse_url.py` — `input("url: ")`, полный пайплайн (резолв → MoreLogin → Playwright → парсер), печатает `ParsedListing` в pretty-print. Это тот самый «следующий шаг» после дампа ссылок.
- Запуск: `uv run --env-file .env python tests/e2e_<name>.py`. Pytest не подхватывает (нет префикса `test_`).

### Юнит-тесты парсеров

- `tests/fixtures/doska_ykt_<id>.html`, `tests/fixtures/youla_<id>.html` — снятые руками снепшоты страниц.
- `tests/test_parser_doska.py`, `tests/test_parser_youla.py` — грузят фикстуру, вызывают `parse_html`, проверяют извлечённые поля. Без сети, без браузера.

## Фаза 2: фронт + ограничение прав

### Бэк

- `POST /apartments` → `require_role("owner")` (было `owner`, `admin`).
- `POST /apartments/parse-url` → `require_role("owner")`.
- PATCH/DELETE/mark-dirty/mark-clean — без изменений.

### Фронт `/apartments/new`

Полная переделка экрана:
- Единственный инпут — URL, кнопка «Разобрать».
- Во время парсинга — спиннер, инпут заблокирован.
- Успех → под формой появляются заполненные поля (все редактируемые). Кнопка «Сохранить».
- Ошибка → баннер, «Сохранить» скрыт, овнер правит URL и жмёт «Разобрать» снова.
- Старая ручная форма удаляется целиком.

### Фронт `/apartments`

- Кнопка «Добавить квартиру» показывается только если `me.role === 'owner'`.
- Остальное на странице — без изменений.

### Тесты authz

- `tests/test_authz.py` — кейсы: `admin POST /apartments` → 403, `admin POST /apartments/parse-url` → 403, `owner POST /apartments` → 201.

## Конфиг / env

Добавляется:
- `MORELOGIN_API_URL` (default `http://127.0.0.1:40000`).
- `MORELOGIN_PROFILE_ID` (default `1`).

Уже есть, остаются как было:
- `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` — для `scripts/fetch_links.py` (используется разово, не в проде).

## Открытые вопросы / риски

1. **MoreLogin API**: точные эндпоинты `/profile/start` и формат ответа — на этапе имплементации сниффим локальный API, смотрим доку. В плане — явный шаг «разобраться с API» перед клиентом.
2. **Бот-детект Youla**: вся схема с MoreLogin нужна именно для обхода; если всё равно блокирует — это отдельная задача (прокси/профиль с другим fingerprint).
3. **Селекторы источников**: HTML структура doska.ykt.ru и youla.ru — снимаем вручную на этапе имплементации.
4. **Конкурентность MoreLogin-профиля**: один профиль нельзя стартовать дважды одновременно. На текущем MVP (один овнер, один клик) — ок; если потребуется параллельность — придётся ставить лок/очередь. YAGNI сейчас.

## Success criteria

- Овнер вставляет ссылку doska.ykt.ru → видит заполненные поля → сохраняет квартиру.
- Овнер вставляет ссылку `trk.mail.ru` (Youla-трекер) → редирект резолвится → Youla-парсер отрабатывает → квартира сохраняется с `source = "youla"`.
- Повторная вставка той же ссылки → 409 на сохранении.
- Админ не видит кнопку «Добавить» и получает 403 при прямом POST.
- `tests/e2e_parse_url.py` работает интерактивно и на 14 ссылках из фикстуры проходит без ошибок.
- Юнит-тесты парсеров зелёные.
