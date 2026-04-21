from datetime import date

from fastapi import APIRouter, Depends

from backend.auth import require_role
from backend.db import get_conn
from backend.lib.stats import (
    aggregate_bookings_in_period,
    days_in_month,
    month_bounds,
    parse_date,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _prev_month(ym: str) -> str:
    y, m = (int(x) for x in ym.split("-"))
    if m == 1:
        return f"{y - 1}-12"
    return f"{y}-{m - 1:02d}"


@router.get("/summary")
def summary(_: dict = Depends(require_role("owner", "admin"))):
    today = date.today()
    ym = today.strftime("%Y-%m")
    p_start, p_end = month_bounds(ym)
    prev_start, prev_end = month_bounds(_prev_month(ym))
    with get_conn() as conn:
        apt_total = conn.execute("SELECT COUNT(*) FROM apartments").fetchone()[0]
        occupied = conn.execute(
            "SELECT COUNT(DISTINCT apartment_id) FROM bookings "
            "WHERE status='active' AND check_in <= ? AND check_out > ?",
            (today.isoformat(), today.isoformat()),
        ).fetchone()[0]
        rows = conn.execute(
            "SELECT check_in, check_out, total_price, status FROM bookings "
            "WHERE check_out > ? AND check_in < ?",
            (prev_start.isoformat(), p_end.isoformat()),
        ).fetchall()
        bookings = [dict(r) for r in rows]
        events_rows = conn.execute(
            """
            SELECT b.id, b.check_in, b.check_out, b.total_price, b.status,
                   c.full_name AS client_name, a.title AS apartment_title, a.address AS apartment_address
            FROM bookings b
            JOIN clients c ON c.id = b.client_id
            JOIN apartments a ON a.id = b.apartment_id
            WHERE b.status != 'cancelled'
              AND (b.check_in = ? OR b.check_out = ?)
            ORDER BY b.check_in
            """,
            (today.isoformat(), today.isoformat()),
        ).fetchall()

    revenue_mtd = aggregate_bookings_in_period(bookings, p_start, p_end)["revenue"]
    revenue_prev = aggregate_bookings_in_period(bookings, prev_start, prev_end)["revenue"]

    dim = days_in_month(ym)
    daily = [0] * dim
    for b in bookings:
        if b["status"] == "cancelled":
            continue
        ci, co = parse_date(b["check_in"]), parse_date(b["check_out"])
        nights_full = (co - ci).days
        if nights_full <= 0:
            continue
        per_night = b["total_price"] / nights_full
        d = ci
        while d < co:
            if p_start <= d < p_end:
                daily[d.day - 1] += round(per_night)
            d = date.fromordinal(d.toordinal() + 1)

    today_events = []
    for r in events_rows:
        if r["check_in"] == today.isoformat():
            today_events.append(
                {
                    "booking_id": r["id"],
                    "kind": "check_in",
                    "time": "14:00",
                    "client_name": r["client_name"],
                    "apartment_title": r["apartment_title"],
                    "apartment_address": r["apartment_address"],
                    "total_price": r["total_price"],
                    "status": r["status"],
                }
            )
        if r["check_out"] == today.isoformat():
            today_events.append(
                {
                    "booking_id": r["id"],
                    "kind": "check_out",
                    "time": "12:00",
                    "client_name": r["client_name"],
                    "apartment_title": r["apartment_title"],
                    "apartment_address": r["apartment_address"],
                    "total_price": r["total_price"],
                    "status": r["status"],
                }
            )

    return {
        "occupancy": {"occupied": occupied, "total": apt_total},
        "revenue_mtd": revenue_mtd,
        "revenue_prev_month": revenue_prev,
        "daily_series": daily,
        "today_events": today_events,
        "month": ym,
    }
