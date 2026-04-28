"""Ручной сброс demo-БД и demo-media к фикстуру.

Запускать из корня /opt/fil-crm-demo/. Не импортит backend (правило CLAUDE.md).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    seed_db = root / "docs" / "demo-seed.sqlite3"
    seed_media = root / "docs" / "demo-media"
    target_db = root / "db.sqlite3"
    target_media = root / "backend" / "media"

    if not seed_db.exists():
        print(f"ERROR: фикстур {seed_db} не найден", file=sys.stderr)
        return 1

    shutil.copy(seed_db, target_db)
    print(f"copied {seed_db} -> {target_db}")

    if target_media.exists():
        shutil.rmtree(target_media)
    target_media.mkdir(parents=True, exist_ok=True)
    if seed_media.exists():
        for item in seed_media.iterdir():
            dst = target_media / item.name
            if item.is_dir():
                shutil.copytree(item, dst)
            else:
                shutil.copy(item, dst)
        print(f"copied {seed_media}/* -> {target_media}/")
    else:
        print(f"warning: {seed_media} отсутствует, медиа не копируем")

    print("demo reset complete. Перезапусти tmux: bash demo_start.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
