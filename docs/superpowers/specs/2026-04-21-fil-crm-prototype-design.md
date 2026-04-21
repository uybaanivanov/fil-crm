# fil-crm — прототип: дизайн

**Дата:** 2026-04-21
**Статус:** утверждённая спецификация, готовая к переходу в план реализации

## Цель

Собрать работающий прототип CRM для посуточной аренды в Якутске: управление квартирами, клиентами и бронями, плюс простой воркфлоу уборки (админ ставит флаг "требует уборки" → горничная отмечает убрано). Фокус — быстрота и ясность; безопасность и красота UI оставлены на потом.

## Стек

- **Бэк:** Python 3.13 + FastAPI, работает через `uv run --env-file .env`
- **БД:** SQLite (файл `db.sqlite3` в корне), общение raw-запросами через `sqlite3` stdlib, без ORM
- **Фронт:** SvelteKit (dev на `:5173`)

## Роли и права

| Действие | Owner | Admin | Горничная |
|---|---|---|---|
| Управлять пользователями (создавать/удалять) | ✅ | ❌ | ❌ |
| CRUD квартир | ✅ | ✅ | ❌ |
| CRUD клиентов | ✅ | ✅ | ❌ |
| CRUD броней | ✅ | ✅ | ❌ |
| Ставить флаг "требует уборки" | ✅ | ✅ | ❌ |
| Снимать флаг (отметить убрано) | ✅ | ✅ | ✅ |
| Видеть квартиры | все | все | только `needs_cleaning=1` |

## Аутентификация

Прототип без паролей. На странице логина — список всех юзеров с ролями. Клик по юзеру = POST `/auth/login` с `user_id`; фронт сохраняет `{id, role, full_name}` в `localStorage`. Каждый защищённый запрос шлёт заголовок `X-User-Id: <id>`. Бэк через FastAPI `Depends` читает заголовок, находит юзера, проверяет роль. Юзера нет → 401, роль не подходит → 403.

Безопасность нулевая (любой может подставить `X-User-Id`) — это осознанный компромисс прототипа.

## Структура проекта

```
fil-crm/
├── backend/
│   ├── main.py                       # FastAPI app, CORS, startup (apply migrations)
│   ├── db.py                         # connection helper, Row factory, PRAGMA foreign_keys=ON
│   ├── auth.py                       # Depends(require_role(...))
│   ├── migrations/
│   │   └── 001_init.sql              # схема БД
│   ├── routes/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── apartments.py
│   │   ├── clients.py
│   │   └── bookings.py
│   └── seed.py                       # одноразовый скрипт, удаляется после первого запуска
├── frontend/                          # SvelteKit
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api.js                # fetch-helper с X-User-Id + ApiError
│   │   │   └── auth.js               # работа с localStorage
│   │   ├── routes/
│   │   │   ├── +layout.svelte        # навбар по роли, защита от неавторизованных
│   │   │   ├── login/+page.svelte
│   │   │   ├── apartments/+page.svelte
│   │   │   ├── clients/+page.svelte
│   │   │   ├── bookings/+page.svelte
│   │   │   ├── users/+page.svelte
│   │   │   └── cleaning/+page.svelte
│   │   └── app.css                   # минимальный ванильный CSS
│   └── ...                            # стандартная обвязка SvelteKit (package.json, vite config и т.п.)
├── db.sqlite3                         # создаётся при первом запуске
├── pyproject.toml
└── CLAUDE.md
```

