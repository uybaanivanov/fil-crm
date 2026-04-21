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
                "SELECT id, check_in, check_out, total_price, status, "
                "(SELECT full_name FROM clients WHERE clients.id = bookings.client_id) AS client_name "
                "FROM bookings "
                "WHERE check_out > ? AND check_in < ? AND status != 'cancelled'",
                (p_start.isoformat(), p_end.isoformat()),
            ).fetchall()
        ]
        expenses = [
            dict(r) for r in conn.execute(
                "SELECT id, amount, category, description, occurred_at FROM expenses "
                "WHERE substr(occurred_at, 1, 7) = ? ORDER BY occurred_at DESC",
                (ym,),
            ).fetchall()
        ]
    agg = aggregate_bookings_in_period(bookings, p_start, p_end)
    revenue = agg["revenue"]
    expenses_total = sum(e["amount"] for e in expenses)
    by_category: dict[str, int] = {}
    for e in expenses:
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]

    feed = []
    for b in bookings:
        feed.append(
            {
                "type": "income",
                "amount": b["total_price"],
                "label": f"Бронь {b['client_name'] or ''}".strip(),
                "dt": b["check_out"],
                "ref": {"booking_id": b["id"]},
            }
        )
    for e in expenses:
        feed.append(
            {
                "type": "expense",
                "amount": e["amount"],
                "label": f"{e['category']}"
                + (f" · {e['description']}" if e["description"] else ""),
                "dt": e["occurred_at"],
                "ref": {"expense_id": e["id"]},
            }
        )
    feed.sort(key=lambda x: x["dt"], reverse=True)

    return {
        "month": ym,
        "revenue": revenue,
        "expenses_total": expenses_total,
        "net": revenue - expenses_total,
        "by_category": by_category,
        "feed": feed,
    }
