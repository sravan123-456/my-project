from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.i18n import set_language
from app.models import ActivityLog, DONOR_GROUP_COMMITTEE, DONOR_GROUP_OTHER, Donation, Expense, PasswordResetRequest, Pledge, PLEDGE_STATUS_PENDING
from app.org_scope import org_query
from app.year_scope import (
    filter_donations_by_year,
    filter_expenses_by_year,
    filter_pledges_by_year,
    get_current_festival_year,
)

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET", "POST"])
def index():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    from app.routes.auth import render_landing_page

    return render_landing_page()


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
    festival_year = get_current_festival_year(current_user.organization)
    donations_q = filter_donations_by_year(org_query(Donation), festival_year)
    expenses_q = filter_expenses_by_year(org_query(Expense), festival_year)

    total_donations = donations_q.with_entities(
        func.coalesce(func.sum(Donation.amount), 0)
    ).scalar()
    total_expenses = expenses_q.with_entities(
        func.coalesce(func.sum(Expense.amount), 0)
    ).scalar()
    balance = total_donations - total_expenses

    recent_donations = (
        donations_q.order_by(Donation.donation_date.desc(), Donation.id.desc())
        .limit(5)
        .all()
    )
    recent_expenses = (
        expenses_q.order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(5)
        .all()
    )

    expense_by_category = (
        filter_expenses_by_year(
            db.session.query(Expense.category, func.sum(Expense.amount).label("total"))
            .filter(Expense.organization_id == org_id),
            festival_year,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    donation_count = donations_q.count()
    expense_count = expenses_q.count()

    committee_donations = (
        donations_q.filter(Donation.donor_group == DONOR_GROUP_COMMITTEE)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )
    other_donations = (
        donations_q.filter(Donation.donor_group == DONOR_GROUP_OTHER)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )

    pending_pledges = (
        filter_pledges_by_year(org_query(Pledge), festival_year)
        .filter_by(status=PLEDGE_STATUS_PENDING)
        .all()
    )
    pending_pledge_total = sum(p.promised_amount for p in pending_pledges)
    pending_pledge_count = len(pending_pledges)
    overdue_pledges = [p for p in pending_pledges if p.is_overdue()]
    overdue_pledge_total = sum(p.promised_amount for p in overdue_pledges)
    overdue_pledge_count = len(overdue_pledges)

    pending_password_resets = 0
    if current_user.is_admin:
        pending_password_resets = PasswordResetRequest.query.filter_by(
            organization_id=org_id,
            status=PasswordResetRequest.STATUS_PENDING,
        ).count()

    recent_activities = (
        org_query(ActivityLog)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "dashboard.html",
        dashboard_year=festival_year,
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
        pending_password_resets=pending_password_resets,
        recent_activities=recent_activities,
        today=date.today(),
    )
