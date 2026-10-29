
from decimal import Decimal

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User, Product, Order, OrderItem, StockNote


DEMO_PASSWORD = "StockPilotDemo2026!"

DEMO_USERS = [
    ("admin1", "admin1@stockpilot.local", "admin"),
    ("admin2", "admin2@stockpilot.local", "admin"),
    ("staff1", "staff1@stockpilot.local", "staff"),
    ("staff2", "staff2@stockpilot.local", "staff"),
]

DEMO_PRODUCTS = [
    ("Wireless Mouse", "SP-001", "Wireless computer mouse", 50, "19.99"),
    ("USB Keyboard", "SP-002", "Full-size USB keyboard", 35, "29.99"),
    ("USB-C Cable", "SP-003", "One-metre USB-C cable", 100, "7.99"),
    ("Laptop Stand", "SP-004", "Adjustable laptop stand", 20, "34.50"),
    ("Webcam", "SP-005", "HD USB webcam", 15, "49.99"),
    ("Headphones", "SP-006", "Over-ear headphones", 25, "39.99"),
    ("USB Hub", "SP-007", "Four-port USB hub", 30, "14.99"),
    ("SSD 1TB", "SP-008", "One-terabyte solid-state drive", 12, "89.99"),
    ("Laptop Charger", "SP-009", "Universal laptop charger", 18, "44.99"),
    ("Monitor 24", "SP-010", "24-inch computer monitor", 10, "149.99"),
    ("Ethernet Cable", "SP-011", "Two-metre network cable", 80, "5.99"),
    ("Desk Lamp", "SP-012", "LED desk lamp", 22, "24.99"),
    ("Mouse Pad", "SP-013", "Large mouse pad", 60, "8.99"),
    ("HDMI Cable", "SP-014", "Two-metre HDMI cable", 45, "9.99"),
    ("Microphone", "SP-015", "USB desktop microphone", 14, "59.99"),
    ("Laptop Bag", "SP-016", "Padded laptop bag", 17, "32.99"),
    ("Flash Drive 64GB", "SP-017", "64GB USB flash drive", 70, "11.99"),
    ("Power Strip", "SP-018", "Six-outlet power strip", 28, "18.99"),
    ("Bluetooth Adapter", "SP-019", "USB Bluetooth adapter", 32, "12.99"),
    ("Graphics Tablet", "SP-020", "Entry-level graphics tablet", 8, "79.99"),
]


def seed_database():
    app = create_app()

    with app.app_context():
        # Create missing tables; existing tables and records are preserved.
        db.create_all()

        users = {}

        # Create four demo accounts: two admins and two staff members.
        for username, email, role in DEMO_USERS:
            user = User.query.filter_by(username=username).first()

            if user is None:
                user = User(
                    username=username,
                    email=email,
                    password_hash=generate_password_hash(
                        DEMO_PASSWORD,
                        method="scrypt",
                    ),
                    role=role,
                )
                db.session.add(user)
            elif user.role != role:
                raise RuntimeError(
                    f"Existing demo user {username!r} has an unexpected role. "
                    "Review it manually before seeding."
                )

            users[username] = user

        db.session.flush()

        # Distribute five products to each demo user.
        product_owners = [
            "admin1", "admin2", "staff1", "staff2"
        ]
        products_by_sku = {}

        for index, item in enumerate(DEMO_PRODUCTS):
            name, sku, description, quantity, price = item
            owner = users[product_owners[index // 5]]

            product = Product.query.filter_by(sku=sku).first()

            if product is None:
                product = Product(
                    name=name,
                    sku=sku,
                    description=description,
                    quantity=quantity,
                    unit_price=Decimal(price),
                    owner=owner,
                )
                db.session.add(product)
            elif product.owner_id != owner.id:
                raise RuntimeError(
                    f"Product {sku!r} already belongs to another user. "
                    "Review it manually before seeding."
                )

            products_by_sku[sku] = product

        db.session.flush()

        # Create one demo order per user, only using their own products.
        for index, username in enumerate(product_owners):
            user = users[username]
            sku = DEMO_PRODUCTS[index * 5][1]
            product = products_by_sku[sku]

            order = Order.query.filter_by(
                created_by_id=user.id
            ).filter(
                Order.items.any(OrderItem.product_id == product.id)
            ).first()

            if order is None:
                order = Order(
                    status="pending",
                    created_by=user,
                )
                db.session.add(order)
                db.session.flush()

                db.session.add(
                    OrderItem(
                        order=order,
                        product=product,
                        quantity=1,
                        unit_price=product.unit_price,
                    )
                )

        db.session.flush()

        # Add one shared inventory note per user's first product.
        for username in product_owners:
            user = users[username]
            product = products_by_sku[
                DEMO_PRODUCTS[product_owners.index(username) * 5][1]
            ]
            content = f"Demo inventory note for {product.name}."

            existing_note = StockNote.query.filter_by(
                author_id=user.id,
                product_id=product.id,
                content=content,
            ).first()

            if existing_note is None:
                db.session.add(
                    StockNote(
                        author=user,
                        product=product,
                        content=content,
                    )
                )

        db.session.commit()

        print("StockPilot seed completed successfully.")
        print(f"Demo users: {User.query.count()}")
        print(f"Products: {Product.query.count()}")
        print(f"Orders: {Order.query.count()}")
        print(f"Order items: {OrderItem.query.count()}")
        print(f"Stock notes: {StockNote.query.count()}")
        print()
        print("Demo accounts:")
        for username, email, role in DEMO_USERS:
            print(f"  Username: {username} | Role: {role}")
        print(f"Demo password for newly created accounts: {DEMO_PASSWORD}")
        print("Change demo passwords before any public deployment.")


if __name__ == "__main__":
    seed_database()
