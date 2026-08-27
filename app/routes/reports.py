import csv
import io
from datetime import datetime

from flask import Blueprint, Response, render_template
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.models import Donation, Expense

reports_bp = Blueprint("reports", __name__)


def _donation_group_totals():
    youth = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.donor_group == "youth")
        .scalar()
    )
    village = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.donor_group == "village")
        .scalar()
    )
    return youth, village


@reports_bp.route("/")
@login_required
def reports():
    total_donations = db.session.query(func.coalesce(func.sum(Donation.amount), 0)).scalar()
    total_expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).scalar()

    donations = Donation.query.order_by(Donation.donation_date.desc()).all()
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()

    expense_by_category = (
        db.session.query(Expense.category, func.sum(Expense.amount).label("total"))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

    youth_donations, village_donations = _donation_group_totals()

    return render_template(
        "reports/index.html",
        total_donations=total_donations,
        total_expenses=total_expenses,
        balance=total_donations - total_expenses,
        youth_donations=youth_donations,
        village_donations=village_donations,
        donations=donations,
        expenses=expenses,
        expense_by_category=expense_by_category,
    )


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["VINAYAKA FESTIVAL - FINANCIAL REPORT"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
    writer.writerow([])

    writer.writerow(["DONATIONS"])
    writer.writerow(["Date", "Donor Name", "From", "Payment", "UPI Txn ID", "Phone", "Amount", "Notes"])
    for d in Donation.query.order_by(Donation.donation_date).all():
        group_label = "Youth" if d.donor_group == "youth" else "Village Member"
        writer.writerow([
            d.donation_date.strftime("%Y-%m-%d"),
            d.donor_name,
            group_label,
            d.payment_mode_label(),
            d.upi_transaction_id or "",
            d.phone or "",
            f"{d.amount:.2f}",
            d.notes or "",
        ])

    total_donations = db.session.query(func.coalesce(func.sum(Donation.amount), 0)).scalar()
    writer.writerow(["", "", "Total Donations", f"{total_donations:.2f}", ""])
    writer.writerow([])

    writer.writerow(["EXPENSES"])
    writer.writerow(["Date", "Title", "Category", "Amount", "Description", "Bill"])
    for e in Expense.query.order_by(Expense.expense_date).all():
        writer.writerow([
            e.expense_date.strftime("%Y-%m-%d"),
            e.title,
            e.category,
            f"{e.amount:.2f}",
            e.description or "",
            "Yes" if e.bill_filename else "No",
        ])

    total_expenses = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).scalar()
    writer.writerow(["", "", "", "Total Expenses", f"{total_expenses:.2f}", ""])
    writer.writerow([])
    writer.writerow(["BALANCE", f"{total_donations - total_expenses:.2f}"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=vinayaka_festival_report_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )
