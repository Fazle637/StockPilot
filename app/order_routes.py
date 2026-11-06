
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Order, OrderItem, Product


orders_bp = Blueprint("orders", __name__, url_prefix="/orders")


@orders_bp.route("/")
@login_required
def list_orders():
    if current_user.role == "admin":
        query = Order.query
    else:
        query = Order.query.filter_by(
            created_by_id=current_user.id
        )

    orders = query.order_by(
        Order.created_at.desc()
    ).all()

    return render_template(
        "orders.html",
        orders=orders,
    )

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
        flash("Quantity must be a whole number greater than zero.", "error")
        return render_template("order_form.html", products=products), 400

    try:
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
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash("The order could not be saved. Please try again.", "error")
        return redirect(url_for("orders.create_order"))

    flash("Order created successfully.", "success")
    return redirect(url_for("orders.list_orders"))


@orders_bp.route("/<int:order_id>/edit", methods=["GET", "POST"])
@login_required
def edit_order(order_id):
    order = db.session.scalar(
        select(Order).where(
            Order.id == order_id,
            Order.created_by_id == current_user.id,
        )
    )

    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders.list_orders"))

    if order.status != "pending":
        flash("Only pending orders can be edited.", "error")
        return redirect(url_for("orders.list_orders"))

    if len(order.items) != 1:
        flash("This order cannot be edited through this form.", "error")
        return redirect(url_for("orders.list_orders"))

    item = order.items[0]

    if request.method == "GET":
        return render_template("order_edit.html", order=order, item=item)

    quantity_text = request.form.get("quantity", "").strip()

    try:
        if not quantity_text or len(quantity_text) > 9:
            raise ValueError

        new_quantity = int(quantity_text)

        if new_quantity <= 0 or new_quantity > 1_000_000:
            raise ValueError
    except ValueError:
        flash("Quantity must be a whole number greater than zero.", "error")
        return render_template("order_edit.html", order=order, item=item), 400

    try:
        product = db.session.scalar(
            select(Product)
            .where(
                Product.id == item.product_id,
                Product.owner_id == current_user.id,
            )
            .with_for_update()
        )

        if product is None:
            db.session.rollback()
            flash("The product for this order was not found.", "error")
            return redirect(url_for("orders.list_orders"))

        # The old order quantity is already reserved.
        available_stock = product.quantity + item.quantity

        if new_quantity > available_stock:
            db.session.rollback()
            flash("There is not enough stock for that quantity.", "error")
            return render_template(
                "order_edit.html", order=order, item=item
            ), 400

        product.quantity = available_stock - new_quantity
        item.quantity = new_quantity

        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash("The order could not be updated. Please try again.", "error")
        return redirect(url_for("orders.list_orders"))

    flash("Order updated successfully.", "success")
    return redirect(url_for("orders.list_orders"))


@orders_bp.post("/<int:order_id>/delete")
@login_required
def delete_order(order_id):
    order = db.session.scalar(
        select(Order).where(
            Order.id == order_id,
            Order.created_by_id == current_user.id,
        )
    )

    if order is None:
        flash("Order not found.", "error")
        return redirect(url_for("orders.list_orders"))

    if order.status != "pending":
        flash("Only pending orders can be deleted.", "error")
        return redirect(url_for("orders.list_orders"))

    try:
        # Restore the stock reserved by every item in this order.
        for item in order.items:
            product = db.session.scalar(
                select(Product)
                .where(
                    Product.id == item.product_id,
                    Product.owner_id == current_user.id,
                )
                .with_for_update()
            )

            if product is None:
                db.session.rollback()
                flash("A product for this order could not be found.", "error")
                return redirect(url_for("orders.list_orders"))

            product.quantity += item.quantity

        db.session.delete(order)
        db.session.commit()

    except IntegrityError:
        db.session.rollback()
        flash("The order could not be deleted. Please try again.", "error")
        return redirect(url_for("orders.list_orders"))

    flash("Order deleted and stock restored.", "success")
    return redirect(url_for("orders.list_orders"))
