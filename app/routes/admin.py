from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.activity import log_activity
from app.models import ActivityLog, Donation, Expense, User
from app.permissions import admin_required

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@admin_required
def users():
    users_list = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=users_list)


@admin_bp.route("/users/<int:user_id>/toggle-write", methods=["POST"])
@admin_required
def toggle_write(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_admin:
        flash("Admins always have full access.", "info")
        return redirect(url_for("admin.users"))

    user.can_write = not user.can_write
    access = "write" if user.can_write else "read-only"
    log_activity(
        current_user,
        "updated",
        "user",
        f"Changed {user.full_name} access to {access}",
        user.id,
    )
    db.session.commit()
    flash(f"{user.full_name} now has {access} access.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-admin", methods=["POST"])
@admin_required
def toggle_admin(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.id == current_user.id:
        flash("You cannot change your own admin role.", "warning")
        return redirect(url_for("admin.users"))

    if user.is_admin:
        admin_count = User.query.filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash("At least one admin is required.", "warning")
            return redirect(url_for("admin.users"))
        user.is_admin = False
        log_activity(
            current_user,
            "updated",
            "user",
            f"Removed admin role from {user.full_name}",
            user.id,
        )
        flash(f"{user.full_name} is no longer an admin.", "info")
    else:
        user.is_admin = True
        user.can_write = True
        log_activity(
            current_user,
            "updated",
            "user",
            f"Granted admin role to {user.full_name}",
            user.id,
        )
        flash(f"{user.full_name} is now an admin.", "success")

    db.session.commit()
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.users"))

    if user.is_admin and User.query.filter_by(is_admin=True).count() <= 1:
        flash("Cannot delete the only admin account.", "warning")
        return redirect(url_for("admin.users"))

    full_name = user.full_name
    Donation.query.filter_by(recorded_by_id=user.id).update(
        {"recorded_by_id": current_user.id}
    )
    Expense.query.filter_by(recorded_by_id=user.id).update(
        {"recorded_by_id": current_user.id}
    )
    ActivityLog.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    log_activity(
        current_user,
        "deleted",
        "user",
        f"Deleted user account: {full_name}",
        user_id,
    )
    db.session.commit()
    flash(f"User {full_name} has been deleted.", "info")
    return redirect(url_for("admin.users"))
