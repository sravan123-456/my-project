import re
from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.forms import JoinCommitteeForm, LoginForm, RegisterForm, StartCommitteeForm
from app.models import ORG_STATUS_PENDING, LoginEvent, Organization, User

auth_bp = Blueprint("auth", __name__)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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


def _normalize_slug(slug):
    return slug.strip().lower().replace(" ", "-")


def _registration_org():
    slug = request.args.get("org") or request.form.get("organization_slug")
    if not slug:
        return None
    return Organization.query.filter_by(slug=_normalize_slug(slug), status="active").first()


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
            blocked = _org_login_blocked_message(user)
            if blocked:
                _record_login(user, username, False)
                db.session.commit()
                flash(blocked, "warning" if user.organization and user.organization.is_pending() else "danger")
                return render_template("auth/login.html", form=form)
            if not user.is_approved:
                _record_login(user, username, False)
                db.session.commit()
                flash(
                    "Your account is waiting for committee admin approval.",
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
def register_hub():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    join_form = JoinCommitteeForm()
    if join_form.validate_on_submit():
        slug = _normalize_slug(join_form.committee_code.data)
        org = Organization.query.filter_by(slug=slug, status="active").first()
        if not org:
            flash("Committee code not found or not active yet. Check the code or register a new committee.", "warning")
        else:
            return redirect(url_for("auth.register", org=slug))

    return render_template("auth/register_hub.html", join_form=join_form)


@auth_bp.route("/register/join", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    organization = _registration_org()
    if not organization:
        flash("Choose a valid committee code to join, or register a new committee.", "warning")
        return redirect(url_for("auth.register_hub"))

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


@auth_bp.route("/start-committee", methods=["GET", "POST"])
def start_committee():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = StartCommitteeForm()
    if form.validate_on_submit():
        slug = _normalize_slug(form.slug.data)
        if not SLUG_PATTERN.match(slug):
            flash("Committee code may only use lowercase letters, numbers, and hyphens.", "warning")
            return render_template("auth/start_committee.html", form=form)

        if Organization.query.filter_by(slug=slug).first():
            flash("That committee code is already taken. Choose another.", "warning")
            return render_template("auth/start_committee.html", form=form)

        username = form.username.data.strip().lower()
        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "warning")
            return render_template("auth/start_committee.html", form=form)

        org = Organization(
            name=form.name.data.strip(),
            slug=slug,
            village=form.village.data.strip(),
            festival_name=form.festival_name.data.strip(),
            festival_year=form.festival_year.data or date.today().year,
            status=ORG_STATUS_PENDING,
        )
        db.session.add(org)
        db.session.flush()

        admin = User(
            username=username,
            full_name=form.full_name.data.strip(),
            organization_id=org.id,
            is_admin=True,
            can_write=True,
            is_approved=False,
        )
        admin.set_password(form.password.data)
        db.session.add(admin)
        db.session.commit()

        flash(
            "Your committee registration was submitted. The site admin will review and approve it. "
            "You can log in after approval.",
            "success",
        )
        return redirect(url_for("auth.login"))

    if not form.festival_year.data:
        form.festival_year.data = date.today().year

    return render_template("auth/start_committee.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
