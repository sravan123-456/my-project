from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.activity import log_activity
from app.forms import AdminResetPasswordForm, CommitteeBannerForm
from app.models import ActivityLog, Donation, Expense, PasswordResetRequest, User
from app.org_scope import org_get, org_users_query
from app.permissions import org_admin_required
from app.storage import delete_image, get_image_url, save_image, serve_image

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/users")
@org_admin_required
def users():
    pending_users = (
        org_users_query()
        .filter_by(is_approved=False)
        .order_by(User.created_at.asc())
        .all()
    )
    approved_users = (
        org_users_query()
        .filter_by(is_approved=True)
        .order_by(User.created_at.desc())
        .all()
    )
    pending_resets = (
        PasswordResetRequest.query.filter_by(
            organization_id=current_user.organization_id,
            status=PasswordResetRequest.STATUS_PENDING,
        )
        .order_by(PasswordResetRequest.created_at.asc())
        .all()
    )
    invite_url = None
    committee_code = None
    if current_user.organization:
        committee_code = current_user.organization.slug
        invite_url = url_for(
            "auth.login",
            org=committee_code,
            _anchor="existing-committee",
            _external=True,
        )
    return render_template(
        "admin/users.html",
        pending_users=pending_users,
        pending_resets=pending_resets,
        users=approved_users,
        invite_url=invite_url,
        committee_code=committee_code,
        banner_form=CommitteeBannerForm(),
    )


def _org_user(user_id):
    return org_users_query().filter_by(id=user_id).first()


