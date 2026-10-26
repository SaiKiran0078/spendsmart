from datetime import date

from tests.conftest import register_and_login

TODAY = date.today().isoformat()


def make_expense(client, headers, **overrides):
    payload = {"title": "Lunch", "amount": 150.5, "category": "Food", "spent_on": TODAY}
    payload.update(overrides)
    return client.post("/api/expenses", json=payload, headers=headers)


def test_requires_authentication(client):
    assert client.get("/api/expenses").status_code == 401


def test_create_and_list(client, auth_headers):
    res = make_expense(client, auth_headers)
    assert res.status_code == 201
    assert res.json()["title"] == "Lunch"

    listing = client.get("/api/expenses", headers=auth_headers).json()
    assert len(listing) == 1


def test_rejects_negative_amount(client, auth_headers):
    assert make_expense(client, auth_headers, amount=-5).status_code == 422


def test_rejects_unknown_category(client, auth_headers):
    assert make_expense(client, auth_headers, category="Spaceships").status_code == 422


def test_update_expense(client, auth_headers):
    expense_id = make_expense(client, auth_headers).json()["id"]
    res = client.put(
        f"/api/expenses/{expense_id}", json={"amount": 200, "category": "Transport"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["amount"] == 200
    assert res.json()["category"] == "Transport"
    assert res.json()["title"] == "Lunch"  # untouched fields stay the same


def test_delete_expense(client, auth_headers):
    expense_id = make_expense(client, auth_headers).json()["id"]
    assert client.delete(f"/api/expenses/{expense_id}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/expenses/{expense_id}", headers=auth_headers).status_code == 404


def test_users_cannot_access_each_others_expenses(client, auth_headers):
    expense_id = make_expense(client, auth_headers).json()["id"]
    other = register_and_login(client, email="ravi@example.com")

    assert client.get(f"/api/expenses/{expense_id}", headers=other).status_code == 404
    assert client.delete(f"/api/expenses/{expense_id}", headers=other).status_code == 404
    assert client.get("/api/expenses", headers=other).json() == []


def test_filter_by_category_and_search(client, auth_headers):
    make_expense(client, auth_headers, title="Pizza", category="Food")
    make_expense(client, auth_headers, title="Metro card", category="Transport")

    food = client.get("/api/expenses?category=Food", headers=auth_headers).json()
    assert [e["title"] for e in food] == ["Pizza"]

    found = client.get("/api/expenses?search=metro", headers=auth_headers).json()
    assert [e["title"] for e in found] == ["Metro card"]


def test_csv_export_and_formula_injection_guard(client, auth_headers):
    make_expense(client, auth_headers, title="=HYPERLINK(\"http://evil\")")
    res = client.get("/api/expenses/export/csv", headers=auth_headers)
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "'=HYPERLINK" in res.text


def test_monthly_summary(client, auth_headers):
    client.put("/api/auth/me/budget", json={"monthly_budget": 1000}, headers=auth_headers)
    make_expense(client, auth_headers, amount=300, category="Food")
    make_expense(client, auth_headers, amount=200, category="Transport")

    res = client.get("/api/summary", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["total_spent"] == 500
    assert body["remaining"] == 500
    assert body["budget_used_percent"] == 50
    assert body["expense_count"] == 2
    assert body["by_category"][0] == {"category": "Food", "total": 300}


def test_health_endpoint(client):
    assert client.get("/api/health").json() == {"status": "ok"}



def test_rejects_blank_expense_title(client, auth_headers):
    assert make_expense(client, auth_headers, title="   ").status_code == 422


def test_rejects_inverted_date_range(client, auth_headers):
    res = client.get(
        "/api/expenses?start_date=2026-10-25&end_date=2026-10-01",
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_csv_guard_handles_leading_whitespace(client, auth_headers):
    make_expense(client, auth_headers, title="   =1+1")
    res = client.get("/api/expenses/export/csv", headers=auth_headers)
    assert res.status_code == 200
    assert "'   =1+1" in res.text
