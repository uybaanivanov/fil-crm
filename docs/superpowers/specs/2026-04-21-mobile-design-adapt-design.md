# Мобильный редизайн fil-crm — адаптация под handoff-дизайн

Дата: 2026-04-21
Тема: перевод SvelteKit-фронта на мобильный дизайн из Claude Design (тёмная warm-earth палитра, карточные списки, нижний таб-бар), расширение бэка FastAPI+SQLite под объём дизайна по принципу «бэк — источник правды».

Исходник дизайна: `/tmp/design-fetch/extracted/fil-crm/project/Мобильные экраны.html` + файлы в `mobile/` (frame.jsx, ui.jsx, screens-a.jsx, screens-b.jsx) + обновлённая версия `/apartments/new` из локального `_ _ _ standalone.html`.

---

## 1. Принципы

- Бэк — источник правды. Ничего не «мокаем» на фронте.
- Декор, который не отображает бизнес-данные (погода, праздники, донат источников, уведомления), — **не строим**, если не помечен иначе.
- Расширяем схему SQLite минимально и только там, где без этого теряется целая секция (apartments-обогащение, expenses).
- Тёмная тема по умолчанию. Светлая — через `localStorage`.
- Мобильный first: 390px viewport, фиксированный таб-бар снизу, без боковых меню, без таблиц.

---

## 2. Изменения схемы БД

Миграция `backend/migrations/002_design_adapt.sql`:

```sql
ALTER TABLE apartments ADD COLUMN cover_url TEXT;
ALTER TABLE apartments ADD COLUMN rooms TEXT;        -- 'Студия' | '1-комн' | '2-комн' | '3+'
ALTER TABLE apartments ADD COLUMN area_m2 INTEGER;
ALTER TABLE apartments ADD COLUMN floor TEXT;        -- '3/5'
ALTER TABLE apartments ADD COLUMN district TEXT;     -- 'Сайсары' и т.п.

CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount INTEGER NOT NULL,             -- ₽, положительное
    category TEXT NOT NULL,              -- свободный текст, рекомендуемые: Уборка, ЖКХ, Ремонт, Комиссии, Прочее
    description TEXT,
    occurred_at TEXT NOT NULL,           -- YYYY-MM-DD
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_expenses_occurred ON expenses(occurred_at);
```

Роли в `users.role` остаются: `owner / admin / maid` → в UI «Владелец / Администратор / Горничная».

Пароли, флаги active/invited, email, 2FA, Telegram-бот, реквизиты, шаблоны договоров, чек-листы уборок, события/notifications, источник на бронях — **не добавляются**.

---

## 3. Изменения backend

### 3.1 DEBUG-gated dev-auth

- Текущие `GET /auth/users` и `POST /auth/login` **переезжают на `/dev_auth/*`**.
- Регистрируются в `main.py` только если `os.getenv("DEBUG")` truthy.
- На фронте `src/routes/dev_auth/` проверяет доступность (`GET /dev_auth/users`): если 404/не отвечает — показывает сообщение «Dev-picker отключён, установи `DEBUG=1`».

Прод-эквивалент входа не реализуется — `/login` **декоративный**.

### 3.2 Новые и доработанные endpoints

Таблица (путь, роль, назначение):

| Метод | Путь | Роли | Что делает |
|---|---|---|---|
| GET | `/dev_auth/users` | — | Список юзеров для пикера (DEBUG only) |
| POST | `/dev_auth/login` | — | `{user_id}` → профиль (DEBUG only) |
| GET | `/apartments/{id}` | owner, admin | Один объект со всеми полями |
| GET | `/apartments/{id}/stats?month=YYYY-MM` | owner, admin | `{nights, adr, revenue, utilization}` по броням, попадающим в месяц. `utilization` = booked_nights / days_in_month |
| GET | `/apartments?with_stats=1&month=YYYY-MM` | owner, admin | Список с дополнительным полем `utilization` и `status` (derived: occupied / needs_cleaning / free) на каждую квартиру |
| POST/PATCH | `/apartments` / `/apartments/{id}` | owner, admin | Принимают новые поля: `cover_url, rooms, area_m2, floor, district` (все опциональные) |
| GET | `/bookings/{id}` | owner, admin | Одна бронь с join'ами |
| GET | `/bookings/calendar?from=YYYY-MM-DD&to=YYYY-MM-DD` | owner, admin | `[{apartment_id, bookings: [{id, client_name, check_in, check_out, status}]}]` |
| GET | `/clients/{id}` | owner, admin | Клиент + его `bookings[]` + агрегаты `{count, nights, revenue}` |
| GET | `/dashboard/summary` | owner, admin | KPI (занятость N/total, revenue MTD, Δ к прошлому месяцу), ряд дневной выручки за месяц, список сегодняшних событий (заезды+выезды с ФИО клиента и адресом) |
| GET | `/reports?period=week|month|quarter|year` | owner, admin | Occupancy %, ADR, RevPAR, avg_nights, + `per_apartment: [{apartment_id, title, util}]` |
| GET | `/expenses` | owner, admin | Список расходов с фильтром `month=YYYY-MM` |
| POST | `/expenses` | owner, admin | `{amount, category, description?, occurred_at}` |
| PATCH | `/expenses/{id}` | owner, admin | Частичное обновление |
| DELETE | `/expenses/{id}` | owner, admin | Удалить |
| GET | `/finance/summary?month=YYYY-MM` | owner, admin | `{revenue, expenses_total, net, by_category: {Уборка: N, ...}, feed: [{type: 'income'|'expense', amount, label, dt}]}` |

