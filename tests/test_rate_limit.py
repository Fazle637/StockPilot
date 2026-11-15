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
        "LOGIN_MAX_ATTEMPTS": 3,
        "LOGIN_WINDOW_SECONDS": 60,
    })

    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.session.remove()
        db.drop_all()


def register(client, username="limit_user"):
    response = client.post(
        "/register",
        data={
            "username": username,
            "email": f"{username}@example.com",
            "password": PASSWORD,
        },
    )
    assert response.status_code == 302


def bad_login(client, username="limit_user", **kwargs):
    return client.post(
        "/login",
        data={"identifier": username, "password": "wrong-password-1"},
        **kwargs,
    )


def good_login(client, username="limit_user", **kwargs):
    return client.post(
        "/login",
        data={"identifier": username, "password": PASSWORD},
        **kwargs,
    )


def test_login_is_blocked_after_repeated_failures(limited_client):
    register(limited_client)

    for _ in range(3):
        assert bad_login(limited_client).status_code == 200

    assert bad_login(limited_client).status_code == 429

    # Even the correct password is refused while the client is blocked.
    assert good_login(limited_client).status_code == 429


def test_other_client_address_is_not_blocked(limited_client):
    register(limited_client)

    for _ in range(3):
        bad_login(limited_client)

    assert bad_login(limited_client).status_code == 429

    other = good_login(
        limited_client,
        environ_base={"REMOTE_ADDR": "10.0.0.9"},
    )
    assert other.status_code == 302


def test_successful_login_resets_the_failure_count(limited_client):
    register(limited_client)

    for _ in range(2):
        assert bad_login(limited_client).status_code == 200

    assert good_login(limited_client).status_code == 302

    for _ in range(2):
        assert bad_login(limited_client).status_code == 200

    assert good_login(limited_client).status_code == 302