import os
from datetime import timedelta

from flask import Flask, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_required
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///stockpilot.db",
    )
    
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.path.join(
        app.root_path,
        "uploads",
    )
    
    # Session security settings
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("SESSION_COOKIE_SECURE", "false").lower()
        in {"1", "true", "yes"}
    )
    app.config["SESSION_REFRESH_EACH_REQUEST"] = False
    app.config["LOGIN_MAX_ATTEMPTS"] = 5
    app.config["LOGIN_WINDOW_SECONDS"] = 300
    app.config["REGISTER_MAX_ATTEMPTS"] = 10
    app.config["REGISTER_WINDOW_SECONDS"] = 600
    if test_config:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY must be configured in the environment."
        )


    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.rate_limit import LoginRateLimiter
    app.extensions["login_limiter"] = LoginRateLimiter()
    app.extensions["register_limiter"] = LoginRateLimiter()

    login_manager.login_view = "auth.login"
    login_manager.session_protection = "basic"

    from app.models import User
    from app import models 
    from app.auth import auth_bp

    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except (TypeError, ValueError):
            return None

    app.register_blueprint(auth_bp)

    from app.routes import inventory_bp
    
    app.register_blueprint(inventory_bp)

    from app.order_routes import orders_bp
    
    app.register_blueprint(orders_bp)

    from app.stock_note_routes import stock_notes_bp
    
    app.register_blueprint(stock_notes_bp)

    from app.api_routes import api_bp
    app.register_blueprint(api_bp)

    from app.admin_routes import admin_bp
    app.register_blueprint(admin_bp)

    @app.get("/")
    @login_required
    def home():
        return render_template("dashboard.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"}), 200

    @app.after_request
    def add_security_headers(response):
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "same-origin")
        headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        return response

    # Create any missing tables so a fresh clone works without manual setup.
    # Existing tables and data are left untouched.
    with app.app_context():
        db.create_all()

    return app