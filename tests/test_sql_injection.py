import pytest

from tests.test_inventory import register_and_login

PAYLOADS = [
    "' OR '1'='1",
    "' OR 1=1 --",
    "'; DROP TABLE products; --",
    "' UNION SELECT username, password_hash FROM users --",
    '" OR ""="',
    "%' OR '%'='",
    "%",
    "_",
    "\\",
    "x" * 101,
]

OWNER_PRODUCT = "Alpha Secret Widget"
OWNER_SKU = "SQLI-A-001"
OTHER_PRODUCT = "Bravo Public Gadget"
OTHER_SKU = "SQLI-B-001"


def create_product(client, name, sku):
    response = client.post(
        "/inventory/new",
        data={
            "name": name,
            "sku": sku,
            "description": "SQL injection test",
            "quantity": "5",
            "unit_price": "9.99",
        },
    )
    assert response.status_code == 302


def search(client, text):
    return client.get("/inventory/", query_string={"q": text})


def test_search_finds_own_product_control(client):
    register_and_login(client, "sqli_owner", "sqli_owner@example.com")
    create_product(client, OWNER_PRODUCT, OWNER_SKU)

    response = search(client, "Alpha")

    assert response.status_code == 200
    assert OWNER_PRODUCT.encode() in response.data


@pytest.mark.parametrize("payload", PAYLOADS)
def test_injection_payloads_do_not_leak_or_break(client, payload):
    register_and_login(client, "sqli_owner", "sqli_owner@example.com")
    create_product(client, OWNER_PRODUCT, OWNER_SKU)
    client.post("/logout")

    register_and_login(client, "sqli_other", "sqli_other@example.com")
    create_product(client, OTHER_PRODUCT, OTHER_SKU)

    response = search(client, payload)

    assert response.status_code == 200
    assert OWNER_PRODUCT.encode() not in response.data
    assert OWNER_SKU.encode() not in response.data
    assert b"scrypt:" not in response.data
    assert b"sqli_owner@example.com" not in response.data

    # The tables are still intact after the payload ran.
    after = search(client, "Bravo")

    assert after.status_code == 200
    assert OTHER_PRODUCT.encode() in after.data