from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.activity import log_activity
from app.forms import GalleryUploadForm
from app.models import GalleryImage
from app.org_scope import org_get, org_query
from app.permissions import write_required
from app.storage import delete_image, make_image_response, save_image

gallery_bp = Blueprint("gallery", __name__)


@gallery_bp.route("/")
@login_required
def index():
    images = (
        org_query(GalleryImage)
        .order_by(GalleryImage.created_at.desc(), GalleryImage.id.desc())
        .all()
    )
    form = GalleryUploadForm()
    return render_template("gallery/index.html", images=images, form=form)


@gallery_bp.route("/upload", methods=["POST"])
@write_required
def upload():
    form = GalleryUploadForm()
    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for message in field_errors:
                flash(message, "danger")
        return redirect(url_for("gallery.index"))

    org_id = current_user.organization_id
    year = date.today().year
    prefix = f"gallery/org-{org_id}/{year}"
    storage_key = save_image(form.photo.data, prefix)
    if not storage_key:
        flash("Invalid image file. Allowed: JPG, PNG, GIF, WEBP.", "warning")
        return redirect(url_for("gallery.index"))

    image = GalleryImage(
        organization_id=org_id,
        storage_key=storage_key,
        title=form.title.data.strip() if form.title.data else None,
        caption=form.caption.data.strip() if form.caption.data else None,
        festival_year=year,
        uploaded_by_id=current_user.id,
    )
    db.session.add(image)
    log_activity(
        current_user,
        "added",
        "gallery",
        f"Uploaded festival photo{f': {image.title}' if image.title else ''}",
        image.id,
    )
    db.session.commit()
    flash("Photo added to the festival gallery.", "success")
    return redirect(url_for("gallery.index"))


@gallery_bp.route("/<int:image_id>/photo")
@login_required
def photo(image_id):
    image = org_get(GalleryImage, image_id)
    if not image:
        abort(404)
    response = make_image_response(image.storage_key)
    if not response:
        abort(404)
    return response


@gallery_bp.route("/<int:image_id>/delete", methods=["POST"])
@write_required
def delete(image_id):
    image = org_get(GalleryImage, image_id)
    if not image:
        flash("Photo not found.", "danger")
        return redirect(url_for("gallery.index"))

    title = image.title or "Festival photo"
    deleted_id = image.id
    delete_image(image.storage_key)
    db.session.delete(image)
    log_activity(
        current_user,
        "deleted",
        "gallery",
        f"Removed gallery photo: {title}",
        deleted_id,
    )
    db.session.commit()
    flash("Photo removed from gallery.", "info")
    return redirect(url_for("gallery.index"))
