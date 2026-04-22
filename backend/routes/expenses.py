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
    apartment_id: int | None = None


class ExpensePatch(BaseModel):
    amount: int | None = Field(default=None, gt=0)
    category: str | None = Field(default=None, min_length=1)
    description: str | None = None
    occurred_at: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    apartment_id: int | None = None


FIELDS = (
    "id, amount, category, description, occurred_at, "
    "apartment_id, source, created_at"
)


def _row(conn, eid: int):
    return conn.execute(f"SELECT {FIELDS} FROM expenses WHERE id = ?", (eid,)).fetchone()


def _assert_apartment_exists(conn, apt_id: int | None):
    if apt_id is None:
        return
    row = conn.execute("SELECT 1 FROM apartments WHERE id = ?", (apt_id,)).fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Квартира {apt_id} не найдена",
        )


@router.get("")
def list_expenses(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    apartment_id: int | None = Query(None),
    only_general: bool = Query(False),
    _: dict = Depends(require_role("owner", "admin")),
):
    if apartment_id is not None and only_general:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="apartment_id и only_general взаимоисключающие",
        )
    where = []
    params: list = []
    if month:
        where.append("substr(occurred_at, 1, 7) = ?")
        params.append(month)
    if apartment_id is not None:
        where.append("apartment_id = ?")
        params.append(apartment_id)
    if only_general:
        where.append("apartment_id IS NULL")
    sql = f"SELECT {FIELDS} FROM expenses"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY occurred_at DESC"
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_expense(
    payload: ExpenseIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        _assert_apartment_exists(conn, payload.apartment_id)
        cur = conn.execute(
            "INSERT INTO expenses(amount, category, description, occurred_at, apartment_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                payload.amount, payload.category, payload.description,
                payload.occurred_at, payload.apartment_id,
            ),
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
    with get_conn() as conn:
        if "apartment_id" in fields:
            _assert_apartment_exists(conn, fields["apartment_id"])
        set_clause = ", ".join(f"{k} = ?" for k in fields)
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
