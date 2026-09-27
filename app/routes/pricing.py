from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.forms import StartCommitteeForm
from app.models import ORG_STATUS_PENDING, Organization, User
from app.pricing_plans import get_plan, list_plans
from app.firebase_auth import normalize_phone
from app.routes.auth import SLUG_PATTERN, USERNAME_IN_USE_MESSAGE, _normalize_slug

pricing_bp = Blueprint("pricing", __name__)


def _handle_register(start_form, plan):
    slug = _normalize_slug(start_form.slug.data)
    if not SLUG_PATTERN.match(slug):
        flash("Committee code may only use lowercase letters, numbers, and hyphens.", "warning")
        return None

    if Organization.query.filter_by(slug=slug).first():
        flash("That committee code is already taken. Choose another.", "warning")
        return None

    username = start_form.username.data.strip().lower()
    normalized_phone = normalize_phone(start_form.phone.data)
    if not normalized_phone:
        start_form.phone.errors.append("Enter a valid 10-digit Indian mobile number.")
        flash("Enter a valid 10-digit Indian mobile number.", "danger")
        return None

    if User.query.filter_by(phone=normalized_phone).first():
        start_form.phone.errors.append(
            "This phone number is already linked to another account."
        )
        flash("This phone number is already linked to another account.", "danger")
        return None

    if User.query.filter_by(username=username).first():
        start_form.username.errors.append(USERNAME_IN_USE_MESSAGE)
        flash(USERNAME_IN_USE_MESSAGE, "danger")
        return None

    org = Organization(
        name=start_form.name.data.strip(),
        slug=slug,
        village=start_form.village.data.strip(),
        festival_name=start_form.festival_name.data.strip(),
        festival_year=start_form.festival_year.data or date.today().year,
        status=ORG_STATUS_PENDING,
        subscription_plan=plan["id"],
    )
    db.session.add(org)
    db.session.flush()

    admin = User(
        username=username,
        full_name=start_form.full_name.data.strip(),
        phone=normalized_phone,
        organization_id=org.id,
        is_admin=True,
        can_write=True,
        can_write_donations=True,
        can_write_expenses=True,
        is_approved=False,
    )
    admin.set_password(start_form.password.data)
    db.session.add(admin)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        start_form.username.errors.append(USERNAME_IN_USE_MESSAGE)
        flash(USERNAME_IN_USE_MESSAGE, "danger")
        return None

    if plan["price_inr"] > 0:
        flash(
            f"Committee registered on the {plan['name']} plan ({plan['price_display']}). "
            "Payment will be enabled soon — the site admin will approve your committee shortly.",
            "success",
        )
    else:
        flash(
            "New committee registered on the Free plan. "
            "The site admin will approve it. After approval, log in with your committee code.",
            "success",
        )
    return redirect(url_for("auth.login", org=slug, _anchor="login"))


@pricing_bp.route("/pricing")
def index():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    return render_template("pricing/index.html", plans=list_plans())


@pricing_bp.route("/new-committee/register/<plan_id>", methods=["GET", "POST"])
def register(plan_id):
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    plan = get_plan(plan_id)
    if not plan:
        flash("Please choose a valid subscription plan.", "warning")
        return redirect(url_for("pricing.index"))

    form = StartCommitteeForm()
    if request.method == "POST" and form.validate_on_submit():
        redirect_response = _handle_register(form, plan)
        if redirect_response:
            return redirect_response

    if not form.festival_year.data:
        form.festival_year.data = date.today().year

    return render_template("pricing/register.html", form=form, plan=plan)
