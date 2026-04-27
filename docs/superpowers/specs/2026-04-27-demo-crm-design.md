# Demo-версия CRM

## Цель

Поднять публично доступный demo-инстанс CRM на домене `daily-rental-crm.itartyom.space`, чтобы любой посетитель мог зайти, выбрать роль (owner / admin / maid) и потыкать продукт на фейковых, но реалистично выглядящих данных. Demo обслуживается тем же сервером (`cms-gen-bot`), что и прод, но полностью изолирован от него по БД, медиа, портам и tmux-сессии.

## Out of scope

- **Hourly reset**. Намеренно отложено: лишний инфраструктурный слой (cron / asyncio таймер), который пользователь сделает позже локально. Пока БД переустанавливается из фикстура только вручную через `scripts/demo_reset.py`.
- **i18n / локализация**. Из спецификации убраны селектор языка и сами переводы — мы оставляем интерфейс на русском, как в проде. Когда появится i18n как отдельная задача, тогда же вернётся и селектор.
- **Полировка дизайна demo-страниц**. Минимальный CSS сейчас, отдельный pass через frontend-design skill — позже (см. memory `project_styling_plan.md`).

## Решения, принятые на брейнсторме

- **Источник данных**: разовый снапшот прод-БД, обезличенный руками-через-скрипт, закоммиченный в репо как фикстур. После этого demo не зависит от прода в рантайме.
- **Глубина обезличивания**: все имена и номера, упоминающиеся в БД, заменяются на синтетические. Никаких настоящих ПД третьих лиц или сотрудников в demo-фикстуре не остаётся.
- **Изоляция**: demo живёт в отдельном клоне репозитория `/opt/fil-crm-demo` рядом с прод-клоном `/opt/fil-crm`. Это упрощает изоляцию (отдельный `db.sqlite3`, отдельная `backend/media/`, своя ветка/состояние при необходимости), ценой повторного `git pull` при каждом обновлении.
- **Логин**: обычный `/auth/login` (логин/пароль) в demo отключён. Юзеры заходят только через `/dev_auth` (выбор роли без пароля). Сам `/login` редиректит на `/dev_auth`.

## Архитектура

### Раскладка инфраструктуры на проде

| Компонент | Прод | Demo |
|-----------|------|------|
| Путь | `/opt/fil-crm` | `/opt/fil-crm-demo` |
| Tmux session | `fil-crm` | `fil-crm-demo` |
| Backend port | 8000 | 8001 |
| SQLite | `db.sqlite3` (внутри клона) | `db.sqlite3` (внутри клона demo) |
| Media | `backend/media/` | `backend/media/` (внутри клона demo) |
| Worker | запускается | **не запускается** |
| Domain | `sakha.gay` | `daily-rental-crm.itartyom.space` |
| Nginx vhost | существующий | новый (см. ниже) |
| Frontend build | `npm run build` | `npm run build:demo` (`VITE_DEMO=1`) |

DNS: A-запись `daily-rental-crm.itartyom.space` → IP `cms-gen-bot`. Делается один раз руками. Letsencrypt: certbot выпускает отдельный сертификат для нового домена.

### `demo_start.sh`

Файл в корне репо, рядом со `start.sh`. Запускается на сервере вручную или хуком после deploy. Логика:

1. `SESSION=fil-crm-demo`, `ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)`.
2. Если `db.sqlite3` отсутствует — `cp docs/demo-seed.sqlite3 db.sqlite3`.
3. Если `backend/media/` пустая — `cp -r docs/demo-media/. backend/media/`.
4. Если tmux-сессия `fil-crm-demo` существует — `tmux kill-session -t fil-crm-demo`.
5. Создаём новую сессию, окно `backend`, команда: `uv run --env-file .env.demo uvicorn backend.main:app --port 8001`.
6. Worker не запускаем.
7. Печатаем подсказку про `tmux attach -t fil-crm-demo`.

### `.env.demo`

Лежит в `/opt/fil-crm-demo/.env.demo` на сервере (в git **не коммитим**). Содержит:

- `DEBUG=1` — включает роуты `/dev_auth/*`.
- `FIL_DEV_AUTH_ONLY=1` — новый флаг, выключает обычный `/auth/login` (см. ниже).
- Секреты для внешних API — пустые или явные placeholder-значения, чтобы случайно не достучаться до реальных сервисов. Worker не запускается, но даже если кто-то ткнёт ручку — секретов нет.

В репозиторий добавляем шаблон `.env.demo.example` рядом с `.env.example` (если последний есть; если нет — просто `.env.demo.example`).