`GET /apartments/cleaning` оставляем как есть (это список квартир, где `needs_cleaning=1`).

Существующие `POST /apartments/{id}/mark-dirty`, `POST /apartments/{id}/mark-clean` не трогаем.

### 3.3 Заголовок `X-User-Id`

Сохраняется. Никаких токенов/cookie. После `/dev_auth/login` фронт кладёт id в `localStorage` (как сейчас).

---

## 4. Карта экранов фронта

Размер viewport в дизайне — 390×844. Все экраны верстаем под 390px-mobile-first; на десктопе можно центровать в колонку.

| Роут | Бэк-поддержка | Скопировано из дизайна | Упрощено/выкинуто |
|---|---|---|---|
| `/login` | — (декор) | email, пароль, кнопки «Показать», «Забыли пароль», брендинг «v2.1.0 · Якутск» | Кнопки не работают. Под формой — ссылка-текст «dev picker» (видна только если `GET /dev_auth/users` отвечает 200) |
| `/dev_auth` | `/dev_auth/users`, `/dev_auth/login` | Списочный пикер с аватарами | — |
| `/` (Сводка) | `/dashboard/summary` | Заголовок «Доброе утро, {имя}», KPI-пара «Занято N/total» + «Выручка · {месяц}», график дневной выручки, список «Сегодня» | Виджет погоды и «дней до майских» — **убран** |
| `/calendar` | `/bookings/calendar`, `/apartments` | Шахматка 14 дней × все квартиры, легенда, период-чипы | Цвета: `active=accent`, `completed=positive`, `cancelled` не показываются. Убран цвет «без оплаты» |
| `/apartments` | `/apartments?with_stats=1&month={текущий}` | Список карточек с cover, адресом, rooms·area·district, статус-чип, полоска загрузки% | Статус и утилизация приходят с бэка; fallback для квартир без cover — серая плашка с инициалами адреса |
| `/apartments/new` | `POST /apartments` | Визуал: поле URL, чипы «поддерживается Доска.якт / Юла», «Парсер · результат» (эта таблица-чек-листом), превью «12 фото», блок «Собственник» | Парсер — **декор**. URL не сабмитится. Строки «результат парсера» редактируемы. На сохранение уходят: `title` (отдельное поле «Название / короткий заголовок» над адресом, пользователь сам вводит — например «Лермонтова 58/24»), `address`, `price_per_night`, `rooms`, `area_m2`, `floor`, `district`, `cover_url` (первая фотография; остальные 11 — плейсхолдеры). Блок «Собственник» визуальный, не сохраняется |
| `/apartments/:id` | `/apartments/{id}`, `/apartments/{id}/stats` | Cover сверху, статус-чип, KPI-строка «Ночей / ADR / Выручка», блок «Гость» (текущая активная бронь), «Характеристики» (rooms, area_m2, floor, district, price_per_night, needs_cleaning) | Фотогалерея «1/12» — нет (одна картинка). Отопление/паркинг/питомцы — нет |
| `/bookings` | `/bookings` | Группировка по дню, карточка (время, тип «Заезд/Выезд», ФИО, адрес, ночи, сумма, статус-чип, источник) | Время `14:00`/`12:00` зашито в UI моно-шрифтом бледно. Статус-чип: active→«активная», completed→«закрыта», cancelled скрыт (видно через фильтр). Источник — `client.source`, иначе «—». Фильтр-табы: Все / Заезды / Выезды / Отменённые |
| `/bookings/new` | `POST /bookings`, `/apartments`, `/clients`, `POST /clients` | Блоки «Квартира», «Даты» (диапазон 14:00→12:00), «Гость» (поиск + inline-создание), «Сумма» (auto `nights × price_per_night`, editable) | Один экран, один сабмит, без шагов |
| `/bookings/:id` | `/bookings/{id}`, `/clients/{id}` | Статус-чип, заезд/выезд, карточка квартиры, карточка гостя с «N-й визит» (считаем из ответа `/clients/{id}`), одна строка расчёта «N ночей × ставка = сумма» | Уборка/залог/способ оплаты — нет. Кнопки «Изменить» / «Зарегистрировать» — первая ведёт на форму редактирования, вторая = PATCH status=completed |
| `/cleaning` | `/apartments/cleaning`, `POST /apartments/{id}/mark-clean` | Список карточек с адресом, статусом | Без слотов/исполнителей/прогресса. Одна кнопка «Закрыть уборку». Тап по карточке — на `/apartments/{id}` |
| `/clients` | `/clients` | Алфавитная группировка, аватар, тег «Сегодня · заезд HH:MM» или «Постоянный · N броней», дата последнего визита | «Чёрный список» — нет. Теги считаются на фронте из активных броней и `completed`-истории |
| `/clients/:id` | `/clients/{id}` | Аватар, статы (броней/ночей/выручка), быстрые действия, история, заметка | Quick actions: «Позвонить» (`tel:`), «SMS» (`sms:`), «Бронь» (→ `/bookings/new?client_id=…`). Заметка — `clients.notes` readonly в read-view и editable в отдельной секции |
| `/finance` | `/finance/summary`, `/expenses` | Hero (чистая = revenue − expenses), блок «Расходы» (донат по category + строки), merged-feed «Последние платежи» | Кнопка «+» открывает форму добавить расход (amount/category/description/occurred_at). Источник дохода строки — бронь с `check_out` или `created_at` |
| `/reports` | `/reports?period=…` | Период-табы, KPI-сетка (Занятость/ADR/RevPAR/Ср.ночи), бары загрузки per-apartment | Донат «Источники броней» **скрыт** |
| `/users` | `/users` (owner only) | Список: аватар + имя + ВЫ-бейдж + роль | Без email, без active/invited, без inline-переключателей. Блок «Роли» — статический текст (3 роли с описанием из бэка) |
| `/settings` | — | Карточка профиля (имя + роль + ID), переключатель темы, кнопка «Выйти» | Разделы «Аккаунт» (Профиль/Пароль/Telegram), «Организация», «Уведомления Push/Email», «Помощь», «О приложении» — **убраны**. Остался только минимум. |

