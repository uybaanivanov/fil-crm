# fil-crm

CRM-прототип для посуточной аренды в Якутске. Три роли (owner/admin/maid), сущности квартира/клиент/бронь, флаг "требует уборки".

Стек: Python 3.13 + FastAPI + SQLite (raw queries, без ORM) · SvelteKit · uv · npm.

## Запуск

```bash
# 1. зависимости бэка
uv sync

# 2. зависимости фронта
cd frontend && npm install && cd ..

# 3. бэк на :8000
uv run --env-file .env uvicorn backend.main:app --reload --port 8000

# 4. фронт на :5173 (в другом терминале)
cd frontend && npm run dev -- --port 5173
```

Открыть `http://localhost:5173`.

## Структура

- `backend/` — FastAPI, SQLite, миграции
- `frontend/` — SvelteKit
- `db.sqlite3` — БД (создаётся автоматически при первом запуске)
- `docs/superpowers/` — spec и план реализации

## Примечания

Это прототип. Аутентификации по паролю нет — юзер просто выбирается из списка. Не для продакшена.
