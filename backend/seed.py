"""One-shot seed: создаёт трёх тестовых юзеров. После успешного запуска файл удаляется вручную."""

from backend.db import apply_migrations, get_conn


USERS = [
    ("Хозяин Иван", "owner"),
    ("Админ Анна", "admin"),
    ("Горничная Мария", "maid"),
]


def main() -> None:
    apply_migrations()
    with get_conn() as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if existing > 0:
            print(f"В таблице users уже {existing} записей — сид пропущен.")
            return
        for full_name, role in USERS:
            conn.execute(
                "INSERT INTO users (full_name, role) VALUES (?, ?)",
                (full_name, role),
            )
    print("Сид выполнен: Owner/Admin/Maid созданы. Теперь удали backend/seed.py.")


if __name__ == "__main__":
    main()
