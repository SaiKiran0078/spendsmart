<div align="center">

# SpendSmart

### Track every rupee. Spend smarter.

A full-stack personal expense tracker for recording expenses, managing monthly budgets, and understanding spending patterns through category analytics.

Built with FastAPI, SQLAlchemy, SQLite, and vanilla JavaScript.

[![CI](https://github.com/SaiKiran0078/spendsmart/actions/workflows/ci.yml/badge.svg)](https://github.com/SaiKiran0078/spendsmart/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688)
![License](https://img.shields.io/badge/License-MIT-green)

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [API Overview](#api-overview)
- [Testing and Code Quality](#testing-and-code-quality)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Overview

SpendSmart helps users record everyday expenses, monitor their monthly budget, and understand where their money goes.

The project demonstrates practical full-stack development using a Python API, relational database models, authenticated endpoints, a browser-based interface, automated tests, and a containerized deployment workflow.

## Features

- **Expense management:** Create, view, update, and delete expense records.
- **Monthly budgeting:** Set a monthly budget and track spending against it.
- **Spending analytics:** Review monthly totals and category-level breakdowns.
- **Expense filtering:** Retrieve expense records using supported filters.
- **CSV export:** Export expense records with protection against spreadsheet formula injection.
- **User authentication:** Register and log in using password-based authentication and JWT access tokens.
- **User data isolation:** Restrict expense access to the authenticated user.
- **Responsive interface:** Use the web interface across different screen sizes, with light and dark themes.
- **API documentation:** Explore endpoints through FastAPI's interactive Swagger UI.
- **Automated quality checks:** Run tests and linting locally and through GitHub Actions.
- **Docker support:** Build and run the application in a container.

## Technology Stack

| Area | Technologies |
|---|---|
| Language | Python 3.12 |
| Backend | FastAPI, Pydantic |
| Database and ORM | SQLite, SQLAlchemy |
| Authentication | PyJWT, bcrypt |
| Frontend | HTML5, CSS3, JavaScript |
| Visualization | Chart.js |
| Testing | pytest, pytest-cov, httpx |
| Code quality | Ruff |
| Deployment | Docker, Docker Compose |
| CI | GitHub Actions |

## Project Structure

```text
spendsmart/
├── .github/
│   ├── workflows/
│   │   └── ci.yml
│   ├── ISSUE_TEMPLATE/
│   │   └── bug_report.md
│   └── pull_request_template.md
├── app/
│   ├── routers/
│   │   ├── auth.py
│   │   ├── expenses.py
│   │   └── summary.py
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── deps.py
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   └── security.py
├── docs/
│   ├── API.md
│   └── ARCHITECTURE.md
├── frontend/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── index.html
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   └── test_expenses.py
├── .dockerignore
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
├── Dockerfile
├── docker-compose.yml
├── LICENSE
├── Makefile
├── pyproject.toml
├── requirements-dev.txt
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12 or later
- Git
- PowerShell on Windows, or a compatible terminal on macOS/Linux

### Option A: Run Locally

#### 1. Clone the repository

```bash
git clone https://github.com/SaiKiran0078/spendsmart.git
cd spendsmart
```

#### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, you can invoke the environment's Python directly using `.\.venv\Scripts\python.exe`.

**macOS/Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 3. Install dependencies

```bash
python -m pip install -r requirements-dev.txt
```

#### 4. Configure environment variables

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux/Git Bash:**

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder `SECRET_KEY` with a strong random value. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Do not commit `.env` or share its contents.

#### 5. Start the application

```bash
uvicorn app.main:app --reload
```

Open the application at:

- Web interface: http://localhost:8000
- Interactive API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/api/health

The default database configuration uses SQLite. Ensure the configured database directory is writable.

### Option B: Run with Docker

Make sure Docker Desktop and Docker Compose are installed and running.

Create the environment file first.

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux/Git Bash:**

```bash
cp .env.example .env
```

Replace the placeholder `SECRET_KEY` in `.env` with a strong random value, then run:

```bash
docker compose up --build
```

Open http://localhost:8000 to use the application.

Docker Compose configures a persistent volume for the SQLite database so application data can survive container recreation.

To stop the application:

```bash
docker compose down
```

To stop the application and remove its named database volume, use `docker compose down -v`. This permanently deletes the data stored in that volume.

## Configuration

SpendSmart reads settings from environment variables and the optional `.env` file.

| Variable | Example | Description |
|---|---|---|
| `SECRET_KEY` | A strong random secret | Required signing key for JWT access tokens. Must not be a placeholder or short secret. |
| `ALGORITHM` | `HS256` | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access-token lifetime in minutes; must be positive. |
| `DATABASE_URL` | `sqlite:///./data/spendsmart.db` | SQLAlchemy database connection URL. |

The application configuration supplies defaults for settings other than `SECRET_KEY`. Set the secret explicitly before starting the application.

The Docker Compose configuration overrides `DATABASE_URL` to use the container's persistent data volume.

## API Overview

The API is organized into authentication, expense management, and summary endpoints.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register` | Register a user |
| `POST` | `/api/auth/login` | Authenticate and obtain an access token |
| `GET` | `/api/auth/me` | Retrieve the authenticated user's profile |
| `PUT` | `/api/auth/me/budget` | Update the monthly budget |
| `GET` | `/api/expenses` | List expenses |
| `POST` | `/api/expenses` | Create an expense |
| `GET` | `/api/expenses/{id}` | Retrieve an expense |
| `PUT` | `/api/expenses/{id}` | Update an expense |
| `DELETE` | `/api/expenses/{id}` | Delete an expense |
| `GET` | `/api/expenses/export/csv` | Export expenses as CSV |
| `GET` | `/api/summary` | Retrieve monthly spending summaries |
| `GET` | `/api/health` | Check application health |

For request schemas, parameters, and response examples, see [API Documentation](docs/API.md). For the application's structure and design decisions, see [Architecture Documentation](docs/ARCHITECTURE.md).

## Testing and Code Quality

Run the test suite:

```bash
python -m pytest -v
```

Run tests with coverage:

```bash
python -m pytest --cov=app --cov-report=term-missing
```

Check code quality with Ruff:

```bash
ruff check .
```

Format Python code when needed:

```bash
ruff format .
```

The automated tests use an isolated in-memory SQLite database rather than the normal application database.

GitHub Actions runs linting, tests with coverage, and a Docker image build on pushes and pull requests targeting `main`.

## Security

Security-related measures implemented in the project include:

- Password hashing using bcrypt.
- JWT access tokens with expiration.
- Environment-based JWT signing configuration.
- Authentication dependencies for protected endpoints.
- Per-user authorization checks for expense access.
- Pydantic validation of incoming data.
- Frontend rendering through `textContent` where applicable to reduce DOM-based XSS risks.
- CSV formula-injection protection during export.
- A non-root user in the Docker image.
- Exclusion of environment secrets and local database files from version control.

**Deployment note:** Use a strong, unique secret, keep dependencies maintained, and deploy behind HTTPS. SQLite is appropriate for this project's current scope; production deployments with multiple application instances may require a different database and a migration strategy.

## Roadmap

Potential future enhancements include:

- Recurring expenses.
- Income tracking and savings goals.
- Database migrations with Alembic.
- PostgreSQL support.
- Password reset and refresh-token workflows.
- Additional financial reports and analytics.

## Contributing

Contributions, bug reports, and suggestions are welcome.

Before submitting a change:

1. Install the development dependencies.
2. Run `python -m pytest`.
3. Run `ruff check .`.
4. Update relevant documentation when behavior or configuration changes.

Use the repository's issue and pull request templates when applicable.

## License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.