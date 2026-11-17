from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.deps import CurrentUser, DbSession
from app.models import User
from app.ratelimit import login_limiter
from app.schemas import (
    AccountDelete,
    BudgetUpdate,
    PasswordChange,
    ProfileUpdate,
    Token,
    UserCreate,
    UserOut,
)
from app.security import create_access_token, hash_password, verify_password

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession):
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Two simultaneous sign-ups with the same email: the unique index wins.
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered") from None
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(request: Request, form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession):
    """OAuth2 password flow: send the email in the `username` field.

    After several failed attempts for the same client + email, further attempts are
    rejected with HTTP 429 for a while (brute-force protection).
    """
    email = form.username.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    limiter_key = f"{client_ip}:{email}"
    login_limiter.check(limiter_key)

    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(form.password, user.hashed_password):
        login_limiter.register_failure(limiter_key)
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    login_limiter.clear(limiter_key)
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def read_me(current_user: CurrentUser):
    return current_user


@router.put("/me", response_model=UserOut)
def update_profile(payload: ProfileUpdate, current_user: CurrentUser, db: DbSession):
    current_user.full_name = payload.full_name
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/budget", response_model=UserOut)
def set_budget(payload: BudgetUpdate, current_user: CurrentUser, db: DbSession):
    current_user.monthly_budget = payload.monthly_budget
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordChange, current_user: CurrentUser, db: DbSession):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(payload: AccountDelete, current_user: CurrentUser, db: DbSession):
    """Permanently delete the account and everything that belongs to it."""
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Password is incorrect")
    db.delete(current_user)  # ORM cascades remove expenses, income, goals, budgets...
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
