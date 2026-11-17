from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import CategoryBudget
from app.schemas import BudgetLimit, BudgetStatus, Category
from app.services.analytics import category_budget_status
from app.services.dates import month_range

router = APIRouter()


@router.get("", response_model=list[BudgetStatus])
def list_budgets(
    db: DbSession,
    current_user: CurrentUser,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
):
    """Category limits with how much has been spent in the chosen month (default: this month)."""
    today = date.today()
    start, end = month_range(year or today.year, month or today.month)
    return category_budget_status(db, current_user.id, start, end)


@router.put("/{category}", response_model=BudgetStatus)
def set_budget(
    category: Category,
    payload: BudgetLimit,
    db: DbSession,
    current_user: CurrentUser,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
):
    """Create or replace the monthly limit for one category."""
    budget = db.scalar(
        select(CategoryBudget).where(
            CategoryBudget.owner_id == current_user.id,
            CategoryBudget.category == category.value,
        )
    )
    if budget is None:
        budget = CategoryBudget(
            owner_id=current_user.id, category=category.value, limit_amount=payload.limit_amount
        )
        db.add(budget)
    else:
        budget.limit_amount = payload.limit_amount
    db.commit()

    # Return the status for the requested month (defaults to the current month).
    today = date.today()
    start, end = month_range(year or today.year, month or today.month)
    for item in category_budget_status(db, current_user.id, start, end):
        if item.category == category.value:
            return item
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Budget could not be loaded")


@router.delete("/{category}", status_code=status.HTTP_204_NO_CONTENT)
def delete_budget(category: Category, db: DbSession, current_user: CurrentUser):
    budget = db.scalar(
        select(CategoryBudget).where(
            CategoryBudget.owner_id == current_user.id,
            CategoryBudget.category == category.value,
        )
    )
    if budget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No budget set for this category")
    db.delete(budget)
    db.commit()
