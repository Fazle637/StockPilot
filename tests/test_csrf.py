import re

import pytest

from app import create_app, db

PASSWORD = "TestPassword123!"


@pytest.fixture
def csrf_client():
    """A client for an app with CSRF protection switched ON."""
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": True,
    })
    
    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.session.remove()
        db.drop_all()


def extract_token(html):
    match = re.search(
        r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', html
    ) or re.search(
        r'<input[^>]*value="([^"]+)"[^>]*name="csrf_token"', html
    )
    assert match, "No CSRF token found on the page"
    return match.group(1)


def register_and_login_with_csrf(client, username, email):
    token = extract_token(client.get("/register").get_data(as_text=True))
    response = client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": PASSWORD,
            "csrf_token": token,
        },
    )
    assert response.status_code == 302, response.get_data(as_text=True)

    token = extract_token(client.get("/login").get_data(as_text=True))
    response = client.post(
        "/login",
        data={
            "identifier": username,
            "password": PASSWORD,
            "csrf_token": token,
        },
    )
    assert response.status_code == 302, response.get_data(as_text=True)

    with client.session_transaction() as session:
        assert "_user_id" in session


def test_login_without_csrf_token_is_rejected(csrf_client):
    response = csrf_client.post(
        "/login",
        data={"identifier": "nobody", "password": PASSWORD},
    )
    assert response.status_code == 400


def test_register_without_csrf_token_is_rejected(csrf_client):
    response = csrf_client.post(
        "/register",
        data={
            "username": "no_token_user",
            "email": "no_token_user@example.com",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 400


def test_register_with_valid_csrf_token_is_accepted(csrf_client):
    # Proves the guard is selective, not rejecting every request.
    token = extract_token(csrf_client.get("/register").get_data(as_text=True))
    response = csrf_client.post(
        "/register",
        data={
            "username": "token_user",
            "email": "token_user@example.com",
            "password": PASSWORD,
            "csrf_token": token,
        },
    )
    assert response.status_code == 302


@pytest.mark.parametrize(
    "path",
    [
        "/logout",
        "/inventory/new",
        "/inventory/1/edit",
        "/inventory/1/notes",
        "/orders/new",
        "/orders/1/edit",
        "/orders/1/delete",
    ],
)
def test_state_changing_web_routes_reject_missing_csrf_token(csrf_client, path):
    response = csrf_client.post(path, data={})
    assert response.status_code == 400, (
        f"POST {path} accepted a request with no CSRF token"
    )


def test_json_api_write_requires_csrf_token(csrf_client):
    register_and_login_with_csrf(
        csrf_client, "csrf_api_user", "csrf_api_user@example.com"
    )

    # A fresh token from a logged-in page (the session may rotate at login).
    token = extract_token(csrf_client.get("/").get_data(as_text=True))

    product = {
        "name": "CSRF API Product",
        "sku": "CSRF-API-001",
        "description": "probe",
        "quantity": 5,
        "unit_price": "9.99",
    }

    # Logged in, but no CSRF header: must be rejected.
    blocked = csrf_client.post("/api/products", json=product)
    assert blocked.status_code == 400

    # Same request with the header: accepted.
    allowed = csrf_client.post(
        "/api/products",
        json=product,
        headers={"X-CSRFToken": token},
    )
    assert allowed.status_code == 201, allowed.get_data(as_text=True)