
from datetime import timedelta

from flask import jsonify

from app import db
from app.models import User
from app.permissions import roles_required


def register_user(client):
    return client.post(
        "/register",
        data={
            "username": "stockpilot_test",
            "email": "stockpilot_test@example.com",
            "password": "TestPassword123!",
        },
        follow_redirects=True,
    )


def login_user(client):
    return client.post(
        "/login",
        data={
            "identifier": "stockpilot_test",
            "password": "TestPassword123!",
        },
    )


def test_dashboard_requires_login(client):
    response = client.get("/", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_user_can_register(client, app):
    response = register_user(client)

    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(
            username="stockpilot_test"
        ).first()

        assert user is not None
        assert user.role == "staff"
        assert user.password_hash != "TestPassword123!"


def test_user_can_login_and_session_survives_refresh(client):
    register_user(client)

    response = login_user(client)
    assert response.status_code == 302

    assert client.get("/").status_code == 200
    assert client.get("/").status_code == 200


def test_logout_removes_dashboard_access(client):
    register_user(client)
    login_user(client)

    assert client.get("/").status_code == 200

    response = client.post("/logout", follow_redirects=False)
    assert response.status_code == 302

    dashboard = client.get("/", follow_redirects=False)
    assert dashboard.status_code == 302
    assert "/login" in dashboard.headers["Location"]


def test_staff_cannot_access_admin_only_route(client, app):
    @app.get("/test-admin-only")
    @roles_required("admin")
    def test_admin_only():
        return jsonify({"message": "admin access granted"})

    register_user(client)
    login_user(client)

    response = client.get("/test-admin-only")

    assert response.status_code == 403


def test_registration_cannot_assign_admin_role(client, app):
    response = client.post(
        "/register",
        data={
            "username": "attempted_admin",
            "email": "attempted_admin@example.com",
            "password": "TestPassword123!",
            "role": "admin",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(
            username="attempted_admin"
        ).first()

        assert user is not None
        assert user.role == "staff"


def test_admin_can_access_admin_only_route(client, app):
    @app.get("/test-admin-access")
    @roles_required("admin")
    def test_admin_access():
        return jsonify({"message": "admin access granted"})

    register_user(client)

    # Promote the test account directly in the test database.
    with app.app_context():
        user = User.query.filter_by(
            username="stockpilot_test"
        ).first()
        user.role = "admin"
        db.session.commit()

    login_user(client)

    response = client.get("/test-admin-access")

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "admin access granted"
    }


def test_staff_cannot_access_real_admin_users_page(client):
    register_user(client)
    login_user(client)

    response = client.get("/admin/users")

    assert response.status_code == 403


def test_admin_can_access_real_admin_users_page(client, app):
    register_user(client)

    # Promote the test account in the test database.
    with app.app_context():
        user = User.query.filter_by(
            username="stockpilot_test"
        ).first()

        user.role = "admin"
        db.session.commit()

    login_user(client)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert b"User Management" in response.data
    assert b"stockpilot_test" in response.data

def test_session_cookie_security_configuration(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False


def test_session_lifetime_is_30_minutes(app):
    from datetime import timedelta

    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(
        minutes=30
    )


def test_session_is_permanent_after_login(client):
    register_user(client)
    login_user(client)

    with client.session_transaction() as session:
        assert session.permanent is True


def test_session_cookie_has_security_flags(client):
    register_user(client)

    response = client.post(
        "/login",
        data={
            "identifier": "stockpilot_test",
            "password": "TestPassword123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    cookie_header = response.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie_header
    assert "SameSite=Lax" in cookie_header
    assert "Secure" not in cookie_header


def test_session_cookie_security_configuration(app):
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["SESSION_COOKIE_SECURE"] is False


def test_session_lifetime_is_30_minutes(app):
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(
        minutes=30
    )

def test_session_is_permanent_after_login(client):
    register_user(client)
    login_user(client)

    with client.session_transaction() as session:
        assert session.permanent is True


def test_session_cookie_has_security_flags(client):
    register_user(client)

    response = login_user(client)

    assert response.status_code == 302

    cookie_header = response.headers.get("Set-Cookie", "")

    assert "HttpOnly" in cookie_header
    assert "SameSite=Lax" in cookie_header
    assert "Secure" not in cookie_header

def test_anonymous_user_cannot_access_admin_users_page(client):
    response = client.get(
        "/admin/users",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]