from app import db
from app.models import Order, Product, User

from tests.test_inventory import register_and_login


def create_product(client, sku, quantity=10):
    response = client.post(
        "/api/products",
        json={
            "name": "Web Order Test Product",
            "sku": sku,
            "description": "Product for web order tests",
            "quantity": quantity,
            "unit_price": "50.00",
        },
    )

    assert response.status_code == 201
    return response.get_json()


def create_order(client, product_id, quantity):
    response = client.post(
        "/api/orders",
        json={
            "product_id": product_id,
            "quantity": quantity,
        },
    )

    assert response.status_code == 201
    return response.get_json()["id"]


def get_product(client, product_id):
    response = client.get(f"/api/products/{product_id}")
    assert response.status_code == 200
    return response.get_json()


def test_user_can_edit_own_pending_order(client):
    register_and_login(
        client,
        "web_edit_user",
        "web_edit_user@example.com",
    )

    product = create_product(client, "WEB-EDIT-001", quantity=10)
    order_id = create_order(client, product["id"], quantity=3)

    response = client.post(
        f"/orders/{order_id}/edit",
        data={"quantity": "5"},
    )

    assert response.status_code == 302

    updated_product = get_product(client, product["id"])
    assert updated_product["quantity"] == 5

    with client.application.app_context():
        order = db.session.get(Order, order_id)
        assert order.items[0].quantity == 5


def test_edit_order_rejects_insufficient_stock(client):
    register_and_login(
        client,
        "web_stock_user",
        "web_stock_user@example.com",
    )

    product = create_product(client, "WEB-EDIT-002", quantity=5)
    order_id = create_order(client, product["id"], quantity=3)

    response = client.post(
        f"/orders/{order_id}/edit",
        data={"quantity": "6"},
    )

    assert response.status_code == 400

    updated_product = get_product(client, product["id"])
    assert updated_product["quantity"] == 2

    with client.application.app_context():
        order = db.session.get(Order, order_id)
        assert order.items[0].quantity == 3


def test_user_cannot_edit_another_users_order(client):
    register_and_login(
        client,
        "web_edit_owner",
        "web_edit_owner@example.com",
    )

    product = create_product(client, "WEB-EDIT-003")
    order_id = create_order(client, product["id"], quantity=2)

    client.post("/logout")

    register_and_login(
        client,
        "web_edit_other",
        "web_edit_other@example.com",
    )

    response = client.post(
        f"/orders/{order_id}/edit",
        data={"quantity": "4"},
    )

    assert response.status_code == 302

    # User 1's product through the API.
    with client.application.app_context():
        product_record = db.session.get(Product, product["id"])
        order = db.session.get(Order, order_id)

        assert product_record.quantity == 8
        assert order.items[0].quantity == 2


def test_user_can_delete_own_pending_order_and_restore_stock(client):
    register_and_login(
        client,
        "web_delete_user",
        "web_delete_user@example.com",
    )

    product = create_product(client, "WEB-DELETE-001", quantity=10)
    order_id = create_order(client, product["id"], quantity=3)

    response = client.post(f"/orders/{order_id}/delete")

    assert response.status_code == 302

    updated_product = get_product(client, product["id"])
    assert updated_product["quantity"] == 10

    with client.application.app_context():
        assert db.session.get(Order, order_id) is None


def test_user_cannot_delete_another_users_order(client):
    register_and_login(
        client,
        "web_delete_owner",
        "web_delete_owner@example.com",
    )

    product = create_product(client, "WEB-DELETE-002")
    order_id = create_order(client, product["id"], quantity=2)

    client.post("/logout")

    register_and_login(
        client,
        "web_delete_other",
        "web_delete_other@example.com",
    )

    response = client.post(f"/orders/{order_id}/delete")

    assert response.status_code == 302

    # Verify that User 2 could not delete the order or change stock.
    with client.application.app_context():
        product_record = db.session.get(Product, product["id"])
        order = db.session.get(Order, order_id)

        assert product_record.quantity == 8
        assert order is not None


def test_user_cannot_delete_non_pending_order(client):
    register_and_login(
        client,
        "web_status_user",
        "web_status_user@example.com",
    )

    product = create_product(client, "WEB-DELETE-003", quantity=10)
    order_id = create_order(client, product["id"], quantity=2)

    with client.application.app_context():
        order = db.session.get(Order, order_id)
        order.status = "processing"
        db.session.commit()

    response = client.post(f"/orders/{order_id}/delete")

    assert response.status_code == 302

    updated_product = get_product(client, product["id"])
    assert updated_product["quantity"] == 8

    with client.application.app_context():
        assert db.session.get(Order, order_id) is not None


def test_admin_can_see_all_users_orders(client):
    # Staff A creates an order.
    register_and_login(
        client,
        "order_staff_a",
        "order_staff_a@example.com",
    )

    product_a = create_product(client, "ADMIN-ORDER-001")
    order_a_id = create_order(client, product_a["id"], 2)

    client.post("/logout")

    # Staff B creates another order.
    register_and_login(
        client,
        "order_staff_b",
        "order_staff_b@example.com",
    )

    product_b = create_product(client, "ADMIN-ORDER-002")
    order_b_id = create_order(client, product_b["id"], 3)

    client.post("/logout")

    # Create an admin account.
    register_and_login(
        client,
        "order_admin",
        "order_admin@example.com",
    )

    with client.application.app_context():
        admin = User.query.filter_by(
            username="order_admin"
        ).first()

        admin.role = "admin"
        db.session.commit()

    client.post("/logout")

    # Admin logs in and opens the orders page.
    response = client.post(
        "/login",
        data={
            "identifier": "order_admin",
            "password": "TestPassword123!",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    orders_page = client.get("/orders/")
    assert orders_page.status_code == 200

    html = orders_page.get_data(as_text=True)

    # Both staff users' orders appear as table rows.
    assert f"<td>{order_a_id}</td>" in html
    assert f"<td>{order_b_id}</td>" in html

    # Admin can see other users' orders but gets no delete controls for them.
    assert f"/orders/{order_a_id}/delete" not in html
    assert f"/orders/{order_b_id}/delete" not in html