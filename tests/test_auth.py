
import pytest
from flask import jsonify

from app import create_app, db
from app.models import User
from app.permissions import roles_required


@pytest.fixture
def app():
    test_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


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
