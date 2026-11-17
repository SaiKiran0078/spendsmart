from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import Base, engine
from app.routers import auth, budgets, expenses, goals, income, recurring, summary

settings = get_settings()
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# Chart.js is the only third-party script; fonts come from Google Fonts.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "frame-ancestors 'none'"
)
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # create tables on startup
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    description=(
        "Personal finance API: expenses, income, category budgets, savings goals, "
        "recurring bills and spending insights."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # The production UI is served by this same FastAPI origin. Keep CORS
    # closed by default; configure an explicit allow-list only for a split UI/API.
    allow_origins=[],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    # The interactive API docs load their own CDN assets, so they are exempt from the CSP.
    if not request.url.path.startswith(DOCS_PATHS):
        response.headers.setdefault("Content-Security-Policy", CONTENT_SECURITY_POLICY)
    return response


app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(income.router, prefix="/api/income", tags=["Income"])
app.include_router(budgets.router, prefix="/api/budgets", tags=["Category budgets"])
app.include_router(goals.router, prefix="/api/goals", tags=["Savings goals"])
app.include_router(recurring.router, prefix="/api/recurring", tags=["Recurring bills"])
app.include_router(summary.router, prefix="/api/summary", tags=["Summary & insights"])


@app.get("/api/health", tags=["Health"])
def health() -> dict[str, str]:
    """Liveness and database-readiness check for hosting health probes."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc
    return {"status": "ok", "database": "ok"}


# Serve the website at "/" (must be registered last so it doesn't shadow /api routes)
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
