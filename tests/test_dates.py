from datetime import date

import pytest

from app.services.dates import add_months, advance_due, days_in_month, month_range


def test_month_range_regular_and_december():
    assert month_range(2026, 5) == (date(2026, 5, 1), date(2026, 6, 1))
    assert month_range(2026, 12) == (date(2026, 12, 1), date(2027, 1, 1))


def test_days_in_month_handles_leap_years():
    assert days_in_month(2024, 2) == 29
    assert days_in_month(2026, 2) == 28


def test_add_months_clamps_to_month_length():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)


def test_add_months_crosses_year_boundaries_both_ways():
    assert add_months(date(2026, 11, 15), 3) == date(2027, 2, 15)
    assert add_months(date(2026, 2, 15), -3) == date(2025, 11, 15)


def test_anchor_day_prevents_drift():
    feb = add_months(date(2026, 1, 31), 1, anchor_day=31)
    assert feb == date(2026, 2, 28)
    assert add_months(feb, 1, anchor_day=31) == date(2026, 3, 31)


def test_advance_due_for_each_frequency():
    assert advance_due(date(2026, 3, 1), "weekly", 1) == date(2026, 3, 8)
    assert advance_due(date(2026, 3, 15), "monthly", 15) == date(2026, 4, 15)
    assert advance_due(date(2026, 3, 15), "yearly", 15) == date(2027, 3, 15)


def test_advance_due_leap_day_yearly():
    assert advance_due(date(2024, 2, 29), "yearly", 29) == date(2025, 2, 28)


def test_advance_due_rejects_unknown_frequency():
    with pytest.raises(ValueError):
        advance_due(date(2026, 1, 1), "daily", 1)
