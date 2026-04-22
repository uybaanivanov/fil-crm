import re
import sqlite3
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn
from backend.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])

_USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


class Role(str, Enum):
    owner = "owner"
    admin = "admin"
    maid = "maid"


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)
    role: Role


@router.get("")
def list_users(_: dict = Depends(require_role("owner"))):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, role, username, created_at FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserIn, _: dict = Depends(require_role("owner"))):
    if not _USERNAME_RE.match(payload.username):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="username должен быть [a-z0-9_]{3,32}",
        )
    pw_hash = hash_password(payload.password)
    try:
        with get_conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (full_name, role, username, password_hash) VALUES (?, ?, ?, ?)",
                (payload.full_name, payload.role.value, payload.username, pw_hash),
            )
            new_id = cur.lastrowid
            row = conn.execute(
                "SELECT id, full_name, role, username, created_at FROM users WHERE id = ?",
                (new_id,),
            ).fetchone()
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="username занят",
        )
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
