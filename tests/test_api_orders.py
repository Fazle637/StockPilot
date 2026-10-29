
import pytest

from app import db
from app.models import Product

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
    assert any(order["id"] == order_id for order in listing.get_json())

    detail = api_user.get(f"/api/orders/{order_id}")
    assert detail.status_code == 200
    assert detail.get_json()["id"] == order_id



def test_api_order_rejects_another_users_product(client, app):
    register_and_login(
        client,
        "order_owner",
        "order_owner@example.com",
    )

    product = create_product(
        client,
        sku="API-ORDER-005",
    )

    # Log out the owner and authenticate as a different user.
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

    # End User 1's session before registering User 2.
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
