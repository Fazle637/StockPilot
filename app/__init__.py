

import os

from flask import Flask, jsonify, render_template
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_login import  LoginManager, current_user, login_required
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
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
    
    if test_config:
        app.config.update(test_config)


    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.session_protection = "basic"

    from app.models import User
    from app import models  # noqa: F401
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

    @app.get("/")
    @login_required
    def home():
        return render_template("dashboard.html")

    @app.get("/health")
    def health():
        return jsonify({"status": "healthy"}), 200

    return app