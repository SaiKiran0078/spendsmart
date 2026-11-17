from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

_CASCADE = "all, delete-orphan"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    hashed_password: Mapped[str] = mapped_column(String(255))
    monthly_budget: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    expenses: Mapped[list["Expense"]] = relationship(back_populates="owner", cascade=_CASCADE)
    incomes: Mapped[list["Income"]] = relationship(back_populates="owner", cascade=_CASCADE)
    category_budgets: Mapped[list["CategoryBudget"]] = relationship(
        back_populates="owner", cascade=_CASCADE
    )
    goals: Mapped[list["Goal"]] = relationship(back_populates="owner", cascade=_CASCADE)
    recurring: Mapped[list["RecurringExpense"]] = relationship(
        back_populates="owner", cascade=_CASCADE
    )


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (Index("ix_expenses_owner_date", "owner_id", "spent_on"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    spent_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    owner: Mapped[User] = relationship(back_populates="expenses")


class Income(Base):
    __tablename__ = "incomes"
    __table_args__ = (Index("ix_incomes_owner_date", "owner_id", "received_on"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    received_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    owner: Mapped[User] = relationship(back_populates="incomes")


class CategoryBudget(Base):
    """A monthly spending limit for one category (one row per user + category)."""

    __tablename__ = "category_budgets"
    __table_args__ = (UniqueConstraint("owner_id", "category", name="uq_budget_owner_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(30))
    limit_amount: Mapped[float] = mapped_column(Float)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    owner: Mapped[User] = relationship(back_populates="category_budgets")


class Goal(Base):
    """A savings goal, e.g. 'Emergency fund' or 'New laptop'."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    target_amount: Mapped[float] = mapped_column(Float)
    saved_amount: Mapped[float] = mapped_column(Float, default=0.0)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    owner: Mapped[User] = relationship(back_populates="goals")


class RecurringExpense(Base):
    """A bill or subscription that is added automatically when it falls due."""

    __tablename__ = "recurring_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(30))
    frequency: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[date] = mapped_column(Date)
    next_due: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    owner: Mapped[User] = relationship(back_populates="recurring")
