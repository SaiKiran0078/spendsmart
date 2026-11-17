from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CategoryBudget, Expense, Income, User
from app.schemas import (
    BudgetStatus,
    CategoryTotal,
    DailyTotal,
    ExpenseOut,
    MonthlySummary,
    TrendPoint,
)
from app.services.dates import add_months, days_in_month, month_range

WARNING_THRESHOLD = 80.0
OVER_THRESHOLD = 100.0


def _sum_between(db: Session, amount, date_col, owner_col, user_id: int, start: date, end: date):
    stmt = select(func.coalesce(func.sum(amount), 0.0)).where(
        owner_col == user_id, date_col >= start, date_col < end
    )
    return float(db.scalar(stmt) or 0.0)


def expenses_between(db: Session, user_id: int, start: date, end: date) -> float:
    return _sum_between(db, Expense.amount, Expense.spent_on, Expense.owner_id, user_id, start, end)


def income_between(db: Session, user_id: int, start: date, end: date) -> float:
    return _sum_between(
        db, Income.amount, Income.received_on, Income.owner_id, user_id, start, end
    )


def category_budget_status(
    db: Session, user_id: int, start: date, end: date
) -> list[BudgetStatus]:
    """Spent vs. limit for every category that has a limit, worst first."""
    limits = db.scalars(select(CategoryBudget).where(CategoryBudget.owner_id == user_id)).all()
    if not limits:
        return []
    spent_rows = db.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(Expense.owner_id == user_id, Expense.spent_on >= start, Expense.spent_on < end)
        .group_by(Expense.category)
    ).all()
    spent_by_category = {category: float(total) for category, total in spent_rows}

    result = []
    for budget in limits:
        spent = round(spent_by_category.get(budget.category, 0.0), 2)
        percent = round(spent / budget.limit_amount * 100, 1) if budget.limit_amount > 0 else 0.0
        if percent > OVER_THRESHOLD:
            status = "over"
        elif percent >= WARNING_THRESHOLD:
            status = "warning"
        else:
            status = "ok"
        result.append(
            BudgetStatus(
                category=budget.category,
                limit_amount=budget.limit_amount,
                spent=spent,
                remaining=round(budget.limit_amount - spent, 2),
                percent_used=percent,
                status=status,
            )
        )
    return sorted(result, key=lambda item: item.percent_used, reverse=True)


def build_insights(
    *,
    total: float,
    count: int,
    income: float,
    budget: float,
    budget_used: float,
    change: float | None,
    projected: float | None,
    savings_rate: float | None,
    top_category: CategoryTotal | None,
    alerts: list[BudgetStatus],
    days_left: int | None,
) -> list[str]:
    """Turn the numbers into short, human-friendly observations."""
    if count == 0 and income == 0:
        return ["Add your first expense or income to start seeing insights."]

    tips: list[str] = []

    if budget > 0:
        if budget_used >= OVER_THRESHOLD:
            tips.append(f"You've used {budget_used:g}% of your monthly budget.")
        elif budget_used >= WARNING_THRESHOLD:
            suffix = f" with {days_left} days left" if days_left else ""
            tips.append(f"You've used {budget_used:g}% of your monthly budget{suffix}.")

    if change is not None:
        if change >= 10:
            tips.append(f"Spending is up {change:g}% compared with last month.")
        elif change <= -10:
            tips.append(f"Nice! Spending is down {abs(change):g}% compared with last month.")

    if top_category is not None and total > 0:
        share = round(top_category.total / total * 100)
        tips.append(f"{top_category.category} is your biggest category at {share}% of spending.")

    if projected is not None and budget > 0 and projected > budget:
        tips.append(
            f"At this pace you'll spend about {round(projected / budget * 100)}% "
            "of your budget by month end."
        )

    if savings_rate is not None:
        if savings_rate < 0:
            tips.append("You've spent more than you earned this month.")
        elif savings_rate >= 20:
            tips.append(f"You're saving {savings_rate:g}% of your income. Great work!")
        else:
            tips.append(f"You're saving {savings_rate:g}% of your income. Aim for 20% or more.")

    for alert in alerts[:2]:
        if alert.status == "over":
            tips.append(f"{alert.category} is over its budget ({alert.percent_used:g}% used).")
        else:
            tips.append(f"{alert.category} is at {alert.percent_used:g}% of its budget.")

    return tips[:6] or ["You're on track. Keep logging expenses to unlock more insights."]


