#!/usr/bin/env bash
# Прод-старт: бэк (uvicorn, без --reload) + worker.
# Фронт собирается отдельно (см. ниже) и раздаётся nginx из frontend/build/.
#
# Перед первым запуском (и после каждого pull):
#   cd frontend && npm install && npm run build && cd ..
#
# Для дев-режима используй прямые команды:
#   uv run --env-file .env uvicorn backend.main:app --reload --port 8000
#   cd frontend && npm run dev -- --port 5173

set -euo pipefail

SESSION=fil-crm
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Сессия '$SESSION' уже существует — перезапускаю."
    tmux kill-session -t "$SESSION"
fi

tmux new-session -d -s "$SESSION" -n backend -c "$ROOT"
tmux send-keys -t "$SESSION:backend" \
    "uv run --env-file .env uvicorn backend.main:app --port 8000" C-m

tmux new-window -t "$SESSION" -n worker -c "$ROOT"
tmux send-keys -t "$SESSION:worker" \
    "uv run --env-file .env python -m backend.worker" C-m

echo "Сессия tmux '$SESSION' запущена: backend :8000, worker."
echo "Подключиться: tmux attach -t $SESSION"
