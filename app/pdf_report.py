import io
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

CHART_PALETTE = [
    "#c0392b",
    "#e67e22",
    "#f1c40f",
    "#27ae60",
    "#2980b9",
    "#8e44ad",
    "#16a085",
    "#d35400",
    "#2c3e50",
    "#7f8c8d",
]

DEFAULT_EXPENSE_CHART = "bar"
DEFAULT_DONATION_CHART = "pie"


def _money(value):
    return f"₹{value:,.2f}"


def _short_label(label, max_len=18):
    text = str(label)
    return text if len(text) <= max_len else f"{text[: max_len - 3]}..."


def _chart_image_buffer(labels, values, chart_type, title):
    if not labels or not any(values):
        return None

    colors_list = CHART_PALETTE[: len(labels)]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))

    if chart_type == "pie":
        ax.pie(
            values,
            labels=[_short_label(label) for label in labels],
            autopct="%1.1f%%",
            colors=colors_list,
            startangle=90,
            textprops={"fontsize": 8},
        )
        ax.axis("equal")
    elif chart_type == "doughnut":
        _wedges, _texts, autotexts = ax.pie(
            values,
            labels=[_short_label(label) for label in labels],
            autopct="%1.1f%%",
            colors=colors_list,
            startangle=90,
            wedgeprops={"width": 0.45},
            textprops={"fontsize": 8},
        )
        for autotext in autotexts:
            autotext.set_fontsize(8)
        ax.axis("equal")
    elif chart_type == "horizontalBar":
        y_pos = range(len(labels))
        ax.barh(y_pos, values, color=colors_list)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([_short_label(label) for label in labels], fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel("Amount (₹)", fontsize=8)
    else:
        x_pos = range(len(labels))
        ax.bar(x_pos, values, color=colors_list)
        ax.set_xticks(x_pos)
        ax.set_xticklabels([_short_label(label) for label in labels], rotation=35, ha="right", fontsize=8)
        ax.set_ylabel("Amount (₹)", fontsize=8)

    ax.set_title(title, fontsize=11, fontweight="bold", pad=10)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer


def _add_chart_section(story, section_style, title, labels, values, chart_type):
    chart_buffer = _chart_image_buffer(labels, values, chart_type, title)
    if not chart_buffer:
        return

    story.append(Paragraph(title, section_style))
    story.append(
        Image(
            chart_buffer,
            width=6.5 * inch,
            height=3.0 * inch,
        )
    )
    story.append(Spacer(1, 0.15 * inch))


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

    expense_labels = report_data.get("expense_chart_labels") or []
    expense_values = report_data.get("expense_chart_values") or []
    donation_labels = report_data.get("donation_chart_labels") or []
    donation_values = report_data.get("donation_chart_values") or []

    if expense_labels and expense_values:
        _add_chart_section(
            story,
            section_style,
            "Expense Spending by Category (Bar Chart)",
            expense_labels,
            expense_values,
            DEFAULT_EXPENSE_CHART,
        )

    if donation_labels and any(donation_values):
        _add_chart_section(
            story,
            section_style,
            "Donations by Source (Pie Chart)",
            donation_labels,
            donation_values,
            DEFAULT_DONATION_CHART,
        )

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
