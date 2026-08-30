from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.activity import log_activity
from app.forms import GalleryUploadForm
from app.gallery_service import (
    GALLERY_MAX_PHOTOS_PER_YEAR,
    count_gallery_photos,
    gallery_has_room,
    get_gallery_years,
    resolve_gallery_year,
)
from app.models import GalleryImage
from app.org_scope import org_get, org_query
from app.permissions import write_required
from app.storage import delete_image, save_image, serve_image

gallery_bp = Blueprint("gallery", __name__)


def _gallery_redirect(year):
    return redirect(url_for("gallery.index", year=year))


@gallery_bp.route("/")
@login_required
def index():
    org_id = current_user.organization_id
    selected_year = resolve_gallery_year(org_id, request.args.get("year", type=int))
    available_years = get_gallery_years(org_id)
    photo_count = count_gallery_photos(org_id, selected_year)
    can_upload = gallery_has_room(org_id, selected_year)

    images = (
        org_query(GalleryImage)
        .filter(GalleryImage.festival_year == selected_year)
        .order_by(GalleryImage.created_at.desc(), GalleryImage.id.desc())
        .all()
    )

    form = GalleryUploadForm()
    form.festival_year.choices = [(year, str(year)) for year in available_years]
    form.festival_year.data = selected_year

    return render_template(
        "gallery/index.html",
        images=images,
        form=form,
        selected_year=selected_year,
        available_years=available_years,
        photo_count=photo_count,
        max_photos=GALLERY_MAX_PHOTOS_PER_YEAR,
        can_upload=can_upload,
    )


@gallery_bp.route("/upload", methods=["POST"])
@write_required
def upload():
    org_id = current_user.organization_id
    form = GalleryUploadForm()
    form.festival_year.choices = [(year, str(year)) for year in get_gallery_years(org_id)]

    if not form.validate_on_submit():
        for field_errors in form.errors.values():
            for message in field_errors:
                flash(message, "danger")
        return _gallery_redirect(request.args.get("year", type=int) or date.today().year)

    year = form.festival_year.data
    if not gallery_has_room(org_id, year):
        flash(
            f"This year already has {GALLERY_MAX_PHOTOS_PER_YEAR} photos. "
            "Delete an old photo or choose another year.",
            "warning",
        )
        return _gallery_redirect(year)

    prefix = f"gallery/org-{org_id}/{year}"
    storage_key = save_image(form.photo.data, prefix)
    if not storage_key:
        flash("Invalid image file. Allowed: JPG, PNG, GIF, WEBP.", "warning")
        return _gallery_redirect(year)

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
        f"Uploaded {year} festival photo{f': {image.title}' if image.title else ''}",
        image.id,
    )
    db.session.commit()
    flash("Photo added to the festival gallery.", "success")
    return _gallery_redirect(year)


@gallery_bp.route("/<int:image_id>/photo")
@login_required
def photo(image_id):
    image = org_get(GalleryImage, image_id)
    if not image:
        abort(404)
    response = serve_image(image.storage_key, "gallery.photo", image_id=image.id)
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

    year = image.festival_year or date.today().year
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
    return _gallery_redirect(year)
