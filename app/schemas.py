from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

MAX_AMOUNT = 100_000_000


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


class Frequency(str, Enum):
    weekly = "weekly"
    monthly = "monthly"
    yearly = "yearly"


# ---------- Shared validators ----------
def _not_blank(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} must not be blank")
    return value


def _not_blank_optional(value: str | None, label: str) -> str | None:
    return None if value is None else _not_blank(value, label)


def _check_password_bytes(value: str) -> str:
    # bcrypt only processes up to 72 UTF-8 bytes; reject rather than silently truncate.
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    return value


# ---------- Users & auth ----------
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _not_blank(value, "Full name")

    @field_validator("password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        return _check_password_bytes(value)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    monthly_budget: float


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        return _not_blank(value, "Full name")


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str = Field(min_length=8, max_length=72)

    @field_validator("new_password")
    @classmethod
    def validate_password_bytes(cls, value: str) -> str:
        return _check_password_bytes(value)


class AccountDelete(BaseModel):
    password: str = Field(min_length=1, max_length=72)


class BudgetUpdate(BaseModel):
    monthly_budget: float = Field(ge=0, le=MAX_AMOUNT, allow_inf_nan=False)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Expenses ----------
class ExpenseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    category: Category
    note: str | None = Field(default=None, max_length=255)
    spent_on: date = Field(default_factory=date.today)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Expense title must not be blank")
        # Preserve intentional leading/trailing whitespace; only use strip for validation.
        return value


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    category: Category | None = None
    note: str | None = Field(default=None, max_length=255)
    spent_on: date | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
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


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


# ---------- Income ----------
class IncomeCreate(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    note: str | None = Field(default=None, max_length=255)
    received_on: date = Field(default_factory=date.today)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return _not_blank(value, "Income source")


class IncomeUpdate(BaseModel):
    source: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    note: str | None = Field(default=None, max_length=255)
    received_on: date | None = None

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str | None) -> str | None:
        return _not_blank_optional(value, "Income source")


class IncomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    amount: float
    note: str | None
    received_on: date


# ---------- Category budgets ----------
class BudgetLimit(BaseModel):
    limit_amount: float = Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)


class BudgetStatus(BaseModel):
    category: str
    limit_amount: float
    spent: float
    remaining: float
    percent_used: float
    status: str  # "ok" | "warning" | "over"


# ---------- Goals ----------
class GoalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    target_amount: float = Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    saved_amount: float = Field(default=0, ge=0, le=MAX_AMOUNT, allow_inf_nan=False)
    deadline: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _not_blank(value, "Goal name")


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    target_amount: float | None = Field(default=None, gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    deadline: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return _not_blank_optional(value, "Goal name")


class Contribution(BaseModel):
    """Money added to (positive) or taken out of (negative) a goal."""

    amount: float = Field(ge=-MAX_AMOUNT, le=MAX_AMOUNT, allow_inf_nan=False)

    @field_validator("amount")
    @classmethod
    def validate_non_zero(cls, value: float) -> float:
        if value == 0:
            raise ValueError("Amount must not be zero")
        return value


class GoalOut(BaseModel):
    id: int
    name: str
    target_amount: float
    saved_amount: float
    deadline: date | None
    remaining: float
    progress_percent: float
    is_complete: bool
    days_left: int | None
    monthly_needed: float | None


# ---------- Recurring expenses ----------
class RecurringCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    amount: float = Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    category: Category
    frequency: Frequency = Frequency.monthly
    start_date: date = Field(default_factory=date.today)
    note: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _not_blank(value, "Title")


class RecurringUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    amount: float | None = Field(default=None, gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    category: Category | None = None
    frequency: Frequency | None = None
    note: str | None = Field(default=None, max_length=255)
    active: bool | None = None
    next_due: date | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        return _not_blank_optional(value, "Title")


class RecurringOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    amount: float
    category: str
    frequency: str
    start_date: date
    next_due: date
    active: bool
    note: str | None


class ProcessResult(BaseModel):
    created: int


# ---------- Analytics ----------
class CategoryTotal(BaseModel):
    category: str
    total: float


class DailyTotal(BaseModel):
    date: date
    total: float


class TrendPoint(BaseModel):
    year: int
    month: int
    income: float
    expenses: float
    savings: float


class MonthlySummary(BaseModel):
    year: int
    month: int
    # --- original fields (kept for backward compatibility) ---
    total_spent: float
    expense_count: int
    monthly_budget: float
    remaining: float
    budget_used_percent: float
    by_category: list[CategoryTotal]
    # --- added in v2 ---
    total_income: float = 0.0
    net_savings: float = 0.0
    savings_rate_percent: float | None = None
    previous_month_spent: float = 0.0
    change_vs_previous_percent: float | None = None
    projected_spend: float | None = None
    daily: list[DailyTotal] = Field(default_factory=list)
    top_expenses: list[ExpenseOut] = Field(default_factory=list)
    budget_alerts: list[BudgetStatus] = Field(default_factory=list)
    insights: list[str] = Field(default_factory=list)
