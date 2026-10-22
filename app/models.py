
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint

from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    products = db.relationship("Product", back_populates="owner")
    orders = db.relationship("Order", back_populates="created_by")
    stock_notes = db.relationship("StockNote", back_populates="author")

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'staff')", name="check_user_role"),
    )


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, index=True)
    sku = db.Column(db.String(60), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=False, default="")
    quantity = db.Column(db.Integer, nullable=False, default=0)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)

    owner_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    owner = db.relationship("User", back_populates="products")
    order_items = db.relationship("OrderItem", back_populates="product")

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="check_product_quantity"),
        CheckConstraint("unit_price >= 0", name="check_product_price"),
    )


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_by = db.relationship("User", back_populates="orders")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'cancelled')",
            name="check_order_status",
        ),
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_order_item_quantity"),
        CheckConstraint("unit_price >= 0", name="check_order_item_price"),
        UniqueConstraint("order_id", "product_id", name="unique_product_per_order"),
    )


class StockNote(db.Model):
    __tablename__ = "stock_notes"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author = db.relationship("User", back_populates="stock_notes")
    product = db.relationship("Product", backref="stock_notes")
