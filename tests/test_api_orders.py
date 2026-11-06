
import pytest

from app import db
from app.models import Order, Product, User

from tests.test_inventory import register_and_login


@pytest.fixture
def api_user(client):
    register_and_login(
        client,
        "order_api_user",
        "order_api_user@example.com",
    )
    return client


def create_product(client, sku="API-ORDER-001", quantity=10):
    response = client.post(
        "/api/products",
        json={
            "name": "Test Keyboard",
            "sku": sku,
            "description": "Product for order API tests",
            "quantity": quantity,
            "unit_price": "50.00",
        },
    )

    assert response.status_code == 201
    return response.get_json()


def test_api_user_can_create_order(api_user):
    product = create_product(api_user)

    response = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 3,
        },
    )

    assert response.status_code == 201

    order = response.get_json()

    assert order["status"] == "pending"
    assert order["items"][0]["quantity"] == 3
    assert order["items"][0]["unit_price"] == "50.00"

    updated_product = api_user.get(
        f"/api/products/{product['id']}"
    ).get_json()

    assert updated_product["quantity"] == 7


def test_api_order_rejects_insufficient_stock(api_user):
    product = create_product(
        api_user,
        sku="API-ORDER-002",
        quantity=2,
    )

    response = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 3,
        },
    )

    assert response.status_code == 409

    updated_product = api_user.get(
        f"/api/products/{product['id']}"
    ).get_json()

    assert updated_product["quantity"] == 2


def test_api_order_rejects_invalid_quantity(api_user):
    product = create_product(
        api_user,
        sku="API-ORDER-003",
    )

    response = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": -1,
        },
    )

    assert response.status_code == 400


def test_api_user_can_list_and_get_orders(api_user):
    product = create_product(
        api_user,
        sku="API-ORDER-004",
    )

    created = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 2,
        },
    )

    order_id = created.get_json()["id"]

    listing = api_user.get("/api/orders")

    assert listing.status_code == 200
    assert any(
        order["id"] == order_id
        for order in listing.get_json()
    )

    detail = api_user.get(f"/api/orders/{order_id}")

    assert detail.status_code == 200
    assert detail.get_json()["id"] == order_id


def test_api_order_rejects_another_users_product(client):
    register_and_login(
        client,
        "order_owner",
        "order_owner@example.com",
    )

    product = create_product(
        client,
        sku="API-ORDER-005",
    )

    # Log out the owner and authenticate as another user.
    client.post("/logout")

    register_and_login(
        client,
        "order_other",
        "order_other@example.com",
    )

    response = client.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 1,
        },
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Product not found."
    }


def test_api_user_cannot_read_another_users_order(client):
    # User 1 creates a product and an order.
    register_and_login(
        client,
        "order_reader_owner",
        "order_reader_owner@example.com",
    )

    product = create_product(
        client,
        sku="API-ORDER-006",
    )

    created = client.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 1,
        },
    )

    assert created.status_code == 201

    order_id = created.get_json()["id"]

    # End User 1's session.
    logout_response = client.post("/logout")

    assert logout_response.status_code == 302

    # User 2 registers and logs in using the same test client.
    register_and_login(
        client,
        "order_reader_other",
        "order_reader_other@example.com",
    )

    # User 2 must not see User 1's individual order.
    detail = client.get(f"/api/orders/{order_id}")

    assert detail.status_code == 404

    # User 2's list must not contain User 1's order.
    listing = client.get("/api/orders")

    assert listing.status_code == 200
    assert all(
        order["id"] != order_id
        for order in listing.get_json()
    )


def test_api_order_rejects_non_json_request(api_user):
    response = api_user.post(
        "/api/orders",
        data="not JSON",
        content_type="text/plain",
    )

    assert response.status_code == 400
    assert response.is_json
    assert "error" in response.get_json()


def test_api_user_can_update_pending_order_quantity(api_user):
    product = create_product(
        api_user,
        sku="API-ORDER-UPDATE-001",
        quantity=10,
    )

    created = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 3,
        },
    )

    assert created.status_code == 201

    order_id = created.get_json()["id"]

    response = api_user.patch(
        f"/api/orders/{order_id}",
        json={"quantity": 5},
    )

    assert response.status_code == 200
    assert response.get_json()["items"][0]["quantity"] == 5

    updated_product = api_user.get(
        f"/api/products/{product['id']}"
    ).get_json()

    assert updated_product["quantity"] == 5


def test_api_order_update_rejects_insufficient_stock(api_user):
    product = create_product(
        api_user,
        sku="API-ORDER-UPDATE-002",
        quantity=5,
    )

    created = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 3,
        },
    )

    order_id = created.get_json()["id"]

    response = api_user.patch(
        f"/api/orders/{order_id}",
        json={"quantity": 6},
    )

    assert response.status_code == 409

    # Rejected update must leave order and stock unchanged.
    detail = api_user.get(
        f"/api/orders/{order_id}"
    ).get_json()

    assert detail["items"][0]["quantity"] == 3

    updated_product = api_user.get(
        f"/api/products/{product['id']}"
    ).get_json()

    assert updated_product["quantity"] == 2


