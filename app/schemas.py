from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class Category(str, Enum):
    food = "Food"
    transport = "Transport"
    rent = "Rent"
    utilities = "Utilities"
    shopping = "Shopping"
    health = "Health"
    entertainment = "Entertainment"
    education = "Education"
    other = "Other"


# ---------- Users & auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Full name must not be blank")
        return value

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        # bcrypt only processes up to 72 UTF-8 bytes; reject rather than silently truncate.
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    monthly_budget: float


class BudgetUpdate(BaseModel):
    monthly_budget: float = Field(ge=0, le=100_000_000)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, le=100_000_000)
    category: Category
    note: str | None = Field(default=None, max_length=255)
    spent_on: date = Field(default_factory=date.today)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Expense title must not be blank")
        return value


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0, le=100_000_000)
    category: Category | None = None
    note: str | None = Field(default=None, max_length=255)
    spent_on: date | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()
        if not value:
            raise ValueError("Expense title must not be blank")
        return value


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: float
    category: str
    note: str | None
    spent_on: date


# ---------- Summary ----------
class CategoryTotal(BaseModel):
    category: str
    total: float


class MonthlySummary(BaseModel):
    year: int
    month: int
    total_spent: float
    expense_count: int
    monthly_budget: float
    remaining: float
    budget_used_percent: float
    by_category: list[CategoryTotal]
