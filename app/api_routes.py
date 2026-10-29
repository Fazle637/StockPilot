
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_login import current_user
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Order, OrderItem, Product


api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.before_request
def require_api_authentication():
    if not current_user.is_authenticated:
        return jsonify({"error": "Authentication required."}), 401


def product_to_dict(product):
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "description": product.description,
        "quantity": product.quantity,
        "unit_price": str(product.unit_price),
    }


def get_json_object():
    if not request.is_json:
        return None

    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def parse_product_data(data):
    name = data.get("name")
    sku = data.get("sku")
    description = data.get("description", "")
    quantity = data.get("quantity")
    price = data.get("unit_price")

    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 120:
        raise ValueError("Name must contain 1–120 characters.")

    if not isinstance(sku, str) or not sku.strip() or len(sku.strip()) > 60:
        raise ValueError("SKU must contain 1–60 characters.")

    if not isinstance(description, str) or len(description) > 5000:
        raise ValueError("Description must be at most 5000 characters.")

    if isinstance(quantity, bool):
        raise ValueError("Quantity must be a whole number.")

    try:
        parsed_quantity = int(quantity)
    except (TypeError, ValueError):
        raise ValueError("Quantity must be a whole number.")

    if str(parsed_quantity) != str(quantity) or not 0 <= parsed_quantity <= 1_000_000:
        raise ValueError("Quantity must be between 0 and 1000000.")

    if isinstance(price, bool) or price is None:
        raise ValueError("Unit price must be a valid non-negative amount.")

    try:
        parsed_price = Decimal(str(price))
    except (InvalidOperation, ValueError):
        raise ValueError("Unit price must be a valid non-negative amount.")

    if (
        not parsed_price.is_finite()
        or parsed_price < 0
        or parsed_price > Decimal("99999999.99")
        or parsed_price.as_tuple().exponent < -2
    ):
        raise ValueError("Unit price must be non-negative with at most 2 decimal places.")

    return {
        "name": name.strip(),
        "sku": sku.strip().upper(),
        "description": description,
        "quantity": parsed_quantity,
        "unit_price": parsed_price,
    }


@api_bp.get("/products")
@login_required
def api_list_products():
    products = (
        Product.query
        .filter_by(owner_id=current_user.id)
        .order_by(Product.name.asc())
        .all()
    )

    return jsonify([product_to_dict(product) for product in products])


@api_bp.post("/products")
@login_required
def api_create_product():
    data = get_json_object()

    if data is None:
        return jsonify({"error": "A JSON object is required."}), 400

    try:
        values = parse_product_data(data)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    product = Product(
        **values,
        owner_id=current_user.id,
    )

    try:
        db.session.add(product)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "That SKU is already in use."}), 409

    return jsonify(product_to_dict(product)), 201



@api_bp.get("/products/<int:product_id>")
@login_required
def api_get_product(product_id):
    product = Product.query.filter_by(
        id=product_id,
        owner_id=current_user.id,
    ).first()

    if product is None:
        return jsonify({
            "error": "Product not found."
        }), 404

    return jsonify(product_to_dict(product))



@api_bp.patch("/products/<int:product_id>")
@login_required
def api_update_product(product_id):
    product = Product.query.filter_by(
        id=product_id,
        owner_id=current_user.id,
    ).first()

    if product is None:
        return jsonify({"error": "Product not found."}), 404

    data = get_json_object()
    if data is None:
        return jsonify({"error": "A JSON object is required."}), 400

    allowed_fields = {"name", "sku", "description", "quantity", "unit_price"}
    if not data or not set(data).issubset(allowed_fields):
        return jsonify({"error": "Provide only valid product fields."}), 400

    values_to_validate = {
        "name": data.get("name", product.name),
        "sku": data.get("sku", product.sku),
        "description": data.get("description", product.description),
        "quantity": data.get("quantity", product.quantity),
        "unit_price": data.get("unit_price", str(product.unit_price)),
    }

    try:
        values = parse_product_data(values_to_validate)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    for field, value in values.items():
        setattr(product, field, value)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "That SKU is already in use."}), 409

    return jsonify(product_to_dict(product))


@api_bp.delete("/products/<int:product_id>")
@login_required
def api_delete_product(product_id):
    product = Product.query.filter_by(
        id=product_id,
        owner_id=current_user.id,
    ).first()

    if product is None:
        return jsonify({"error": "Product not found."}), 404

    try:
        db.session.delete(product)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "error": "This product is referenced by an order and cannot be deleted."
        }), 409

    return jsonify({"message": "Product deleted successfully."})


@api_bp.get("/orders")
@login_required
def api_list_orders():
    orders = (
        Order.query
        .filter_by(created_by_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return jsonify([
        {
            "id": order.id,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                }
                for item in order.items
            ],
        }
        for order in orders
    ])


@api_bp.get("/orders/<int:order_id>")
@login_required
def api_get_order(order_id):
    order = Order.query.filter_by(
        id=order_id,
        created_by_id=current_user.id,
    ).first()

    if order is None:
        return jsonify({"error": "Order not found."}), 404

    return jsonify({
        "id": order.id,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
            }
            for item in order.items
        ],
    })


@api_bp.post("/orders")
@login_required
def api_create_order():
    data = get_json_object()

    if data is None:
        return jsonify({"error": "A JSON object is required."}), 400

    if set(data) != {"product_id", "quantity"}:
        return jsonify({
            "error": "Provide only product_id and quantity."
        }), 400

    product_id = data["product_id"]
    quantity = data["quantity"]

    # bool is a subclass of int in Python, so reject it explicitly.
    if (
        isinstance(product_id, bool)
        or not isinstance(product_id, int)
        or product_id <= 0
    ):
        return jsonify({"error": "Invalid product ID."}), 400

    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, int)
        or not 1 <= quantity <= 1_000_000
    ):
        return jsonify({
            "error": "Quantity must be a positive integer."
        }), 400

    try:
        product = (
            Product.query
            .filter_by(id=product_id, owner_id=current_user.id)
            .with_for_update()
            .first()
        )

        if product is None:
            return jsonify({"error": "Product not found."}), 404

        if product.quantity < quantity:
            return jsonify({
                "error": "Insufficient stock."
            }), 409

        order = Order(
            status="pending",
            created_by_id=current_user.id,
        )
        db.session.add(order)
        db.session.flush()

        item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.unit_price,
        )
        db.session.add(item)

        product.quantity -= quantity
        db.session.commit()

        return jsonify({
            "id": order.id,
            "status": order.status,
            "items": [
                {
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "unit_price": str(item.unit_price),
                }
            ],
        }), 201

    except Exception:
        db.session.rollback()
        raise
