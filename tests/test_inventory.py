
import pytest

from app import create_app, db
from app.models import User, Product


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


def register_and_login(client, username, email):
    """Register a staff user and log in with that user's credentials."""
    response = client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 302, response.get_data(as_text=True)

    response = client.post(
        "/login",
        data={
            "identifier": username,
            "password": "TestPassword123!",
        },
    )
    assert response.status_code == 302, response.get_data(as_text=True)

    # A redirect alone does not prove authentication succeeded.
    with client.session_transaction() as session:
        assert "_user_id" in session, (
            f"Login did not establish a session for {username!r}: {dict(session)}"
        )


def test_inventory_requires_login(client):
    response = client.get("/inventory/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logged_in_user_can_create_product(client, app):
    register_and_login(
        client, "inventory_user", "inventory@example.com"
    )

    response = client.post("/inventory/new", data={
        "name": "Wireless Mouse",
        "sku": "SP-MOUSE-001",
        "description": "Test inventory product",
        "quantity": "25",
        "unit_price": "19.99",
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Wireless Mouse" in response.data

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-MOUSE-001"
        ).first()

        assert product is not None
        assert product.quantity == 25
        assert float(product.unit_price) == 19.99


def test_negative_quantity_is_rejected(client, app):
    register_and_login(
        client, "quantity_user", "quantity@example.com"
    )

    response = client.post("/inventory/new", data={
        "name": "Invalid Product",
        "sku": "SP-INVALID-001",
        "description": "Invalid quantity test",
        "quantity": "-1",
        "unit_price": "10.00",
    })

    assert response.status_code == 400

    with app.app_context():
        assert Product.query.filter_by(
            sku="SP-INVALID-001"
        ).first() is None


def test_invalid_price_is_rejected(client, app):
    register_and_login(
        client, "price_user", "price@example.com"
    )

    response = client.post("/inventory/new", data={
        "name": "Invalid Price Product",
        "sku": "SP-INVALID-002",
        "description": "Invalid price test",
        "quantity": "5",
        "unit_price": "-10.00",
    })

    assert response.status_code == 400

    with app.app_context():
        assert Product.query.filter_by(
            sku="SP-INVALID-002"
        ).first() is None


def test_users_cannot_see_each_others_products(client, app):
    # Create two separate users with separate browser sessions.
    register_and_login(
        client, "owner_user", "owner@example.com"
    )

    with app.app_context():
        owner = User.query.filter_by(
            username="owner_user"
        ).first()

        product = Product(
            name="Owner Secret Product",
            sku="SP-OWNER-001",
            description="Private test product",
            quantity=10,
            unit_price=15.00,
            owner_id=owner.id,
        )
        db.session.add(product)
        db.session.commit()

    # Log out the owner, then sign in as a different user.
    client.post("/logout")

    register_and_login(
        client, "other_user", "other@example.com"
    )

    response = client.get("/inventory/")

    assert response.status_code == 200
    assert b"Owner Secret Product" not in response.data
    assert b"SP-OWNER-001" not in response.data


def test_inventory_search_finds_matching_product(client):
    register_and_login(
        client, "search_user", "search@example.com"
    )

    client.post("/inventory/new", data={
        "name": "Wireless Keyboard",
        "sku": "SP-KEYBOARD-001",
        "description": "Search test",
        "quantity": "8",
        "unit_price": "29.99",
    })

    response = client.get("/inventory/?q=Keyboard")

    assert response.status_code == 200
    assert b"Wireless Keyboard" in response.data


def test_owner_can_edit_own_product(client, app):
    register_and_login(
        client, "edit_owner", "edit_owner@example.com"
    )

    client.post("/inventory/new", data={
        "name": "Original Product",
        "sku": "SP-EDIT-001",
        "description": "Before editing",
        "quantity": "10",
        "unit_price": "15.00",
    })

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-EDIT-001"
        ).first()
        product_id = product.id

    response = client.post(
        f"/inventory/{product_id}/edit",
        data={
            "name": "Updated Product",
            "sku": "SP-EDIT-001",
            "description": "After editing",
            "quantity": "20",
            "unit_price": "25.00",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Updated Product" in response.data

    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.name == "Updated Product"
        assert product.quantity == 20


def test_user_cannot_edit_another_users_product(client, app):
    register_and_login(
        client, "edit_victim", "edit_victim@example.com"
    )

    client.post("/inventory/new", data={
        "name": "Private Product",
        "sku": "SP-PRIVATE-EDIT",
        "description": "Owner's product",
        "quantity": "10",
        "unit_price": "15.00",
    })

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-PRIVATE-EDIT"
        ).first()
        product_id = product.id

    client.post("/logout")

    register_and_login(
        client, "edit_attacker", "edit_attacker@example.com"
    )

    response = client.post(
        f"/inventory/{product_id}/edit",
        data={
            "name": "Stolen Product",
            "sku": "SP-PRIVATE-EDIT",
            "description": "Unauthorized change",
            "quantity": "999",
            "unit_price": "1.00",
        },
    )

    assert response.status_code == 404

    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product.name == "Private Product"
        assert product.quantity == 10


def test_user_cannot_delete_another_users_product(client, app):
    register_and_login(
        client, "delete_victim", "delete_victim@example.com"
    )

    client.post("/inventory/new", data={
        "name": "Protected Product",
        "sku": "SP-PRIVATE-DELETE",
        "description": "Owner's product",
        "quantity": "5",
        "unit_price": "12.00",
    })

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-PRIVATE-DELETE"
        ).first()
        product_id = product.id

    client.post("/logout")

    register_and_login(
        client, "delete_attacker", "delete_attacker@example.com"
    )

    response = client.post(
        f"/inventory/{product_id}/delete"
    )

    assert response.status_code == 404

    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product is not None
        assert product.name == "Protected Product"


def test_owner_can_delete_own_product(client, app):
    register_and_login(
        client, "delete_owner", "delete_owner@example.com"
    )

    client.post("/inventory/new", data={
        "name": "Temporary Product",
        "sku": "SP-DELETE-OWN",
        "description": "Temporary test product",
        "quantity": "3",
        "unit_price": "5.00",
    })

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-DELETE-OWN"
        ).first()
        product_id = product.id

    response = client.post(
        f"/inventory/{product_id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Product deleted successfully." in response.data

    with app.app_context():
        assert db.session.get(Product, product_id) is None

def test_products_api_requires_login(client):
    response = client.get("/api/products")

    assert response.status_code == 401
    assert response.is_json
    assert response.get_json() == {
        "error": "Authentication required."
    }

def test_api_users_cannot_access_each_others_products(app):
    from werkzeug.security import generate_password_hash

    owner_client = app.test_client()
    attacker_client = app.test_client()

    # 1. Create two users and a product owned by User A.
    with app.app_context():
        owner = User(
            username="apiowner",
            email="apiowner@example.com",
            password_hash=generate_password_hash(
                "TestPassword123!",
                method="scrypt",
            ),
            role="staff",
        )
        attacker = User(
            username="apiattacker",
            email="apiattacker@example.com",
            password_hash=generate_password_hash(
                "TestPassword123!",
                method="scrypt",
            ),
            role="staff",
        )

        db.session.add_all([owner, attacker])
        db.session.commit()

        owner_id = owner.id
        attacker_id = attacker.id
        assert owner_id != attacker_id

        product = Product(
            name="Private API Product",
            sku="API-PRIVATE-001",
            description="This product belongs to User A.",
            quantity=10,
            unit_price=25.00,
            owner_id=owner_id,
        )
        db.session.add(product)
        db.session.commit()
        product_id = product.id
        assert product.owner_id == owner_id

    # 2. Authenticate each user through a separate test client.
    owner_login = owner_client.post(
        "/login",
        data={
            "identifier": "apiowner",
            "password": "TestPassword123!",
        },
    )
    assert owner_login.status_code == 302, owner_login.get_data(as_text=True)
    
    attacker_login = attacker_client.post(
        "/login",
        data={
            "identifier": "apiattacker",
            "password": "TestPassword123!",
            },
    )
    print("ATTACKER LOGIN STATUS:", attacker_login.status_code)
    print("ATTACKER LOGIN REDIRECT:", attacker_login.headers.get("Location"))
    print("ATTACKER LOGIN RESPONSE:", attacker_login.get_data(as_text=True))
    
    with attacker_client.session_transaction() as session:
        print("ATTACKER SESSION AFTER LOGIN:", dict(session))
        
    assert attacker_login.status_code == 302, attacker_login.get_data(as_text=True)

    # 3. Verify that the clients have independent authenticated sessions.
    with owner_client.session_transaction() as session:
        owner_session = dict(session)
    with attacker_client.session_transaction() as session:
        attacker_session = dict(session)

    assert "_user_id" in owner_session, f"Owner session missing user id: {owner_session}"
    assert "_user_id" in attacker_session, f"Attacker session missing user id: {attacker_session}"
    assert owner_session["_user_id"] == str(owner_id)
    assert attacker_session["_user_id"] == str(attacker_id)
    assert owner_session["_user_id"] != attacker_session["_user_id"]

    # 4. User B must not see User A's product in the list.
    list_response = attacker_client.get("/api/products")
    assert list_response.status_code == 200, list_response.get_data(as_text=True)
    listed_products = list_response.get_json()
    assert isinstance(listed_products, list), listed_products
    assert product_id not in [item["id"] for item in listed_products]

    # 5. User B must not read User A's product.
    read_response = attacker_client.get(f"/api/products/{product_id}")
    assert read_response.status_code == 404

    # 6. User B must not update User A's product.
    update_response = attacker_client.patch(
        f"/api/products/{product_id}",
        json={"name": "Hijacked Product"},
    )
    assert update_response.status_code == 404

    # 7. User B must not delete User A's product.
    delete_response = attacker_client.delete(f"/api/products/{product_id}")
    assert delete_response.status_code == 404

    # 8. Confirm the product remains unchanged.
    with app.app_context():
        product = db.session.get(Product, product_id)
        assert product is not None
        assert product.owner_id == owner_id
        assert product.owner_id != attacker_id
        assert product.name == "Private API Product"
        assert product.quantity == 10
