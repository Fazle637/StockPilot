import re

from app import db
from app.models import Product, User

from tests.test_inventory import register_and_login

# Pages that are meant to be reachable without logging in.
# If the first test lists a route that is public by design, add it here.
PUBLIC_PATHS = {"/login", "/register", "/health"}


def _concrete_path(rule):
    return re.sub(r"<(?:\w+:)?\w+>", "1", rule.rule)


def test_every_non_public_route_rejects_anonymous_users(client):
    failures = []

    for rule in client.application.url_map.iter_rules():
        if rule.endpoint == "static":
            continue

        path = _concrete_path(rule)
        if path in PUBLIC_PATHS:
            continue

        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            kwargs = {} if method == "GET" else {"json": {}}
            response = client.open(path, method=method, **kwargs)

            if response.status_code not in (302, 401, 403):
                failures.append(f"{method} {path} -> {response.status_code}")

    assert not failures, "Routes reachable without login:\n" + "\n".join(failures)


def test_api_create_product_cannot_set_owner_or_role(client):
    register_and_login(client, "mass_user", "mass_user@example.com")

    response = client.post(
        "/api/products",
        json={
            "name": "Mass Assignment Probe",
            "sku": "MASS-001",
            "description": "probe",
            "quantity": 1,
            "unit_price": "1.00",
            "id": 9999,
            "owner_id": 9999,
            "role": "admin",
        },
    )

    # Rejecting unknown fields (400) or ignoring them (201) are both safe.
    assert response.status_code in (201, 400)

    if response.status_code == 201:
        body = response.get_json()
        assert body["id"] != 9999

        with client.application.app_context():
            user = User.query.filter_by(username="mass_user").first()
            product = db.session.get(Product, body["id"])

            assert product.owner_id == user.id
            assert user.role == "staff"


def test_product_text_is_html_escaped_on_inventory_page(client):
    register_and_login(client, "xss_user", "xss_user@example.com")

    payload = "<script>alert(1)</script>"
    response = client.post(
        "/api/products",
        json={
            "name": payload,
            "sku": "XSS-001",
            "description": payload,
            "quantity": 1,
            "unit_price": "1.00",
        },
    )

    # Rejecting the input outright is also an acceptable defense.
    assert response.status_code in (201, 400)

    if response.status_code == 201:
        page = client.get("/inventory/")
        assert page.status_code == 200

        html = page.get_data(as_text=True)
        assert payload not in html
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_stock_note_is_html_escaped_for_other_users(client):
    register_and_login(client, "note_author", "note_author@example.com")

    created = client.post(
        "/api/products",
        json={
            "name": "Note XSS Product",
            "sku": "NOTE-XSS-001",
            "description": "probe",
            "quantity": 1,
            "unit_price": "1.00",
        },
    )
    assert created.status_code == 201
    product_id = created.get_json()["id"]

    payload = "<script>alert('note')</script>"
    posted = client.post(
        f"/inventory/{product_id}/notes",
        data={"content": payload},
    )
    assert posted.status_code == 302

    client.post("/logout")
    register_and_login(client, "note_reader", "note_reader@example.com")

    page = client.get(f"/inventory/{product_id}/notes")
    assert page.status_code == 200

    html = page.get_data(as_text=True)
    assert payload not in html
    assert "&lt;script&gt;" in html


def test_non_owner_sees_product_name_but_not_sku_or_stock(client):
    register_and_login(client, "priv_owner", "priv_owner@example.com")

    created = client.post(
        "/api/products",
        json={
            "name": "Private Detail Product",
            "sku": "PRIV-NOTE-001",
            "description": "probe",
            "quantity": 8642,
            "unit_price": "1.00",
        },
    )
    assert created.status_code == 201
    product_id = created.get_json()["id"]

    owner_page = client.get(f"/inventory/{product_id}/notes")
    assert owner_page.status_code == 200
    assert "PRIV-NOTE-001" in owner_page.get_data(as_text=True)

    client.post("/logout")
    register_and_login(client, "priv_other", "priv_other@example.com")

    other_page = client.get(f"/inventory/{product_id}/notes")
    assert other_page.status_code == 200

    html = other_page.get_data(as_text=True)
    assert "Private Detail Product" in html
    assert "PRIV-NOTE-001" not in html
    assert "Current stock" not in html