import os
from datetime import datetime

from flask import current_app

from app import db
from app.models import (
    ActivityLog,
    Donation,
    Expense,
    GalleryImage,
    LoginEvent,
    MarketingContact,
    PasswordResetRequest,
    Pledge,
    UpgradeLead,
    User,
)
from app.phone_utils import normalize_phone
from app.storage import delete_image


def archive_org_users_for_outreach(org, users):
    """Save user phone numbers before committee accounts are removed."""
    for user in users:
        if not user.phone:
            continue
        phone = normalize_phone(user.phone) or user.phone.strip()
        if not phone:
            continue

        existing = MarketingContact.query.filter_by(
            phone=phone,
            former_committee_slug=org.slug,
            username=user.username,
        ).first()
        if existing:
            existing.full_name = user.full_name
            if user.email:
                existing.email = user.email
            existing.former_committee_name = org.display_name()
            existing.subscription_plan = org.subscription_plan
            existing.archived_at = datetime.utcnow()
            continue

        db.session.add(
            MarketingContact(
                full_name=user.full_name,
                phone=phone,
                email=user.email,
                username=user.username,
                former_committee_name=org.display_name(),
                former_committee_slug=org.slug,
                subscription_plan=org.subscription_plan,
            )
        )


def delete_organization_data(org):
    """Remove a committee and all related data; archive outreach contacts first."""
    users = User.query.filter_by(organization_id=org.id).all()
    archive_org_users_for_outreach(org, users)

    for image in GalleryImage.query.filter_by(organization_id=org.id).all():
        delete_image(image.storage_key)
        db.session.delete(image)

    if org.banner_image_key:
        delete_image(org.banner_image_key)
        org.banner_image_key = None
    if org.payment_qr_image_key:
        delete_image(org.payment_qr_image_key)
        org.payment_qr_image_key = None

    for user in users:
        if user.profile_photo_key:
            delete_image(user.profile_photo_key)

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    for expense in Expense.query.filter_by(organization_id=org.id).all():
        if expense.bill_filename:
            bill_path = os.path.join(upload_folder, expense.bill_filename)
            if os.path.exists(bill_path):
                os.remove(bill_path)

    Pledge.query.filter_by(organization_id=org.id).delete(synchronize_session=False)
    PasswordResetRequest.query.filter_by(organization_id=org.id).delete(
        synchronize_session=False
    )
    UpgradeLead.query.filter_by(organization_id=org.id).delete(synchronize_session=False)
    Donation.query.filter_by(organization_id=org.id).delete(synchronize_session=False)
    Expense.query.filter_by(organization_id=org.id).delete(synchronize_session=False)
    ActivityLog.query.filter_by(organization_id=org.id).delete(synchronize_session=False)

    user_ids = [user.id for user in users]
    if user_ids:
        LoginEvent.query.filter(LoginEvent.user_id.in_(user_ids)).delete(
            synchronize_session=False
        )
    LoginEvent.query.filter_by(organization_id=org.id).delete(synchronize_session=False)

    User.query.filter_by(organization_id=org.id).delete(synchronize_session=False)
    db.session.delete(org)
