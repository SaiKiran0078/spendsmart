from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.deps import CurrentUser, DbSession
from app.schemas import MonthlySummary, TrendPoint
from app.services.analytics import build_summary, build_trend
from app.services.recurring import process_due

router = APIRouter()


@router.get("", response_model=MonthlySummary)
def monthly_summary(
    db: DbSession,
    current_user: CurrentUser,
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
):
    """Totals, comparisons, daily spending, top expenses and plain-English insights."""
    if (year is None) != (month is None):
        raise HTTPException(
            status_code=422,
            detail="year and month must be supplied together",
        )
    today = date.today()
    process_due(db, current_user.id)  # make sure due recurring bills are counted
    return build_summary(db, current_user, year or today.year, month or today.month)


@router.get("/trend", response_model=list[TrendPoint])
def trend(
    db: DbSession,
    current_user: CurrentUser,
    months: int = Query(default=6, ge=2, le=12),
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
):
    """Income vs. expenses for the last N months, ending at the chosen month."""
    if (year is None) != (month is None):
        raise HTTPException(
            status_code=422,
            detail="year and month must be supplied together",
        )
    today = date.today()
    return build_trend(db, current_user.id, year or today.year, month or today.month, months)
