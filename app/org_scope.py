"""Organization-scoped queries and access helpers."""

from flask import abort
from flask_login import current_user

from app import db
from app.models import User


def require_org_member():
    if not current_user.is_authenticated:
        abort(401)
    if current_user.is_site_admin and current_user.organization_id is None:
        abort(403)
    if current_user.organization_id is None:
        abort(403)


def current_organization():
    require_org_member()
    return current_user.organization


def org_query(model):
    require_org_member()
    return model.query.filter_by(organization_id=current_user.organization_id)


def org_get(model, object_id):
    require_org_member()
    obj = db.session.get(model, object_id)
    if obj is None or obj.organization_id != current_user.organization_id:
        return None
    return obj


def org_users_query():
    require_org_member()
    return User.query.filter_by(organization_id=current_user.organization_id)
