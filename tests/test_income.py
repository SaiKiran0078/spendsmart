from tests.conftest import register_and_login


def add_income(client, headers, **overrides):
    payload = {"source": "Salary", "amount": 50000, "received_on": "2026-03-01"}
    payload.update(overrides)
    return client.post("/api/income", json=payload, headers=headers)


def test_requires_authentication(client):
    assert client.get("/api/income").status_code == 401


def test_create_and_list_income(client, auth_headers):
    res = add_income(client, auth_headers)
    assert res.status_code == 201
    assert res.json()["source"] == "Salary"
    assert len(client.get("/api/income", headers=auth_headers).json()) == 1


def test_validation_rejects_bad_income(client, auth_headers):
    assert add_income(client, auth_headers, amount=0).status_code == 422
    assert add_income(client, auth_headers, source="   ").status_code == 422


def test_update_and_delete_income(client, auth_headers):
    income_id = add_income(client, auth_headers).json()["id"]
    res = client.put(f"/api/income/{income_id}", json={"amount": 55000}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["amount"] == 55000
    assert res.json()["source"] == "Salary"

    assert client.delete(f"/api/income/{income_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/income", headers=auth_headers).json() == []


def test_date_filter_and_search(client, auth_headers):
    add_income(client, auth_headers, source="Salary", received_on="2026-03-01")
    add_income(client, auth_headers, source="Freelance", received_on="2026-04-10")

    march = client.get(
        "/api/income?start_date=2026-03-01&end_date=2026-03-31", headers=auth_headers
    ).json()
    assert [i["source"] for i in march] == ["Salary"]

    found = client.get("/api/income?search=free", headers=auth_headers).json()
    assert [i["source"] for i in found] == ["Freelance"]


def test_inverted_date_range_rejected(client, auth_headers):
    res = client.get("/api/income?start_date=2026-05-01&end_date=2026-04-01", headers=auth_headers)
    assert res.status_code == 422


def test_users_cannot_touch_each_others_income(client, auth_headers):
    income_id = add_income(client, auth_headers).json()["id"]
    other = register_and_login(client, email="ravi@example.com")
    res = client.put(f"/api/income/{income_id}", json={"amount": 1}, headers=other)
    assert res.status_code == 404
    assert client.delete(f"/api/income/{income_id}", headers=other).status_code == 404
    assert client.get("/api/income", headers=other).json() == []
