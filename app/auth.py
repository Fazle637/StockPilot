
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
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

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if len(username) > 80 or len(email) > 254:
            flash("Username or email is too long.", "error")
            return render_template("register.html")

        if len(password) < 12:
            flash("Password must contain at least 12 characters.", "error")
            return render_template("register.html")

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("Username or email is already registered.", "error")
            return render_template("register.html")

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password, method="scrypt"),
            role="staff",
        )

        db.session.add(user)
        db.session.commit()

        flash("Account created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if user and check_password_hash(user.password_hash, password):
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
