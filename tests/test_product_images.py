
from io import BytesIO

import pytest
from PIL import Image

from app import db
from app.models import Product, User


PASSWORD = "TestPassword123!"


def register_and_login(client, username, email):
    """Register a staff user and log them in."""
    response = client.post(
        "/register",
        data={
            "username": username,
            "email": email,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 302

    response = client.post(
        "/login",
        data={
            "identifier": username,
            "password": PASSWORD,
        },
    )
    assert response.status_code == 302


def create_test_image():
    """Create a real PNG image in memory."""
    image = Image.new("RGB", (10, 10), color="red")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return image_bytes


def create_product(client, sku, image=None):
    """Submit a valid product form, optionally including an image."""
    data = {
        "name": "Test Product",
        "sku": sku,
        "description": "Image upload test",
        "quantity": "5",
        "unit_price": "10.00",
    }

    if image is not None:
        data["image"] = (
            image,
            "test.png",
            "image/png",
        )

    return client.post(
        "/inventory/new",
        data=data,
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def test_owner_can_upload_and_view_product_image(
    client, app
):
    register_and_login(
        client,
        "image_owner",
        "image_owner@example.com",
    )

    response = create_product(
        client,
        "SP-IMAGE-001",
        create_test_image(),
    )

    assert response.status_code == 200

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-IMAGE-001"
        ).first()

        assert product is not None
        assert product.image_filename is not None
        image_filename = product.image_filename

    image_response = client.get(
        f"/inventory/images/{image_filename}"
    )

    assert image_response.status_code == 200
    assert image_response.mimetype == "image/png"
    assert image_response.data.startswith(b"\x89PNG\r\n\x1a\n")


def test_product_can_be_created_without_an_image(client, app):
    register_and_login(
        client,
        "no_image_user",
        "no_image@example.com",
    )

    response = create_product(
        client,
        "SP-IMAGE-002",
    )

    assert response.status_code == 200

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-IMAGE-002"
        ).first()

        assert product is not None
        assert product.image_filename is None


def test_invalid_image_content_is_rejected(client, app):
    register_and_login(
        client,
        "invalid_image_user",
        "invalid_image@example.com",
    )

    fake_image = BytesIO(b"This is not an image")

    response = create_product(
        client,
        "SP-IMAGE-003",
        fake_image,
    )

    assert response.status_code == 400

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-IMAGE-003"
        ).first()

        assert product is None


def test_user_cannot_view_another_users_product_image(
    client, app
):
    register_and_login(
        client,
        "image_victim",
        "image_victim@example.com",
    )

    response = create_product(
        client,
        "SP-IMAGE-004",
        create_test_image(),
    )

    assert response.status_code == 200

    with app.app_context():
        product = Product.query.filter_by(
            sku="SP-IMAGE-004"
        ).first()

        assert product is not None
        image_filename = product.image_filename

    # Switch to a different user's authenticated session.
    client.post("/logout")

    register_and_login(
        client,
        "image_other_user",
        "image_other@example.com",
    )

    response = client.get(
        f"/inventory/images/{image_filename}"
    )

    assert response.status_code == 404
