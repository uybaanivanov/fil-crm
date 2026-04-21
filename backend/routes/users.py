from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/users", tags=["users"])


class Role(str, Enum):
    owner = "owner"
    admin = "admin"
    maid = "maid"


class UserIn(BaseModel):
    full_name: str = Field(min_length=1)
    role: Role


@router.get("")
def list_users(_: dict = Depends(require_role("owner"))):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, role, created_at FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserIn, _: dict = Depends(require_role("owner"))):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (full_name, role) VALUES (?, ?)",
            (payload.full_name, payload.role.value),
        )
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT id, full_name, role, created_at FROM users WHERE id = ?",
            (new_id,),
        ).fetchone()
    return dict(row)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, current: dict = Depends(require_role("owner"))):
    if user_id == current["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственную учётную запись",
        )
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    if cur.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return None