@admin_bp.route("/users/<int:user_id>/approve", methods=["POST"])
@org_admin_required
def approve_user(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_approved:
        flash(f"{user.full_name} is already approved.", "info")
        return redirect(url_for("admin.users"))

    user.is_approved = True
    log_activity(
        current_user,
        "updated",
        "user",
        f"Approved join request for {user.full_name}",
        user.id,
    )
    db.session.commit()
    flash(f"{user.full_name} can now log in.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/reject", methods=["POST"])
@org_admin_required
def reject_user(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_site_admin:
        flash("Cannot reject a site administrator.", "warning")
        return redirect(url_for("admin.users"))

    if user.is_admin:
        flash("Cannot reject a committee admin. Remove admin role first.", "warning")
        return redirect(url_for("admin.users"))

    if user.id == current_user.id:
        flash("You cannot reject your own account.", "warning")
        return redirect(url_for("admin.users"))

    full_name = user.full_name
    ActivityLog.query.filter_by(user_id=user.id).delete()
    PasswordResetRequest.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    log_activity(
        current_user,
        "deleted",
        "user",
        f"Rejected join request and removed account: {full_name}",
        user_id,
    )
    db.session.commit()
    flash(f"Join request from {full_name} was rejected.", "info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-donations-write", methods=["POST"])
@org_admin_required
def toggle_donations_write(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_admin or user.is_site_admin:
        flash("Admins always have full access.", "info")
        return redirect(url_for("admin.users"))

    user.can_write_donations = not user.can_write_donations
    user.sync_can_write()
    access = "donations write" if user.can_write_donations else "no donations write"
    log_activity(
        current_user,
        "updated",
        "user",
        f"Changed {user.full_name} access to {access}",
        user.id,
    )
    db.session.commit()
    flash(f"{user.full_name} — donations: {'enabled' if user.can_write_donations else 'disabled'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-expenses-write", methods=["POST"])
@org_admin_required
def toggle_expenses_write(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_admin or user.is_site_admin:
        flash("Admins always have full access.", "info")
        return redirect(url_for("admin.users"))

    user.can_write_expenses = not user.can_write_expenses
    user.sync_can_write()
    access = "expenses write" if user.can_write_expenses else "no expenses write"
    log_activity(
        current_user,
        "updated",
        "user",
        f"Changed {user.full_name} access to {access}",
        user.id,
    )
    db.session.commit()
    flash(f"{user.full_name} — expenses: {'enabled' if user.can_write_expenses else 'disabled'}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle-write", methods=["POST"])
@org_admin_required
def toggle_write(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_admin or user.is_site_admin:
        flash("Admins always have full access.", "info")
        return redirect(url_for("admin.users"))

    has_any = user.can_write_donations or user.can_write_expenses
    user.can_write_donations = not has_any
    user.can_write_expenses = not has_any
    user.sync_can_write()
    access = "full write" if user.can_edit() else "read-only"
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
@org_admin_required
def toggle_admin(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_site_admin:
        flash("Site administrators are managed from the site admin portal.", "warning")
        return redirect(url_for("admin.users"))

    if user.id == current_user.id:
        flash("You cannot change your own admin role.", "warning")
        return redirect(url_for("admin.users"))

    if user.is_admin:
        admin_count = org_users_query().filter_by(is_admin=True).count()
        if admin_count <= 1:
            flash("At least one committee admin is required.", "warning")
            return redirect(url_for("admin.users"))
        user.is_admin = False
        log_activity(
            current_user,
            "updated",
            "user",
            f"Removed committee admin role from {user.full_name}",
            user.id,
        )
        flash(f"{user.full_name} is no longer a committee admin.", "info")
    else:
        user.is_admin = True
        user.can_write_donations = True
        user.can_write_expenses = True
        user.sync_can_write()
        log_activity(
            current_user,
            "updated",
            "user",
            f"Granted committee admin role to {user.full_name}",
            user.id,
        )
        flash(f"{user.full_name} is now a committee admin.", "success")

    db.session.commit()
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@org_admin_required
def delete_user(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if user.is_site_admin:
        flash("Cannot delete a site administrator.", "warning")
        return redirect(url_for("admin.users"))

    if user.id == current_user.id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.users"))

    if user.is_admin and org_users_query().filter_by(is_admin=True).count() <= 1:
        flash("Cannot delete the only committee admin.", "warning")
        return redirect(url_for("admin.users"))

    full_name = user.full_name
    Donation.query.filter_by(recorded_by_id=user.id).update(
        {"recorded_by_id": current_user.id}
    )
    Expense.query.filter_by(recorded_by_id=user.id).update(
        {"recorded_by_id": current_user.id}
    )
    ActivityLog.query.filter_by(user_id=user.id).delete()
    PasswordResetRequest.query.filter_by(user_id=user.id).delete()
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


def _resolve_password_reset(user, admin):
    pending = PasswordResetRequest.query.filter_by(
        user_id=user.id,
        status=PasswordResetRequest.STATUS_PENDING,
    ).all()
    for reset_request in pending:
        reset_request.status = PasswordResetRequest.STATUS_RESOLVED
        reset_request.resolved_at = datetime.utcnow()
        reset_request.resolved_by_id = admin.id


@admin_bp.route("/users/<int:user_id>/reset-password", methods=["GET", "POST"])
@org_admin_required
def reset_user_password(user_id):
    user = _org_user(user_id)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin.users"))

    if not user.is_approved:
        flash("Approve this user before resetting their password.", "warning")
        return redirect(url_for("admin.users"))

    form = AdminResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        _resolve_password_reset(user, current_user)
        log_activity(
            current_user,
            "updated",
            "user",
            f"Reset password for {user.full_name}",
            user.id,
        )
        db.session.commit()
        flash(f"Password updated for {user.full_name}. Share the new password securely.", "success")
        return redirect(url_for("admin.users"))

    return render_template(
        "admin/reset_password.html",
        form=form,
        user=user,
    )


@admin_bp.route("/password-resets/<int:reset_id>/cancel", methods=["POST"])
@org_admin_required
def cancel_password_reset(reset_id):
    reset_request = PasswordResetRequest.query.filter_by(
        id=reset_id,
        organization_id=current_user.organization_id,
        status=PasswordResetRequest.STATUS_PENDING,
    ).first()
    if not reset_request:
        flash("Password reset request not found or already handled.", "warning")
        return redirect(url_for("admin.users"))

    user = reset_request.user
    reset_request.status = PasswordResetRequest.STATUS_CANCELLED
    reset_request.resolved_at = datetime.utcnow()
    reset_request.resolved_by_id = current_user.id
    log_activity(
        current_user,
        "cancelled",
        "password_reset",
        f"Cancelled password reset request for {user.full_name}",
        reset_request.id,
    )
    db.session.commit()
    flash(f"Password reset request for {user.full_name} was cancelled.", "info")
    return redirect(url_for("admin.users"))


@admin_bp.route("/banner/image")
@login_required
def committee_banner_image():
    org = current_user.organization
    if not org or not org.banner_image_key:
        abort(404)
    response = serve_image(org.banner_image_key, "admin.committee_banner_image")
    if not response:
        abort(404)
    return response


@admin_bp.route("/banner", methods=["POST"])
@org_admin_required
def update_committee_banner():
    org = current_user.organization
    if not org:
        flash("Committee not found.", "danger")
        return redirect(url_for("admin.users"))

    form = CommitteeBannerForm()
    if form.remove_banner.data:
        if org.banner_image_key:
            delete_image(org.banner_image_key)
            org.banner_image_key = None
            log_activity(current_user, "updated", "organization", "Removed festival dashboard banner")
            db.session.commit()
            flash("Festival banner removed.", "info")
        return redirect(url_for("admin.users"))

    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for message in field_errors:
                flash(message, "danger")
        return redirect(url_for("admin.users"))

    if not form.banner_image.data:
        flash("Please choose a banner image to upload.", "warning")
        return redirect(url_for("admin.users"))

    prefix = f"banners/org-{org.id}"
    if org.banner_image_key:
        delete_image(org.banner_image_key)

    storage_key = save_image(form.banner_image.data, prefix)
    if not storage_key:
        flash("Invalid image file. Allowed: JPG, PNG, GIF, WEBP.", "warning")
        return redirect(url_for("admin.users"))

    org.banner_image_key = storage_key
    log_activity(current_user, "updated", "organization", "Updated festival dashboard banner")
    db.session.commit()
    flash("Festival banner updated. It will appear on your committee dashboard.", "success")
    return redirect(url_for("admin.users"))
