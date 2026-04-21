from datetime import date

from backend.lib.stats import (
    month_bounds,
    overlap_nights,
    aggregate_bookings_in_period,
)


def test_month_bounds_april():
    ci, co = month_bounds("2026-04")
    assert ci == date(2026, 4, 1)
    assert co == date(2026, 5, 1)


def test_month_bounds_december():
    ci, co = month_bounds("2026-12")
    assert ci == date(2026, 12, 1)
    assert co == date(2027, 1, 1)


def test_overlap_full_inside():
    # booking 10.04 → 13.04, period апрель
    n = overlap_nights(
        date(2026, 4, 10), date(2026, 4, 13),
        date(2026, 4, 1), date(2026, 5, 1),
    )
    assert n == 3


def test_overlap_partial_before_period():
    # booking 30.03 → 03.04, period апрель
    n = overlap_nights(
        date(2026, 3, 30), date(2026, 4, 3),
        date(2026, 4, 1), date(2026, 5, 1),
    )
    assert n == 2


def test_overlap_no_intersection():
    n = overlap_nights(
        date(2026, 3, 1), date(2026, 3, 31),
        date(2026, 4, 1), date(2026, 5, 1),
    )
    assert n == 0


def test_aggregate_bookings_basic():
    # Одна бронь 3 ночи, одна 2 ночи — все в апреле
    bookings = [
        {"check_in": "2026-04-10", "check_out": "2026-04-13", "total_price": 12840, "status": "active"},
        {"check_in": "2026-04-20", "check_out": "2026-04-22", "total_price": 9600, "status": "completed"},
    ]
    agg = aggregate_bookings_in_period(bookings, date(2026, 4, 1), date(2026, 5, 1))
    assert agg["nights"] == 5
    assert agg["revenue"] == 12840 + 9600
    assert agg["adr"] == round((12840 + 9600) / 5)


def test_aggregate_skips_cancelled():
    bookings = [
        {"check_in": "2026-04-10", "check_out": "2026-04-13", "total_price": 12840, "status": "cancelled"},
    ]
    agg = aggregate_bookings_in_period(bookings, date(2026, 4, 1), date(2026, 5, 1))
    assert agg["nights"] == 0
    assert agg["revenue"] == 0
    assert agg["adr"] == 0
