from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user, login_required


def write_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.can_edit():
            flash("You have read-only access. Contact an admin to get write permission.", "warning")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def org_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            flash("Committee admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    return org_admin_required(view)


def site_admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if not current_user.is_site_admin:
            flash("Site admin access required.", "danger")
            return redirect(url_for("main.dashboard"))
        return view(*args, **kwargs)

    return wrapped
