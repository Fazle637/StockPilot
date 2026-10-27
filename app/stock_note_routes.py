
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.models import Product, StockNote


stock_notes_bp = Blueprint(
    "stock_notes",
    __name__,
    url_prefix="/inventory",
)


@stock_notes_bp.route(
    "/<int:product_id>/notes",
    methods=["GET", "POST"],
)
@login_required
def product_notes(product_id):
    product = db.session.get(Product, product_id)

    if product is None:
        from flask import abort
        abort(404)

    if request.method == "POST":
        content = request.form.get("content", "").strip()

        if not content:
            flash("A note cannot be empty.", "error")
            return redirect(
                url_for("stock_notes.product_notes", product_id=product.id)
            )

        if len(content) > 1000:
            flash("A note cannot exceed 1000 characters.", "error")
            return redirect(
                url_for("stock_notes.product_notes", product_id=product.id)
            )

        note = StockNote(
            content=content,
            author_id=current_user.id,
            product_id=product.id,
        )

        db.session.add(note)
        db.session.commit()

        flash("Stock note added successfully.", "success")
        return redirect(
            url_for("stock_notes.product_notes", product_id=product.id)
        )

    notes = (
        StockNote.query
        .filter_by(product_id=product.id)
        .order_by(StockNote.created_at.desc())
        .all()
    )

    return render_template(
        "stock_notes.html",
        product=product,
        notes=notes,
    )
