# StockPilot — Inventory and Order Management System

StockPilot is a web-based inventory and order management application developed using Python and Flask. It allows authenticated users to manage products, track inventory quantities, create orders, and collaborate through shared stock notes.

The project was developed for the Web Application Programming course at the Romanian-American University (RAU).

## Features

- **Authentication:** User registration, login, logout, and session management.
- **Role-based access control:** Admin and staff roles enforced on the server.
- **Inventory management:** Create, view, edit, delete, and search products.
- **Product images:** Upload and view validated product images.
- **Order management:** Create orders, check available stock, and track order status.
- **Stock notes:** Add notes to products and allow other authorized users to read them.
- **REST-style JSON API:** Manage products and orders through API endpoints.
- **Input validation:** Validate submitted data on the server.
- **Security:** Password hashing, CSRF protection, authentication checks, and resource ownership restrictions.
- **Automated testing:** Pytest tests for authentication, validation, and access control.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend programming |
| Flask | Web application framework |
| Flask-SQLAlchemy | Database integration and ORM |
| SQLite | Local development database |
| Flask-Login | User authentication and sessions |
| Flask-WTF | CSRF protection |
| Pillow | Product image validation |
| Pytest | Automated testing |
| HTML and CSS | User interface |

## Project Structure

```text
StockPilot/
├── app/
│   ├── __init__.py
│   ├── models.py
│   ├── routes.py
│   ├── auth.py
│   ├── permissions.py
│   ├── order_routes.py
│   ├── stock_note_routes.py
│   ├── api_routes.py
│   ├── templates/
│   └── uploads/
├── tests/
│   ├── test_auth.py
│   ├── test_inventory.py
│   ├── test_product_images.py
│   ├── test_stock_notes.py
│   └── test_api_orders.py
├── uploads/
├── instance/
├── .env.example
├── .gitignore
├── requirements.txt
├── run.py
├── seed.py
├── README.md
└── SECURITY.md
```

## Requirements

- Python 3.13 or a compatible supported Python version
- Git
- PowerShell or another terminal
- A web browser

SQLite is used for local development, so a separate database server is not required.

## Installation

### 1. Clone the repository

```powershell
git clone https://github.com/Fazle637/StockPilot.git
cd StockPilot
```

### 2. Create a virtual environment

```powershell
py -3.13 -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root, next to `run.py`.

Generate a random secret key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Add the following configuration to `.env`:

```dotenv
SECRET_KEY=replace_with_your_generated_secret
DATABASE_URL=sqlite:///stockpilot.db
```

Replace the secret placeholder with the generated value. Do not commit `.env` or share its contents. The `.env.example` file documents the required configuration variables.

## Database Setup

StockPilot uses SQLite for local development.

The application uses Flask-SQLAlchemy to manage database access. Before using the application, ensure that the required tables have been initialized.

To create local demonstration data, run:

```powershell
python seed.py
```

The seed script creates demonstration users, products, orders, order items, and stock notes while preserving existing records where supported.

**Important:** The seed script uses demonstration credentials. Keep these accounts in local development and change or disable them before any public deployment.

## Run the Application

Start the development server:

```powershell
python run.py
```

Open the address displayed in your terminal. By default, it is:

http://127.0.0.1:5000

You can register a staff account or sign in with an existing development account.

Use the Flask development server for local development only, not public production hosting.

## Main Pages

| Page | Route | Purpose |
|---|---|---|
| Dashboard | `/` | Main application page |
| Registration | `/register` | Create a user account |
| Login | `/login` | Authenticate a user |
| Inventory | `/inventory/` | View and search products |
| New product | `/inventory/new` | Add a product |
| Edit product | `/inventory/<product_id>/edit` | Update an owned product |
| Orders | `/orders/` | View the current user's orders |
| New order | `/orders/new` | Create an order |
| Stock notes | `/inventory/<product_id>/notes` | Read and add product notes |
| Edit order | `/orders/<order_id>/edit` | Update an owned pending order |

## JSON API Endpoints

The application provides ten JSON API endpoints for products and orders.

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products` | List the current user's products |
| POST | `/api/products` | Create a product |
| GET | `/api/products/<product_id>` | Retrieve a product |
| PATCH | `/api/products/<product_id>` | Update a product |
| DELETE | `/api/products/<product_id>` | Delete a product |
| GET | `/api/orders` | List the current user's orders |
| GET | `/api/orders/<order_id>` | Retrieve an order |
| POST | `/api/orders` | Create an order |
| PATCH | `/api/orders/<order_id>` | Update a pending order |
| DELETE | `/api/orders/<order_id>` | Delete a pending order |

API requests require authentication. The server validates submitted data and checks resource ownership before allowing access or changes.

## Automated Tests

Run the complete test suite from the project root:

```powershell
python -m pytest -v
```

The test suite covers:

- Registration, login, logout, and session behavior
- Role-based access restrictions
- Product creation and validation
- Product ownership and access control
- Product image validation and access control
- Stock note creation and visibility
- Order creation, stock validation, and order ownership
- JSON API authentication and request validation
- Web order editing, deletion, stock restoration, and ownership restrictions

The current test suite contains **52 passing tests**. Run the command above to verify the results after any changes.

## Security Considerations

StockPilot implements password hashing, session-based authentication, server-side role checks, CSRF protection, ownership-scoped database queries, input validation, and product image validation.

Review [SECURITY.md](SECURITY.md) for additional information about security controls and testing.

Never commit secrets, production credentials, personal data, or private uploaded files to the repository.

## Future Improvements

Potential improvements include database migrations, expanded administrative functionality, additional API tests, and deployment to a production hosting environment.

## Author

Developed as an individual university project for the Web Application Programming course at the Romanian-American University.
