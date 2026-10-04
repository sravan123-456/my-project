"""Clear foreign-key references before removing a user account."""

from app import db
from app.models import (
    ActivityLog,
    Donation,
    Expense,
    GalleryImage,
    LoginEvent,
    PasswordResetRequest,
    Pledge,
    UpgradeLead,
    User,
)
from app.storage import delete_image


def prepare_user_for_deletion(user, successor_id):
    """Reassign or remove rows that reference this user."""
    user_id = user.id

    Donation.query.filter_by(recorded_by_id=user_id).update(
        {"recorded_by_id": successor_id},
        synchronize_session=False,
    )
    Expense.query.filter_by(recorded_by_id=user_id).update(
        {"recorded_by_id": successor_id},
        synchronize_session=False,
    )
    Pledge.query.filter_by(recorded_by_id=user_id).update(
        {"recorded_by_id": successor_id},
        synchronize_session=False,
    )
    GalleryImage.query.filter_by(uploaded_by_id=user_id).update(
        {"uploaded_by_id": successor_id},
        synchronize_session=False,
    )

    ActivityLog.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    PasswordResetRequest.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    PasswordResetRequest.query.filter_by(resolved_by_id=user_id).update(
        {"resolved_by_id": None},
        synchronize_session=False,
    )
    LoginEvent.query.filter_by(user_id=user_id).delete(synchronize_session=False)
    UpgradeLead.query.filter_by(user_id=user_id).delete(synchronize_session=False)

    if user.profile_photo_key:
        delete_image(user.profile_photo_key)
        user.profile_photo_key = None


def user_deletion_block_reason(user, acting_user, remaining_admin_count):
    if user.is_site_admin:
        return "Cannot delete a site administrator."
    if user.id == acting_user.id:
        return "Cannot delete your own account."
    if user.is_admin and remaining_admin_count < 1:
        return "Cannot delete the only committee admin."
    return None


def remaining_admin_count_after_deletions(users_to_delete):
    deleting_admin_ids = {user.id for user in users_to_delete if user.is_admin}
    if not deleting_admin_ids:
        return None
    org_id = users_to_delete[0].organization_id
    total_admins = User.query.filter_by(organization_id=org_id, is_admin=True).count()
    return total_admins - len(deleting_admin_ids)
