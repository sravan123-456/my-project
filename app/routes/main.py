from datetime import date

from flask import Blueprint, render_template
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.models import ActivityLog, Donation, Expense

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


@main_bp.route("/dashboard")
@login_required
def dashboard():
    total_donations = db.session.query(func.coalesce(func.sum(Donation.amount), 0)).scalar()
    total_expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).scalar()
    balance = total_donations - total_expenses

    recent_donations = (
        Donation.query.order_by(Donation.donation_date.desc(), Donation.id.desc()).limit(5).all()
    )
    recent_expenses = (
        Expense.query.order_by(Expense.expense_date.desc(), Expense.id.desc()).limit(5).all()
    )

    expense_by_category = (
        db.session.query(Expense.category, func.sum(Expense.amount).label("total"))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    donation_count = Donation.query.count()
    expense_count = Expense.query.count()

    youth_donations = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.donor_group == "youth")
        .scalar()
    )
    village_donations = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.donor_group == "village")
        .scalar()
    )

    recent_activities = (
        ActivityLog.query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(10).all()
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
        youth_donations=youth_donations,
        village_donations=village_donations,
        recent_activities=recent_activities,
        today=date.today(),
    )
