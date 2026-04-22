# Учёт расходов по квартирам

## Проблема

Сейчас в CRM таблица `expenses` плоская, без привязки к квартире. Невозможно:

- видеть сколько стоит содержание конкретной квартиры
- считать чистую прибыль по квартире (доход от броней минус её расходы)
- гарантировать что фиксированные ежемесячные обязательства (аренда помещения, ЖКХ) не забыты

Нужно:

1. Привязать расходы к квартирам (при этом сохранить «общие» расходы фирмы).
2. Ввести baseline — фиксированные ежемесячные суммы аренды и ЖКХ на каждую квартиру.
3. Сделать эти baseline обязательными при редактировании карточки квартиры.
4. Автоматически генерировать фактические записи расходов из baseline раз в месяц.

## Решения

### Модель данных

**Миграция `backend/migrations/006_apartment_expenses.sql`:**

```sql
ALTER TABLE apartments ADD COLUMN monthly_rent INTEGER;
ALTER TABLE apartments ADD COLUMN monthly_utilities INTEGER;

ALTER TABLE expenses ADD COLUMN apartment_id INTEGER REFERENCES apartments(id);
ALTER TABLE expenses ADD COLUMN source TEXT NOT NULL DEFAULT 'manual'
    CHECK (source IN ('manual', 'auto'));

CREATE INDEX idx_expenses_apartment ON expenses(apartment_id);

CREATE UNIQUE INDEX idx_expenses_auto_unique
    ON expenses(apartment_id, category, substr(occurred_at, 1, 7))
    WHERE source = 'auto';
```

- `apartments.monthly_rent`, `apartments.monthly_utilities` — NULL-able в БД; обязательность проверяется на уровне API при PATCH (мягкая миграция существующих данных).
- `expenses.apartment_id` — NULL = общий расход фирмы (зарплата, реклама, бензин), не-NULL = привязан к квартире (интернет, ремонт, аренда/ЖКХ auto-записи, и т.п.).
- `expenses.source` — `manual` для введённых руками, `auto` для сгенерированных скриптом. Auto-записи можно редактировать и удалять; при повторном запуске скрипта за тот же месяц они не перезапишутся (UNIQUE-индекс).
- Частичный UNIQUE-индекс `idx_expenses_auto_unique` — гарантирует максимум одну авто-запись `(apartment, category, month)`, при этом не мешает вводить несколько ручных записей той же категории в том же месяце.

### Backend API

**`PATCH /apartments/{id}`:**
- После применения patch проверяется что `monthly_rent IS NOT NULL AND monthly_utilities IS NOT NULL` в итоговом состоянии строки.
- Если хотя бы одно NULL — `400` с `detail="monthly_rent и monthly_utilities обязательны"`.
- Валидация происходит после merge'а patch с текущей строкой в БД: т.е. если в БД оба поля уже заполнены, PATCH другого поля (например `price_per_night`) проходит без указания baseline.

**`POST /apartments`:**
- Без изменений в части обязательности — квартира создаётся без baseline. Любой последующий PATCH упадёт пока baseline не заполнен, что соответствует «мягкой миграции».

**`GET /apartments` / `GET /apartments/{id}`:**
- Отдают `monthly_rent`, `monthly_utilities`.

**`POST /expenses`, `PATCH /expenses/{id}`:**
- Добавлено поле `apartment_id: int | None`.
- При не-NULL значении — валидация существования квартиры: `SELECT 1 FROM apartments WHERE id = ?`; если не найдена — `400`.
- `source` всегда `'manual'` для записей через API.

**`GET /expenses`:**
- Добавлены query-параметры:
  - `apartment_id: int | None` — если передан, фильтр по конкретной квартире.
  - `only_general: bool = false` — если `true`, вернуть только расходы с `apartment_id IS NULL`.
  - Передавать одновременно обе опции — 400 (взаимоисключающие).
  - Существующий фильтр `month` работает в сочетании с любым из них.
- Возврат строки расширен полями `apartment_id`, `source`.

**`GET /finance/summary`:**
- В ответ добавлено поле `by_apartment: [{apartment_id, title, revenue, expenses_total, net}, ...]`, сортировано по `net DESC`.
  - `revenue` — сумма по броням этой квартиры в месяце (по логике `aggregate_bookings_in_period`).
  - `expenses_total` — сумма `expenses` где `apartment_id = X` в месяце.
  - `net = revenue - expenses_total`.
- Также добавлен отдельный блок `general_expenses_total` — сумма расходов с `apartment_id IS NULL`.
- В `feed` у расходов добавлены поля `apartment_id` и `apartment_title` (NULL у общих).
- Общая `expenses_total` остаётся как есть (включает auto-записи автоматически — они уже в таблице `expenses`).

### Скрипт генерации baseline

**`scripts/generate_baseline_expenses.py`:**
- Самодостаточный, только `sqlite3` из stdlib + `argparse`, **не импортирует backend** (соответствует `CLAUDE.md`).
- Путь к БД берёт из env `DB_PATH` (по дефолту `db.sqlite3` в текущей директории).
- CLI:
  - `--month YYYY-MM` — за какой месяц генерить; по умолчанию текущий (`date.today().strftime("%Y-%m")`).
  - `--dry-run` — вывести что бы сделал, но не писать в БД.
- Логика:
  - Выбирает все квартиры где `monthly_rent IS NOT NULL AND monthly_utilities IS NOT NULL`.
  - Для каждой пытается вставить две записи: `(amount=monthly_rent, category='rent', ...)` и `(amount=monthly_utilities, category='utilities', ...)`, `occurred_at='YYYY-MM-01'`, `source='auto'`, `description='auto-generated'`.
  - Использует `INSERT ... ON CONFLICT DO NOTHING` — UNIQUE-индекс гарантирует идемпотентность.
  - В конце выводит сводку: `created=N, skipped=M`.
