from flask import Blueprint, render_template
from flask_login import login_required

from app.models import ActivityLog

activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/")
@login_required
def activity_log():
    activities = ActivityLog.query.order_by(
        ActivityLog.created_at.desc(), ActivityLog.id.desc()
    ).all()
    return render_template("activity/list.html", activities=activities)
