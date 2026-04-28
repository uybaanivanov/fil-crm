#!/usr/bin/env bash
# Старт demo-инстанса fil-crm. Полный аналог start.sh, но:
# - tmux session: fil-crm-demo
# - порт: 8002
# - env: .env.demo
# - worker НЕ запускается (никаких внешних дёрганий)
# - при первом запуске копирует фикстур БД и медиа

set -euo pipefail

SESSION=fil-crm-demo
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Если БД нет — копируем фикстур
if [ ! -f "$ROOT/db.sqlite3" ]; then
    if [ ! -f "$ROOT/docs/demo-seed.sqlite3" ]; then
        echo "ERROR: docs/demo-seed.sqlite3 отсутствует. Сначала сгенерируй фикстур (scripts/demo_make_seed.py)." >&2
        exit 1
    fi
    cp "$ROOT/docs/demo-seed.sqlite3" "$ROOT/db.sqlite3"
    echo "Скопирован фикстур в db.sqlite3"
fi

# 2. Если media пуста — копируем demo-media (если они есть)
mkdir -p "$ROOT/backend/media"
if [ -z "$(ls -A "$ROOT/backend/media" 2>/dev/null)" ] && [ -d "$ROOT/docs/demo-media" ]; then
    cp -r "$ROOT/docs/demo-media/." "$ROOT/backend/media/"
    echo "Скопированы demo-media в backend/media"
fi

# 3. Перезапуск tmux
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Сессия '$SESSION' уже существует — перезапускаю."
    tmux kill-session -t "$SESSION"
fi

tmux new-session -d -s "$SESSION" -n backend -c "$ROOT"
tmux send-keys -t "$SESSION:backend" \
    "uv run --env-file .env.demo uvicorn backend.main:app --port 8002" C-m

echo "Demo tmux '$SESSION' запущен: backend :8002 (worker отключён)."
echo "Подключиться: tmux attach -t $SESSION"
