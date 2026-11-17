from datetime import date

from app.services.dates import add_months, days_in_month
from tests.conftest import register_and_login

TODAY = date.today()
FIRST_OF_THIS_MONTH = TODAY.replace(day=1)
LAST_MONTH = add_months(FIRST_OF_THIS_MONTH, -1)


def add_expense(client, headers, amount, category="Food", on=TODAY, title="Item"):
    res = client.post(
        "/api/expenses",
        json={"title": title, "amount": amount, "category": category, "spent_on": on.isoformat()},
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()


def add_income(client, headers, amount, on=TODAY):
    res = client.post(
        "/api/income",
        json={"source": "Salary", "amount": amount, "received_on": on.isoformat()},
        headers=headers,
    )
    assert res.status_code == 201


def test_summary_is_zeroed_for_a_new_user(client, auth_headers):
    body = client.get("/api/summary", headers=auth_headers).json()
    assert body["total_spent"] == 0
    assert body["total_income"] == 0
    assert body["savings_rate_percent"] is None
    assert body["change_vs_previous_percent"] is None
    assert body["projected_spend"] is None
    assert body["top_expenses"] == []
    assert len(body["insights"]) == 1


def test_income_net_savings_and_rate(client, auth_headers):
    add_income(client, auth_headers, 1000)
    add_expense(client, auth_headers, 250)
    body = client.get("/api/summary", headers=auth_headers).json()
    assert body["total_income"] == 1000
    assert body["net_savings"] == 750
    assert body["savings_rate_percent"] == 75.0


def test_comparison_with_previous_month(client, auth_headers):
    add_expense(client, auth_headers, 200, on=LAST_MONTH)
    add_expense(client, auth_headers, 300)
    body = client.get("/api/summary", headers=auth_headers).json()
    assert body["previous_month_spent"] == 200
    assert body["change_vs_previous_percent"] == 50.0
    assert any("up 50% compared with last month" in tip for tip in body["insights"])


def test_daily_series_covers_every_day_of_the_month(client, auth_headers):
    add_expense(client, auth_headers, 120)
    body = client.get("/api/summary", headers=auth_headers).json()
    assert len(body["daily"]) == days_in_month(TODAY.year, TODAY.month)
    today_row = next(d for d in body["daily"] if d["date"] == TODAY.isoformat())
    assert today_row["total"] == 120


def test_top_expenses_are_the_five_largest(client, auth_headers):
    for amount in (10, 70, 30, 90, 50, 20, 60):
        add_expense(client, auth_headers, amount)
    top = client.get("/api/summary", headers=auth_headers).json()["top_expenses"]
    assert [e["amount"] for e in top] == [90, 70, 60, 50, 30]


def test_projection_only_for_the_current_month(client, auth_headers):
    add_expense(client, auth_headers, 100)
    current = client.get("/api/summary", headers=auth_headers).json()
    assert current["projected_spend"] is not None
    assert current["projected_spend"] >= 100

    add_expense(client, auth_headers, 100, on=LAST_MONTH)
    past = client.get(
        f"/api/summary?year={LAST_MONTH.year}&month={LAST_MONTH.month}", headers=auth_headers
    ).json()
    assert past["projected_spend"] is None
    assert past["total_spent"] == 100


def test_budget_usage_creates_insight(client, auth_headers):
    client.put("/api/auth/me/budget", json={"monthly_budget": 1000}, headers=auth_headers)
    add_expense(client, auth_headers, 850)
    body = client.get("/api/summary", headers=auth_headers).json()
    assert body["budget_used_percent"] == 85.0
    assert any("85% of your monthly budget" in tip for tip in body["insights"])


def test_category_budget_alerts_appear_in_summary(client, auth_headers):
    client.put("/api/budgets/Food", json={"limit_amount": 100}, headers=auth_headers)
    client.put("/api/budgets/Transport", json={"limit_amount": 1000}, headers=auth_headers)
    add_expense(client, auth_headers, 150, category="Food")
    add_expense(client, auth_headers, 100, category="Transport")

    alerts = client.get("/api/summary", headers=auth_headers).json()["budget_alerts"]
    assert [(a["category"], a["status"]) for a in alerts] == [("Food", "over")]



def test_category_budget_at_exact_limit_is_reached_not_over(client, auth_headers):
    client.put("/api/budgets/Rent", json={"limit_amount": 5000}, headers=auth_headers)
    add_expense(client, auth_headers, 5000, category="Rent")
    body = client.get("/api/summary", headers=auth_headers).json()
    rent = next(item for item in body["budget_alerts"] if item["category"] == "Rent")
    assert rent["percent_used"] == 100.0
    assert rent["status"] == "warning"
    assert any("Rent is at 100% of its budget" in tip for tip in body["insights"])
    assert not any("Rent is over its budget" in tip for tip in body["insights"])

def test_other_users_data_is_never_included(client, auth_headers):
    other = register_and_login(client, email="ravi@example.com")
    add_expense(client, other, 999)
    body = client.get("/api/summary", headers=auth_headers).json()
    assert body["total_spent"] == 0


def test_trend_returns_requested_number_of_months(client, auth_headers):
    add_income(client, auth_headers, 1000)
    add_expense(client, auth_headers, 300)
    add_expense(client, auth_headers, 100, on=LAST_MONTH)

    points = client.get("/api/summary/trend", headers=auth_headers).json()
    assert len(points) == 6
    assert (points[-1]["year"], points[-1]["month"]) == (TODAY.year, TODAY.month)
    assert points[-1]["income"] == 1000
    assert points[-1]["expenses"] == 300
    assert points[-1]["savings"] == 700
    assert points[-2]["expenses"] == 100

    short = client.get("/api/summary/trend?months=3", headers=auth_headers).json()
    assert len(short) == 3


def test_trend_validates_month_count(client, auth_headers):
    assert client.get("/api/summary/trend?months=1", headers=auth_headers).status_code == 422
    assert client.get("/api/summary/trend?months=99", headers=auth_headers).status_code == 422


def test_summary_requires_year_and_month_together(client, auth_headers):
    assert client.get("/api/summary?year=2026", headers=auth_headers).status_code == 422
    assert client.get("/api/summary?month=4", headers=auth_headers).status_code == 422


def test_trend_requires_year_and_month_together(client, auth_headers):
    assert client.get("/api/summary/trend?year=2026", headers=auth_headers).status_code == 422
    assert client.get("/api/summary/trend?month=4", headers=auth_headers).status_code == 422
