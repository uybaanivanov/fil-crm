# Polish карточки квартиры + онбординг + мульти-валюта

## Контекст

В существующий прототип нужно внести пакет UI/UX-улучшений и одну продуктовую добавку. Все блоки разноразмерные, но связаны темой «довести до боевого вида то, что уже работает», поэтому идут единым спеком.

1. **Карточка квартиры (`/apartments/[id]`):**
   - Снять визуальное выделение обязательных полей (сейчас primary-пунктир + звёздочка). Все поля выглядят одинаково.
   - Сделать `monthly_utilities` опциональным; обязательным остаётся только `monthly_rent`.
   - Добавить тултипы-подсказки для бизнес-метрик (ADR, RevPAR и т.д.).
   - Заменить «уродскую ссылку» в поле обложки на квадрат-превью с загрузкой файла.
2. **Онбординг новой квартиры (`/apartments/new`):**
   - Сейчас единственный путь — парсер. Добавить ручной режим как равноправную альтернативу через табы.
3. **Команда (`/users`):**
   - Owner может создать нового юзера прямо из интерфейса (форма username/password/full_name/role). Сейчас там только список.
4. **Выбор квартиры в форме брони (`/bookings/new`):**
   - Заменить простой select на combobox с подстрочным поиском по позывному/адресу, thumbnail-превью и пометкой ближайшей пересекающейся брони.
5. **Мульти-валюта (глобально):**
   - Все суммы хранятся в рублях, но в шапке появляется свитч RUB/USD/VND, выбранная валюта применяется во всём UI. Курсы тянутся бэкендом раз в сутки с `open.er-api.com`.

Хранение медиа — локальная файловая система (`backend/media/`), на дев бэкенд раздаёт через `StaticFiles`, на проде nginx маппит `location /media/` → `/opt/fil-crm/backend/media/` под доменом `sakha.gay`.

## Область и не-область

**В области:**
- Эндпоинты: `POST/DELETE /apartments/{id}/cover`, `POST /users`, `GET /currency/rates`, расширение `GET /apartments` параметрами `q`, `check_in`, `check_out`.
- Изменение поведения `PATCH /apartments/{id}`: `monthly_utilities` больше не обязателен.
- Изменение поведения парсера: внешние `cover_url` скачиваются локально и при создании квартиры перемещаются в её каталог.
- Миграция `003_currency.sql` (таблица `currency_rates`).
- Самостоятельный скрипт `scripts/refresh_rates.py` для крона.
- Раздача `backend/media/` через `StaticFiles` в дев-режиме.
- Фронт: правка `EditableField`, новые компоненты `HelpTip`, `CoverPicker`, `ApartmentPicker`, табы на `/apartments/new`, форма `/users/new`, валютный свитч в `+layout.svelte`, переход с `fmtRub` на `fmtMoney`.
- Глоссарий терминов в `frontend/src/lib/glossary.js` (минимум: `adr`, `revpar`).
- Пример nginx-конфига для `sakha.gay` в `docs/`.
- Тесты `tests/e2e_*.py` для новых эндпоинтов.

**Вне области:**
- Галерея фотографий квартиры (только одна обложка).
- Профиль/аватар юзера, восстановление пароля, инвайт-флоу.
- Конвертация валют при вводе сумм (только при отображении; ввод всегда в рублях).
- Полнотекстовый/подлинный fuzzy-поиск (используем `LOWER(...) LIKE`).
- Ре-парсинг существующих квартир, рефреш cover для уже импортированных.
- Капча/прокси-логика для парсера, кеш курсов в RAM.

## Бэкенд

### Загрузка обложки

Эндпоинты в `backend/routes/apartments.py`:

- `POST /apartments/{id}/cover` — `multipart/form-data`, поле `file`. Доступ: owner и admin.
  - Валидация: `Content-Type` ∈ `image/jpeg|image/png|image/webp`, размер ≤ 5 МБ.
  - Сохраняем в `backend/media/apartments/{id}/cover.<ext>` (всегда одно имя на квартиру; перед записью удаляем все старые `cover.*` в каталоге, чтобы при смене расширения не оставался мусор).
  - Обновляем `apartments.cover_url = '/media/apartments/{id}/cover.<ext>'` через raw SQL.
  - Ответ: `{"cover_url": "..."}`.
- `DELETE /apartments/{id}/cover` — owner/admin. Стирает файл (если есть) и обнуляет `cover_url`. Идемпотентен.

В `backend/main.py` на дев-режиме монтируем статику:

```python
from fastapi.staticfiles import StaticFiles
app.mount("/media", StaticFiles(directory="backend/media"), name="media")
```

