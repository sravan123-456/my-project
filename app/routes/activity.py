from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app import db
from app.models import ActivityLog
from app.org_scope import org_query
from app.permissions import org_admin_required

activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/")
@login_required
def activity_log():
    activities = org_query(ActivityLog).order_by(
        ActivityLog.created_at.desc(), ActivityLog.id.desc()
    ).all()
    return render_template("activity/list.html", activities=activities)


@activity_bp.route("/clear", methods=["POST"])
@org_admin_required
def clear_activity_log():
    count = org_query(ActivityLog).count()
    org_query(ActivityLog).delete(synchronize_session=False)
    db.session.commit()
    flash(f"Activity log cleared ({count} entries removed).", "info")
    return redirect(url_for("activity.activity_log"))
