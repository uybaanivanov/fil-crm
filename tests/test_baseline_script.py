import os
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "generate_baseline_expenses.py"


def _init_schema(db_path: Path) -> None:
    from backend.db import MIGRATIONS_DIR
    conn = sqlite3.connect(str(db_path))
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        conn.executescript(f.read_text(encoding="utf-8"))
    conn.commit()
    conn.close()


def _run_script(db_path: Path, *args: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DB_PATH": str(db_path)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env, capture_output=True, text=True, check=False,
    )


def _setup_db(tmp_path):
    db = tmp_path / "t.sqlite3"
    _init_schema(db)
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        INSERT INTO apartments(title, address, price_per_night, monthly_rent, monthly_utilities)
        VALUES ('A1', 'x', 1000, 50000, 7000);
        INSERT INTO apartments(title, address, price_per_night, monthly_rent, monthly_utilities)
        VALUES ('A2', 'y', 1000, 30000, 5000);
        INSERT INTO apartments(title, address, price_per_night)
        VALUES ('A3 no baseline', 'z', 1000);
        """
    )
    conn.commit()
    conn.close()
    return db


def test_script_creates_two_records_per_apartment(tmp_path):
    db = _setup_db(tmp_path)
    r = _run_script(db, "--month", "2026-04")
    assert r.returncode == 0, r.stderr
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT apartment_id, category, amount, source, occurred_at FROM expenses"
    ).fetchall()
    conn.close()
    assert len(rows) == 4
    for row in rows:
        assert row[3] == "auto"
        assert row[4] == "2026-04-01"
    cats = sorted({r[1] for r in rows})
    assert cats == ["rent", "utilities"]


def test_script_skips_apartments_without_baseline(tmp_path):
    db = _setup_db(tmp_path)
    r = _run_script(db, "--month", "2026-04")
    assert r.returncode == 0
    conn = sqlite3.connect(str(db))
    apt_ids = {row[0] for row in conn.execute("SELECT apartment_id FROM expenses").fetchall()}
    conn.close()
    assert 3 not in apt_ids


def test_script_is_idempotent(tmp_path):
    db = _setup_db(tmp_path)
    _run_script(db, "--month", "2026-04")
    _run_script(db, "--month", "2026-04")
    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    assert count == 4


def test_script_month_flag(tmp_path):
    db = _setup_db(tmp_path)
    _run_script(db, "--month", "2026-03")
    _run_script(db, "--month", "2026-04")
    conn = sqlite3.connect(str(db))
    months = {row[0] for row in conn.execute(
        "SELECT substr(occurred_at,1,7) FROM expenses").fetchall()}
    conn.close()
    assert months == {"2026-03", "2026-04"}


def test_script_without_utilities_generates_only_rent(tmp_path):
    """Квартира с monthly_rent но без monthly_utilities — только строка rent, без utilities."""
    db = tmp_path / "t.sqlite3"
    _init_schema(db)
    conn = sqlite3.connect(str(db))
    conn.executescript(
        """
        INSERT INTO apartments(title, address, price_per_night, monthly_rent)
        VALUES ('RentOnly', 'z', 1000, 45000);
        """
    )
    conn.commit()
    conn.close()

    r = _run_script(db, "--month", "2026-04")
    assert r.returncode == 0, r.stderr

    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT category FROM expenses WHERE apartment_id = 1"
    ).fetchall()
    conn.close()

    cats = [row[0] for row in rows]
    assert cats == ["rent"]
    assert "utilities" not in cats


def test_script_dry_run_writes_nothing(tmp_path):
    db = _setup_db(tmp_path)
    r = _run_script(db, "--month", "2026-04", "--dry-run")
    assert r.returncode == 0
    conn = sqlite3.connect(str(db))
    count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    conn.close()
    assert count == 0
