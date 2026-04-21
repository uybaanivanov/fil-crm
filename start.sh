#!/usr/bin/env bash
set -euo pipefail

SESSION=fil-crm
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "Сессия '$SESSION' уже существует — перезапускаю."
    tmux kill-session -t "$SESSION"
fi

tmux new-session -d -s "$SESSION" -n backend -c "$ROOT"
tmux send-keys -t "$SESSION:backend" \
    "uv run --env-file .env uvicorn backend.main:app --reload --port 8000" C-m

tmux new-window -t "$SESSION" -n frontend -c "$ROOT/frontend"
tmux send-keys -t "$SESSION:frontend" \
    'if [ -s "$HOME/.nvm/nvm.sh" ]; then . "$HOME/.nvm/nvm.sh"; nvm use node >/dev/null; fi; npm run dev -- --port 5173' C-m

echo "Сессия tmux '$SESSION' запущена: backend :8000, frontend :5173."
echo "Подключиться: tmux attach -t $SESSION"
