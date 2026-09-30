from datetime import datetime

from app import db
from app.models import UpgradeLead


def maybe_create_upgrade_lead(user):
    if not user or not user.organization:
        return
    if user.organization.subscription_plan != "free":
        return
    if (user.login_count or 0) != 1:
        return
    if UpgradeLead.query.filter_by(user_id=user.id).first():
        return

    db.session.add(
        UpgradeLead(
            user_id=user.id,
            organization_id=user.organization_id,
            full_name=user.full_name,
            phone=user.phone,
            committee_name=user.organization.display_name(),
            subscription_plan=user.organization.subscription_plan,
            first_login_at=user.last_login_at or datetime.utcnow(),
        )
    )
