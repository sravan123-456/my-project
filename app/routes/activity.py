from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app import db
from app.models import ActivityLog
from app.permissions import admin_required

activity_bp = Blueprint("activity", __name__)


@activity_bp.route("/")
@login_required
def activity_log():
    activities = ActivityLog.query.order_by(
        ActivityLog.created_at.desc(), ActivityLog.id.desc()
    ).all()
    return render_template("activity/list.html", activities=activities)


@activity_bp.route("/clear", methods=["POST"])
@admin_required
def clear_activity_log():
    count = ActivityLog.query.count()
    ActivityLog.query.delete()
    db.session.commit()
    flash(f"Activity log cleared ({count} entries removed).", "info")
    return redirect(url_for("activity.activity_log"))