## Схема БД

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'maid')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE apartments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    address TEXT NOT NULL,
    price_per_night INTEGER NOT NULL,
    needs_cleaning INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    source TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE bookings (
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

CREATE INDEX idx_bookings_apartment_dates ON bookings(apartment_id, check_in, check_out);
```

**Договорённости:**
- Даты — ISO-строки `YYYY-MM-DD` (sqlite их корректно сравнивает лексикографически)
- `check_out` — exclusive (бронь `21→23` занимает 21-е и 22-е, 23-е уже свободно)
- Цены — целые рубли
- FK без `ON DELETE CASCADE`: удаление квартиры/клиента с привязанными бронями вернёт 409 — сначала отмени/удали брони

## Детектирование конфликтов броней

Для квартиры `A` две активных брони `x` и `y` конфликтуют если:

```
x.check_in < y.check_out AND x.check_out > y.check_in
```

Проверка выполняется при `POST /bookings` и `PATCH /bookings/{id}` (если меняются даты, квартира или статус). При редактировании текущая бронь исключается из проверки. При нахождении конфликта — HTTP 409, в `detail` — `"Даты пересекаются с бронью #<id>"`.

## API

Все защищённые маршруты требуют заголовок `X-User-Id`. В скобках — роли с доступом.

**Auth** (публично)
- `GET  /auth/users` — список всех юзеров для экрана логина (id, full_name, role)
- `POST /auth/login` — `{user_id}` → `{id, full_name, role}`; 404 если юзер не найден

**Users** (owner)
- `GET    /users`
- `POST   /users` — `{full_name, role}`; `role` валидируется Pydantic-енумом (`owner`/`admin`/`maid`), иначе 422
- `DELETE /users/{id}` — нельзя удалить самого себя → 400 `"Нельзя удалить собственную учётную запись"`

**Apartments**
- `GET    /apartments` (owner, admin)
- `GET    /apartments/cleaning` (maid) — только `needs_cleaning=1`
- `POST   /apartments` (owner, admin)
- `PATCH  /apartments/{id}` (owner, admin) — не принимает `needs_cleaning`
- `DELETE /apartments/{id}` (owner, admin)
- `POST   /apartments/{id}/mark-dirty` (owner, admin) — идемпотентно, всегда выставляет `needs_cleaning=1`
- `POST   /apartments/{id}/mark-clean` (owner, admin, maid) — идемпотентно, всегда выставляет `needs_cleaning=0`

**Clients** (owner, admin)
- `GET    /clients`
- `POST   /clients`
- `PATCH  /clients/{id}`
- `DELETE /clients/{id}`

**Bookings** (owner, admin)
- `GET    /bookings` — join-ом подтягивает `apartment_title` и `client_name`
- `POST   /bookings` — проверка пересечения → 409
- `PATCH  /bookings/{id}` — повторная проверка пересечения
- `DELETE /bookings/{id}`

**Ошибки:** `HTTPException` с `detail` на русском. Коды: 401, 403, 404, 409, 422.

## UI / страницы фронта

**`/login`** — карточки всех юзеров (имя + роль-бейдж). Клик → POST `/auth/login` → сохраняем в localStorage → редирект:
- owner/admin → `/apartments`
- maid → `/cleaning`

**`+layout.svelte`** — навбар сверху, пункты по роли. Нет юзера → редирект `/login`.

- **owner:** Квартиры · Клиенты · Брони · Пользователи · [имя + выход]
- **admin:** Квартиры · Клиенты · Брони · [имя + выход]
- **maid:** Уборка · [имя + выход]

**`/apartments` (owner, admin)** — таблица (title, адрес, цена/ночь, статус уборки, действия). Кнопки: Редактировать, Удалить, "Пометить грязно". Сверху "+ Новая квартира" с inline-формой.

**`/clients` (owner, admin)** — таблица (ФИО, телефон, источник, заметки, действия). "+ Новый клиент".

**`/bookings` (owner, admin)** — таблица (Квартира, Клиент, Заезд, Выезд, Сумма, Статус, действия). Форма: селекты квартиры и клиента, даты, сумма, заметки. При 409 — красная плашка "Даты пересекаются с бронью #N".

**`/users` (owner)** — таблица (ФИО, роль, удалить). "+ Новый пользователь" (имя + селект роли).

**`/cleaning` (maid)** — карточки квартир с `needs_cleaning=1`. В каждой — кнопка "Отметить убрано" → POST `mark-clean` → карточка исчезает. Пустой список → "Всё чисто 🎉".

## Стилизация

Минимальная: ванильный CSS в `src/app.css`, системный шрифт, нейтральный фон, один акцентный цвет для кнопок. Без UI-библиотек. Полированный дизайн — отдельным шагом через skill `frontend-design` позже.

## Обработка ошибок

- Бэк — `HTTPException` с коротким русским `detail`
- `sqlite3.IntegrityError` (FK) → 409 с человекочитаемым сообщением
- Фронт — `api.js` на `!response.ok` кидает `ApiError(status, detail)`; компоненты ловят и показывают плашку (простой `div` над формой или `position:fixed` toast)

## Тестирование

Только ручное через UI после сида. Автотестов в прототипе не пишем (осознанный YAGNI). pytest/httpx — на потом.

## Seeding

`backend/seed.py` — одноразовый скрипт. Создаёт три юзера:
- "Хозяин Иван" (owner)
- "Админ Анна" (admin)
- "Горничная Мария" (maid)

Запускается руками: `uv run --env-file .env backend/seed.py`. После первого успешного запуска — удаляется (пользователь явно так просил).

## Что не делаем

- Пароли, сессии, CSRF, rate-limit
- Загрузка фото квартир
- Многогостевые брони, учёт количества гостей
- Email/SMS-уведомления
- i18n (интерфейс только на русском)
- Мультитенантность (один инстанс = одна компания)
- Автотесты
