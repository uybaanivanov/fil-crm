import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "db.sqlite3"
MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def apply_migrations() -> None:
    with get_conn() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_migrations ("
            "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))"
        )
        applied = {
            r["name"]
            for r in conn.execute("SELECT name FROM _schema_migrations").fetchall()
        }
        for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if f.name in applied:
                continue
            conn.executescript(f.read_text(encoding="utf-8"))
            conn.execute(
                "INSERT INTO _schema_migrations(name) VALUES (?)", (f.name,)
            )
