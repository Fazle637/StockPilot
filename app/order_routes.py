
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Order, OrderItem, Product


orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


@orders_bp.get("/")
@login_required
def list_orders():
    orders = (
        Order.query
        .filter_by(created_by_id=current_user.id)
        .order_by(Order.created_at.desc())
        .all()
    )

    return render_template("orders.html", orders=orders)



@orders_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_order():
    products = (
        Product.query
        .filter_by(owner_id=current_user.id)
        .filter(Product.quantity > 0)
        .order_by(Product.name.asc())
        .all()
    )

    if request.method == "GET":
        return render_template("order_form.html", products=products)

    product_id_text = request.form.get("product_id", "").strip()
    quantity_text = request.form.get("quantity", "").strip()

    try:
        if not product_id_text or len(product_id_text) > 10:
            raise ValueError
        product_id = int(product_id_text)
        if product_id <= 0:
            raise ValueError
    except ValueError:
        flash("Select a valid product.", "error")
        return render_template("order_form.html", products=products), 400

    try:
        if not quantity_text or len(quantity_text) > 9:
            raise ValueError
        quantity = int(quantity_text)
        if quantity <= 0 or quantity > 1_000_000:
            raise ValueError
    except ValueError:
        flash(
            "Quantity must be a whole number greater than zero.",
            "error",
        )
        return render_template("order_form.html", products=products), 400

    try:
        # The session may already have a transaction from the earlier query.
        # Use that transaction instead of calling session.begin() again.
        product = db.session.scalar(
            select(Product)
            .where(
                Product.id == product_id,
                Product.owner_id == current_user.id,
            )
            .with_for_update()
        )

        if product is None:
            db.session.rollback()
            flash("The selected product was not found.", "error")
            return render_template("order_form.html", products=products), 404

        if product.quantity < quantity:
            db.session.rollback()
            flash("There is not enough stock for this order.", "error")
            return render_template("order_form.html", products=products), 400

        order = Order(
            status="pending",
            created_by_id=current_user.id,
        )
        db.session.add(order)
        db.session.flush()

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.unit_price,
        )
        db.session.add(order_item)

        product.quantity -= quantity

        # Save the order, order item, and stock change together.
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash("The order could not be saved. Please try again.", "error")
        return redirect(url_for("orders.create_order"))

    flash("Order created successfully.", "success")
    return redirect(url_for("orders.list_orders"))
