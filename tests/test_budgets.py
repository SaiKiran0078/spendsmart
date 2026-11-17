from datetime import date

from tests.conftest import register_and_login

TODAY = date.today().isoformat()


def spend(client, headers, amount, category="Food"):
    return client.post(
        "/api/expenses",
        json={"title": "Item", "amount": amount, "category": category, "spent_on": TODAY},
        headers=headers,
    )


def test_requires_authentication(client):
    assert client.get("/api/budgets").status_code == 401


def test_set_and_list_category_budget(client, auth_headers):
    res = client.put("/api/budgets/Food", json={"limit_amount": 1000}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["category"] == "Food"
    assert res.json()["limit_amount"] == 1000
    assert res.json()["status"] == "ok"

    listing = client.get("/api/budgets", headers=auth_headers).json()
    assert [b["category"] for b in listing] == ["Food"]


def test_setting_again_replaces_the_limit(client, auth_headers):
    client.put("/api/budgets/Food", json={"limit_amount": 1000}, headers=auth_headers)
    client.put("/api/budgets/Food", json={"limit_amount": 2500}, headers=auth_headers)
    listing = client.get("/api/budgets", headers=auth_headers).json()
    assert len(listing) == 1
    assert listing[0]["limit_amount"] == 2500


def test_status_moves_from_ok_to_warning_to_over(client, auth_headers):
    client.put("/api/budgets/Food", json={"limit_amount": 1000}, headers=auth_headers)

    spend(client, auth_headers, 500)
    item = client.get("/api/budgets", headers=auth_headers).json()[0]
    assert (item["percent_used"], item["status"]) == (50.0, "ok")

    spend(client, auth_headers, 350)
    item = client.get("/api/budgets", headers=auth_headers).json()[0]
    assert (item["percent_used"], item["status"], item["remaining"]) == (85.0, "warning", 150.0)

    spend(client, auth_headers, 200)
    item = client.get("/api/budgets", headers=auth_headers).json()[0]
    assert (item["percent_used"], item["status"]) == (105.0, "over")


def test_only_counts_spending_in_that_category(client, auth_headers):
    client.put("/api/budgets/Food", json={"limit_amount": 1000}, headers=auth_headers)
    spend(client, auth_headers, 900, category="Transport")
    item = client.get("/api/budgets", headers=auth_headers).json()[0]
    assert item["spent"] == 0


def test_invalid_limit_and_category_rejected(client, auth_headers):
    assert client.put(
        "/api/budgets/Food", json={"limit_amount": 0}, headers=auth_headers
    ).status_code == 422
    assert client.put(
        "/api/budgets/Spaceships", json={"limit_amount": 10}, headers=auth_headers
    ).status_code == 422


def test_delete_budget(client, auth_headers):
    client.put("/api/budgets/Food", json={"limit_amount": 1000}, headers=auth_headers)
    assert client.delete("/api/budgets/Food", headers=auth_headers).status_code == 204
    assert client.get("/api/budgets", headers=auth_headers).json() == []
    assert client.delete("/api/budgets/Food", headers=auth_headers).status_code == 404


def test_budgets_are_private_to_each_user(client, auth_headers):
    client.put("/api/budgets/Food", json={"limit_amount": 1000}, headers=auth_headers)
    other = register_and_login(client, email="ravi@example.com")
    assert client.get("/api/budgets", headers=other).json() == []
