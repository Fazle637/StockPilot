
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user,
)
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Validate required fields.
        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html"), 400

        if len(username) > 80 or len(email) > 254:
            flash("Username or email is too long.", "error")
            return render_template("register.html"), 400

        if len(password) < 12:
            flash("Password must contain at least 12 characters.", "error")
            return render_template("register.html"), 400

        # Never allow a public registration form to assign admin privileges.
        existing_user = User.query.filter(
            or_(
                User.username == username,
                User.email == email,
            )
        ).first()

        if existing_user:
            flash("Username or email is already registered.", "error")
            return render_template("register.html"), 409

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(
                password,
                method="scrypt",
            ),
            role="staff",
        )

        try:
            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            # Handles duplicate username/email races safely.
            db.session.rollback()
            flash("Username or email is already registered.", "error")
            return render_template("register.html"), 409

        flash("Account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET" and current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Enter your username/email and password.", "error")
            return render_template("login.html"), 400

        # Allow login using either username or email.
        user = User.query.filter(
            or_(
                User.username == identifier,
                User.email == identifier.lower(),
            )
        ).first()

        if user is not None and check_password_hash(
            user.password_hash,
            password,
        ):
            login_user(user, remember=False)
            return redirect(url_for("home"))

        flash("Invalid username/email or password.", "error")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