### Бэкенд: новый флаг `FIL_DEV_AUTH_ONLY`

В `backend/main.py`:

- Если `os.environ.get("FIL_DEV_AUTH_ONLY")` — **не подключаем** `auth_login_routes.router` (роут `/auth/login`). Любые попытки настоящего логина возвращают 404.
- `DEBUG=1` всё ещё подключает `dev_auth_routes` — это уже существующая логика, не меняем.
- `FIL_DEV_AUTH_ONLY` ортогонален `DEBUG`: можно представить себе demo с `DEBUG=0` без dev_auth, или прод с `DEBUG=1` и обоими login-маршрутами; нам важна именно комбинация в demo.

Никаких других изменений на бэкенде. Никакого «demo middleware», никаких баннеров в API-ответах, никакой автогенерации фикстуров на старте.

### Фронтенд: флаг `VITE_DEMO`

Один runtime-флаг сборки, читается через `import.meta.env.VITE_DEMO`. В `package.json` новый скрипт:

```json
"build:demo": "VITE_DEMO=1 vite build"
```

Что меняется когда флаг включён:

1. **Логин-флоу**:
   - В корневом `+layout.js` (или там, где сейчас редирект на `/login` для незалогиненного юзера) — если `VITE_DEMO`, редиректим на `/dev_auth`.
   - Страница `/login/+page.svelte` при `VITE_DEMO` сразу редиректит на `/dev_auth` (через `goto` в `onMount`).
2. **Баннер «DEMO»**: маленькая фиксированная плашка где-то в шапке. Стиль минимальный, рендерится только когда `VITE_DEMO`. Нужна, чтобы посетитель сразу понимал, что он не на проде.
3. **Пояснение на `/dev_auth`**: один абзац под заголовком, типа «Демо: выбери любую роль чтобы войти. Изменения видны только тебе и не сохраняются между развёртываниями.». Рендерится только при `VITE_DEMO`.

Все остальные страницы рендерятся идентично проду, просто на других данных.

### Nginx vhost

Новый файл, например `docs/nginx-daily-rental-crm.conf`, с тем же шаблоном что у `sakha.gay`, с заменами:

- `server_name daily-rental-crm.itartyom.space;`
- `root /opt/fil-crm-demo/frontend/build;`
- `proxy_pass http://127.0.0.1:8001/;`
- `alias /opt/fil-crm-demo/backend/media/;`
- свой letsencrypt cert.

Файл коммитим в репо (как и существующий `docs/nginx-sakha-gay.conf`) для документации, реальный конфиг кладётся в `/etc/nginx/sites-available/` руками при деплое.

## Генерация сид-фикстура

### Скрипт `scripts/demo_make_seed.py`

Самодостаточный (не импортит backend, см. CLAUDE.md), запускается локально один раз. Шаги:

1. Принимает на вход путь к свежему дампу прод-БД (`scripts/artyom_prod_dump.py` уже существует и тянет с прода; альтернативно — `scp` `db.sqlite3` руками).
2. Копирует входной файл → `docs/demo-seed.sqlite3` (работаем с копией, оригинал не трогаем).
3. Открывает копию через стандартный `sqlite3` (raw SQL).
4. Проходит по списку таблиц/колонок (см. ниже) и обезличивает данные.
5. Очищает sensitive blob-поля (фотки паспортов, скриншоты переписки и т.п.).
6. Закрывает БД, пишет результат на диск.

Параллельно: скрипт копирует **только обложки квартир** из прод-`backend/media/` в `docs/demo-media/`. Всё остальное (фотки паспортов, скрины переписки, любые загруженные документы) — **не копируется вообще**. Из обложек дополнительно отбрасываются те, где видны лица или узнаваемые адресные ориентиры (это глазами при подготовке фикстура; в скрипте — список «исключить» с именами файлов).

### Контракт обезличивания

Скрипт **должен** иметь явный, читаемый список «таблица.колонка → правило обработки». Псевдо-формат:

```python
RULES = [
    ("users", "full_name", lambda i, _: f"User {i}"),
    ("users", "username", lambda i, _: f"user{i}"),
    ("users", "password_hash", lambda *_: ""),
    ("clients", "full_name", fake_name_from_pool),
    ("clients", "phone", lambda i, _: f"+7 999 000 {i:04d}"),
    ("clients", "email", lambda i, _: f"client{i}@example.com"),
    ("clients", "telegram_username", lambda i, _: f"client{i}"),
    ("clients", "passport_data", lambda *_: ""),
    ("bookings", "notes", lambda *_: ""),
    ("apartments", "title", keep),  # если адресов нет
    ...
]
```

