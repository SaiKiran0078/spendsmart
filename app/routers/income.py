from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Income
from app.schemas import IncomeCreate, IncomeOut, IncomeUpdate

router = APIRouter()


def _get_owned_income(db, income_id: int, user_id: int) -> Income:
    income = db.get(Income, income_id)
    if income is None or income.owner_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Income not found")
    return income


@router.get("", response_model=list[IncomeOut])
def list_income(
    db: DbSession,
    current_user: CurrentUser,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = Query(default=None, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "start_date must be on or before end_date",
        )
    stmt = select(Income).where(Income.owner_id == current_user.id)
    if start_date:
        stmt = stmt.where(Income.received_on >= start_date)
    if end_date:
        stmt = stmt.where(Income.received_on <= end_date)
    if search:
        stmt = stmt.where(Income.source.ilike(f"%{search}%"))
    stmt = stmt.order_by(Income.received_on.desc(), Income.id.desc()).offset(skip).limit(limit)
    return db.scalars(stmt).all()


@router.post("", response_model=IncomeOut, status_code=status.HTTP_201_CREATED)
def create_income(payload: IncomeCreate, db: DbSession, current_user: CurrentUser):
    income = Income(**payload.model_dump(), owner_id=current_user.id)
    db.add(income)
    db.commit()
    db.refresh(income)
    return income


@router.put("/{income_id}", response_model=IncomeOut)
def update_income(income_id: int, payload: IncomeUpdate, db: DbSession, current_user: CurrentUser):
    income = _get_owned_income(db, income_id, current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is None and field in ("source", "amount", "received_on"):
            continue  # required columns: ignore explicit nulls
        setattr(income, field, value)
    db.commit()
    db.refresh(income)
    return income


@router.delete("/{income_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_income(income_id: int, db: DbSession, current_user: CurrentUser):
    income = _get_owned_income(db, income_id, current_user.id)
    db.delete(income)
    db.commit()
