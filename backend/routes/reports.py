from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query

from backend.auth import require_role
from backend.db import get_conn
from backend.lib.stats import aggregate_bookings_in_period

router = APIRouter(prefix="/reports", tags=["reports"])


def _period_bounds(period: str) -> tuple[date, date]:
    today = date.today()
    if period == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
    elif period == "quarter":
        q_start_month = ((today.month - 1) // 3) * 3 + 1
        start = date(today.year, q_start_month, 1)
        end_m = q_start_month + 3
        end_y = today.year + (1 if end_m > 12 else 0)
        end = date(end_y, ((end_m - 1) % 12) + 1, 1)
    elif period == "year":
        start = date(today.year, 1, 1)
        end = date(today.year + 1, 1, 1)
    else:  # month (default)
        start = date(today.year, today.month, 1)
        if today.month == 12:
            end = date(today.year + 1, 1, 1)
        else:
            end = date(today.year, today.month + 1, 1)
    return start, end


def _parse_d(s: str):
    return datetime.fromisoformat(s).date()


@router.get("")
def reports(
    period: str = Query("month", pattern=r"^(week|month|quarter|year)$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    p_start, p_end = _period_bounds(period)
    days = (p_end - p_start).days
    with get_conn() as conn:
        apts = conn.execute("SELECT id, title, callsign FROM apartments ORDER BY id").fetchall()
        all_bookings = conn.execute(
            "SELECT apartment_id, check_in, check_out, total_price, status FROM bookings "
            "WHERE check_out > ? AND check_in < ? AND status != 'cancelled'",
            (p_start.isoformat(), p_end.isoformat()),
        ).fetchall()
    by_apt: dict[int, list] = {}
    for b in all_bookings:
        by_apt.setdefault(b["apartment_id"], []).append(dict(b))

    total_nights = 0
    total_revenue = 0
    total_bookings = 0
    nights_sum_for_avg = 0
    per_apartment = []
    total_avail = len(apts) * days
    for a in apts:
        bookings = by_apt.get(a["id"], [])
        agg = aggregate_bookings_in_period(bookings, p_start, p_end)
        util = round(agg["nights"] / days, 4) if days else 0.0
        per_apartment.append(
            {
                "apartment_id": a["id"],
                "title": a["title"],
                "callsign": a["callsign"],
                "util": util,
                "nights": agg["nights"],
                "revenue": agg["revenue"],
            }
        )
        total_nights += agg["nights"]
        total_revenue += agg["revenue"]
        total_bookings += len(bookings)
        nights_sum_for_avg += sum(
            (_parse_d(b["check_out"]) - _parse_d(b["check_in"])).days
            for b in bookings
        )
    occupancy = round(total_nights / total_avail, 4) if total_avail else 0.0
    adr = round(total_revenue / total_nights) if total_nights else 0
    revpar = round(total_revenue / total_avail) if total_avail else 0
    avg_nights = round(nights_sum_for_avg / total_bookings, 2) if total_bookings else 0.0

    return {
        "period": period,
        "from": p_start.isoformat(),
        "to": p_end.isoformat(),
        "occupancy": occupancy,
        "adr": adr,
        "revpar": revpar,
        "avg_nights": avg_nights,
        "per_apartment": per_apartment,
    }
