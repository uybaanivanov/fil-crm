from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from backend.db import get_conn
from backend.security import verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@router.post("/login")
def login(payload: LoginIn):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id, full_name, role, username, password_hash "
            "FROM users WHERE username = ?",
            (payload.username,),
        ).fetchone()
    if row is None or not row["password_hash"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    if not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")
    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "role": row["role"],
        "username": row["username"],
    }
