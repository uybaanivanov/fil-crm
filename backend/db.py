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
    files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    with get_conn() as conn:
        for f in files:
            conn.executescript(f.read_text(encoding="utf-8"))
