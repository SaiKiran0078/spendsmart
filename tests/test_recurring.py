from datetime import date, timedelta

from tests.conftest import register_and_login


def make_item(client, headers, **overrides):
    payload = {
        "title": "Netflix",
        "amount": 649,
        "category": "Entertainment",
        "frequency": "monthly",
        "start_date": (date.today() + timedelta(days=10)).isoformat(),
    }
    payload.update(overrides)
    return client.post("/api/recurring", json=payload, headers=headers)


def list_expenses(client, headers):
    return client.get("/api/expenses", headers=headers).json()


def test_requires_authentication(client):
    assert client.get("/api/recurring").status_code == 401


def test_create_sets_next_due_to_start_date(client, auth_headers):
    start = (date.today() + timedelta(days=10)).isoformat()
    res = make_item(client, auth_headers, start_date=start)
    assert res.status_code == 201
    assert res.json()["next_due"] == start
    assert res.json()["active"] is True


def test_future_items_are_not_processed_yet(client, auth_headers):
    make_item(client, auth_headers)
    res = client.post("/api/recurring/process", headers=auth_headers)
    assert res.json() == {"created": 0}
    assert list_expenses(client, auth_headers) == []


def test_overdue_monthly_item_catches_up_exactly_once_per_period(client, auth_headers):
    start = (date.today() - timedelta(days=40)).isoformat()
    make_item(client, auth_headers, start_date=start)

    first = client.post("/api/recurring/process", headers=auth_headers).json()
    assert first == {"created": 2}  # the start date and one month later

    again = client.post("/api/recurring/process", headers=auth_headers).json()
    assert again == {"created": 0}  # idempotent: nothing is added twice

    expenses = list_expenses(client, auth_headers)
    assert len(expenses) == 2
    assert {e["title"] for e in expenses} == {"Netflix"}
    assert {e["category"] for e in expenses} == {"Entertainment"}


def test_weekly_item_creates_one_expense_per_week(client, auth_headers):
    start = (date.today() - timedelta(days=14)).isoformat()
    make_item(client, auth_headers, frequency="weekly", start_date=start)
    assert client.post("/api/recurring/process", headers=auth_headers).json() == {"created": 3}


def test_next_due_moves_into_the_future_after_processing(client, auth_headers):
    start = (date.today() - timedelta(days=40)).isoformat()
    item_id = make_item(client, auth_headers, start_date=start).json()["id"]
    client.post("/api/recurring/process", headers=auth_headers)

    item = next(i for i in client.get("/api/recurring", headers=auth_headers).json()
                if i["id"] == item_id)
    assert item["next_due"] > date.today().isoformat()


def test_paused_items_are_skipped(client, auth_headers):
    start = (date.today() - timedelta(days=40)).isoformat()
    item_id = make_item(client, auth_headers, start_date=start).json()["id"]
    res = client.put(f"/api/recurring/{item_id}", json={"active": False}, headers=auth_headers)
    assert res.json()["active"] is False

    assert client.post("/api/recurring/process", headers=auth_headers).json() == {"created": 0}


def test_summary_automatically_counts_due_items(client, auth_headers):
    make_item(client, auth_headers, start_date=date.today().isoformat(), amount=500)
    summary = client.get("/api/summary", headers=auth_headers).json()
    assert summary["total_spent"] == 500
    assert summary["expense_count"] == 1


def test_update_and_delete(client, auth_headers):
    item_id = make_item(client, auth_headers).json()["id"]
    res = client.put(
        f"/api/recurring/{item_id}",
        json={"amount": 799, "frequency": "yearly", "category": "Utilities"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert (res.json()["amount"], res.json()["frequency"]) == (799, "yearly")
    assert res.json()["category"] == "Utilities"
    assert res.json()["title"] == "Netflix"

    assert client.delete(f"/api/recurring/{item_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/recurring", headers=auth_headers).json() == []


def test_validation(client, auth_headers):
    assert make_item(client, auth_headers, amount=-1).status_code == 422
    assert make_item(client, auth_headers, frequency="daily").status_code == 422
    assert make_item(client, auth_headers, title="  ").status_code == 422


def test_users_cannot_access_each_others_items(client, auth_headers):
    item_id = make_item(client, auth_headers).json()["id"]
    other = register_and_login(client, email="ravi@example.com")
    assert client.delete(f"/api/recurring/{item_id}", headers=other).status_code == 404
    assert client.put(
        f"/api/recurring/{item_id}", json={"active": False}, headers=other
    ).status_code == 404
    assert client.get("/api/recurring", headers=other).json() == []
