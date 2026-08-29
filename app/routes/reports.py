import csv
import io
from datetime import datetime

from flask import Blueprint, Response, render_template, request
from flask_login import current_user, login_required

from app.pdf_report import generate_report_pdf
from app.report_service import build_report_data
from app.year_scope import get_available_years, resolve_report_year, year_archive_summary

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/")
@login_required
def reports():
    org_id = current_user.organization_id
    year = resolve_report_year(org_id, request.args.get("year", type=int))
    data = build_report_data(org_id, year)
    data["available_years"] = get_available_years(org_id)
    data["year_summaries"] = year_archive_summary(org_id)
    return render_template("reports/index.html", **data)


@reports_bp.route("/export/csv")
@login_required
def export_csv():
    org_id = current_user.organization_id
    org_name = current_user.organization.display_name() if current_user.organization else "Festival"
    year = resolve_report_year(org_id, request.args.get("year", type=int))
    data = build_report_data(org_id, year)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([f"{org_name.upper()} - FINANCIAL REPORT ({year})"])
    writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M")])
    writer.writerow([])

    writer.writerow(["DONATIONS"])
    writer.writerow(["Date", "Donor Name", "From", "Payment", "UPI Txn ID", "Phone", "Amount", "Notes"])
    for d in data["donations"]:
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

    writer.writerow(["", "", "Total Donations", f"{data['total_donations']:.2f}", ""])
    writer.writerow([])

    writer.writerow(["EXPENSES"])
    writer.writerow(["Date", "Title", "Category", "Amount", "Description", "Bill"])
    for e in data["expenses"]:
        writer.writerow([
            e.expense_date.strftime("%Y-%m-%d"),
            e.title,
            e.category,
            f"{e.amount:.2f}",
            e.description or "",
            "Yes" if e.bill_filename else "No",
        ])

    writer.writerow(["", "", "", "Total Expenses", f"{data['total_expenses']:.2f}", ""])
    writer.writerow([])
    writer.writerow(["BALANCE", f"{data['balance']:.2f}"])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=festival_report_{year}_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )


@reports_bp.route("/export/pdf")
@login_required
def export_pdf():
    org_id = current_user.organization_id
    org_name = current_user.organization.display_name() if current_user.organization else "Festival"
    year = resolve_report_year(org_id, request.args.get("year", type=int))
    data = build_report_data(org_id, year)
    pdf_buffer = generate_report_pdf(org_name, data)

    return Response(
        pdf_buffer.getvalue(),
        mimetype="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=festival_report_{year}_{datetime.now().strftime('%Y%m%d')}.pdf"
            )
        },
    )
