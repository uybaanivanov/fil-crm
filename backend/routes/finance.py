from datetime import date

from fastapi import APIRouter, Depends, Query

from backend.auth import require_role
from backend.db import get_conn
from backend.lib.stats import aggregate_bookings_in_period, month_bounds

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/summary")
def summary(
    month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
    _: dict = Depends(require_role("owner", "admin")),
):
    ym = month or date.today().strftime("%Y-%m")
    p_start, p_end = month_bounds(ym)
    with get_conn() as conn:
        bookings = [
            dict(r) for r in conn.execute(
                "SELECT id, apartment_id, check_in, check_out, total_price, status, "
                "(SELECT full_name FROM clients WHERE clients.id = bookings.client_id) AS client_name "
                "FROM bookings "
                "WHERE check_out > ? AND check_in < ? AND status != 'cancelled'",
                (p_start.isoformat(), p_end.isoformat()),
            ).fetchall()
        ]
        expenses = [
            dict(r) for r in conn.execute(
                "SELECT e.id, e.amount, e.category, e.description, e.occurred_at, "
                "e.apartment_id, e.source, a.title AS apartment_title, a.callsign AS apartment_callsign "
                "FROM expenses e LEFT JOIN apartments a ON a.id = e.apartment_id "
                "WHERE substr(e.occurred_at, 1, 7) = ? ORDER BY e.occurred_at DESC",
                (ym,),
            ).fetchall()
        ]
        apartments = [
            dict(r) for r in conn.execute(
                "SELECT id, title, callsign FROM apartments"
            ).fetchall()
        ]
    agg = aggregate_bookings_in_period(bookings, p_start, p_end)
    revenue = agg["revenue"]
    expenses_total = sum(e["amount"] for e in expenses)
    general_expenses_total = sum(e["amount"] for e in expenses if e["apartment_id"] is None)
    by_category: dict[str, int] = {}
    for e in expenses:
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]

    by_apt_map: dict[int, dict] = {}
    for a in apartments:
        by_apt_map[a["id"]] = {
            "apartment_id": a["id"], "title": a["title"], "callsign": a["callsign"],
            "revenue": 0, "expenses_total": 0, "net": 0,
        }
    for apt_id, row in by_apt_map.items():
        apt_bookings = [b for b in bookings if b["apartment_id"] == apt_id]
        apt_agg = aggregate_bookings_in_period(apt_bookings, p_start, p_end)
        row["revenue"] = apt_agg["revenue"]
    for e in expenses:
        if e["apartment_id"] is not None and e["apartment_id"] in by_apt_map:
            by_apt_map[e["apartment_id"]]["expenses_total"] += e["amount"]
    for row in by_apt_map.values():
        row["net"] = row["revenue"] - row["expenses_total"]
    by_apartment = sorted(by_apt_map.values(), key=lambda x: x["net"], reverse=True)

    feed = []
    for b in bookings:
        feed.append({
            "type": "income",
            "amount": b["total_price"],
            "label": f"Бронь {b['client_name'] or ''}".strip(),
            "dt": b["check_out"],
            "ref": {"booking_id": b["id"]},
        })
    for e in expenses:
        feed.append({
            "type": "expense",
            "amount": e["amount"],
            "label": f"{e['category']}"
                + (f" · {e['description']}" if e["description"] else ""),
            "dt": e["occurred_at"],
            "ref": {"expense_id": e["id"]},
            "apartment_id": e["apartment_id"],
            "apartment_title": e["apartment_title"],
            "apartment_callsign": e["apartment_callsign"],
            "source": e["source"],
        })
    feed.sort(key=lambda x: x["dt"], reverse=True)

    return {
        "month": ym,
        "revenue": revenue,
        "expenses_total": expenses_total,
        "general_expenses_total": general_expenses_total,
        "net": revenue - expenses_total,
        "by_category": by_category,
        "by_apartment": by_apartment,
        "feed": feed,
    }
