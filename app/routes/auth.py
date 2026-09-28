import re
import time
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.exceptions import BadRequest
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import db
from app.forms import (
    ChangePasswordForm,
    ForgotPasswordForm,
    JoinRegisterForm,
    LoginForm,
    RegisterForm,
)
from app.msg91 import msg91_enabled, send_otp, verify_otp
from app.phone_utils import normalize_email, normalize_phone
from app.models import (
    ORG_STATUS_PENDING,
    LoginEvent,
    Organization,
    User,
)

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


def _post_login_redirect(user, next_page):
    if next_page:
        return redirect(next_page)
    if not user.profile_photo_key:
        flash("Add a profile photo so your committee can recognize you.", "info")
        return redirect(url_for("profile.view_profile", welcome=1))
    return redirect(url_for("main.dashboard"))


def _complete_login(user, username_attempt):
    blocked = _org_login_blocked_message(user)
    if blocked:
        _record_login(user, username_attempt, False, user.organization_id)
        db.session.commit()
        return None, blocked
    if not user.is_approved:
        _record_login(user, username_attempt, False, user.organization_id)
        db.session.commit()
        return None, (
            "Your join request is pending. Your committee admin must approve you before you can log in."
        )
    _record_login(user, username_attempt, True, user.organization_id)
    db.session.commit()
    login_user(user)
    return user, None