def test_api_user_cannot_update_another_users_order(client):
    register_and_login(
        client,
        "order_update_owner",
        "order_update_owner@example.com",
    )

    product = create_product(
        client,
        sku="API-ORDER-UPDATE-003",
        quantity=10,
    )

    created = client.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 2,
        },
    )

    assert created.status_code == 201

    order_id = created.get_json()["id"]

    client.post("/logout")

    register_and_login(
        client,
        "order_update_other",
        "order_update_other@example.com",
    )

    response = client.patch(
        f"/api/orders/{order_id}",
        json={"quantity": 4},
    )

    assert response.status_code == 404
    assert response.get_json() == {
        "error": "Order not found."
    }


def test_api_user_can_delete_pending_order_and_restore_stock(api_user):
    product = create_product(
        api_user,
        sku="API-ORDER-DELETE-001",
        quantity=10,
    )

    created = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 3,
        },
    )

    assert created.status_code == 201

    order_id = created.get_json()["id"]

    response = api_user.delete(
        f"/api/orders/{order_id}"
    )

    assert response.status_code == 200
    assert response.get_json() == {
        "message": "Order deleted successfully."
    }

    detail = api_user.get(
        f"/api/orders/{order_id}"
    )

    assert detail.status_code == 404

    updated_product = api_user.get(
        f"/api/products/{product['id']}"
    ).get_json()

    assert updated_product["quantity"] == 10


def test_api_user_cannot_delete_another_users_order(client):
    register_and_login(
        client,
        "order_delete_owner",
        "order_delete_owner@example.com",
    )

    product = create_product(
        client,
        sku="API-ORDER-DELETE-002",
        quantity=10,
    )

    created = client.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 2,
        },
    )

    assert created.status_code == 201

    order_id = created.get_json()["id"]

    client.post("/logout")

    register_and_login(
        client,
        "order_delete_other",
        "order_delete_other@example.com",
    )

    response = client.delete(
        f"/api/orders/{order_id}"
    )

    assert response.status_code == 404


def test_api_user_cannot_delete_non_pending_order(api_user):
    product = create_product(
        api_user,
        sku="API-ORDER-DELETE-003",
        quantity=10,
    )

    created = api_user.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 2,
        },
    )

    assert created.status_code == 201

    order_id = created.get_json()["id"]

    # Change the order status to simulate processing.
    order = db.session.get(Order, order_id)

    order.status = "processing"
    db.session.commit()

    response = api_user.delete(
        f"/api/orders/{order_id}"
    )

    assert response.status_code == 409

    updated_product = api_user.get(
        f"/api/products/{product['id']}"
    ).get_json()

    assert updated_product["quantity"] == 8


def test_api_admin_can_list_all_users_orders(client):
    # Staff user 1 creates an order.
    register_and_login(
        client,
        "api_admin_staff1",
        "api_admin_staff1@example.com",
    )

    product1 = create_product(
        client,
        sku="API-ADMIN-ORDER-001",
    )

    order1 = client.post(
        "/api/orders",
        json={
            "product_id": product1["id"],
            "quantity": 2,
        },
    )

    assert order1.status_code == 201

    order1_id = order1.get_json()["id"]

    # Staff user 2 creates another order.
    client.post("/logout")

    register_and_login(
        client,
        "api_admin_staff2",
        "api_admin_staff2@example.com",
    )

    product2 = create_product(
        client,
        sku="API-ADMIN-ORDER-002",
    )

    order2 = client.post(
        "/api/orders",
        json={
            "product_id": product2["id"],
            "quantity": 3,
        },
    )

    assert order2.status_code == 201

    order2_id = order2.get_json()["id"]

    # Register a third user and promote them to admin.
    client.post("/logout")

    register_and_login(
        client,
        "api_order_admin",
        "api_order_admin@example.com",
    )

    admin = User.query.filter_by(
        username="api_order_admin"
    ).first()

    assert admin is not None

    admin.role = "admin"
    db.session.commit()

    assert admin.role == "admin"

    # Admin must see both staff users' orders.
    response = client.get("/api/orders")

    assert response.status_code == 200

    order_ids = {
        order["id"]
        for order in response.get_json()
    }

    assert order1_id in order_ids
    assert order2_id in order_ids


def test_api_admin_can_get_another_users_order(client):
    # Staff user creates an order.
    register_and_login(
        client,
        "api_detail_staff",
        "api_detail_staff@example.com",
    )

    product = create_product(
        client,
        sku="API-ADMIN-DETAIL-001",
    )

    created = client.post(
        "/api/orders",
        json={
            "product_id": product["id"],
            "quantity": 2,
        },
    )

    assert created.status_code == 201

    order_id = created.get_json()["id"]

    # Log out and register an admin.
    client.post("/logout")

    register_and_login(
        client,
        "api_detail_admin",
        "api_detail_admin@example.com",
    )

    admin = User.query.filter_by(
        username="api_detail_admin"
    ).first()

    assert admin is not None

    admin.role = "admin"
    db.session.commit()

    # Verify admin authorization through the admin page.
    admin_page = client.get("/admin/users")

    assert admin_page.status_code == 200

    # Admin can retrieve another user's individual order.
    response = client.get(
        f"/api/orders/{order_id}"
    )

    assert response.status_code == 200
    assert response.get_json()["id"] == order_id
