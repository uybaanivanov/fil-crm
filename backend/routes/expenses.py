from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/expenses", tags=["expenses"])


class ExpenseIn(BaseModel):
    amount: int = Field(gt=0)
    category: str = Field(min_length=1)
    description: str | None = None
    occurred_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class ExpensePatch(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1)
    description: str | None = None
    occurred_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


FIELDS = "id, amount, category, description, occurred_at, created_at"


def _row(conn, eid: int):
    return conn.execute(f"SELECT {FIELDS} FROM expenses WHERE id = ?", (eid,)).fetchone()


@router.get("")
def list_expenses(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        if month:
            rows = conn.execute(
                f"SELECT {FIELDS} FROM expenses "
                "WHERE substr(occurred_at, 1, 7) = ? "
                "ORDER BY occurred_at DESC",
                (month,),
            ).fetchall()
        else:
            rows = conn.execute(
                f"SELECT {FIELDS} FROM expenses ORDER BY occurred_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO expenses(amount, category, description, occurred_at) "
            "VALUES (?, ?, ?, ?)",
            (payload.amount, payload.category, payload.description, payload.occurred_at),
        )
        row = _row(conn, cur.lastrowid)
    return dict(row)


@router.patch("/{eid}")
def update_expense(
    eid: int,
    payload: ExpensePatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?",
            list(fields.values()) + [eid],
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расход не найден")
        row = _row(conn, eid)
    return dict(row)


@router.delete("/{eid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(eid: int, _: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM expenses WHERE id = ?", (eid,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Расход не найден")
    return None
