import io
import re

import pytest
from PIL import Image

from app import create_app, db
from app.models import Product
from tests.test_inventory import register_and_login

HEX_NAME = re.compile(r"^[0-9a-f]{32}\.png$")


@pytest.fixture
def upload_env(tmp_path):
    """An app whose uploads go to a temporary folder, not app/uploads."""
    upload_dir = tmp_path / "uploads"

    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "UPLOAD_FOLDER": str(upload_dir),
    })

    with app.app_context():
        db.create_all()

    yield app.test_client(), app, upload_dir

    with app.app_context():
        db.session.remove()
        db.drop_all()


def make_png(size=(10, 10), mode="RGB", color="red"):
    buffer = io.BytesIO()
    Image.new(mode, size, color).save(buffer, format="PNG")
    return buffer.getvalue()


def make_gif():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buffer, format="GIF")
    return buffer.getvalue()


def make_animated_png():
    first = Image.new("RGB", (10, 10), "red")
    second = Image.new("RGB", (10, 10), "blue")
    buffer = io.BytesIO()
    first.save(
        buffer,
        format="PNG",
        save_all=True,
        append_images=[second],
        duration=100,
        loop=0,
    )
    return buffer.getvalue()


def make_huge_png():
    # 25 million pixels: above the app's 20 million limit, tiny on disk.
    return make_png(size=(5000, 5000), mode="L", color=0)


def make_truncated_png():
    data = make_png(size=(200, 200))
    return data[: len(data) // 2]


def post_product(
    client,
    sku,
    image=None,
    filename="photo.png",
    content_type="image/png",
):
    data = {
        "name": "Upload Test Product",
        "sku": sku,
        "description": "upload test",
        "quantity": "5",
        "unit_price": "10.00",
    }

    if image is not None:
        data["image"] = (io.BytesIO(image), filename, content_type)

    return client.post(
        "/inventory/new",
        data=data,
        content_type="multipart/form-data",
    )


def stored_files(upload_dir):
    if not upload_dir.exists():
        return []

    return sorted(path.name for path in upload_dir.iterdir())


def product_exists(app, sku):
    with app.app_context():
        return Product.query.filter_by(sku=sku).first() is not None


def product_image_name(app, sku):
    with app.app_context():
        product = Product.query.filter_by(sku=sku).first()
        return product.image_filename if product else None


@pytest.mark.parametrize(
    "filename",
    ["../../evil.png", "..\\..\\evil.png", "shell.php.png"],
)
def test_hostile_filename_is_never_used_on_disk(upload_env, tmp_path, filename):
    client, app, upload_dir = upload_env
    register_and_login(client, "upload_user", "upload_user@example.com")

    response = post_product(client, "UP-NAME-1", make_png(), filename=filename)

    assert response.status_code == 302

    files = stored_files(upload_dir)
    assert len(files) == 1
    assert HEX_NAME.match(files[0])
    assert product_image_name(app, "UP-NAME-1") == files[0]

    leaked = [
        path.name
        for path in tmp_path.rglob("*")
        if "evil" in path.name or "shell" in path.name
    ]
    assert leaked == []


def test_oversized_upload_is_refused(upload_env):
    client, app, upload_dir = upload_env
    register_and_login(client, "upload_user", "upload_user@example.com")

    response = post_product(client, "UP-BIG-1", b"0" * (6 * 1024 * 1024))

    assert response.status_code == 413
    assert not product_exists(app, "UP-BIG-1")
    assert stored_files(upload_dir) == []


REJECTED = [
    pytest.param(make_gif, "photo.gif", "image/gif", id="gif-format"),
    pytest.param(
        lambda: b"<html><script>alert(1)</script></html>",
        "photo.png",
        "image/png",
        id="html-named-png",
    ),
    pytest.param(
        lambda: b"just text", "photo.png", "image/png", id="text-named-png"
    ),
    pytest.param(lambda: b"", "photo.png", "image/png", id="empty-file"),
    pytest.param(
        make_huge_png, "photo.png", "image/png", id="too-many-pixels"
    ),
    pytest.param(
        make_animated_png, "photo.png", "image/png", id="animated-png"
    ),
    pytest.param(
        make_truncated_png, "photo.png", "image/png", id="truncated-png"
    ),
]


@pytest.mark.parametrize("build, filename, content_type", REJECTED)
def test_bad_uploads_are_rejected_without_leaving_files(
    upload_env, build, filename, content_type
):
    client, app, upload_dir = upload_env
    register_and_login(client, "upload_user", "upload_user@example.com")

    response = post_product(
        client, "UP-BAD-1", build(), filename=filename, content_type=content_type
    )

    assert response.status_code == 400
    assert not product_exists(app, "UP-BAD-1")
    assert stored_files(upload_dir) == []


def test_uploaded_image_is_served_with_safe_headers(upload_env):
    client, app, upload_dir = upload_env
    register_and_login(client, "upload_user", "upload_user@example.com")

    assert post_product(client, "UP-SERVE-1", make_png()).status_code == 302

    name = product_image_name(app, "UP-SERVE-1")
    response = client.get(f"/inventory/images/{name}")

    assert response.status_code == 200
    assert response.mimetype == "image/png"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"