**Удалённые из навигации:** `/cleaning/:id`, `/notifications`.

---

## 5. Таб-бар и навигация

Нижний таб-бар, 5 иконок:

1. **Сводка** → `/`
2. **Квартиры** → `/apartments` (с этой вкладки доступны `/calendar` — переключатель «Список / Шахматка» в шапке `/apartments`; `/apartments/:id`, `/apartments/new`)
3. **Брони** → `/bookings` (с этой вкладки — `/bookings/:id`, `/bookings/new`)
4. **Уборка** → `/cleaning`
5. **Профиль** → `/settings`

`/clients`, `/finance`, `/reports`, `/users` — доступны из `/settings` как меню-ссылки (grid или список) и из шорткатов в Сводке. `/users` видно только owner'у.

Роут `/calendar` как отдельный URL оставляем (дизайн ссылается так), но его можно открывать и как вкладку в `/apartments`.

---

## 6. Дизайн-система

### Палитра

Базовые токены — из `colors_and_type.css`. Две темы: `dark` (по умолчанию) и `light`, значения — из `THEMES` в `mobile/frame.jsx`.

Как применяется:
- В `src/app.css` — CSS-переменные на `:root` (light) и `[data-theme="dark"]` (dark).
- На `<html>` ставится `data-theme` из `localStorage.fil_crm_theme`; до первого render — inline-script в `app.html` читает storage и проставляет атрибут (чтоб не мигало).
- Переключатель в `/settings` пишет в `localStorage` и меняет `data-theme`.

### Типографика

Через Google Fonts в `<head>`:
- Instrument Serif (display, заголовки)
- Inter Tight 400/500/600/700 (body)
- JetBrains Mono 400/500/600 (числа, метки, eyebrow, timestamps)

Шкала — из CSS-файла (fs-12…fs-56).

### Компоненты (`src/lib/ui/`)

Один-в-один порт из `mobile/ui.jsx` в Svelte 5 runes:

