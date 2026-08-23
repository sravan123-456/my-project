from app import db
from app.models import ActivityLog


def log_activity(user, action, entity_type, description, entity_id=None):
    entry = ActivityLog(
        user_id=user.id,
        user_name=user.full_name,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.session.add(entry)
