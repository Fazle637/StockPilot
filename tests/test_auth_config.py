import pytest

from app import create_app
from app.models import User
from tests.test_inventory import register_and_login

PASSWORD = "TestPassword123!"


def get_hash(client, username):
    with client.application.app_context():
        user = User.query.filter_by(username=username).first()
        return user.password_hash


def test_registered_password_is_stored_as_a_scrypt_hash(client):
    register_and_login(client, "hash_user_a", "hash_user_a@example.com")

    stored = get_hash(client, "hash_user_a")

    assert stored.startswith("scrypt:")
    assert PASSWORD not in stored


def test_same_password_gets_a_different_salted_hash(client):
    register_and_login(client, "hash_user_a", "hash_user_a@example.com")
    client.post("/logout")
    register_and_login(client, "hash_user_b", "hash_user_b@example.com")

    assert get_hash(client, "hash_user_a") != get_hash(client, "hash_user_b")


@pytest.mark.parametrize("value", [None, ""])
def test_app_refuses_to_start_without_a_secret_key(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", value)

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        })
        