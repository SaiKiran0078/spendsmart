import csv
import io
from datetime import date

from fastapi import APIRouter, HTTPException, Query, Response, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Expense
from app.schemas import Category, ExpenseCreate, ExpenseOut, ExpenseUpdate

router = APIRouter()


def _get_owned_expense(db, expense_id: int, user_id: int) -> Expense:
    """Fetch an expense only if it belongs to the user (else 404, never leak existence)."""
    expense = db.get(Expense, expense_id)
    if expense is None or expense.owner_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Expense not found")
    return expense


def _csv_safe(value: object) -> str:
    """Neutralize spreadsheet formula injection while preserving whitespace."""
    text = "" if value is None else str(value)

    # Detect formulas even when preceded by whitespace or control characters.
    probe = text.lstrip(" \t\r\n\x00")

    if probe[:1] in ("=", "+", "-", "@"):
        return "'" + text

    return text


@router.get("", response_model=list[ExpenseOut])
def list_expenses(
    db: DbSession,
    current_user: CurrentUser,
    category: Category | None = None,
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
    stmt = select(Expense).where(Expense.owner_id == current_user.id)
    if category:
        stmt = stmt.where(Expense.category == category.value)
    if start_date:
        stmt = stmt.where(Expense.spent_on >= start_date)
    if end_date:
        stmt = stmt.where(Expense.spent_on <= end_date)
    if search:
        stmt = stmt.where(Expense.title.ilike(f"%{search}%"))
    stmt = stmt.order_by(Expense.spent_on.desc(), Expense.id.desc()).offset(skip).limit(limit)
    return db.scalars(stmt).all()


@router.post("", response_model=ExpenseOut, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: DbSession, current_user: CurrentUser):
    data = payload.model_dump()
    data["category"] = payload.category.value
    expense = Expense(**data, owner_id=current_user.id)
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/export/csv")
def export_csv(db: DbSession, current_user: CurrentUser):
    rows = db.scalars(
        select(Expense).where(Expense.owner_id == current_user.id).order_by(Expense.spent_on)
    ).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "date", "title", "category", "amount", "note"])
    for e in rows:
        writer.writerow(
            [e.id, e.spent_on.isoformat(), _csv_safe(e.title), e.category, e.amount,
             _csv_safe(e.note)]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="expenses.csv"'},
    )


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: int, db: DbSession, current_user: CurrentUser):
    return _get_owned_expense(db, expense_id, current_user.id)


@router.put("/{expense_id}", response_model=ExpenseOut)
def update_expense(
    expense_id: int, payload: ExpenseUpdate, db: DbSession, current_user: CurrentUser
):
    expense = _get_owned_expense(db, expense_id, current_user.id)
    changes = payload.model_dump(exclude_unset=True)
    if "category" in changes and changes["category"] is not None:
        changes["category"] = payload.category.value
    for field, value in changes.items():
        if value is None and field in ("title", "amount", "category", "spent_on"):
            continue  # these columns are required; ignore explicit nulls
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_expense(expense_id: int, db: DbSession, current_user: CurrentUser):
    expense = _get_owned_expense(db, expense_id, current_user.id)
    db.delete(expense)
    db.commit()