На проде маршрут `/media/*` отдаёт nginx, статикой бэкенда не пользуемся (mount остаётся, но запросы до бэка не доходят).

### Парсер: локализация cover

Расширяем `POST /apartments/parse-url` (`backend/routes/apartments.py`):

1. После того как парсер вернул `ParsedListing` с внешним `cover_url`, бэк делает `httpx.get(cover_url, timeout=10, follow_redirects=True)`.
2. По `Content-Type` определяем расширение (`jpeg|png|webp`); если тип не поддержан или запрос упал — оставляем `cover_url=None` (превью без картинки), парсинг не валим.
3. Сохраняем во временный файл `backend/media/apartments/_pending/<uuid>.<ext>` и в превью отдаём путь `/media/apartments/_pending/<uuid>.<ext>`.

В `POST /apartments`:

- Если `cover_url` начинается с `/media/apartments/_pending/`, после INSERT берём `id` новой квартиры, перемещаем файл в `backend/media/apartments/{id}/cover.<ext>` и переписываем `cover_url` в БД.
- Очистка `_pending/` (файлы старше 24 ч) — простая GC-функция, вызывается в начале `parse-url`. Сложного крона не нужно.

### ЖКХ → опциональный

В `apartments.py` (PATCH-обработчик):

- Удалить условие, требующее `monthly_utilities`. Required-логика остаётся только для `monthly_rent` (`HTTPException(400, detail='monthly_rent обязателен')`).
- В `scripts/generate_baseline_expenses.py` строка «ЖКХ» добавляется в baseline только если `monthly_utilities is not None`. Если NULL — пропускаем.

### Создание юзеров

Новый эндпоинт в `backend/routes/users.py`:

- `POST /users` — `require_role("owner")`.
- Тело: `{username: str, password: str, full_name: str, role: 'owner'|'admin'|'maid'}`.
- Валидация: `username` 3–32 символа `[a-z0-9_]`, `password` ≥ 8 символов, `role` из набора, `full_name` непустой.
- Хеширование пароля — той же функцией, что используется в `auth.py` для существующих юзеров (используем уже имеющийся хелпер; не вводим новых криптопрактик).
- Конфликт `username` (UNIQUE-нарушение) → `409 username_taken`.
- Ответ: созданный юзер без полей пароля/хеша.

### Курсы валют

Миграция `backend/migrations/003_currency.sql`:

```sql
CREATE TABLE IF NOT EXISTS currency_rates (
    date TEXT NOT NULL,
    code TEXT NOT NULL,
    rate_to_rub REAL NOT NULL,
    PRIMARY KEY (date, code)
);
```

`rate_to_rub` хранит, сколько единиц валюты в одном рубле (как отдаёт `open.er-api.com` для `base=RUB`). Для USD это будет ~0.011, для VND ~273.

Новый модуль `backend/currency.py`:

- `async def refresh_rates() -> None` — `httpx.get('https://open.er-api.com/v6/latest/RUB')`, читает `rates.USD` и `rates.VND`, делает `INSERT OR REPLACE` для текущей даты.
- `def get_latest_rates() -> dict` — `SELECT code, rate_to_rub, date FROM currency_rates WHERE date = (SELECT MAX(date) FROM currency_rates)`. Возвращает `{usd, vnd, updated_at}`. Если в таблице пусто — `{usd: None, vnd: None, updated_at: None}`, фронт молча падает в RUB.

Новый эндпоинт `GET /currency/rates` (без авторизации, ответ кешируется фронтом).

Самостоятельный скрипт `scripts/refresh_rates.py` (по правилам CLAUDE.md — не импортит `backend`):

- Открывает sqlite напрямую, делает HTTP-запрос через `httpx`, пишет в `currency_rates`.
- Запускается через `uv run --env-file .env scripts/refresh_rates.py`.
- В `README.md` добавить cron-рецепт по аналогии с `generate_baseline_expenses`.

### Поиск квартир для брони

Расширяем `GET /apartments` в `backend/routes/apartments.py`:

- Опциональные query-параметры: `q: str | None`, `check_in: date | None`, `check_out: date | None`.
- Если `q` непустой: добавляем `WHERE LOWER(callsign) LIKE :q OR LOWER(address) LIKE :q` (подстановка `%q%`).
- Если `check_in` и `check_out` заданы: к каждой квартире джоином из `bookings` считаем `next_booked_from` — минимальная `check_in` брони, у которой диапазон пересекается с `[check_in, check_out)` или начинается позже `check_in` в пределах ближайших 60 дней. Возвращаем строкой `'YYYY-MM-DD'` или `null`.
- Сортировка результата: квартиры со свободным окном — сверху, занятые — снизу.

