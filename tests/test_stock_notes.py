import pytest
from werkzeug.security import generate_password_hash

from app import db
from app.models import Product, StockNote, User


@pytest.fixture
def note_users(app):
    """Create two users and a product owned by the first user."""
    with app.app_context():
        user_a = User(
            username="noteuser_a",
            email="noteuser_a@example.com",
            password_hash=generate_password_hash(
                "TestPassword123!",
                method="scrypt",
            ),
            role="staff",
        )

        user_b = User(
            username="noteuser_b",
            email="noteuser_b@example.com",
            password_hash=generate_password_hash(
                "TestPassword123!",
                method="scrypt",
            ),
            role="staff",
        )

        db.session.add_all([user_a, user_b])
        db.session.commit()

        product = Product(
            name="Notes Test Product",
            sku="NOTES-TEST-001",
            description="Product used for stock note tests",
            quantity=10,
            unit_price=25.00,
            owner_id=user_a.id,
        )

        db.session.add(product)
        db.session.commit()

        yield {
            "user_a_id": user_a.id,
            "user_b_id": user_b.id,
            "product_id": product.id,
        }



def login_user(client, username):
    """Log in using the application's existing login form."""
    return client.post(
        "/login",
        data={
            "identifier": username,
            "password": "TestPassword123!",
        },
        follow_redirects=True,
    )



def test_notes_page_requires_login(client, note_users):
    response = client.get(
        f"/inventory/{note_users['product_id']}/notes"
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_user_can_create_stock_note(client, note_users):
    login_user(client, "noteuser_a")

    response = client.post(
        f"/inventory/{note_users['product_id']}/notes",
        data={"content": "Stock checked successfully."},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Stock checked successfully." in response.data

    with client.application.app_context():
        note = StockNote.query.filter_by(
            product_id=note_users["product_id"]
        ).first()

        assert note is not None
        assert note.content == "Stock checked successfully."
        assert note.author_id == note_users["user_a_id"]


def test_another_user_can_read_stock_note(client, note_users):
    login_user(client, "noteuser_a")

    client.post(
        f"/inventory/{note_users['product_id']}/notes",
        data={"content": "Please check the next delivery."},
    )

    client.post("/logout", follow_redirects=True)
    login_user(client, "noteuser_b")

    response = client.get(
        f"/inventory/{note_users['product_id']}/notes"
    )

    assert response.status_code == 200
    assert b"Please check the next delivery." in response.data
    assert b"noteuser_a" in response.data


def test_empty_stock_note_is_rejected(client, note_users):
    login_user(client, "noteuser_a")

    response = client.post(
        f"/inventory/{note_users['product_id']}/notes",
        data={"content": "   "},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"A note cannot be empty." in response.data

    with client.application.app_context():
        assert StockNote.query.filter_by(
            product_id=note_users["product_id"]
        ).count() == 0


def test_stock_note_over_1000_characters_is_rejected(client, note_users):
    login_user(client, "noteuser_a")

    response = client.post(
        f"/inventory/{note_users['product_id']}/notes",
        data={"content": "x" * 1001},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"A note cannot exceed 1000 characters." in response.data

    with client.application.app_context():
        assert StockNote.query.filter_by(
            product_id=note_users["product_id"]
        ).count() == 0