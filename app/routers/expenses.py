import csv
import io
import re
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import Expense
from app.schemas import Category, ExpenseCreate, ExpenseOut, ExpenseUpdate, ImportResult

router = APIRouter()

MAX_IMPORT_BYTES = 1_000_000
MAX_IMPORT_ROWS = 1000
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y")
FORMULA_PREFIXES = ("=", "+", "-", "@")


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

    if probe[:1] in FORMULA_PREFIXES:
        return "'" + text

    return text


def _csv_unsafe(value: str) -> str:
    """Undo `_csv_safe` so an exported file can be imported again unchanged."""
    if value.startswith("'") and value[1:].lstrip(" \t\r\n\x00")[:1] in FORMULA_PREFIXES:
        return value[1:]
    return value


def _parse_amount(raw: str) -> float:
    cleaned = re.sub(r"[^\d.\-]", "", raw or "")
    if not cleaned:
        raise ValueError("amount is missing")
    return float(cleaned)


def _parse_date(raw: str | None) -> date:
    raw = (raw or "").strip()
    if not raw:
        return date.today()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"unrecognised date '{raw}'")


def _parse_category(raw: str | None) -> Category:
    wanted = (raw or "").strip().lower()
    for category in Category:
        if category.value.lower() == wanted:
            return category
    return Category.other


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


@router.post("/import/csv", response_model=ImportResult)
def import_csv(
    file: Annotated[UploadFile, File(description="CSV with title, amount, category, date, note")],
    db: DbSession,
    current_user: CurrentUser,
):
    """Bulk-add expenses from a CSV file (for example your bank export or a previous export).

    Required columns: `title`, `amount`. Optional: `category`, `date`, `note`.
    Rows that cannot be parsed are skipped and reported back.
    """
    raw = file.file.read(MAX_IMPORT_BYTES + 1)
    if len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CSV file is too large")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV must be UTF-8 encoded") from None

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "CSV file is empty")
    reader.fieldnames = [(name or "").strip().lower() for name in reader.fieldnames]
    if "title" not in reader.fieldnames or "amount" not in reader.fieldnames:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "CSV needs at least 'title' and 'amount' columns"
        )

    imported, skipped, errors = 0, 0, []
    for line_number, row in enumerate(reader, start=2):
        if line_number - 1 > MAX_IMPORT_ROWS:
            errors.append(f"Stopped after {MAX_IMPORT_ROWS} rows")
            break
        try:
            payload = ExpenseCreate(
                title=_csv_unsafe(row.get("title") or ""),
                amount=_parse_amount(row.get("amount") or ""),
                category=_parse_category(row.get("category")),
                note=_csv_unsafe(row.get("note") or "") or None,
                spent_on=_parse_date(row.get("date") or row.get("spent_on")),
            )
        except (ValueError, ValidationError) as exc:
            skipped += 1
            if len(errors) < 10:
                reason = exc.errors()[0]["msg"] if isinstance(exc, ValidationError) else str(exc)
                errors.append(f"Line {line_number}: {reason}")
            continue
        data = payload.model_dump()
        data["category"] = payload.category.value
        db.add(Expense(**data, owner_id=current_user.id))
        imported += 1

    db.commit()
    return ImportResult(imported=imported, skipped=skipped, errors=errors)


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
