
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Product

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.get("/")
@login_required
def list_products():
    search = request.args.get("q", "").strip()

    if len(search) > 100:
        flash("Search text must be 100 characters or fewer.", "error")
        search = ""

    query = Product.query.filter_by(owner_id=current_user.id)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Product.name.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    products = query.order_by(Product.name.asc()).all()

    return render_template(
        "inventory.html",
        products=products,
        search=search,
    )


@inventory_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        sku = request.form.get("sku", "").strip().upper()
        description = request.form.get("description", "").strip()
        quantity_text = request.form.get("quantity", "").strip()
        price_text = request.form.get("unit_price", "").strip()

        errors = []

        if not name or len(name) > 120:
            errors.append("Product name is required and must be at most 120 characters.")

        if not sku or len(sku) > 60:
            errors.append("SKU is required and must be at most 60 characters.")

        if len(description) > 5000:
            errors.append("Description must be 5,000 characters or fewer.")

        quantity = None
        try:
            if not quantity_text or len(quantity_text) > 9:
                raise ValueError
            quantity = int(quantity_text)
            if quantity < 0 or quantity > 1_000_000:
                raise ValueError
        except ValueError:
            errors.append("Quantity must be a whole number from 0 to 1,000,000.")

        price = None
        try:
            if not price_text or len(price_text) > 20:
                raise ValueError
            price = Decimal(price_text)
            if (
                not price.is_finite()
                or price < 0
                or price > Decimal("99999999.99")
                or price.as_tuple().exponent < -2
            ):
                raise ValueError
        except (ValueError, InvalidOperation):
            errors.append("Price must be a valid non-negative amount with at most two decimal places.")

        if sku and Product.query.filter_by(sku=sku).first():
            errors.append("That SKU is already in use.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("product_form.html", product=None), 400

        product = Product(
            name=name,
            sku=sku,
            description=description,
            quantity=quantity,
            unit_price=price,
            owner_id=current_user.id,
        )

        db.session.add(product)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("The product could not be saved. Check that its SKU is unique.", "error")
            return render_template("product_form.html", product=None), 400

        flash("Product created successfully.", "success")
        return redirect(url_for("inventory.list_products"))

    return render_template("product_form.html", product=None)

@inventory_bp.route("/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    product = Product.query.filter_by(
        id=product_id,
        owner_id=current_user.id,
    ).first_or_404()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        sku = request.form.get("sku", "").strip().upper()
        description = request.form.get("description", "").strip()
        quantity_text = request.form.get("quantity", "").strip()
        price_text = request.form.get("unit_price", "").strip()

        errors = []

        if not name or len(name) > 120:
            errors.append(
                "Product name is required and must be at most 120 characters."
            )

        if not sku or len(sku) > 60:
            errors.append(
                "SKU is required and must be at most 60 characters."
            )

        if len(description) > 5000:
            errors.append(
                "Description must be 5,000 characters or fewer."
            )

        quantity = None

        try:
            if not quantity_text or len(quantity_text) > 9:
                raise ValueError

            quantity = int(quantity_text)

            if quantity < 0 or quantity > 1_000_000:
                raise ValueError

        except ValueError:
            errors.append(
                "Quantity must be a whole number from 0 to 1,000,000."
            )

        price = None

        try:
            if not price_text or len(price_text) > 20:
                raise ValueError

            price = Decimal(price_text)

            if (
                not price.is_finite()
                or price < 0
                or price > Decimal("99999999.99")
                or price.as_tuple().exponent < -2
            ):
                raise ValueError

        except (ValueError, InvalidOperation):
            errors.append(
                "Price must be a valid non-negative amount "
                "with at most two decimal places."
            )

        duplicate = Product.query.filter(
            Product.sku == sku,
            Product.id != product.id,
        ).first()

        if duplicate:
            errors.append("That SKU is already in use.")

        if errors:
            for error in errors:
                flash(error, "error")

            return render_template(
                "product_form.html",
                product=product,
            ), 400

        product.name = name
        product.sku = sku
        product.description = description
        product.quantity = quantity
        product.unit_price = price

        try:
            db.session.commit()

        except IntegrityError:
            db.session.rollback()

            flash(
                "The product could not be updated. Check that its SKU is unique.",
                "error",
            )

            return render_template(
                "product_form.html",
                product=product,
            ), 400

        flash("Product updated successfully.", "success")

        return redirect(url_for("inventory.list_products"))

    return render_template(
        "product_form.html",
        product=product,
    )


@inventory_bp.route("/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    product = Product.query.filter_by(
        id=product_id,
        owner_id=current_user.id,
    ).first_or_404()

    db.session.delete(product)

    try:
        db.session.commit()

    except IntegrityError:
        db.session.rollback()

        flash(
            "This product cannot be deleted because it is referenced "
            "by an existing order.",
            "error",
        )

        return redirect(url_for("inventory.list_products"))

    flash("Product deleted successfully.", "success")

    return redirect(url_for("inventory.list_products"))