def build_summary(db: Session, user: User, year: int, month: int) -> MonthlySummary:
    today = date.today()
    start, end = month_range(year, month)
    prev_start = add_months(start, -1)

    in_month = (Expense.owner_id == user.id, Expense.spent_on >= start, Expense.spent_on < end)

    category_rows = db.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(*in_month)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
    ).all()
    count = db.scalar(select(func.count(Expense.id)).where(*in_month)) or 0

    by_category = [CategoryTotal(category=c, total=round(t, 2)) for c, t in category_rows]
    total = round(sum(item.total for item in by_category), 2)
    budget = user.monthly_budget
    used = round(total / budget * 100, 1) if budget > 0 else 0.0

    income = round(income_between(db, user.id, start, end), 2)
    savings_rate = round((income - total) / income * 100, 1) if income > 0 else None

    previous = round(expenses_between(db, user.id, prev_start, start), 2)
    change = round((total - previous) / previous * 100, 1) if previous > 0 else None

    is_current_month = (year, month) == (today.year, today.month)
    projected = (
        round(total / today.day * days_in_month(year, month), 2)
        if is_current_month and total > 0
        else None
    )
    days_left = days_in_month(year, month) - today.day if is_current_month else None

    daily_rows = db.execute(
        select(Expense.spent_on, func.sum(Expense.amount))
        .where(*in_month)
        .group_by(Expense.spent_on)
    ).all()
    daily_map = {day: float(amount) for day, amount in daily_rows}
    daily = []
    for day_number in range(1, days_in_month(year, month) + 1):
        day = date(year, month, day_number)
        daily.append(DailyTotal(date=day, total=round(daily_map.get(day, 0.0), 2)))

    top = db.scalars(
        select(Expense).where(*in_month).order_by(Expense.amount.desc(), Expense.id).limit(5)
    ).all()

    alerts = [
        item
        for item in category_budget_status(db, user.id, start, end)
        if item.status != "ok"
    ]

    insights = build_insights(
        total=total,
        count=count,
        income=income,
        budget=budget,
        budget_used=used,
        change=change,
        projected=projected,
        savings_rate=savings_rate,
        top_category=by_category[0] if by_category else None,
        alerts=alerts,
        days_left=days_left,
    )

    return MonthlySummary(
        year=year,
        month=month,
        total_spent=total,
        expense_count=count,
        monthly_budget=budget,
        remaining=round(budget - total, 2),
        budget_used_percent=used,
        by_category=by_category,
        total_income=income,
        net_savings=round(income - total, 2),
        savings_rate_percent=savings_rate,
        previous_month_spent=previous,
        change_vs_previous_percent=change,
        projected_spend=projected,
        daily=daily,
        top_expenses=[ExpenseOut.model_validate(e) for e in top],
        budget_alerts=alerts,
        insights=insights,
    )


def build_trend(db: Session, user_id: int, year: int, month: int, months: int) -> list[TrendPoint]:
    """Income vs. expenses for the last `months` months, oldest first."""
    anchor = date(year, month, 1)
    points = []
    for offset in range(months - 1, -1, -1):
        start = add_months(anchor, -offset)
        _, end = month_range(start.year, start.month)
        income = round(income_between(db, user_id, start, end), 2)
        spent = round(expenses_between(db, user_id, start, end), 2)
        points.append(
            TrendPoint(
                year=start.year,
                month=start.month,
                income=income,
                expenses=spent,
                savings=round(income - spent, 2),
            )
        )
    return points
