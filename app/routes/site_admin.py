from datetime import date, datetime, timedelta

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user
from sqlalchemy import func

from app import db
from app.forms import CreateOrganizationForm
from app.models import ORG_STATUS_ACTIVE, Donation, Expense, LoginEvent, Organization, User
from app.permissions import site_admin_required

site_admin_bp = Blueprint("site_admin", __name__, url_prefix="/site-admin")


@site_admin_bp.route("/")
@site_admin_required
def dashboard():
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    stats = {
        "organizations": Organization.query.count(),
        "active_organizations": Organization.query.filter_by(status=ORG_STATUS_ACTIVE).count(),
        "pending_organizations": Organization.query.filter_by(status="pending").count(),
        "users": User.query.count(),
        "approved_users": User.query.filter_by(is_approved=True).count(),
        "logins_today": LoginEvent.query.filter(
            LoginEvent.success.is_(True),
            LoginEvent.created_at >= today_start,
        ).count(),
        "logins_week": LoginEvent.query.filter(
            LoginEvent.success.is_(True),
            LoginEvent.created_at >= week_ago,
        ).count(),
        "donations_total": db.session.query(func.coalesce(func.sum(Donation.amount), 0)).scalar(),
        "expenses_total": db.session.query(func.coalesce(func.sum(Expense.amount), 0)).scalar(),
    }

    recent_logins = (
        LoginEvent.query.filter_by(success=True)
        .order_by(LoginEvent.created_at.desc())
        .limit(15)
        .all()
    )
    organizations = Organization.query.order_by(Organization.created_at.desc()).all()
    pending_organizations = Organization.query.filter_by(status="pending").order_by(
        Organization.created_at.asc()
    ).all()

    return render_template(
        "site_admin/dashboard.html",
        stats=stats,
        recent_logins=recent_logins,
        organizations=organizations,
        pending_organizations=pending_organizations,
    )


@site_admin_bp.route("/organizations")
@site_admin_required
def organizations():
    orgs = Organization.query.order_by(Organization.name.asc()).all()
    org_stats = []
    for org in orgs:
        org_stats.append(
            {
                "org": org,
                "users": User.query.filter_by(organization_id=org.id).count(),
                "approved_users": User.query.filter_by(
                    organization_id=org.id, is_approved=True
                ).count(),
                "donations": Donation.query.filter_by(organization_id=org.id).count(),
                "last_login": db.session.query(func.max(User.last_login_at))
                .filter(User.organization_id == org.id)
                .scalar(),
            }
        )
    return render_template("site_admin/organizations.html", org_stats=org_stats)


@site_admin_bp.route("/organizations/new", methods=["GET", "POST"])
@site_admin_required
def create_organization():
    form = CreateOrganizationForm()
    if form.validate_on_submit():
        slug = form.slug.data.strip().lower()
        if Organization.query.filter_by(slug=slug).first():
            flash("That committee code is already in use.", "warning")
            return render_template("site_admin/create_organization.html", form=form)

        org = Organization(
            name=form.name.data.strip(),
            slug=slug,
            village=form.village.data.strip() if form.village.data else None,
            festival_name=form.festival_name.data.strip(),
            festival_year=form.festival_year.data or date.today().year,
            status=ORG_STATUS_ACTIVE,
        )
        db.session.add(org)
        db.session.commit()
        flash(
            f"Committee '{org.display_name()}' created. Share register link: "
            f"{url_for('auth.register', org=org.slug, _external=True)}",
            "success",
        )
        return redirect(url_for("site_admin.organization_detail", org_id=org.id))

    if not form.festival_year.data:
        form.festival_year.data = date.today().year

    return render_template("site_admin/create_organization.html", form=form)


@site_admin_bp.route("/organizations/<int:org_id>")
@site_admin_required
def organization_detail(org_id):
    org = db.session.get(Organization, org_id)
    if not org:
        flash("Committee not found.", "danger")
        return redirect(url_for("site_admin.organizations"))

    users = User.query.filter_by(organization_id=org.id).order_by(User.created_at.desc()).all()
    login_count = LoginEvent.query.filter_by(organization_id=org.id, success=True).count()
    donation_total = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.organization_id == org.id)
        .scalar()
    )

    return render_template(
        "site_admin/organization_detail.html",
        org=org,
        users=users,
        login_count=login_count,
        donation_total=donation_total,
        register_url=url_for("auth.register", org=org.slug, _external=True),
    )


@site_admin_bp.route("/organizations/<int:org_id>/toggle-status", methods=["POST"])
@site_admin_required
def toggle_organization_status(org_id):
    org = db.session.get(Organization, org_id)
    if not org:
        flash("Committee not found.", "danger")
        return redirect(url_for("site_admin.organizations"))

    if org.slug == "indukuru":
        flash("The primary Indukuru committee cannot be suspended.", "warning")
        return redirect(url_for("site_admin.organization_detail", org_id=org.id))

    org.status = "suspended" if org.is_active() else "active"
    db.session.commit()
    flash(f"{org.display_name()} is now {org.status}.", "info")
    return redirect(url_for("site_admin.organization_detail", org_id=org.id))


@site_admin_bp.route("/organizations/<int:org_id>/approve", methods=["POST"])
@site_admin_required
def approve_organization(org_id):
    org = db.session.get(Organization, org_id)
    if not org:
        flash("Committee not found.", "danger")
        return redirect(url_for("site_admin.organizations"))

    org.status = ORG_STATUS_ACTIVE
    User.query.filter_by(organization_id=org.id).update(
        {"is_approved": True}, synchronize_session=False
    )
    db.session.commit()
    flash(f"{org.display_name()} approved. The committee admin can now log in.", "success")
    return redirect(url_for("site_admin.organization_detail", org_id=org.id))
