import csv
import io
from datetime import datetime

from flask import Blueprint, Response, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.models import DONOR_GROUP_COMMITTEE, DONOR_GROUP_OTHER, Donation, Expense
from app.org_scope import org_query

reports_bp = Blueprint("reports", __name__)


def _donation_group_totals():
    committee = (
        org_query(Donation)
        .filter(Donation.donor_group == DONOR_GROUP_COMMITTEE)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )
    other = (
        org_query(Donation)
        .filter(Donation.donor_group == DONOR_GROUP_OTHER)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )
    return committee, other


@reports_bp.route("/")
@login_required
def reports():
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

    donations = org_query(Donation).order_by(Donation.donation_date.desc()).all()
    expenses = org_query(Expense).order_by(Expense.expense_date.desc()).all()

    expense_by_category = (
        db.session.query(Expense.category, func.sum(Expense.amount).label("total"))
        .filter(Expense.organization_id == org_id)
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    committee_donations, other_donations = _donation_group_totals()

    expense_chart_labels = [category for category, _total in expense_by_category]
    expense_chart_values = [float(total) for _category, total in expense_by_category]

    return render_template(
        "reports/index.html",
        total_donations=total_donations,
        total_expenses=total_expenses,
        balance=total_donations - total_expenses,
        committee_donations=committee_donations,
        other_donations=other_donations,
        donations=donations,
        expenses=expenses,
        expense_by_category=expense_by_category,
        expense_chart_labels=expense_chart_labels,
        expense_chart_values=expense_chart_values,
        donation_chart_labels=["Committee Member", "Other"],
        donation_chart_values=[float(committee_donations), float(other_donations)],
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    org_id = current_user.organization_id
    org_name = current_user.organization.display_name() if current_user.organization else "Festival"

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([f"{org_name.upper()} - FINANCIAL REPORT"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
    writer.writerow([])

    writer.writerow(["DONATIONS"])
    writer.writerow(["Date", "Donor Name", "From", "Payment", "UPI Txn ID", "Phone", "Amount", "Notes"])
    for d in org_query(Donation).order_by(Donation.donation_date).all():
        writer.writerow([
            d.donation_date.strftime("%Y-%m-%d"),
            d.donor_name,
            d.donor_group_label(),
            d.payment_mode_label(),
            d.upi_transaction_id or "",
            d.phone or "",
            f"{d.amount:.2f}",
            d.notes or "",
        ])

    total_donations = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.organization_id == org_id)
        .scalar()
    )
    writer.writerow(["", "", "Total Donations", f"{total_donations:.2f}", ""])
    writer.writerow([])

    writer.writerow(["EXPENSES"])
    writer.writerow(["Date", "Title", "Category", "Amount", "Description", "Bill"])
    for e in org_query(Expense).order_by(Expense.expense_date).all():
        writer.writerow([
            e.expense_date.strftime("%Y-%m-%d"),
            e.title,
            e.category,
            f"{e.amount:.2f}",
            e.description or "",
            "Yes" if e.bill_filename else "No",
        ])

    total_expenses = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.organization_id == org_id)
        .scalar()
    )
    writer.writerow(["", "", "", "Total Expenses", f"{total_expenses:.2f}", ""])
    writer.writerow([])
    writer.writerow(["BALANCE", f"{total_donations - total_expenses:.2f}"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=festival_report_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )
