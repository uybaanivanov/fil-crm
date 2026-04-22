# Cleaning Schedule — Design Spec

**Дата:** 2026-04-22
**Статус:** approved, ready for planning

## Цель

Расширить существующую кнопку «Требует уборки» в карточке квартиры: при нажатии спрашивать, **когда** требуется уборка (datetime). Время показывается горничной в списке `/cleaning`, просрочка подсвечивается.

## Скоуп

- Одно новое поле `apartments.cleaning_due_at` (ISO-8601 local datetime, nullable).
- API `mark-dirty` принимает `cleaning_due_at` (обязательно).
- Фронт — диалог с `datetime-local`, дефолт = checkout ближайшей активной брони (12:00) или «следующий круглый час».
- Сортировка `/cleaning` по возрастанию `cleaning_due_at`, просрочка в красной плашке сверху.
- **Не в скоупе:** история уборок, кто убирал, автосоздание уборки при checkout брони, фильтры «сегодня / неделя», таймзоны. Если понадобится — отдельные специки.

## Модель данных

Миграция `backend/migrations/004_cleaning_due_at.sql`:

```sql
ALTER TABLE apartments ADD COLUMN cleaning_due_at TEXT;
```

**Семантика:**
- `TEXT` в ISO-8601 без TZ (`"2026-04-23T14:00:00"`). Таймзону не храним — весь проект работает в локальном времени Якутска.
- `NULL` — дата не задана. Легальное состояние для старых записей с `needs_cleaning=1` без даты (после миграции).
- `needs_cleaning INTEGER` (уже есть) — источник истины «надо убирать». `cleaning_due_at` — метаданные.

**Инвариант:** если `needs_cleaning = 0`, то `cleaning_due_at IS NULL`. Обеспечивается эндпоинтами (`mark-clean` обнуляет оба поля, `mark-dirty` проставляет оба).

`SELECT_FIELDS` в `backend/routes/apartments.py` расширяется на `cleaning_due_at`.

## API

### `POST /apartments/{id}/mark-dirty`

**Изменение:** теперь требует body.

Request body:
```json
{ "cleaning_due_at": "2026-04-23T14:00:00" }
```

- Формат: ISO-8601 local datetime без TZ. Pydantic-модель парсит как `datetime` (без tzinfo). При невалидном формате → `422`.
- Прошедшее время разрешено — легитимный кейс «просрочено сразу».
- Пустое / отсутствующее поле → `422`.
- Роль: `owner | admin`.
- **Идемпотентность:** повторный вызов на уже грязной квартире перезаписывает `cleaning_due_at`. `needs_cleaning` остаётся `1`.

Response: `200` + актуальная карточка квартиры (с новым полем).

### `POST /apartments/{id}/mark-clean`

Контракт снаружи не меняется. Внутри:
```sql
UPDATE apartments SET needs_cleaning = 0, cleaning_due_at = NULL WHERE id = ?
```

### `GET /apartments/cleaning`

- Добавляется поле `cleaning_due_at` в каждый элемент.
- Сортировка: `ORDER BY cleaning_due_at IS NULL, cleaning_due_at ASC, id` — NULL в хвосте.

### `GET /apartments`, `GET /apartments/{id}`

Добавляется поле `cleaning_due_at` в ответ. Прочих изменений нет.

## UX / Фронт

### Компонент `frontend/src/lib/ui/CleaningDueDialog.svelte`

Модалка с одним полем `<input type="datetime-local">` + кнопки «Сохранить» / «Отмена».

- Props: `open` (bool), `defaultValue` (string|null), `onSubmit(iso: string)`, `onCancel()`.
- Enter в поле = submit (аналог клика «Сохранить»).
- Пустое значение disable-ит кнопку.
- Прошедшее время разрешено (без предупреждения — соответствует API).

### Страница `frontend/src/routes/apartments/[id]/+page.svelte`

**Кнопка действий с уборкой** (одна, состояние зависит от `apt.needs_cleaning`):

- `apt.needs_cleaning === 0`: label «Требует уборки» → открывает диалог с дефолтом → на submit `POST /apartments/{id}/mark-dirty { cleaning_due_at }`.
- `apt.needs_cleaning === 1`: label «Изменить время уборки» → диалог с `defaultValue = apt.cleaning_due_at` → тот же endpoint (перезаписывает).

Существующая кнопка «Убрано» (`POST /mark-clean`) — без изменений.

**Дефолт времени** (helper `defaultCleaningDueAt(apt)` в `frontend/src/lib/format.js`):
- Если у квартиры есть активный гость (`currentGuest` уже считается на карточке) — дефолт = `currentGuest.booking.check_out` со временем `12:00` локально.
- Иначе — `now()` округлённое вверх до ближайшего часа.
- Возвращает строку в формате `datetime-local`: `YYYY-MM-DDTHH:MM`.

**Секция «Нужна уборка»** (блок `{#if apt.needs_cleaning}`):
- Строка `К ${fmtDateTime(apt.cleaning_due_at)}` или «Время не указано» при `NULL`.
- Если `cleaning_due_at !== null && new Date(cleaning_due_at) < new Date()` — плашка-чип tone `"due"` с текстом «Просрочено».

### Страница `frontend/src/routes/cleaning/+page.svelte`

Сортировка приходит с бэка. Рендер карточки:
- Заголовок: `apt.title` / `apt.address` (как сейчас).
- Под заголовком: `«к 14:00, 23 апр.»` через `fmtDateTime`, при `NULL` — ничего.
- Если просрочено — красный чип-префикс «Просрочено» (используем существующий `Chip` с tone `"due"`).

### Формат даты/времени

Новый хелпер `fmtDateTime(iso)` в `frontend/src/lib/format.js`:
```js
new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
```
Для `null` возвращает пустую строку. Паттерн параллелен существующему `fmtDate`.

## Обработка ошибок

- `422` от `/mark-dirty` (невалидный datetime, пустое поле) — фронт показывает `error.detail` внутри модалки, модалка не закрывается.
- `404` / `403` — отрабатывается существующим общим ApiError-флоу.
- NULL-совместимость: `fmtDateTime(null)` → `""`, просрочка не подсвечивается. Старые записи (`needs_cleaning=1`, `cleaning_due_at=NULL`) отображаются корректно.
- Гонки: одновременный `mark-dirty` от двух админов с разным временем → last-write-wins (UPDATE атомарен в SQLite). Не предотвращаем — не критично для прототипа.

## Тестирование

Следуем существующему паттерну — самодостаточные e2e-скрипты на httpx, без импорта `backend.*`.

**`tests/e2e_cleaning_schedule.py`:**

1. Логин owner через `GET /dev_auth/users` + `X-User-Id`.
2. Выбрать/создать квартиру.
3. `POST /apartments/{id}/mark-dirty { "cleaning_due_at": "2026-04-24T14:00:00" }` → `200`, ответ содержит `needs_cleaning=1`, `cleaning_due_at="2026-04-24T14:00:00"`.
4. `POST /apartments/{id}/mark-dirty { "cleaning_due_at": "2026-04-24T16:30:00" }` → `200`, время перезаписано.
5. `POST /apartments/{id}/mark-dirty { "cleaning_due_at": "not-a-date" }` → `422`.
6. `POST /apartments/{id}/mark-dirty {}` → `422`.
7. Создать вторую грязную квартиру с `cleaning_due_at="2026-04-24T10:00:00"`. `GET /apartments/cleaning` → первая с `10:00` идёт раньше второй с `16:30`.
8. `POST /apartments/{id}/mark-clean` → `needs_cleaning=0`, `cleaning_due_at=null`.

**Ручная проверка UI (чеклист в плане):**
- Открыть карточку свободной квартиры, нажать «Требует уборки» → диалог с дефолтом (next hour).
- Открыть карточку с активной бронью → дефолт = checkout 12:00.
- Сохранить → статус-чип «Требует уборки», секция показывает «К 14:00, 24 апр.».
- Повторный клик по кнопке → label «Изменить время уборки», в поле старое значение.
- `/cleaning` сортирует по возрастанию, просрочка — красный чип.
- Зайти под ролью maid → `/cleaning` показывает то же.

**Unit-тесты бэкенда не вводим** — их в проекте нет, e2e покрывает контракт и регрессии.

## Риски и допущения

- Таймзоны: принимаем, что сервер и браузеры открывающих CRM работают в одной локальной зоне (Якутск). Если появится разная TZ — отдельная задача, затронет парсинг и сравнения.
- SQLite `TEXT` для datetime: сортировка ISO-8601 лексикографически = сортировка хронологически, пока формат `YYYY-MM-DDTHH:MM:SS`. Это держим контрактом на стороне API.
- `needs_cleaning` остаётся отдельной колонкой — не заменяем на `cleaning_due_at IS NOT NULL`, потому что легальный NULL-кейс (старые записи) требует явного флага.