Точный список заполняется при реализации проходом по `PRAGMA table_info` для каждой таблицы и ручной разметкой полей, которые потенциально содержат ПД. Все blob-таблицы с фотками/скринами (паспорт, переписки) — `DELETE FROM`.

Имена/фамилии берутся из небольшого встроенного словаря (10-30 имён + 10-30 фамилий), детерминированно по `id` чтобы при повторных прогонах фикстур получался одинаковым. Никаких внешних библиотек faker — лишняя зависимость для одноразового скрипта.

### Скрипт `scripts/demo_reset.py`

Простой Python-скрипт через `shutil` (псевдо):

```
shutil.copy("docs/demo-seed.sqlite3", "db.sqlite3")
shutil.rmtree("backend/media/", ignore_errors=True)
shutil.copytree("docs/demo-media/", "backend/media/")
```

Запускается вручную на сервере в `/opt/fil-crm-demo/`, чтобы привести demo к чистому состоянию. Не импортит backend.

## Файлы, которые добавим/изменим

**Новые файлы:**
- `demo_start.sh` — стартовый скрипт demo-инстанса.
- `.env.demo.example` — шаблон env-файла для demo.
- `docs/demo-seed.sqlite3` — бинарный фикстур (один раз генерим, коммитим).
- `docs/demo-media/` — обезличенные обложки квартир (если есть).
- `docs/nginx-daily-rental-crm.conf` — nginx-конфиг для нового домена.
- `scripts/demo_make_seed.py` — скрипт генерации фикстура из прод-дампа.
- `scripts/demo_reset.py` — ручной сброс demo-БД к фикстуру.

**Изменения в существующих файлах:**
- `backend/main.py` — обработка флага `FIL_DEV_AUTH_ONLY` (skip `/auth/login`).
- `frontend/package.json` — новый скрипт `build:demo`.
- `frontend/src/routes/+layout.svelte` (или где сейчас редирект незалогиненного юзера) — при `VITE_DEMO` редирект на `/dev_auth` вместо `/login`.
- `frontend/src/routes/login/+page.svelte` — при `VITE_DEMO` сразу `goto('/dev_auth')`.
- `frontend/src/routes/dev_auth/+page.svelte` — поясняющий абзац при `VITE_DEMO`.
- Какой-то компонент шапки/общего лейаута — баннер «DEMO» при `VITE_DEMO`.

## Порядок развёртывания на сервере (один раз)

1. Локально: запустить `scripts/demo_make_seed.py` на свежем дампе прода → получить `docs/demo-seed.sqlite3` и `docs/demo-media/`. Закоммитить.
2. Локально: реализовать все правки бэка/фронта, закоммитить, запушить в `master`.
3. На сервере: `git clone /opt/fil-crm /opt/fil-crm-demo` (или `git clone <remote>` — как удобнее), либо просто `cp -a /opt/fil-crm /opt/fil-crm-demo` с последующим `git fetch`.
4. Создать `/opt/fil-crm-demo/.env.demo` (по шаблону `.env.demo.example`).
5. В `/opt/fil-crm-demo/frontend/`: `npm install && npm run build:demo`.
6. Скопировать `docs/nginx-daily-rental-crm.conf` в `/etc/nginx/sites-available/`, симлинкнуть в `sites-enabled/`, выпустить cert через certbot, `nginx -t && systemctl reload nginx`.
7. На `/opt/fil-crm-demo/`: `bash demo_start.sh`. Готово.

При обновлении: `cd /opt/fil-crm-demo && git pull && cd frontend && npm run build:demo && cd .. && bash demo_start.sh`. БД при этом не пересоздаётся (файл уже есть). Если нужно — руками `python scripts/demo_reset.py`.

## Сложность

- **Бэкенд**: легко. Один новый env-флаг, одна `if` в `main.py`.
- **Фронтенд**: норм. Один env-флаг, два места с правкой логин-флоу, один баннер, один абзац на `/dev_auth`. Без i18n не разрастается.
- **Сид-скрипт**: норм-ближе-к-сложно. Главная работа — пройтись по реальной схеме прод-БД и составить полный список колонок с ПД. Сам код прямолинейный (raw SQL, словарь имён, `UPDATE`).
- **Инфра**: легко. Шаблон nginx + клон репо + tmux-скрипт по образцу `start.sh`. DNS и certbot — стандартные операции.

## Нерешённые вопросы

Нет.
