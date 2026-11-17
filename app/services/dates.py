"""Pure date helpers (no database or framework imports, so they are trivial to test)."""

import calendar
from datetime import date, timedelta


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def month_range(year: int, month: int) -> tuple[date, date]:
    """Return (first day of month, first day of the next month)."""
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)
    return start, end


def add_months(value: date, months: int, anchor_day: int | None = None) -> date:
    """Add (or subtract) whole months, clamping the day to the target month's length.

    `anchor_day` lets a bill that started on the 31st come back to the 31st
    in long months instead of drifting to the 28th forever.
    """
    index = value.year * 12 + (value.month - 1) + months
    year, month_index = divmod(index, 12)
    month = month_index + 1
    day = min(anchor_day or value.day, days_in_month(year, month))
    return date(year, month, day)


def advance_due(due: date, frequency: str, anchor_day: int) -> date:
    """Return the next due date after `due` for a recurring item."""
    if frequency == "weekly":
        return due + timedelta(days=7)
    if frequency == "monthly":
        return add_months(due, 1, anchor_day)
    if frequency == "yearly":
        return add_months(due, 12, anchor_day)
    raise ValueError(f"Unknown frequency: {frequency}")
