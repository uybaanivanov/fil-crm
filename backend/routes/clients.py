import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn
from backend.lib.stats import parse_date

router = APIRouter(prefix="/clients", tags=["clients"])


class ClientIn(BaseModel):
    full_name: str = Field(min_length=1)
    phone: str = Field(min_length=1)
    notes: str | None = None


class ClientPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=1)
    phone: str | None = Field(default=None, min_length=1)
    notes: str | None = None


def _row(conn, client_id: int):
    return conn.execute(
        "SELECT id, full_name, phone, notes, created_at FROM clients WHERE id = ?",
        (client_id,),
    ).fetchone()


@router.get("")
def list_clients(_: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, full_name, phone, notes, created_at FROM clients ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientIn, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO clients (full_name, phone, notes) VALUES (?, ?, ?)",
            (payload.full_name, payload.phone, payload.notes),
        )
        row = _row(conn, cur.lastrowid)
    return dict(row)


@router.patch("/{client_id}")
def update_client(
    client_id: int,
    payload: ClientPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления"
        )
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [client_id]
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE clients SET {set_clause} WHERE id = ?", values
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден"
            )
        row = _row(conn, client_id)
    return dict(row)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: int, _: dict = Depends(require_role("owner", "admin"))):
    try:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден"
                )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить клиента с привязанными бронями",
        )
    return None


@router.get("/{client_id}")
def get_client(
    client_id: int, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        row = _row(conn, client_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден")
        bookings = conn.execute(
            """
            SELECT b.id, b.check_in, b.check_out, b.total_price, b.status,
                   a.title AS apartment_title, a.id AS apartment_id,
                   a.callsign AS apartment_callsign
            FROM bookings b JOIN apartments a ON a.id = b.apartment_id
            WHERE b.client_id = ?
            ORDER BY b.check_in DESC
            """,
            (client_id,),
        ).fetchall()
    bookings = [dict(b) for b in bookings]
    nights = sum(
        (parse_date(b["check_out"]) - parse_date(b["check_in"])).days
        for b in bookings
        if b["status"] != "cancelled"
    )
    active_count = sum(1 for b in bookings if b["status"] != "cancelled")
    revenue = sum(b["total_price"] for b in bookings if b["status"] != "cancelled")
    return {
        **dict(row),
        "bookings": bookings,
        "stats": {"count": active_count, "nights": nights, "revenue": revenue},
    }
