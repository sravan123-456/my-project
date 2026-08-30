from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.activity import log_activity
from app.forms import ProfilePhotoForm
from app.models import User
from app.storage import delete_image, make_image_response, save_image

profile_bp = Blueprint("profile", __name__)


def _same_org_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return None
    if current_user.is_site_admin:
        return user
    if user.organization_id != current_user.organization_id:
        return None
    return user


@profile_bp.route("/")
@login_required
def view_profile():
    form = ProfilePhotoForm()
    welcome = request.args.get("welcome") == "1"
    return render_template(
        "profile/index.html",
        form=form,
        profile_user=current_user,
        welcome=welcome,
    )


@profile_bp.route("/photo/<int:user_id>")
@login_required
def user_photo(user_id):
    user = _same_org_user(user_id)
    if not user or not user.profile_photo_key:
        abort(404)
    response = make_image_response(user.profile_photo_key)
    if not response:
        abort(404)
    return response


@profile_bp.route("/update", methods=["POST"])
@login_required
def update_profile():
    form = ProfilePhotoForm()
    welcome = request.args.get("welcome") == "1"

    if form.remove_photo.data:
        if current_user.profile_photo_key:
            delete_image(current_user.profile_photo_key)
            current_user.profile_photo_key = None
            log_activity(current_user, "updated", "profile", "Removed profile photo")
            db.session.commit()
            flash("Profile photo removed.", "info")
        return redirect(url_for("profile.view_profile", welcome=welcome) if welcome else url_for("profile.view_profile"))

    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for message in field_errors:
                flash(message, "danger")
        return redirect(url_for("profile.view_profile", welcome=welcome) if welcome else url_for("profile.view_profile"))

    if not form.profile_photo.data:
        flash("Please choose a photo to upload.", "warning")
        return redirect(url_for("profile.view_profile", welcome=welcome) if welcome else url_for("profile.view_profile"))

    org_id = current_user.organization_id or 0
    prefix = f"profiles/org-{org_id}/user-{current_user.id}"
    if current_user.profile_photo_key:
        delete_image(current_user.profile_photo_key)

    storage_key = save_image(form.profile_photo.data, prefix)
    if not storage_key:
        flash("Invalid image file. Allowed: JPG, PNG, GIF, WEBP.", "warning")
        return redirect(url_for("profile.view_profile", welcome=welcome) if welcome else url_for("profile.view_profile"))

    current_user.profile_photo_key = storage_key
    log_activity(current_user, "updated", "profile", "Updated profile photo")
    db.session.commit()
    flash("Profile photo updated.", "success")

    if welcome:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("profile.view_profile"))
