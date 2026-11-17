from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, DbSession
from app.models import RecurringExpense
from app.schemas import ProcessResult, RecurringCreate, RecurringOut, RecurringUpdate
from app.services.recurring import process_due

router = APIRouter()


def _get_owned_item(db, item_id: int, user_id: int) -> RecurringExpense:
    item = db.get(RecurringExpense, item_id)
    if item is None or item.owner_id != user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurring expense not found")
    return item


@router.get("", response_model=list[RecurringOut])
def list_recurring(db: DbSession, current_user: CurrentUser):
    stmt = (
        select(RecurringExpense)
        .where(RecurringExpense.owner_id == current_user.id)
        .order_by(RecurringExpense.active.desc(), RecurringExpense.next_due, RecurringExpense.id)
    )
    return db.scalars(stmt).all()


@router.post("", response_model=RecurringOut, status_code=status.HTTP_201_CREATED)
def create_recurring(payload: RecurringCreate, db: DbSession, current_user: CurrentUser):
    data = payload.model_dump()
    data["category"] = payload.category.value
    data["frequency"] = payload.frequency.value
    item = RecurringExpense(
        **data, next_due=payload.start_date, active=True, owner_id=current_user.id
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.post("/process", response_model=ProcessResult)
def process_recurring(db: DbSession, current_user: CurrentUser):
    """Add every recurring expense that is due (today or earlier) as a real expense."""
    return ProcessResult(created=process_due(db, current_user.id))


@router.put("/{item_id}", response_model=RecurringOut)
def update_recurring(
    item_id: int, payload: RecurringUpdate, db: DbSession, current_user: CurrentUser
):
    item = _get_owned_item(db, item_id, current_user.id)
    changes = payload.model_dump(exclude_unset=True)
    if "category" in changes and payload.category is not None:
        changes["category"] = payload.category.value
    if "frequency" in changes and payload.frequency is not None:
        changes["frequency"] = payload.frequency.value
    required = ("title", "amount", "category", "frequency", "active", "next_due")
    for field, value in changes.items():
        if value is None and field in required:
            continue
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recurring(item_id: int, db: DbSession, current_user: CurrentUser):
    item = _get_owned_item(db, item_id, current_user.id)
    db.delete(item)
    db.commit()
