from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.auth import require_role
from backend.db import get_conn

router = APIRouter(prefix="/apartments", tags=["apartments"])


class ApartmentIn(BaseModel):
    title: str = Field(min_length=1)
    address: str = Field(min_length=1)
    price_per_night: int = Field(gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None


class ApartmentPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    price_per_night: int | None = Field(default=None, gt=0)
    rooms: str | None = None
    area_m2: int | None = Field(default=None, gt=0)
    floor: str | None = None
    district: str | None = None
    cover_url: str | None = None
    source: str | None = None
    source_url: str | None = None


SELECT_FIELDS = (
    "id, title, address, price_per_night, needs_cleaning, "
    "cover_url, rooms, area_m2, floor, district, source, source_url, created_at"
)


def _row(conn, apt_id: int):
    return conn.execute(
        f"SELECT {SELECT_FIELDS} FROM apartments WHERE id = ?", (apt_id,)
    ).fetchone()


@router.get("")
def list_apartments(
    with_stats: int = Query(0),
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {SELECT_FIELDS} FROM apartments ORDER BY id"
        ).fetchall()
        apts = [dict(r) for r in rows]
        if not with_stats:
            return apts
        from datetime import date

        from backend.lib.stats import (
            aggregate_bookings_in_period,
            days_in_month,
            month_bounds,
        )

        month = month or date.today().strftime("%Y-%m")
        p_start, p_end = month_bounds(month)
        dim = days_in_month(month)
        today = date.today().isoformat()
        for a in apts:
            bookings = conn.execute(
                "SELECT check_in, check_out, total_price, status FROM bookings WHERE apartment_id = ?",
                (a["id"],),
            ).fetchall()
            bookings = [dict(b) for b in bookings]
            agg = aggregate_bookings_in_period(bookings, p_start, p_end)
            a["nights"] = agg["nights"]
            a["revenue"] = agg["revenue"]
            a["adr"] = agg["adr"]
            a["utilization"] = round(agg["nights"] / dim, 4) if dim else 0.0
            # Статус: если есть бронь где check_in<=today<check_out и status='active' — occupied;
            # иначе если needs_cleaning=1 — needs_cleaning; иначе free.
            is_occupied = any(
                b["status"] == "active"
                and b["check_in"] <= today < b["check_out"]
                for b in bookings
            )
            if is_occupied:
                a["status"] = "occupied"
            elif a["needs_cleaning"]:
                a["status"] = "needs_cleaning"
            else:
                a["status"] = "free"
    return apts


@router.get("/cleaning")
def list_apartments_needing_cleaning(
    _: dict = Depends(require_role("owner", "admin", "maid")),
):
    with get_conn() as conn:
        rows = conn.execute(
            f"SELECT {SELECT_FIELDS} FROM apartments WHERE needs_cleaning = 1 ORDER BY id"
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/{apt_id}")
def get_apartment(
    apt_id: int, _: dict = Depends(require_role("owner", "admin"))
):
    with get_conn() as conn:
        row = _row(conn, apt_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена")
    return dict(row)


@router.get("/{apt_id}/stats")
def apartment_stats(
    apt_id: int,
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    from datetime import date

    from backend.lib.stats import (
        aggregate_bookings_in_period,
        days_in_month,
        month_bounds,
    )

    month = month or date.today().strftime("%Y-%m")
    p_start, p_end = month_bounds(month)
    dim = days_in_month(month)
    with get_conn() as conn:
        if _row(conn, apt_id) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена")
        rows = conn.execute(
            "SELECT check_in, check_out, total_price, status FROM bookings WHERE apartment_id = ?",
            (apt_id,),
        ).fetchall()
    bookings = [dict(r) for r in rows]
    agg = aggregate_bookings_in_period(bookings, p_start, p_end)
    agg["utilization"] = round(agg["nights"] / dim, 4) if dim else 0.0
    return agg


@router.post("", status_code=status.HTTP_201_CREATED)
def create_apartment(
    payload: ApartmentIn, _: dict = Depends(require_role("owner", "admin"))
):
    import sqlite3

    fields = payload.model_dump()
    cols = ", ".join(fields.keys())
    placeholders = ", ".join("?" * len(fields))
    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO apartments ({cols}) VALUES ({placeholders})",
                list(fields.values()),
            )
            row = _row(conn, cur.lastrowid)
    except sqlite3.IntegrityError as e:
        msg = str(e)
        if "apartments_source_url_uniq" in msg or "apartments.source_url" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Квартира с такой ссылкой уже есть",
            )
        raise
    return dict(row)


@router.patch("/{apt_id}")
def update_apartment(
    apt_id: int,
    payload: ApartmentPatch,
    _: dict = Depends(require_role("owner", "admin")),
):
    fields = payload.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Нет полей для обновления"
        )
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [apt_id]
    with get_conn() as conn:
        cur = conn.execute(
            f"UPDATE apartments SET {set_clause} WHERE id = ?", values
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)


@router.delete("/{apt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_apartment(apt_id: int, _: dict = Depends(require_role("owner", "admin"))):
    import sqlite3

    try:
        with get_conn() as conn:
            cur = conn.execute("DELETE FROM apartments WHERE id = ?", (apt_id,))
            if cur.rowcount == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
                )
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить квартиру с привязанными бронями",
        )
    return None


@router.post("/{apt_id}/mark-dirty")
def mark_dirty(apt_id: int, _: dict = Depends(require_role("owner", "admin"))):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 1 WHERE id = ?", (apt_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)


@router.post("/{apt_id}/mark-clean")
def mark_clean(apt_id: int, _: dict = Depends(require_role("owner", "admin", "maid"))):
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE apartments SET needs_cleaning = 0 WHERE id = ?", (apt_id,)
        )
        if cur.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Квартира не найдена"
            )
        row = _row(conn, apt_id)
    return dict(row)
