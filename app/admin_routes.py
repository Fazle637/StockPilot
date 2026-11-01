from flask import Blueprint, render_template

from app.models import User
from app.permissions import roles_required


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.get("/users")
@roles_required("admin")
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()

    return render_template(
        "admin_users.html",
        users=users,
    )