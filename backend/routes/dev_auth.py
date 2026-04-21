from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.db import get_conn

router = APIRouter(prefix="/dev_auth", tags=["dev_auth"])


class LoginIn(BaseModel):
    user_id: int


@router.get("/users")
def list_users_for_login():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, role FROM users ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/login")
def login(payload: LoginIn):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, full_name, role FROM users WHERE id = ?",
            (payload.user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден",
        )
    return dict(row)