- Код возврата: 0 при успехе, ненулевой при ошибке (падение = cron пришлёт письмо / оставит в логе).

**Prod-cron (`/opt/fil-crm`):** `0 3 1 * *` — 03:00 по серверному времени первого числа месяца. Команда:
```
cd /opt/fil-crm && uv run --env-file .env scripts/generate_baseline_expenses.py >> /var/log/fil-crm/baseline.log 2>&1
```

### Frontend

**Карточка квартиры (`/apartments/[id]`):**

- **Редактируемые поля** отмечаются `border-bottom: 1px dashed var(--border)` под инпутом (остальные стороны без рамки). Ховер — усиление цвета.
- **Обязательные поля (`monthly_rent`, `monthly_utilities`)** — `border-bottom: 1px dashed var(--primary)`. Под полем подпись «Обязательно для сохранения».
- При попытке сохранить с пустым обязательным — подсветка красным + сообщение; кнопка «Сохранить» проверяет клиентски, плюс 400 с сервера как бэкап.
- Секция «Расходы по квартире» ниже основной инфы:
  - По умолчанию показывает записи за текущий месяц, есть переключатель месяца (стрелки влево/вправо).
  - Каждая строка: дата, категория (русский лейбл), сумма, описание. Значок `⚙` у записей с `source='auto'`.
  - Сверху итог за месяц (аренда + ЖКХ + прочее) по этой квартире.
  - Кнопка «+ Добавить расход» — открывает модалку (или inline-форму) с полями: категория (селект), сумма, дата, описание. `apartment_id` подставляется из карточки. `source` всегда `'manual'`.

**Категории в UI (селект):**

Русские лейблы → значения в БД:
- Интернет → `internet`
- Ремонт → `repair`
- Мебель → `furniture`
- Расходники → `supplies`
- Аренда → `rent`
- ЖКХ → `utilities`
- Прочее → `other`
- «Другое…» → инпут свободного текста (значение как есть)

Мапа описана в `frontend/src/lib/expenseCategories.js` (один источник правды: value ↔ label).

**Страница `/finance`:**
- Фильтр «Квартира» в шапке: селект из {«Все», «Только общие», конкретные квартиры}.
- В сводке новый блок «По квартирам»: табличка `{квартира, доход, расход, чистая}` с сортировкой по чистой убыванию. Соответствует `by_apartment` из `/finance/summary`.
- Существующие блоки (общий revenue, expenses_total, by_category, feed) остаются.

**Список квартир (`/apartments`):**
- Значок `⚠` рядом с квартирами где `monthly_rent IS NULL OR monthly_utilities IS NULL` — визуальный сигнал что нужно дозаполнить baseline.

**Пермишены:**
- Админ и овнер — полный доступ: редактирование карточки квартиры, создание/редактирование/удаление расходов.
- Горничная (maid) — read-only карточка квартиры, секция расходов скрыта.

## Обработка ошибок

- `PATCH /apartments/{id}` без заполненных baseline → `400` с текстом; фронт подсвечивает оба обязательных поля.
- `POST/PATCH /expenses` с несуществующим `apartment_id` → `400` (явная проверка).
- Cron упал — stderr в лог, идемпотентность позволяет ручной перезапуск чтобы догнать пропущенный месяц: `uv run --env-file .env scripts/generate_baseline_expenses.py --month 2026-04`.

## Тестирование

Новые тесты pytest (расположение по аналогии с существующими):

- `tests/test_apartments.py` (расширение): PATCH без baseline → 400; PATCH с baseline → 200; PATCH другого поля когда baseline уже в БД → 200; PATCH с одним из двух baseline когда второго в БД нет → 400.
- `tests/test_expenses.py` (расширение): create с `apartment_id` → ok; create с несуществующим `apartment_id` → 400; list с фильтром `?apartment_id=X` → только эта квартира; list с `?only_general=true` → только с `apartment_id IS NULL`; list без фильтра → всё.
- `tests/test_baseline_script.py` (новый): запускает `generate_baseline_expenses.py` через subprocess на временной БД-фикстуре. Проверяет:
  1. Создаёт по 2 записи на квартиру с заполненным baseline.
  2. Пропускает квартиры без baseline.
  3. Повторный запуск за тот же месяц не дублирует (идемпотентность).
  4. Флаг `--month YYYY-MM` работает корректно.
  5. `--dry-run` не пишет в БД.
- `tests/test_finance.py` (расширение): `summary` возвращает `by_apartment` с корректными суммами; `general_expenses_total` корректен; `feed` содержит `apartment_title`.

Фронтовых автотестов не пишем — их нет в проекте.

## Что явно не делаем (YAGNI)

- **История изменения baseline** — если аренда поднимется, новое значение применится к следующему cron-запуску. Прошлые `auto`-записи не пересчитываются. Если нужно задним числом — руками правим `expenses`.
- **Авто-пересчёт `expenses` при удалении квартиры** — `expenses.apartment_id` останется как есть (FK без `ON DELETE`). Удаление квартиры сейчас не реализовано как кейс; когда появится — решим тогда.
- **Роли с гранулярными правами на категории расходов** — всё по ролям owner/admin/maid, как сейчас.
- **Отчёт «план/факт» по baseline** — план и факт сейчас одно и то же (скрипт создаёт факт из плана). Отдельный сценарий когда факт отличается от плана не моделируется.
