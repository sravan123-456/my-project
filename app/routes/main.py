from datetime import date

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import extract, func

from app import db
from app.i18n import set_language
from app.models import ActivityLog, DONOR_GROUP_COMMITTEE, DONOR_GROUP_OTHER, Donation, Expense
from app.org_scope import org_query
from app.year_scope import (
    filter_donations_by_year,
    filter_expenses_by_year,
    get_available_years,
    get_selected_year,
    set_selected_year,
    year_archive_summary,
)

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


@main_bp.route("/set-year/<int:year>")
@login_required
def set_year_route(year):
    if year in get_available_years(current_user.organization_id):
        set_selected_year(year)
    return redirect(request.referrer or url_for("main.dashboard"))


@main_bp.route("/help")
def help_page():
    return render_template("main/help.html")


@main_bp.route("/archive")
@login_required
def archive():
    summaries = year_archive_summary(current_user.organization_id)
    return render_template("main/archive.html", summaries=summaries)


@main_bp.route("/dashboard")
@login_required
def dashboard():
    org_id = current_user.organization_id
    year = get_selected_year()

    total_donations = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(
            Donation.organization_id == org_id,
            extract("year", Donation.donation_date) == year,
        )
        .scalar()
    )
    total_expenses = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            Expense.organization_id == org_id,
            extract("year", Expense.expense_date) == year,
        )
        .scalar()
    )
    balance = total_donations - total_expenses

    recent_donations = (
        filter_donations_by_year(org_query(Donation), year)
        .order_by(Donation.donation_date.desc(), Donation.id.desc())
        .limit(5)
        .all()
    )
    recent_expenses = (
        filter_expenses_by_year(org_query(Expense), year)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .limit(5)
        .all()
    )

    expense_by_category = (
        db.session.query(Expense.category, func.sum(Expense.amount).label("total"))
        .filter(
            Expense.organization_id == org_id,
            extract("year", Expense.expense_date) == year,
        )
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    donation_count = filter_donations_by_year(org_query(Donation), year).count()
    expense_count = filter_expenses_by_year(org_query(Expense), year).count()

    committee_donations = (
        filter_donations_by_year(org_query(Donation), year)
        .filter(Donation.donor_group == DONOR_GROUP_COMMITTEE)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )
    other_donations = (
        filter_donations_by_year(org_query(Donation), year)
        .filter(Donation.donor_group == DONOR_GROUP_OTHER)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )

    recent_activities = (
        org_query(ActivityLog)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc())
        .limit(10)
        .all()
    )

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
        recent_activities=recent_activities,
        selected_year=year,
        today=date.today(),
    )
