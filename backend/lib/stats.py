from calendar import monthrange
from datetime import date, datetime


def month_bounds(month: str) -> tuple[date, date]:
    """'2026-04' → (date(2026,4,1), date(2026,5,1))"""
    y, m = (int(x) for x in month.split("-"))
    start = date(y, m, 1)
    if m == 12:
        end = date(y + 1, 1, 1)
    else:
        end = date(y, m + 1, 1)
    return start, end


def parse_date(d: str | date) -> date:
    if isinstance(d, date):
        return d
    return datetime.fromisoformat(d).date()


def overlap_nights(ci: str | date, co: str | date, p_start: date, p_end: date) -> int:
    ci_d, co_d = parse_date(ci), parse_date(co)
    start = max(ci_d, p_start)
    end = min(co_d, p_end)
    delta = (end - start).days
    return max(0, delta)


def aggregate_bookings_in_period(bookings, p_start: date, p_end: date) -> dict:
    nights = 0
    revenue = 0
    for b in bookings:
        if b.get("status") == "cancelled":
            continue
        total_nights_full = (parse_date(b["check_out"]) - parse_date(b["check_in"])).days
        if total_nights_full <= 0:
            continue
        night_in_period = overlap_nights(
            b["check_in"], b["check_out"], p_start, p_end
        )
        if night_in_period == 0:
            continue
        nights += night_in_period
        # Пропорциональная выручка
        revenue += round(b["total_price"] * night_in_period / total_nights_full)
    adr = round(revenue / nights) if nights else 0
    return {"nights": nights, "revenue": revenue, "adr": adr}


def days_in_month(month: str) -> int:
    y, m = (int(x) for x in month.split("-"))
    return monthrange(y, m)[1]
