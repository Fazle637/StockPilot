import pytest

from app import create_app, db

PASSWORD = "TestPassword123!"


@pytest.fixture
def limited_client():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "REGISTER_MAX_ATTEMPTS": 3,
        "REGISTER_WINDOW_SECONDS": 60,
    })

    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.session.remove()
        db.drop_all()


def register(client, number, password=PASSWORD, **kwargs):
    return client.post(
        "/register",
        data={
            "username": f"reg_user_{number}",
            "email": f"reg_user_{number}@example.com",
            "password": password,
        },
        **kwargs,
    )


def test_registration_is_blocked_after_too_many_attempts(limited_client):
    for number in range(3):
        assert register(limited_client, number).status_code == 302

    assert register(limited_client, 3).status_code == 429


def test_failed_attempts_also_count(limited_client):
    for number in range(3):
        response = register(limited_client, number, password="short")
        assert response.status_code == 400

    assert register(limited_client, 3).status_code == 429


def test_other_client_address_is_not_blocked(limited_client):
    for number in range(3):
        register(limited_client, number)

    assert register(limited_client, 3).status_code == 429

    other = register(
        limited_client,
        4,
        environ_base={"REMOTE_ADDR": "10.0.0.9"},
    )
    assert other.status_code == 302