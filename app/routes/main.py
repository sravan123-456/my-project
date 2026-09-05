from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.i18n import set_language
from app.models import ActivityLog, DONOR_GROUP_COMMITTEE, DONOR_GROUP_OTHER, Donation, Expense, Pledge, PLEDGE_STATUS_PENDING
from app.org_scope import org_query

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/pending")
@login_required
def pending():
    if current_user.is_approved:
        return redirect(url_for("main.dashboard"))
    return render_template("main/pending.html")


@main_bp.route("/set-language/<lang>")
def set_language_route(lang):
    set_language(lang)
    return redirect(request.referrer or url_for("main.index"))


@main_bp.route("/help")
def help_page():
    return render_template("main/help.html")


@main_bp.route("/archive")
@login_required
def archive():
    return redirect(url_for("reports.reports"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    org_id = current_user.organization_id
    total_donations = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.organization_id == org_id)
        .scalar()
    )
    total_expenses = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.organization_id == org_id)
        .scalar()
    )
    balance = total_donations - total_expenses

    recent_donations = (
        org_query(Donation)
        .order_by(Donation.donation_date.desc(), Donation.id.desc())
        .limit(5)
        .all()
    )
    recent_expenses = (
        org_query(Expense)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(5)
        .all()
    )

    expense_by_category = (
        db.session.query(Expense.category, func.sum(Expense.amount).label("total"))
        .filter(Expense.organization_id == org_id)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    donation_count = org_query(Donation).count()
    expense_count = org_query(Expense).count()

    committee_donations = (
        org_query(Donation)
        .filter(Donation.donor_group == DONOR_GROUP_COMMITTEE)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )
    other_donations = (
        org_query(Donation)
        .filter(Donation.donor_group == DONOR_GROUP_OTHER)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )

    pending_pledges = org_query(Pledge).filter_by(status=PLEDGE_STATUS_PENDING).all()
    pending_pledge_total = sum(p.promised_amount for p in pending_pledges)
    pending_pledge_count = len(pending_pledges)
    overdue_pledges = [p for p in pending_pledges if p.is_overdue()]
    overdue_pledge_total = sum(p.promised_amount for p in overdue_pledges)
    overdue_pledge_count = len(overdue_pledges)

    recent_activities = (
        org_query(ActivityLog)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(10)
        .all()
    )

    from datetime import date

    return render_template(
        "dashboard.html",
        balance=balance,
        total_donations=total_donations,
        total_expenses=total_expenses,
        recent_donations=recent_donations,
        recent_expenses=recent_expenses,
        expense_by_category=expense_by_category,
        donation_count=donation_count,
        expense_count=expense_count,
        committee_donations=committee_donations,
        other_donations=other_donations,
        pending_pledge_total=pending_pledge_total,
        pending_pledge_count=pending_pledge_count,
        overdue_pledge_total=overdue_pledge_total,
        overdue_pledge_count=overdue_pledge_count,
        recent_activities=recent_activities,
        today=date.today(),
    )
