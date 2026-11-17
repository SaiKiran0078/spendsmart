"""Fill the database with realistic demo data (great for screenshots and live demos).

Usage (from the project root, with your .env in place):

    python -m scripts.seed_demo

Creates / resets the account  demo@spendsmart.app  with password  Demo@12345.
"""

import random
from datetime import date, timedelta

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import CategoryBudget, Expense, Goal, Income, RecurringExpense, User
from app.security import hash_password
from app.services.dates import add_months

DEMO_EMAIL = "demo@spendsmart.app"
DEMO_PASSWORD = "Demo@12345"

# (title, category, low, high, how many per month)
VARIABLE_SPENDING = [
    ("Groceries", "Food", 600, 1800, 5),
    ("Restaurant", "Food", 350, 1200, 4),
    ("Coffee", "Food", 120, 280, 6),
    ("Metro / cab", "Transport", 60, 450, 8),
    ("Fuel", "Transport", 500, 1500, 2),
    ("Online shopping", "Shopping", 499, 3499, 2),
    ("Movie night", "Entertainment", 300, 900, 2),
    ("Pharmacy", "Health", 150, 900, 1),
    ("Online course", "Education", 499, 1999, 1),
]


def seed() -> None:
    rng = random.Random(42)  # deterministic: same demo data every time
    Base.metadata.create_all(bind=engine)
    today = date.today()

    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if existing:
            db.delete(existing)
            db.commit()

        user = User(
            email=DEMO_EMAIL,
            full_name="Demo User",
            hashed_password=hash_password(DEMO_PASSWORD),
            monthly_budget=30000,
        )
        db.add(user)
        db.flush()

        for months_back in range(3, -1, -1):
            first = add_months(date(today.year, today.month, 1), -months_back)
            last_day = today if months_back == 0 else add_months(first, 1) - timedelta(days=1)
            span = max((last_day - first).days, 1)

            db.add(Income(source="Salary", amount=65000, received_on=first, owner_id=user.id))
            if months_back % 2 == 0:
                db.add(
                    Income(
                        source="Freelance project",
                        amount=rng.randrange(6000, 14000, 500),
                        received_on=first + timedelta(days=min(14, span)),
                        owner_id=user.id,
                    )
                )

            db.add(Expense(title="Rent", amount=15000, category="Rent", spent_on=first,
                           owner_id=user.id))
            db.add(Expense(title="Electricity & internet", amount=rng.randrange(1500, 2400, 50),
                           category="Utilities", spent_on=first + timedelta(days=min(6, span)),
                           owner_id=user.id))
            for title, category, low, high, times in VARIABLE_SPENDING:
                for _ in range(times):
                    db.add(
                        Expense(
                            title=title,
                            amount=rng.randrange(low, high, 10),
                            category=category,
                            spent_on=first + timedelta(days=rng.randint(0, span)),
                            owner_id=user.id,
                        )
                    )

        for category, limit in [("Food", 8000), ("Transport", 3500), ("Shopping", 4000),
                                ("Entertainment", 2000)]:
            db.add(CategoryBudget(category=category, limit_amount=limit, owner_id=user.id))

        db.add(Goal(name="Emergency fund", target_amount=150000, saved_amount=62000,
                    deadline=add_months(today, 10), owner_id=user.id))
        db.add(Goal(name="New laptop", target_amount=80000, saved_amount=24000,
                    deadline=add_months(today, 5), owner_id=user.id))
        db.add(Goal(name="Goa trip", target_amount=30000, saved_amount=30000, owner_id=user.id))

        next_month = add_months(date(today.year, today.month, 1), 1)
        for title, amount, category, frequency, due in [
            ("Netflix", 649, "Entertainment", "monthly", next_month.replace(day=5)),
            ("Gym membership", 1200, "Health", "monthly", next_month.replace(day=1)),
            ("Cloud storage", 1300, "Utilities", "yearly", add_months(today, 4)),
        ]:
            db.add(RecurringExpense(title=title, amount=amount, category=category,
                                    frequency=frequency, start_date=due, next_due=due,
                                    active=True, owner_id=user.id))

        db.commit()

    print(f"Demo data ready. Log in with  {DEMO_EMAIL}  /  {DEMO_PASSWORD}")


if __name__ == "__main__":
    seed()
