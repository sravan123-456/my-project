import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _money(value):
    return f"₹{value:,.2f}"


def generate_report_pdf(org_name, report_data, generated_at=None):
    generated_at = generated_at or datetime.now()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=10,
        spaceAfter=6,
    )

    story = [
        Paragraph(org_name, title_style),
        Paragraph(
            f"Financial Report — Festival Year {report_data['year']}",
            styles["Normal"],
        ),
        Paragraph(
            f"Generated: {generated_at.strftime('%d %b %Y, %I:%M %p')}",
            styles["Normal"],
        ),
        Spacer(1, 0.2 * inch),
    ]

    summary_table = Table(
        [
            ["Total Donations", _money(report_data["total_donations"])],
            ["Total Expenses", _money(report_data["total_expenses"])],
            ["Balance", _money(report_data["balance"])],
            ["Committee Member Donations", _money(report_data["committee_donations"])],
            ["Other Donations", _money(report_data["other_donations"])],
        ],
        colWidths=[3.2 * inch, 2.2 * inch],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8f9fa")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    story.extend([summary_table, Spacer(1, 0.2 * inch)])

    if report_data["expense_by_category"]:
        story.append(Paragraph("Expense Breakdown by Category", section_style))
        category_rows = [["Category", "Amount", "%"]]
        total_expenses = report_data["total_expenses"] or 1
        for category, total in report_data["expense_by_category"]:
            pct = (float(total) / total_expenses) * 100
            category_rows.append([category, _money(float(total)), f"{pct:.1f}%"])
        category_table = Table(category_rows, colWidths=[2.8 * inch, 1.5 * inch, 1.1 * inch])
        category_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dc3545")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ]
            )
        )
        story.extend([category_table, Spacer(1, 0.15 * inch)])

    story.append(Paragraph("All Donations", section_style))
    donation_rows = [["Date", "Donor", "From", "Amount"]]
    for donation in report_data["donations"]:
        donation_rows.append(
            [
                donation.donation_date.strftime("%d %b %Y"),
                donation.donor_name,
                donation.donor_group_label(),
                _money(donation.amount),
            ]
        )
    if len(donation_rows) == 1:
        donation_rows.append(["-", "No donations", "-", "-"])
    donation_table = Table(donation_rows, colWidths=[1.1 * inch, 2.2 * inch, 1.3 * inch, 1.0 * inch])
    donation_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#198754")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.extend([donation_table, Spacer(1, 0.15 * inch)])

    story.append(Paragraph("All Expenses", section_style))
    expense_rows = [["Date", "Title", "Category", "Amount"]]
    for expense in report_data["expenses"]:
        expense_rows.append(
            [
                expense.expense_date.strftime("%d %b %Y"),
                expense.title,
                expense.category,
                _money(expense.amount),
            ]
        )
    if len(expense_rows) == 1:
        expense_rows.append(["-", "No expenses", "-", "-"])
    expense_table = Table(expense_rows, colWidths=[1.1 * inch, 2.0 * inch, 1.4 * inch, 1.0 * inch])
    expense_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dc3545")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(expense_table)

    doc.build(story)
    buffer.seek(0)
    return buffer
