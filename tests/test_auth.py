from tests.conftest import register_and_login

USER = {"email": "asha@example.com", "full_name": "Asha Rao", "password": "strongpass123"}


def test_register_success(client):
    res = client.post("/api/auth/register", json=USER)
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == USER["email"]
    assert "password" not in body and "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    client.post("/api/auth/register", json=USER)
    res = client.post("/api/auth/register", json=USER)
    assert res.status_code == 409


def test_register_short_password_rejected(client):
    res = client.post("/api/auth/register", json={**USER, "password": "short"})
    assert res.status_code == 422


def test_login_success_returns_token(client):
    client.post("/api/auth/register", json=USER)
    res = client.post(
        "/api/auth/login", data={"username": USER["email"], "password": USER["password"]}
    )
    assert res.status_code == 200
    assert res.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json=USER)
    res = client.post("/api/auth/login", data={"username": USER["email"], "password": "wrong-pass"})
    assert res.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_profile(client, auth_headers):
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["full_name"] == "Asha Rao"


def test_invalid_token_rejected(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_set_budget(client):
    headers = register_and_login(client)
    res = client.put("/api/auth/me/budget", json={"monthly_budget": 25000}, headers=headers)
    assert res.status_code == 200
    assert res.json()["monthly_budget"] == 25000



def test_register_rejects_blank_full_name(client):
    res = client.post("/api/auth/register", json={**USER, "full_name": "   "})
    assert res.status_code == 422


def test_register_rejects_password_over_bcrypt_byte_limit(client):
    # 40 copies of a 2-byte character exceed bcrypt's 72-byte input limit.
    res = client.post("/api/auth/register", json={**USER, "password": "é" * 40})
    assert res.status_code == 422
