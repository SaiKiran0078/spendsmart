from datetime import date, timedelta

from tests.conftest import register_and_login


def make_goal(client, headers, **overrides):
    payload = {"name": "Laptop", "target_amount": 12000}
    payload.update(overrides)
    return client.post("/api/goals", json=payload, headers=headers)


def test_requires_authentication(client):
    assert client.get("/api/goals").status_code == 401


def test_create_goal_starts_at_zero(client, auth_headers):
    res = make_goal(client, auth_headers)
    assert res.status_code == 201
    body = res.json()
    assert body["saved_amount"] == 0
    assert body["remaining"] == 12000
    assert body["progress_percent"] == 0
    assert body["is_complete"] is False
    assert body["days_left"] is None
    assert body["monthly_needed"] is None


def test_contribute_updates_progress(client, auth_headers):
    goal_id = make_goal(client, auth_headers).json()["id"]
    res = client.post(
        f"/api/goals/{goal_id}/contribute", json={"amount": 3000}, headers=auth_headers
    )
    assert res.status_code == 200
    assert res.json()["saved_amount"] == 3000
    assert res.json()["progress_percent"] == 25.0
    assert res.json()["remaining"] == 9000


def test_goal_completes_when_target_reached(client, auth_headers):
    goal_id = make_goal(client, auth_headers).json()["id"]
    res = client.post(
        f"/api/goals/{goal_id}/contribute", json={"amount": 12000}, headers=auth_headers
    )
    assert res.json()["is_complete"] is True
    assert res.json()["progress_percent"] == 100.0
    assert res.json()["remaining"] == 0


def test_withdraw_and_cannot_overdraw(client, auth_headers):
    goal_id = make_goal(client, auth_headers, saved_amount=1000).json()["id"]
    ok = client.post(
        f"/api/goals/{goal_id}/contribute", json={"amount": -400}, headers=auth_headers
    )
    assert ok.json()["saved_amount"] == 600

    too_much = client.post(
        f"/api/goals/{goal_id}/contribute", json={"amount": -5000}, headers=auth_headers
    )
    assert too_much.status_code == 400


def test_zero_contribution_rejected(client, auth_headers):
    goal_id = make_goal(client, auth_headers).json()["id"]
    res = client.post(f"/api/goals/{goal_id}/contribute", json={"amount": 0}, headers=auth_headers)
    assert res.status_code == 422


def test_deadline_gives_monthly_saving_hint(client, auth_headers):
    deadline = (date.today() + timedelta(days=365)).isoformat()
    body = make_goal(client, auth_headers, deadline=deadline).json()
    assert body["days_left"] == 365
    assert 900 < body["monthly_needed"] < 1100  # 12000 over ~12 months


def test_update_goal_and_clear_deadline(client, auth_headers):
    deadline = (date.today() + timedelta(days=100)).isoformat()
    goal_id = make_goal(client, auth_headers, deadline=deadline).json()["id"]

    res = client.put(
        f"/api/goals/{goal_id}",
        json={"name": "Gaming laptop", "target_amount": 15000, "deadline": None},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Gaming laptop"
    assert res.json()["target_amount"] == 15000
    assert res.json()["deadline"] is None


def test_delete_goal(client, auth_headers):
    goal_id = make_goal(client, auth_headers).json()["id"]
    assert client.delete(f"/api/goals/{goal_id}", headers=auth_headers).status_code == 204
    assert client.get("/api/goals", headers=auth_headers).json() == []


def test_validation(client, auth_headers):
    assert make_goal(client, auth_headers, target_amount=0).status_code == 422
    assert make_goal(client, auth_headers, name="  ").status_code == 422


def test_users_cannot_access_each_others_goals(client, auth_headers):
    goal_id = make_goal(client, auth_headers).json()["id"]
    other = register_and_login(client, email="ravi@example.com")
    assert client.post(
        f"/api/goals/{goal_id}/contribute", json={"amount": 10}, headers=other
    ).status_code == 404
    assert client.delete(f"/api/goals/{goal_id}", headers=other).status_code == 404
    assert client.get("/api/goals", headers=other).json() == []