Существующие потребители `GET /apartments` без параметров получают тот же ответ + новое поле `next_booked_from: null`.

## Фронт

### Единый стиль `EditableField`

Файл `frontend/src/lib/ui/EditableField.svelte`:

- Удалить: класс `required` (на `<label>`), `<span class="req">*</span>`, hint «Обязательно для сохранения», CSS-селектор `.field.required`.
- Параметр `required` в `$props()` оставить (используется консьюмерами для логической валидации), но никаких визуальных эффектов от него больше нет.
- Состояние `has-error` остаётся как есть.
- Все поля, и в характеристиках, и в расходах, выглядят одинаково.

### Тултипы (`HelpTip`)

Новый словарь `frontend/src/lib/glossary.js`:

```js
export const GLOSSARY = {
    adr: {
        title: 'ADR',
        body: 'Average Daily Rate — средняя цена за ночь по проданным ночам.'
    },
    revpar: {
        title: 'RevPAR',
        body: 'Revenue per Available Room — выручка на доступную комнату-ночь.'
    }
    // далее по мере нужды
};
```

Новый компонент `frontend/src/lib/ui/HelpTip.svelte`:

- Пропсы: `term: string`.
- Рендерит inline-кнопку `ⓘ` (16×16, цвет `var(--faint)`).
- По клику/тапу/hover — popover с `title` (b) и `body` (плейн-текст).
- Закрытие — клик вне или Esc.
- На мобиле популярный — позиционирование адаптивное (если влево не лезет — вправо, если снизу не лезет — сверху).

Применить в `/apartments/[id]` (стат-блок ADR) и `/reports` (ADR, RevPAR), просто заменив текстовый label на `<span>{label}<HelpTip term="adr"/></span>`.

### Cover-загрузчик

Новый компонент `frontend/src/lib/ui/CoverPicker.svelte`:

- Пропсы: `apartmentId: number`, `cover: string | null`, `onChange: (newUrl: string | null) => void`.
- Рендер:
  - Если `cover` есть — квадрат 160×160 с `background-image: url($cover)`. На hover/тап — оверлей с двумя действиями: «Заменить» и «Удалить».
  - Если нет — dashed-плейсхолдер 160×160 с центром «📷 Загрузить обложку».
- Действия:
  - «Загрузить» / «Заменить» → программный клик по скрытому `<input type="file" accept="image/jpeg,image/png,image/webp">`. После выбора — `FormData`, `POST /apartments/{id}/cover`. После успеха `onChange(новыйUrl)`.
  - «Удалить» → подтверждение → `DELETE /apartments/{id}/cover` → `onChange(null)`.
- Состояние загрузки: оверлей со спиннером; ошибки — toast/inline текст.

В `frontend/src/routes/apartments/[id]/+page.svelte` блок «Обложка» с `EditableField cover_url` заменяем на `<CoverPicker apartmentId={apt.id} cover={apt.cover_url} onChange={(u) => apt.cover_url = u}/>`.

### Табы на `/apartments/new`

В `frontend/src/routes/apartments/new/+page.svelte`:

- Локальный state `mode: 'parse' | 'manual'` (начальное `'parse'`).
- Шапка с двумя табами: «По ссылке» / «Вручную». Клик переключает `mode`.
- Общие поля (`title`, `address`, `rooms`, `area`, `floor`, `district`, `price`, `cover_url`) выносятся в локальный сабкомпонент `PropsForm` (или просто общий блок разметки), используется в обоих режимах.
- В режиме `parse`: сверху URL-блок и кнопка «Распарсить» — после успеха префилит state. Дальше — общий блок полей и кнопка «Сохранить».
- В режиме `manual`: только общий блок полей и «Сохранить». При сабмите `source = 'manual'`, `source_url = null`. URL-блок не показывается.
- При переключении табов state полей сохраняется (на случай «вставил URL → распарсил → переключил на manual поправить»).

### Форма создания юзера

Новый файл `frontend/src/routes/users/new/+page.svelte`:

- Доступ: только owner. Если не owner — показываем «Нет прав» (повтор паттерна с `/users`).
- Поля: `username` (text), `password` (password, toggle «показать»), `full_name` (text), `role` (select: owner/admin/maid).
- Submit → POST `/users` → `goto('/users')`. Ошибки — inline.

В `/users/+page.svelte` (только для owner) добавить кнопку «+» в шапку, ведёт на `/users/new`.

### Combobox `ApartmentPicker`

Новый компонент `frontend/src/lib/ui/ApartmentPicker.svelte`:

