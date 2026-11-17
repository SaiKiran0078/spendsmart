from app.models import Expense
from tests.conftest import TestingSession, register_and_login

EMAIL = "asha@example.com"
PASSWORD = "strongpass123"


def login(client, email=EMAIL, password=PASSWORD):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def test_update_profile_name(client, auth_headers):
    res = client.put("/api/auth/me", json={"full_name": "  Asha R.  "}, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["full_name"] == "Asha R."


def test_update_profile_rejects_blank_name(client, auth_headers):
    res = client.put("/api/auth/me", json={"full_name": "   "}, headers=auth_headers)
    assert res.status_code == 422


def test_change_password_success(client, auth_headers):
    res = client.post(
        "/api/auth/me/password",
        json={"current_password": PASSWORD, "new_password": "brand-new-pass-9"},
        headers=auth_headers,
    )
    assert res.status_code == 204
    assert login(client, password=PASSWORD).status_code == 401
    assert login(client, password="brand-new-pass-9").status_code == 200


def test_change_password_requires_correct_current_password(client, auth_headers):
    res = client.post(
        "/api/auth/me/password",
        json={"current_password": "not-my-password", "new_password": "brand-new-pass-9"},
        headers=auth_headers,
    )
    assert res.status_code == 400


def test_change_password_validates_new_password(client, auth_headers):
    res = client.post(
        "/api/auth/me/password",
        json={"current_password": PASSWORD, "new_password": "short"},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_delete_account_requires_correct_password(client, auth_headers):
    res = client.request(
        "DELETE", "/api/auth/me", json={"password": "wrong-password"}, headers=auth_headers
    )
    assert res.status_code == 400
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 200


def test_delete_account_removes_user_and_their_data(client, auth_headers):
    client.post(
        "/api/expenses",
        json={"title": "Lunch", "amount": 100, "category": "Food"},
        headers=auth_headers,
    )
    res = client.request(
        "DELETE", "/api/auth/me", json={"password": PASSWORD}, headers=auth_headers
    )
    assert res.status_code == 204

    assert login(client).status_code == 401
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 401
    with TestingSession() as db:
        assert db.query(Expense).count() == 0


def test_login_is_rate_limited_after_repeated_failures(client):
    client.post(
        "/api/auth/register",
        json={"email": EMAIL, "full_name": "Asha Rao", "password": PASSWORD},
    )
    for _ in range(5):
        assert login(client, password="wrong-password").status_code == 401

    blocked = login(client, password="wrong-password")
    assert blocked.status_code == 429
    assert "retry-after" in blocked.headers
    # Even the correct password is refused while the lock-out lasts.
    assert login(client).status_code == 429


def test_rate_limit_is_per_email(client):
    client.post(
        "/api/auth/register",
        json={"email": EMAIL, "full_name": "Asha Rao", "password": PASSWORD},
    )
    for _ in range(5):
        login(client, password="wrong-password")
    other = register_and_login(client, email="ravi@example.com")
    assert client.get("/api/auth/me", headers=other).status_code == 200


def test_successful_login_clears_failed_attempts(client):
    client.post(
        "/api/auth/register",
        json={"email": EMAIL, "full_name": "Asha Rao", "password": PASSWORD},
    )
    for _ in range(4):
        login(client, password="wrong-password")
    assert login(client).status_code == 200
    for _ in range(4):
        assert login(client, password="wrong-password").status_code == 401


def test_security_headers_are_present(client):
    res = client.get("/api/health")
    assert res.headers["x-content-type-options"] == "nosniff"
    assert res.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in res.headers["content-security-policy"]
