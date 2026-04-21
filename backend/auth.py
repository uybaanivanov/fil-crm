from typing import Iterable

from fastapi import Header, HTTPException, status

from backend.db import get_conn


def _load_user(user_id: int) -> dict:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, full_name, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    return dict(row)


def require_role(*roles: str):
    allowed = set(roles)

    def dep(x_user_id: int | None = Header(default=None, alias="X-User-Id")) -> dict:
        if x_user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Отсутствует заголовок X-User-Id",
            )
        user = _load_user(x_user_id)
        if user["role"] not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав",
            )
        return user

    return dep
