from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.deps import CurrentUser, DbSession
from app.models import Expense
from app.schemas import CategoryTotal, MonthlySummary

router = APIRouter()


def month_range(year: int, month: int) -> tuple[date, date]:
    """Return (first day of month, first day of next month)."""
    start = date(year, month, 1)
    end = date(year + (month == 12), (month % 12) + 1, 1)
    return start, end


@router.get("", response_model=MonthlySummary)
def monthly_summary(
    db: DbSession,
    current_user: CurrentUser,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
):
    today = date.today()
    year = year or today.year
    month = month or today.month
    start, end = month_range(year, month)

    in_month = (
        Expense.owner_id == current_user.id,
        Expense.spent_on >= start,
        Expense.spent_on < end,
    )
    rows = db.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(*in_month)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
    ).all()
    count = db.scalar(select(func.count(Expense.id)).where(*in_month)) or 0

    by_category = [CategoryTotal(category=c, total=round(t, 2)) for c, t in rows]
    total = round(sum(item.total for item in by_category), 2)
    budget = current_user.monthly_budget
    used = round(total / budget * 100, 1) if budget > 0 else 0.0

    return MonthlySummary(
        year=year,
        month=month,
        total_spent=total,
        expense_count=count,
        monthly_budget=budget,
        remaining=round(budget - total, 2),
        budget_used_percent=used,
        by_category=by_category,
    )
