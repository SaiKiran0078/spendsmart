# API Reference

Interactive docs (Swagger UI) are at **`/docs`** and ReDoc at **`/redoc`** while the server runs.
Every endpoint except register, login and health needs `Authorization: Bearer <token>`.
Errors look like `{ "detail": "Expense not found" }`.

| Code | Meaning |
|---|---|
| 400 | Business-rule error (wrong password, bad CSV, overdrawn goal) |
| 401 | Missing/invalid/expired token or wrong credentials |
| 404 | Not found (or not yours) |
| 409 | Email already registered |
| 413 | Uploaded file too large |
| 422 | Validation error |
| 429 | Too many failed logins (see `Retry-After`) |

## Auth `/api/auth`
| Method | Path | Description |
|---|---|---|
| POST | `/register` | `{email, full_name, password}` (8–72 chars) |
| POST | `/login` | OAuth2 form: `username` = email, `password` → `access_token` |
| GET / PUT | `/me` | Read / update profile (`full_name`) |
| PUT | `/me/budget` | `{monthly_budget}` |
| POST | `/me/password` | `{current_password, new_password}` → 204 |
| DELETE | `/me` | `{password}` — deletes the account and all data → 204 |

## Expenses `/api/expenses`
| Method | Path | Description |
|---|---|---|
| GET | `/` | Filters: `category`, `start_date`, `end_date`, `search`, `skip`, `limit` |
| POST | `/` | `{title, amount, category, spent_on?, note?}` |
| GET / PUT / DELETE | `/{id}` | Read / partial update / delete |
| GET | `/export/csv` | Download all expenses |
| POST | `/import/csv` | Multipart `file`. Columns: `title`, `amount` (required); `category`, `date`, `note`. Returns `{imported, skipped, errors}` |

Categories: Food, Transport, Rent, Utilities, Shopping, Health, Entertainment, Education, Other.
Import accepts dates as `YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY` or `MM/DD/YYYY`; amounts may contain currency symbols and commas; unknown categories become *Other*; max 1 MB / 1000 rows.

## Income `/api/income`
`GET /` (filters `start_date`, `end_date`, `search`, `skip`, `limit`) · `POST /` `{source, amount, received_on?, note?}` · `PUT /{id}` · `DELETE /{id}`

## Category budgets `/api/budgets`
| Method | Path | Description |
|---|---|---|
| GET | `/?year=&month=` | Limits with `spent`, `remaining`, `percent_used`, `status` (`ok` / `warning` ≥ 80 % / `over` ≥ 100 %) |
| PUT | `/{category}` | `{limit_amount}` — create or replace |
| DELETE | `/{category}` | Remove the limit |

## Goals `/api/goals`
`GET /` · `POST /` `{name, target_amount, saved_amount?, deadline?}` · `PUT /{id}` · `DELETE /{id}` ·
`POST /{id}/contribute` `{amount}` (negative withdraws). Responses include `progress_percent`, `remaining`, `is_complete`, `days_left` and `monthly_needed`.

## Recurring bills `/api/recurring`
`GET /` · `POST /` `{title, amount, category, frequency, start_date?, note?}` (`weekly` / `monthly` / `yearly`) · `PUT /{id}` (incl. `active`, `next_due`) · `DELETE /{id}` ·
`POST /process` — turns every due bill into an expense (idempotent). Also runs automatically when the summary is requested.

## Analytics `/api/summary`
| Method | Path | Description |
|---|---|---|
| GET | `/?year=&month=` | Totals, income, net savings, savings rate, change vs. previous month, projection, daily series, top expenses, budget alerts, insights |
| GET | `/trend?months=6` | Income vs. expenses per month (2–12 months, oldest first) |

## Health
`GET /api/health` → `{"status": "ok"}`

```bash
curl -X POST http://localhost:8000/api/expenses \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"title":"Groceries","amount":842.50,"category":"Food","spent_on":"2026-11-10"}'
```
