# SECURITY.md: StockPilot threat model

StockPilot is a Flask inventory and order system with two roles (`staff`, `admin`)
and a JSON API. Every permission check runs on the server; the UI only hides controls.

## 1. Sensitive data

| Data | Stored in | Why it matters |
|---|---|---|
| Password hashes | `users.password_hash` | Account takeover if leaked |
| Email addresses | `users.email` | Personal data; shown only to admins on `/admin/users` |
| Products, orders, order items | `products`, `orders`, `order_items` | Private to the owner |
| Product images | `uploads/` | Owner-only viewing |
| Session cookie and `SECRET_KEY` | Browser, `.env` | Session forgery if leaked |

Usernames are visible to other signed-in users as note authors.

## 2. Who may do what

| Resource | Anonymous | Staff | Admin |
|---|---|---|---|
| Register, log in | Yes | n/a | n/a |
| Own products, orders, images | No | Read and write | Read and write |
| Other users' products | No | No | Read only, in the web inventory list |
| Other users' orders | No | No | Read only, web and API |
| Edit or delete another user's product or order | No | No | No |
| Other users' product images | No | No | No |
| Stock notes on any product | No | Read and add | Read and add |
| SKU and stock level on the notes page | No | Owner only | Owner only |
| User management (`/admin/users`) | No | No | Yes |

## 3. Protections, defenses and where they live

| Threat | Defense | Code | Tests |
|---|---|---|---|
| Weak password storage | Werkzeug scrypt hashing | `app/auth.py`: `register`, `login` | `test_user_can_register`, `test_registered_password_is_stored_as_a_scrypt_hash`, `test_same_password_gets_a_different_salted_hash` |
| Self-assigned role or ownership | Role and owner are never read from request data | `app/auth.py`: `register`; `app/api_routes.py` | `test_registration_cannot_assign_admin_role`, `test_api_create_product_cannot_set_owner_or_role` |
| Session theft or fixation | 30-minute session, HttpOnly, SameSite=Lax, Secure flag from environment, `session.clear()` at login, logout ends the session | `app/__init__.py` config; `app/auth.py`: `login`, `logout` | `test_session_lifetime_is_30_minutes`, `test_session_cookie_has_security_flags`, `test_session_is_permanent_after_login`, `test_logout_removes_dashboard_access` |
| Anonymous access | `@login_required` on every page; API gate before every API request | `app/api_routes.py`: `require_api_authentication` | `test_every_non_public_route_rejects_anonymous_users`, `test_products_api_requires_login` |
| Privilege escalation | Server-side role check | `app/permissions.py`: `roles_required`; `app/admin_routes.py`: `list_users` | `test_staff_cannot_access_admin_only_route`, `test_staff_cannot_access_real_admin_users_page`, `test_anonymous_user_cannot_access_admin_users_page` |
| IDOR on products | Queries filtered by `owner_id` | `app/routes.py`; `app/api_routes.py` | `test_user_cannot_edit_another_users_product`, `test_user_cannot_delete_another_users_product`, `test_api_users_cannot_access_each_others_products` |
| IDOR on orders | Queries filtered by `created_by_id`; admins may read but not modify | `app/order_routes.py`; `app/api_routes.py` | `test_user_cannot_edit_another_users_order`, `test_user_cannot_delete_another_users_order`, `test_api_user_cannot_read_another_users_order`, `test_api_user_cannot_update_another_users_order`, `test_api_user_cannot_delete_another_users_order` |
| Private data in shared notes | Non-owners receive only the product name | `app/stock_note_routes.py`: `product_notes` | `test_non_owner_sees_product_name_but_not_sku_or_stock` |
| Malicious file upload | Pillow content check, JPEG/PNG/WebP only, animated images rejected, random `uuid4` filenames, 5 MB request limit | `app/routes.py`: `save_product_image`; `app/__init__.py`: `MAX_CONTENT_LENGTH` | `test_invalid_image_content_is_rejected`, `test_owner_can_upload_and_view_product_image`, `tests/test_uploads.py` (12 tests: oversized file, hostile filenames, disguised and malformed files, no leftover files, safe serving headers) |
| Image access and path traversal | Strict 32-hex filename check, owner-only lookup, fixed content type | `app/routes.py`: `product_image` | `test_user_cannot_view_another_users_product_image` |
| Invalid or hostile input | Server-side validation of quantity, price, SKU, JSON shape, note length | route handlers in `app/routes.py`, `app/api_routes.py`, `app/stock_note_routes.py` | `test_products_api_rejects_negative_price`, `test_products_api_rejects_missing_fields`, `test_products_api_rejects_non_json_request`, `test_stock_note_over_1000_characters_is_rejected` |
| Brute-force login | Failed logins are counted per client address; after 5 failures in 5 minutes login returns HTTP 429, even for the correct password; a successful login resets the count | `app/rate_limit.py`: `LoginRateLimiter`; `app/auth.py`: `login`; limits in `app/__init__.py` | `tests/test_rate_limit.py` (3 tests) |
| Interactive debugger exposed | Flask debug mode is switched off | `run.py` | `test_run_py_does_not_enable_debug_mode` |
| Clickjacking, content sniffing, injected scripts | Every response carries `Content-Security-Policy` (scripts only from this server, no inline scripts or eval, no framing, no plugins, forms post only to this server), `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` and `Referrer-Policy: same-origin`; the inline delete confirmation was moved to a static script | `app/__init__.py`: `add_security_headers`; `app/static/confirm.js` | `tests/test_security_headers.py`, `tests/test_csp_compat.py` |
| CSRF | Flask-WTF `CSRFProtect` on every state-changing route, web and JSON API (API writes need the `X-CSRFToken` header) | `app/__init__.py`: `csrf.init_app` | `tests/test_csrf.py` (11 tests) |
| Stored and reflected XSS | Jinja autoescaping; the `safe` filter and `Markup` are not used | all templates | `test_product_text_is_html_escaped_on_inventory_page`, `test_stock_note_is_html_escaped_for_other_users` |
| SQL injection | SQLAlchemy ORM with bound parameters and no raw SQL; search text is limited to 100 characters; the owner filter is applied before the search filter | `app/routes.py`: `list_products` | `tests/test_sql_injection.py` (11 tests: classic, UNION, DROP TABLE, wildcard and over-length payloads) |
| Secrets in the repository | `.env` is not tracked; `.env.example` is shipped; the app refuses to start without `SECRET_KEY` | `app/__init__.py`; `.gitignore` | `test_app_refuses_to_start_without_a_secret_key` (missing and empty key); `.env` exclusion is enforced by `.gitignore` and checked with `git ls-files` |

## 4. Known gaps (being closed)

- Login rate limiting is per client address and kept in memory: counts reset on restart, are not shared between server processes, and behind a reverse proxy the proxy must pass the real client address.
- No rate limiting on registration, and no limit per account (only per client address).
- The Content-Security-Policy still allows inline styles (`style-src 'unsafe-inline'`) because one template has a `<style>` block and two use `style=` attributes; scripts are fully locked down.
- No `Strict-Transport-Security` header: it must be set by the HTTPS proxy or host at deployment.
- The products API does not give admins read access to all products, unlike the web list.

## 5. Out of scope and reporting

Denial of service and hosting-provider attacks are out of scope. Report issues privately
to the maintainer; do not publish credentials, cookies, or personal data.

## 6. Deployment

Use HTTPS, set `SESSION_COOKIE_SECURE=true`, use a unique `SECRET_KEY`, and replace
the seeded demo credentials.