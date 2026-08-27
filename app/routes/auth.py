from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.forms import LoginForm, RegisterForm
from app.models import LoginEvent, Organization, User

auth_bp = Blueprint("auth", __name__)


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""


def _record_login(user, username_attempt, success):
    event = LoginEvent(
        user_id=user.id if user else None,
        organization_id=user.organization_id if user else None,
        username_attempt=username_attempt,
        success=success,
        ip_address=_client_ip()[:45],
        user_agent=(request.user_agent.string or "")[:255],
    )
    db.session.add(event)
    if success and user:
        user.login_count = (user.login_count or 0) + 1
        user.last_login_at = datetime.utcnow()


def _registration_org():
    slug = (request.args.get("org") or request.form.get("organization_slug") or "indukuru").strip().lower()
    return Organization.query.filter_by(slug=slug, status="active").first()


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(form.password.data):
            if user.organization and not user.organization.is_active():
                _record_login(user, username, False)
                db.session.commit()
                flash("This committee account is suspended. Contact the site administrator.", "danger")
                return render_template("auth/login.html", form=form)
            if not user.is_approved:
                _record_login(user, username, False)
                db.session.commit()
                flash(
                    "Your account is waiting for admin approval. Please contact your committee admin.",
                    "warning",
                )
                return render_template("auth/login.html", form=form)
            _record_login(user, username, True)
            db.session.commit()
            login_user(user)
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.full_name}!", "success")
            return redirect(next_page or url_for("main.dashboard"))
        _record_login(user, username, False)
        db.session.commit()
        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    organization = _registration_org()
    if not organization:
        flash("Invalid committee code. Use the registration link shared by your committee admin.", "warning")
        return redirect(url_for("auth.login"))

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "warning")
            return render_template(
                "auth/register.html",
                form=form,
                organization=organization,
            )

        is_first_in_org = (
            User.query.filter_by(organization_id=organization.id).count() == 0
        )
        user = User(
            username=username,
            full_name=form.full_name.data.strip(),
            organization_id=organization.id,
            is_admin=is_first_in_org,
            can_write=is_first_in_org,
            is_approved=is_first_in_org,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        if is_first_in_org:
            flash(
                f"Account created for {organization.display_name()}. You are the committee admin.",
                "success",
            )
            return redirect(url_for("auth.login"))
        flash(
            "Registration submitted. Your committee admin must approve your account before you can log in.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/register.html",
        form=form,
        organization=organization,
    )


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
