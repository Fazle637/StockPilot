# StockPilot — Inventory and Order Management

StockPilot is a web application built with Python, Flask, Flask-SQLAlchemy, and SQLite. It helps authenticated users manage inventory products, create orders, and collaborate through stock notes.

## Features

- User registration, login, logout, and session management.
- Server-side role enforcement for admin and staff accounts.
- Product creation, viewing, editing, and deletion.
- Product search by name or SKU.
- Product image uploads with validation.
- Order creation with stock availability checks.
- Order management through HTML pages and a JSON API.
- Shared stock notes attached to inventory products.
- Database relationships between users, products, orders, and order items.
- Automated tests for authentication, validation, and access control.

## Technology Stack

- Python
- Flask
- Flask-SQLAlchemy and SQLAlchemy
- Flask-Login
- Flask-WTF for CSRF protection
- SQLite for local development
- Pytest for automated testing
- Pillow for product image validation

## Requirements

- Python 3.13 or a compatible supported Python version.
- Git.
- A terminal such as PowerShell.
- A web browser.

## Installation

Clone the repository:

```powershell
git clone https://github.com/Fazle637/StockPilot.git
cd StockPilot
```

Create and activate a virtual environment on Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

If PowerShell does not allow virtual-environment activation, consult your Python environment configuration or use the appropriate activation command for your terminal.

## Environment Configuration

Create a `.env` file in the project root, next to `run.py`.

Generate a secret key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Add the following configuration to `.env`, replacing the placeholder with the generated secret:

```dotenv
SECRET_KEY=replace_with_your_generated_secret
DATABASE_URL=sqlite:///stockpilot.db
```

Never commit `.env` or disclose its contents. The repository includes `.env.example` for documenting required configuration variables.

## Initialize the Database

The application uses SQLite for local development. The configured database file is created in Flask's instance directory when the application initializes the database tables.

The seed script creates demonstration users and related inventory data:

```powershell
python seed.py
```

The script is intended for local development. Review its demo accounts and credentials before use, and never expose predictable demo credentials in a public deployment.

## Run the Application

Start the Flask development server:

```powershell
python run.py
```

Open the local address displayed in the terminal, normally:

http://127.0.0.1:5000

Register an account or use a local demonstration account.

Do not use Flask's development server as a production server.

## Run Automated Tests

Run the full test suite:

```powershell
python -m pytest -v
```

The tests cover authentication, role enforcement, product CRUD operations, ownership restrictions, product image validation, stock notes, and order API behavior.

## Main Pages

- `/` — Dashboard
- `/register` — Registration
- `/login` — Login
- `/inventory/` — Inventory
- `/inventory/new` — Create a product
- `/orders/` — Orders
- `/orders/new` — Create an order
- `/inventory/<product_id>/notes` — Product stock notes

Additional routes support product editing, deletion, image viewing, and JSON API operations.

## JSON API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/products` | List the authenticated user's products |
| POST | `/api/products` | Create a product |
| GET | `/api/products/<product_id>` | Retrieve an owned product |
| PATCH | `/api/products/<product_id>` | Update an owned product |
| DELETE | `/api/products/<product_id>` | Delete an owned product |
| GET | `/api/orders` | List the authenticated user's orders |
| GET | `/api/orders/<order_id>` | Retrieve an owned order |
| POST | `/api/orders` | Create an order |

API access requires authentication. Resource ownership and request validation must also be enforced by the server.

## Security

StockPilot uses password hashing, authenticated sessions, CSRF protection, server-side role checks, ownership-scoped queries, validated input, and product image validation.

Read `SECURITY.md` for additional security details and known limitations.

## Development Notes

- Keep secrets in environment variables.
- Do not commit virtual environments, database files containing personal data, or uploaded user files.
- Run the automated tests after making changes.
- Review migrations and database initialization before changing database schemas.
- Use a production-grade WSGI server and HTTPS when deploying publicly.