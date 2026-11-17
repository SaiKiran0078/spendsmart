from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Expense, RecurringExpense
from app.services.dates import advance_due

MAX_CATCH_UP = 400  # safety cap so a very old start date can't create endless rows


def process_due(db: Session, user_id: int, today: date | None = None) -> int:
    """Turn every recurring item that has fallen due into real expenses.

    Safe to call repeatedly: each item's `next_due` moves forward as expenses are
    created, so the same occurrence is never added twice.
    """
    today = today or date.today()
    items = db.scalars(
        select(RecurringExpense).where(
            RecurringExpense.owner_id == user_id,
            RecurringExpense.active.is_(True),
            RecurringExpense.next_due <= today,
        )
    ).all()

    created = 0
    for item in items:
        steps = 0
        while item.next_due <= today and steps < MAX_CATCH_UP:
            db.add(
                Expense(
                    title=item.title,
                    amount=item.amount,
                    category=item.category,
                    note=item.note or "Added automatically (recurring)",
                    spent_on=item.next_due,
                    owner_id=user_id,
                )
            )
            item.next_due = advance_due(item.next_due, item.frequency, item.start_date.day)
            created += 1
            steps += 1

    if items:
        db.commit()
    return created