def _handle_landing_post(login_form, join_form):
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
                logged_in_user, error = _complete_login(user, username)
                if error:
                    flash(error, "warning" if user.organization and user.organization.is_pending() else "danger")
                else:
                    next_page = request.args.get("next")
                    flash(f"Welcome back, {logged_in_user.full_name}!", "success")
                    return _post_login_redirect(logged_in_user, next_page), active_tab
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
                normalized_phone = normalize_phone(join_form.phone.data)
                normalized_email = normalize_email(join_form.email.data)
                if not normalized_phone:
                    _mark_join_form_error(
                        join_form,
                        "phone",
                        "Enter a valid 10-digit Indian mobile number.",
                    )
                elif User.query.filter_by(phone=normalized_phone).first():
                    _mark_join_form_error(
                        join_form,
                        "phone",
                        "This phone number is already linked to another account.",
                    )
                elif normalized_email and User.query.filter_by(email=normalized_email).first():
                    _mark_join_form_error(
                        join_form,
                        "email",
                        "This email is already linked to another account.",
                    )
                else:
                    user = User(
                        username=username,
                        full_name=full_name,
                        phone=normalized_phone,
                        email=normalized_email,
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

    return None, active_tab


def _landing_view(login_form, join_form, active_tab):
    if request.method == "POST":
        if join_form.join_submit.data or join_form.errors:
            return "existing-join"
        if login_form.login_submit.data or login_form.errors:
            return "existing-login"
    return "choice"


def render_landing_page():
    login_flash = session.pop("login_flash", None)
    if login_flash:
        flash(login_flash, "success")

    login_form = LoginForm()
    join_form = JoinRegisterForm()
    active_tab = request.form.get("active_tab", "existing")

    if request.method == "POST":
        redirect_response, active_tab = _handle_landing_post(login_form, join_form)
        if redirect_response:
            return redirect_response

    org_slug = request.args.get("org")
    if org_slug and request.method == "GET":
        login_form.committee_code.data = org_slug
        join_form.committee_code.data = org_slug

    landing_view = _landing_view(login_form, join_form, active_tab)
    if org_slug and request.method == "GET" and landing_view == "choice":
        landing_view = "existing-join"

    return render_template(
        "landing.html",
        login_form=login_form,
        join_form=join_form,
        active_tab=active_tab,
        landing_view=landing_view,
    )


def _mask_phone(phone):
    if not phone or len(phone) < 4:
        return "****"
    return f"{'*' * (len(phone) - 4)}{phone[-4:]}"


def _clear_password_reset_session():
    session.pop("pwd_reset_user_id", None)
    session.pop("pwd_reset_phone", None)
    session.pop("pwd_reset_otp_sent_at", None)
MSG91_RESEND_GAP_SECONDS = 30


def _send_reset_otp(phone, force=False):
    now = time.time()
    last_sent = session.get("pwd_reset_otp_sent_at")
    if last_sent and now - last_sent < MSG91_RESEND_GAP_SECONDS:
        if force:
            wait = int(MSG91_RESEND_GAP_SECONDS - (now - last_sent)) + 1
            return (
                False,
                f"Please wait {wait} seconds before requesting another OTP.",
            )
        return True, None

    otp = f"{secrets.randbelow(10**6):06d}"
    ok, error = send_otp(phone, otp=otp)
    if ok:
        session["pwd_reset_otp_sent_at"] = now
        _store_reset_otp(otp)
    return ok, error


@auth_bp.route("/forgot-password/otp")
def forgot_password_otp():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    user_id = session.get("pwd_reset_user_id")
    phone = session.get("pwd_reset_phone")
    if not user_id or not phone:
        flash("Start again by entering your committee code and username.", "warning")
        return redirect(url_for("auth.forgot_password"))

    user = User.query.get(user_id)
    if not user or user.phone != phone:
        _clear_password_reset_session()
        flash("Password reset session expired. Please try again.", "warning")
        return redirect(url_for("auth.forgot_password"))

    if not msg91_enabled():
        flash("Phone OTP reset is not configured yet. Contact your committee admin.", "warning")
        return redirect(url_for("auth.forgot_password"))

    force_resend = request.args.get("resend") == "1"
    otp_sent, otp_error = _send_reset_otp(phone, force=force_resend)

    return render_template(
        "auth/forgot_password_otp.html",
        masked_phone=_mask_phone(phone),
        otp_sent=otp_sent,
        otp_error=otp_error,
    )


@auth_bp.route("/forgot-password/otp/send", methods=["POST"])
def forgot_password_otp_send():
    if not msg91_enabled():
        return jsonify({"ok": False, "error": "Phone OTP reset is not configured."}), 503

    user_id = session.get("pwd_reset_user_id")
    phone = session.get("pwd_reset_phone")
    if not user_id or not phone:
        return jsonify({"ok": False, "error": "Session expired. Start again."}), 400

    user = User.query.get(user_id)
    if not user or user.phone != phone:
        _clear_password_reset_session()
        return jsonify({"ok": False, "error": "Session expired. Start again."}), 400

    ok, error = _send_reset_otp(phone, force=True)
    if not ok:
        return jsonify({"ok": False, "error": error or "Could not send OTP."}), 502

    return jsonify({"ok": True})


@auth_bp.route("/forgot-password/complete", methods=["POST"])
def forgot_password_complete():
    if not msg91_enabled():
        return jsonify({"ok": False, "error": "Phone OTP reset is not configured."}), 503

    user_id = session.get("pwd_reset_user_id")
    phone = session.get("pwd_reset_phone")
    if not user_id or not phone:
        return jsonify({"ok": False, "error": "Session expired. Start again."}), 400

    user = User.query.get(user_id)
    if not user or user.phone != phone:
        _clear_password_reset_session()
        return jsonify({"ok": False, "error": "Session expired. Start again."}), 400

    payload = request.get_json(silent=True) or {}
    otp = (payload.get("otp") or "").strip()
    password = (payload.get("password") or "").strip()
    if not otp:
        raise BadRequest("Missing otp.")
    if len(password) < 6:
        return jsonify({"ok": False, "error": "Password must be at least 6 characters."}), 400

    ok, error = _verify_reset_otp(otp)
    if not ok:
        return jsonify({"ok": False, "error": error or "Invalid or expired OTP. Try again."}), 401

    user.set_password(password)
    db.session.commit()
    _clear_password_reset_session()
    session["login_flash"] = "Password updated. Log in with your new password."

    return jsonify(
        {
            "ok": True,
            "redirect": url_for("auth.login", _anchor="login"),
        }
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    return render_landing_page()


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
    return redirect(url_for("pricing.index"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = ForgotPasswordForm()
    org_slug = request.args.get("org")
    if org_slug and request.method == "GET":
        form.committee_code.data = org_slug

    if form.validate_on_submit():
        if not msg91_enabled():
            flash(
                "Phone OTP reset is not configured yet. Contact your committee admin.",
                "warning",
            )
        else:
            committee_code = _normalize_slug(form.committee_code.data)
            username = form.username.data.strip().lower()
            org, org_error = _get_active_org(committee_code)

            if org_error:
                flash(org_error, "danger")
            else:
                user = User.query.filter_by(
                    username=username, organization_id=org.id
                ).first()
                if not user:
                    flash("No account found with that committee code and username.", "danger")
                elif not user.is_approved:
                    flash(
                        "Your account is not approved yet. Contact your committee admin.",
                        "warning",
                    )
                elif not user.phone:
                    flash(
                        "No phone number is saved on your account. Contact your committee admin.",
                        "warning",
                    )
                else:
                    session["pwd_reset_user_id"] = user.id
                    session["pwd_reset_phone"] = user.phone
                    return redirect(url_for("auth.forgot_password_otp"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(form.password.data)
            db.session.commit()
            flash("Your password has been updated.", "success")
            return redirect(url_for("main.dashboard"))

    return render_template("auth/change_password.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.index"))