- `Eyebrow.svelte` — mono+caps метка
- `Chip.svelte` — `tone: ok|due|late|info|draft|accent`
- `Card.svelte` — border + pad
- `Section.svelte` — `title` + optional `action`
- `PageHead.svelte` — `title, sub?, right?, back?`
- `IconBtn.svelte` — круглая кнопка с SVG-path
- `AddBtn.svelte` — плюсик терракотовый
- `Searchbar.svelte`
- `FilterChips.svelte`
- `Avatar.svelte` — инициалы, `size, accent?`
- `Divider.svelte`
- `ListRow.svelte`
- `Chevron.svelte`
- `TabBar.svelte` — 5 вкладок, активная по path

Иконки — inline-SVG внутри компонентов (как в дизайне). Ничего не тянем из npm-пакета.

### Числа и деньги

Монобуквенный `JetBrains Mono` с `font-variant-numeric: tabular-nums`. Утилиты в `src/lib/format.js`:

```js
fmtRub(n)          // 12 840 ₽
fmtShortRub(n)     // 12.8к ₽ / 782к ₽
fmtDate(iso)       // 21.04
fmtNights(ci, co)  // 3 ноч
```

---

## 7. Структура фронта (что появляется/меняется)

```
frontend/src/
├─ app.css                      (переписать: токены тем + базовые стили)
├─ app.html                     (preload шрифтов; inline-script data-theme; viewport mobile)
├─ lib/
│  ├─ api.js                    (+новые методы)
│  ├─ auth.js                   (без изменений)
│  ├─ theme.js                  (новый)
│  ├─ format.js                 (новый)
│  └─ ui/
│     ├─ Chip.svelte, Card.svelte, Eyebrow.svelte, PageHead.svelte,
│     ├─ Section.svelte, IconBtn.svelte, AddBtn.svelte, Searchbar.svelte,
│     ├─ FilterChips.svelte, Avatar.svelte, Divider.svelte,
│     ├─ ListRow.svelte, Chevron.svelte, TabBar.svelte
├─ routes/
│  ├─ +layout.svelte             (auth-guard + TabBar внизу; роли по-прежнему ограничивают доступ)
│  ├─ +page.svelte               (Сводка)
│  ├─ login/+page.svelte         (декоративный + ссылка на /dev_auth при DEBUG)
│  ├─ dev_auth/+page.svelte      (пикер)
│  ├─ apartments/
│  │  ├─ +page.svelte            (список)
│  │  ├─ new/+page.svelte        (парсер-визуал)
│  │  └─ [id]/+page.svelte       (детальная)
│  ├─ bookings/
│  │  ├─ +page.svelte            (список, группировка по дням)
│  │  ├─ new/+page.svelte
│  │  └─ [id]/+page.svelte
│  ├─ calendar/+page.svelte      (шахматка)
│  ├─ cleaning/+page.svelte      (список needs_cleaning)
│  ├─ clients/
│  │  ├─ +page.svelte
│  │  └─ [id]/+page.svelte
│  ├─ finance/+page.svelte
│  ├─ reports/+page.svelte
│  ├─ users/+page.svelte
│  └─ settings/+page.svelte
```

Существующие роуты (`/users`, `/cleaning`, `/bookings`, `/clients`, `/apartments`) — **переписываем**, не правим точечно.

---

## 8. Ограничения и явные отказы

- Нет аутентификации с паролем. Вход через dev-picker при `DEBUG=1`. В проде login-экран останется декоративным; как будет настоящая авторизация — отдельная задача.
- Погода, праздники, события-notifications, донат источников, чёрный список клиентов, чек-листы уборок, фото-галерея квартир, email пользователей — **не строятся**. Место под них в UI не зарезервировано.
- Парсер объявлений (Доска.якт / Юла) — не строится. Визуал остаётся, но все поля заполняются руками.
- Светлая тема — поддерживается, но основной use-case тёмная. Часть хардкод-стилей в компонентах — через CSS-переменные, чтоб обе темы работали.

---

## 9. Риски

- **Большой объём**: ~15 экранов, 12+ UI-примитивов, 10+ новых/изменённых endpoints. План реализации должен разбить это на независимые стадии (бэк → токены → layout → экраны по группам).
- **Миграция БД на существующей sqlite-файл**: `ALTER TABLE` в sqlite работает для добавления nullable-столбцов, что у нас и есть. Проверить, что `apply_migrations()` идемпотентен и видит новую миграцию.
- **Старое API `/auth/*` сносим в пользу `/dev_auth/*`**: фронт обновить синхронно, иначе в не-DEBUG сборке вход сломается даже декоративно.
- **Мобильный viewport на десктопе**: в layout можно ограничить max-width и центровать, чтобы на десктопе не было «пустоты по бокам». Делаем через media-query в `app.css`.

---

## Status

- [x] Backend (план 1/3) — готов 2026-04-21
- [x] Frontend foundation + core screens (план 2/3) — готов 2026-04-21
- [ ] Frontend remaining screens (план 3/3)