- Пропсы: `value: number | null`, `check_in: string | null`, `check_out: string | null`, `onChange: (id) => void`.
- Поле ввода с placeholder «Поиск по позывному или адресу». При фокусе — открывается выпадающий список.
- На каждое изменение текста (debounce 200 мс) — `GET /apartments?q=&check_in=&check_out=`. На пустой `q` — отдаёт топ-N (без фильтра).
- Рендер строки:
  - Слева thumb 40×40 (`cover_url` через `<img>` или плейсхолдер).
  - По центру: жирно — `callsign || title`, мельче серым — `address`.
  - Справа: если `next_booked_from` непустой — красная плашка `до DD.MM`.
- Клавиатура: ↑↓ навигация по строкам, Enter — выбор, Esc — закрыть.
- Выбранная квартира отображается в свёрнутом виде с теми же thumb/название/адрес и кнопкой «Сменить».

В `frontend/src/routes/bookings/new/+page.svelte` — заменить текущий select на `<ApartmentPicker check_in={...} check_out={...} value={...} onChange={...}/>`.

### Глобальный валютный свитч

Новый модуль `frontend/src/lib/currency.js`:

- Svelte store `currentCurrency` — `'RUB' | 'USD' | 'VND'`. Инициализация из `localStorage.currency`, дефолт `RUB`. Запись в localStorage при смене.
- Svelte store `rates` — `{usd, vnd, updated_at}`. Загружается один раз при инициализации (`api.get('/currency/rates')`).
- Функция `fmtMoney(amountRub)` — берёт текущий код и курс, конвертит, возвращает строку с символом валюты:
  - RUB → `1 234 ₽`.
  - USD → `$13.50`.
  - VND → `₫337,500`.
- При отсутствии курсов или ошибке — fallback в RUB.

В `frontend/src/lib/format.js` существующие `fmtRub`/`fmtShortRub` переписываем как обёртки над `fmtMoney`: сигнатура и места вызова не меняются, но внутри они учитывают текущую валюту. Это даёт мгновенный охват без правки всех потребителей.

В `frontend/src/routes/+layout.svelte`:

- Компактный селект `[₽ ▼]` рядом с шапкой (на мобиле — в углу). Показывает текущий символ; в дропдауне — три варианта (`₽ Рубли`, `$ Доллары`, `₫ Донги`).
- Изменение → пишет в store + localStorage. Все компоненты, использующие `fmtMoney`, реактивно обновляются.

## Данные / миграции

- `backend/migrations/003_currency.sql` — таблица `currency_rates`.
- Папка `backend/media/apartments/` создаётся автоматически при первой загрузке (`os.makedirs(..., exist_ok=True)`).
- Папка `backend/media/apartments/_pending/` для временных файлов парсера.
- В `.gitignore` добавить `backend/media/`.
- На проде в `/opt/fil-crm` — то же дерево; nginx-конфиг (пример в `docs/nginx-sakha-gay.conf`):

```
server {
    server_name sakha.gay;
    location /media/ {
        alias /opt/fil-crm/backend/media/;
        expires 7d;
        access_log off;
    }
    location / { proxy_pass http://127.0.0.1:8000; ... }
}
```

## Тестирование

`tests/` (стиль — самодостаточные `e2e_*.py`-скрипты, как в проекте принято):

- `tests/e2e_apartment_cover.py` — загрузка валидного jpeg, отказ на text/plain, перезапись (старый файл удаляется), DELETE.
- `tests/e2e_users_create.py` — owner создаёт, admin получает 403, конфликт username, валидация полей.
- `tests/e2e_apartments_search.py` — фильтр `q` по callsign и адресу, корректный `next_booked_from` при наличии и отсутствии броней.
- `tests/e2e_currency_refresh.py` — `refresh_rates` пишет в БД, `get_latest_rates` отдаёт последнее.
- Парсер с локализацией cover — добавить кейс к существующим тестам парсера: после парсинга `cover_url` начинается с `/media/apartments/_pending/`, после `POST /apartments` файл переехал в `/media/apartments/{id}/cover.<ext>`.

Фронтовые компоненты (CoverPicker, ApartmentPicker, HelpTip, валютный свитч) проверяются вручную в браузере по чек-листу при имплементации.

## Открытые вопросы

- Точные тексты глоссария (формулировки ADR/RevPAR) — допишем при имплементации, согласуем по ходу.
- Поведение валютного свитча в формах ввода (например, при правке `monthly_rent`): пока — ввод всегда в рублях независимо от выбранной валюты отображения. При желании в будущем добавим конвертацию ввода.
