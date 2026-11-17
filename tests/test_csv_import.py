from datetime import date

from tests.conftest import register_and_login

CSV_HEADER = "title,amount,category,date,note\n"


def upload(client, headers, content, name="expenses.csv"):
    if isinstance(content, str):
        content = content.encode("utf-8")
    return client.post(
        "/api/expenses/import/csv", files={"file": (name, content, "text/csv")}, headers=headers
    )


def test_requires_authentication(client):
    res = client.post("/api/expenses/import/csv", files={"file": ("a.csv", b"title,amount\n")})
    assert res.status_code == 401


def test_imports_valid_rows(client, auth_headers):
    content = CSV_HEADER + "Lunch,150.50,Food,2026-03-02,With team\nBus,40,Transport,2026-03-03,\n"
    res = upload(client, auth_headers, content)
    assert res.status_code == 200
    assert res.json() == {"imported": 2, "skipped": 0, "errors": []}

    rows = client.get("/api/expenses", headers=auth_headers).json()
    assert {r["title"] for r in rows} == {"Lunch", "Bus"}
    lunch = next(r for r in rows if r["title"] == "Lunch")
    assert (lunch["amount"], lunch["category"], lunch["spent_on"]) == (150.5, "Food", "2026-03-02")
    assert lunch["note"] == "With team"


def test_flexible_amount_date_and_category_formats(client, auth_headers):
    content = (
        CSV_HEADER
        + 'Dinner,"₹1,250.50",food,25/12/2025,\n'
        + "Mystery,99,Spaceships,2025-12-26,\n"
        + "No date,10,Health,,\n"
    )
    assert upload(client, auth_headers, content).json()["imported"] == 3

    rows = {r["title"]: r for r in client.get("/api/expenses", headers=auth_headers).json()}
    assert rows["Dinner"]["amount"] == 1250.5
    assert rows["Dinner"]["category"] == "Food"
    assert rows["Dinner"]["spent_on"] == "2025-12-25"
    assert rows["Mystery"]["category"] == "Other"  # unknown categories fall back to Other
    assert rows["No date"]["spent_on"] == date.today().isoformat()


def test_bad_rows_are_skipped_and_reported(client, auth_headers):
    content = (
        CSV_HEADER
        + "Good,10,Food,2026-01-01,\n"
        + "Negative,-5,Food,2026-01-01,\n"
        + ",20,Food,2026-01-01,\n"
        + "Bad date,30,Food,not-a-date,\n"
        + "No amount,,Food,2026-01-01,\n"
    )
    body = upload(client, auth_headers, content).json()
    assert body["imported"] == 1
    assert body["skipped"] == 4
    assert len(body["errors"]) == 4
    assert body["errors"][0].startswith("Line 3")


def test_required_columns_must_exist(client, auth_headers):
    res = upload(client, auth_headers, "name,price\nLunch,10\n")
    assert res.status_code == 400


def test_empty_and_non_utf8_files_are_rejected(client, auth_headers):
    assert upload(client, auth_headers, b"").status_code == 400
    assert upload(client, auth_headers, b"\xff\xfe\x00\x00bad").status_code == 400


def test_oversized_files_are_rejected(client, auth_headers):
    big = b"title,amount\n" + b"x," * 600_000
    assert upload(client, auth_headers, big).status_code == 413


def test_export_then_import_round_trip(client, auth_headers):
    client.post(
        "/api/expenses",
        json={"title": "=SUM(1+1)", "amount": 75, "category": "Shopping", "spent_on": "2026-02-02"},
        headers=auth_headers,
    )
    exported = client.get("/api/expenses/export/csv", headers=auth_headers).text
    assert "'=SUM(1+1)" in exported  # protected in the file

    assert upload(client, auth_headers, exported).json()["imported"] == 1
    titles = [r["title"] for r in client.get("/api/expenses", headers=auth_headers).json()]
    assert titles.count("=SUM(1+1)") == 2  # restored to the original text on import


def test_imported_expenses_belong_to_the_importing_user(client, auth_headers):
    other = register_and_login(client, email="ravi@example.com")
    upload(client, auth_headers, CSV_HEADER + "Lunch,10,Food,2026-01-01,\n")
    assert client.get("/api/expenses", headers=other).json() == []


def test_export_import_round_trip_preserves_leading_whitespace(client, auth_headers):
    original_title = "   =SUM(1+1)"
    created = client.post(
        "/api/expenses",
        json={"title": original_title, "amount": 25, "category": "Food"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    assert created.json()["title"] == original_title

    exported = client.get("/api/expenses/export/csv", headers=auth_headers).text
    assert "'   =SUM(1+1)" in exported

    imported = upload(client, auth_headers, exported)
    assert imported.status_code == 200
    assert imported.json()["imported"] == 1

    titles = [row["title"] for row in client.get("/api/expenses", headers=auth_headers).json()]
    assert titles.count(original_title) == 2
