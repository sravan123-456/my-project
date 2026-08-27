import re
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.forms import JoinRegisterForm, LoginForm, RegisterForm, StartCommitteeForm
from app.models import ORG_STATUS_PENDING, LoginEvent, Organization, User

auth_bp = Blueprint("auth", __name__)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_IN_USE_MESSAGE = "This name is already in use. Please choose another name."
USERNAME_IN_USE_MESSAGE = "This username is already in use. Please choose another username."


def _client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or ""


def _record_login(user, username_attempt, success, organization_id=None):
    event = LoginEvent(
        user_id=user.id if user else None,
        organization_id=organization_id or (user.organization_id if user else None),
        username_attempt=username_attempt,
        success=success,
        ip_address=_client_ip()[:45],
        user_agent=(request.user_agent.string or "")[:255],
    )
    db.session.add(event)
    if success and user:
        user.login_count = (user.login_count or 0) + 1
        user.last_login_at = datetime.utcnow()


def _normalize_slug(slug):
    return slug.strip().lower().replace(" ", "-")


def _get_active_org(slug):
    org = Organization.query.filter_by(slug=_normalize_slug(slug)).first()
    if not org:
        return None, "Committee code not found."
    if org.is_pending():
        return None, "This committee is waiting for site admin approval."
    if not org.is_active():
        return None, "This committee is suspended. Contact the site administrator."
    return org, None


def _registration_org():
    slug = request.args.get("org") or request.form.get("organization_slug")
    if not slug:
        return None
    org, _error = _get_active_org(slug)
    return org


def _org_login_blocked_message(user):
    if not user.organization:
        return None
    if user.organization.is_pending():
        return (
            "Your committee is waiting for site admin approval. "
            "You will be able to log in once it is approved."
        )
    if not user.organization.is_active():
        return "This committee account is suspended. Contact the site administrator."
    return None


def _join_registration_conflicts(org_id, username, full_name):
    normalized_username = username.strip().lower()
    normalized_full_name = full_name.strip().lower()

    existing_username = User.query.filter_by(username=normalized_username).first()
    if existing_username:
        return "username", USERNAME_IN_USE_MESSAGE

    existing_full_name = User.query.filter(
        User.organization_id == org_id,
        func.lower(User.full_name) == normalized_full_name,
    ).first()
    if existing_full_name:
        return "full_name", NAME_IN_USE_MESSAGE

    return None, None


def _mark_join_form_error(join_form, field_name, message):
    getattr(join_form, field_name).errors.append(message)
    flash(message, "danger")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    login_form = LoginForm()
    join_form = JoinRegisterForm()
    start_form = StartCommitteeForm()
    active_tab = request.form.get("active_tab", "existing")

    if login_form.login_submit.data and login_form.validate_on_submit():
        active_tab = "existing"
        committee_code = _normalize_slug(login_form.committee_code.data)
        username = login_form.username.data.strip().lower()
        org, org_error = _get_active_org(committee_code)

        if org_error:
            _record_login(None, username, False)
            db.session.commit()
            flash(org_error, "danger")
        else:
            user = User.query.filter_by(username=username, organization_id=org.id).first()
            if user and user.check_password(login_form.password.data):
                blocked = _org_login_blocked_message(user)
                if blocked:
                    _record_login(user, username, False, org.id)
                    db.session.commit()
                    flash(blocked, "warning" if user.organization and user.organization.is_pending() else "danger")
                elif not user.is_approved:
                    _record_login(user, username, False, org.id)
                    db.session.commit()
                    flash(
                        "Your join request is pending. Your committee admin must approve you before you can log in.",
                        "warning",
                    )
                else:
                    _record_login(user, username, True, org.id)
                    db.session.commit()
                    login_user(user)
                    next_page = request.args.get("next")
                    flash(f"Welcome back, {user.full_name}!", "success")
                    return redirect(next_page or url_for("main.dashboard"))
            else:
                _record_login(user, username, False, org.id if org else None)
                db.session.commit()
                flash("Invalid committee code, username, or password.", "danger")

    elif join_form.join_submit.data and join_form.validate_on_submit():
        active_tab = "existing"
        committee_code = _normalize_slug(join_form.committee_code.data)
        org, org_error = _get_active_org(committee_code)
        if org_error:
            flash(org_error, "danger")
        else:
            username = join_form.username.data.strip().lower()
            full_name = join_form.full_name.data.strip()
            conflict_field, conflict_message = _join_registration_conflicts(
                org.id, username, full_name
            )
            if conflict_field:
                _mark_join_form_error(join_form, conflict_field, conflict_message)
            else:
                user = User(
                    username=username,
                    full_name=full_name,
                    organization_id=org.id,
                    is_admin=False,
                    can_write=False,
                    is_approved=False,
                )
                user.set_password(join_form.password.data)
                db.session.add(user)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    _mark_join_form_error(join_form, "username", USERNAME_IN_USE_MESSAGE)
                else:
                    flash(
                        "Join request submitted. Your committee admin will approve your account. "
                        "Then log in with your committee code, username, and password.",
                        "success",
                    )
                    login_form.committee_code.data = committee_code
                    join_form.committee_code.data = committee_code

    elif join_form.join_submit.data and request.method == "POST":
        active_tab = "existing"
        flash("Please correct the errors in the join request form below.", "danger")

    elif start_form.start_submit.data and start_form.validate_on_submit():
        active_tab = "new"
        slug = _normalize_slug(start_form.slug.data)
        if not SLUG_PATTERN.match(slug):
            flash("Committee code may only use lowercase letters, numbers, and hyphens.", "warning")
        elif Organization.query.filter_by(slug=slug).first():
            flash("That committee code is already taken. Choose another.", "warning")
        else:
            username = start_form.username.data.strip().lower()
            if User.query.filter_by(username=username).first():
                start_form.username.errors.append(USERNAME_IN_USE_MESSAGE)
                flash(USERNAME_IN_USE_MESSAGE, "danger")
            else:
                org = Organization(
                    name=start_form.name.data.strip(),
                    slug=slug,
                    village=start_form.village.data.strip(),
                    festival_name=start_form.festival_name.data.strip(),
                    festival_year=start_form.festival_year.data or date.today().year,
                    status=ORG_STATUS_PENDING,
                )
                db.session.add(org)
                db.session.flush()

                admin = User(
                    username=username,
                    full_name=start_form.full_name.data.strip(),
                    organization_id=org.id,
                    is_admin=True,
                    can_write=True,
                    is_approved=False,
                )
                admin.set_password(start_form.password.data)
                db.session.add(admin)
                db.session.commit()
                flash(
                    "New committee registered. The site admin will approve it. "
                    "After approval, log in using the Existing Committee tab with your committee code.",
                    "success",
                )
                login_form.committee_code.data = slug
                active_tab = "existing"

    if not start_form.festival_year.data:
        start_form.festival_year.data = date.today().year

    return render_template(
        "auth/login.html",
        login_form=login_form,
        join_form=join_form,
        start_form=start_form,
        active_tab=active_tab,
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register_hub():
    return redirect(url_for("auth.login", _anchor="existing-committee"))


@auth_bp.route("/register/join", methods=["GET", "POST"])
def register():
    org_slug = request.args.get("org")
    if org_slug:
        return redirect(url_for("auth.login", org=org_slug, _anchor="existing-committee"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/start-committee", methods=["GET", "POST"])
def start_committee():
    return redirect(url_for("auth.login", _anchor="new-committee"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
