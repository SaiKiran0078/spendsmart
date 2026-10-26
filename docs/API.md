# API Reference

Interactive docs (Swagger UI) are available at **`/docs`** when the server is running,
and ReDoc at **`/redoc`**. All endpoints except register, login and health require
the header `Authorization: Bearer <token>`.

## Auth

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create an account (`email`, `full_name`, `password` ≥ 8 chars) |
| POST | `/api/auth/login` | OAuth2 form (`username` = email, `password`) → `access_token` |
| GET | `/api/auth/me` | Current user profile |
| PUT | `/api/auth/me/budget` | Set monthly budget `{ "monthly_budget": 25000 }` |

## Expenses

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/expenses` | List with filters: `category`, `start_date`, `end_date`, `search`, `skip`, `limit` |
| POST | `/api/expenses` | Create an expense |
| GET | `/api/expenses/{id}` | Get one expense |
| PUT | `/api/expenses/{id}` | Partially update an expense |
| DELETE | `/api/expenses/{id}` | Delete an expense (204) |
| GET | `/api/expenses/export/csv` | Download all expenses as CSV |

**Create example**

```bash
curl -X POST http://localhost:8000/api/expenses \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Groceries","amount":842.50,"category":"Food","spent_on":"2026-10-24"}'
```

Allowed categories: `Food`, `Transport`, `Rent`, `Utilities`, `Shopping`, `Health`,
`Entertainment`, `Education`, `Other`.

## Summary

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/summary?year=2026&month=10` | Total spent, budget, remaining, % used and per-category totals (defaults to the current month) |

## Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Returns `{"status": "ok"}` – used by the Docker healthcheck |

## Error format

```json
{ "detail": "Expense not found" }
```

| Code | Meaning |
|---|---|
| 401 | Missing, invalid or expired token / wrong credentials |
| 404 | Resource not found (or not yours) |
| 409 | Email already registered |
| 422 | Validation error (bad amount, unknown category, …) |
