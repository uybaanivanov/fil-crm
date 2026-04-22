import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, model_validator

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/bookings", tags=["bookings"])


BOOKING_STATUSES = {"active", "cancelled", "completed"}


class BookingIn(BaseModel):
    apartment_id: int
    client_id: int
    check_in: date
    check_out: date
    total_price: int = Field(gt=0)
    notes: str | None = None

    @model_validator(mode="after")
    def _dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("check_out должна быть позже check_in")
        return self


class BookingPatch(BaseModel):
    apartment_id: int | None = None
    client_id: int | None = None
    check_in: date | None = None
    check_out: date | None = None
    total_price: int | None = Field(default=None, gt=0)
    status: str | None = None
    notes: str | None = None


def _find_conflict(conn, apartment_id: int, check_in: str, check_out: str, exclude_id: int | None):
    sql = (
        "SELECT id FROM bookings WHERE apartment_id = ? AND status = 'active' "
        "AND check_in < ? AND check_out > ?"
    )
    params: list = [apartment_id, check_out, check_in]
    if exclude_id is not None:
        sql += " AND id != ?"
        params.append(exclude_id)
    row = conn.execute(sql, params).fetchone()
    return row["id"] if row else None


def _row(conn, booking_id: int):
    return conn.execute(
        """
        SELECT b.id, b.apartment_id, b.client_id, b.check_in, b.check_out,
               b.total_price, b.status, b.notes, b.created_at,
               a.title AS apartment_title,
               a.cover_url AS apartment_cover_url,
               a.callsign AS apartment_callsign,
               c.full_name AS client_name
        FROM bookings b
        JOIN apartments a ON a.id = b.apartment_id
        JOIN clients c ON c.id = b.client_id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()


@router.get("")
def list_bookings(_: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT b.id, b.apartment_id, b.client_id, b.check_in, b.check_out,
                   b.total_price, b.status, b.notes, b.created_at,
                   a.title AS apartment_title,
                   a.cover_url AS apartment_cover_url,
                   a.callsign AS apartment_callsign,
                   c.full_name AS client_name
            FROM bookings b
            JOIN apartments a ON a.id = b.apartment_id
            JOIN clients c ON c.id = b.client_id
            ORDER BY b.check_in DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingIn, _: dict = Depends(require_role("owner", "admin"))
):
    ci = payload.check_in.isoformat()
    co = payload.check_out.isoformat()
    try:
        with get_conn() as conn:
            conflict = _find_conflict(conn, payload.apartment_id, ci, co, None)
            if conflict is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Даты пересекаются с бронью #{conflict}",
                )
            cur = conn.execute(
                "INSERT INTO bookings (apartment_id, client_id, check_in, check_out, total_price, notes) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    payload.apartment_id,
                    payload.client_id,
                    ci,
                    co,
                    payload.total_price,
                    payload.notes,
                ),
            )
            row = _row(conn, cur.lastrowid)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указаны несуществующие apartment_id или client_id",
        )
    return dict(row)


@router.patch("/{booking_id}")
def update_booking(
    booking_id: int,
    payload: BookingPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления"
        )
    if "status" in fields and fields["status"] not in BOOKING_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status должен быть одним из: {sorted(BOOKING_STATUSES)}",
        )
    for k in ("check_in", "check_out"):
        if k in fields and fields[k] is not None:
            fields[k] = fields[k].isoformat() if hasattr(fields[k], "isoformat") else fields[k]

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT apartment_id, check_in, check_out, status FROM bookings WHERE id = ?",
            (booking_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена"
            )

        new_apt = fields.get("apartment_id", existing["apartment_id"])
        new_ci = fields.get("check_in", existing["check_in"])
        new_co = fields.get("check_out", existing["check_out"])
        new_status = fields.get("status", existing["status"])

        if new_co <= new_ci:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="check_out должна быть позже check_in",
            )

        if new_status == "active":
            conflict = _find_conflict(conn, new_apt, new_ci, new_co, booking_id)
            if conflict is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Даты пересекаются с бронью #{conflict}",
                )

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [booking_id]
        try:
            conn.execute(f"UPDATE bookings SET {set_clause} WHERE id = ?", values)
        except sqlite3.IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Указаны несуществующие apartment_id или client_id",
            )
        row = _row(conn, booking_id)
    return dict(row)


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(booking_id: int, _: dict = Depends(require_role("owner"))):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    if cur.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена"
        )
    return None


@router.get("/calendar")
def bookings_calendar(
    from_: str = Query(..., alias="from", pattern=r"^\d{4}-\d{2}-\d{2}$"),
    to: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        apartments = conn.execute(
            "SELECT id, title, callsign FROM apartments ORDER BY id"
        ).fetchall()
        bookings = conn.execute(
            """
            SELECT b.id, b.apartment_id, b.check_in, b.check_out, b.status,
                   c.full_name AS client_name
            FROM bookings b
            JOIN clients c ON c.id = b.client_id
            WHERE b.status != 'cancelled'
              AND b.check_in < ? AND b.check_out > ?
            ORDER BY b.check_in
            """,
            (to, from_),
        ).fetchall()
    buckets = {
        a["id"]: {
            "apartment_id": a["id"],
            "apartment_title": a["title"],
            "apartment_callsign": a["callsign"],
            "bookings": [],
        }
        for a in apartments
    }
    for b in bookings:
        buckets[b["apartment_id"]]["bookings"].append(
            {
                "id": b["id"],
                "client_name": b["client_name"],
                "check_in": b["check_in"],
                "check_out": b["check_out"],
                "status": b["status"],
            }
        )
    return list(buckets.values())


@router.get("/{booking_id}")
def get_booking(
    booking_id: int, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        row = _row(conn, booking_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Бронь не найдена")
    return dict(row)
