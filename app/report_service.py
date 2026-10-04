from sqlalchemy import func

from app.models import DONOR_GROUP_COMMITTEE, DONOR_GROUP_OTHER, Donation, Expense
from app.org_scope import org_query
from app.year_scope import filter_donations_by_year, filter_expenses_by_year


def build_report_data(org_id, year):
    donations_q = filter_donations_by_year(org_query(Donation), year)
    expenses_q = filter_expenses_by_year(org_query(Expense), year)

    total_donations = donations_q.with_entities(
        func.coalesce(func.sum(Donation.amount), 0)
    ).scalar()
    total_expenses = expenses_q.with_entities(
        func.coalesce(func.sum(Expense.amount), 0)
    ).scalar()

    donations = donations_q.order_by(Donation.donation_date.desc()).all()
    expenses = expenses_q.order_by(Expense.expense_date.desc()).all()

    expense_by_category = (
        filter_expenses_by_year(org_query(Expense), year)
        .with_entities(Expense.category, func.sum(Expense.amount).label("total"))
        .group_by(Expense.category)
        .order_by(func.sum(Expense.amount).desc())
        .all()
    )

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

    expense_chart_labels = [category for category, _total in expense_by_category]
    expense_chart_values = [float(total) for _category, total in expense_by_category]

    return {
        "year": year,
        "total_donations": float(total_donations or 0),
        "total_expenses": float(total_expenses or 0),
        "balance": float(total_donations or 0) - float(total_expenses or 0),
        "committee_donations": float(committee_donations or 0),
        "other_donations": float(other_donations or 0),
        "donations": donations,
        "expenses": expenses,
        "expense_by_category": expense_by_category,
        "expense_chart_labels": expense_chart_labels,
        "expense_chart_values": expense_chart_values,
        "donation_chart_labels": ["Committee Member", "Other"],
        "donation_chart_values": [
            float(committee_donations or 0),
            float(other_donations or 0),
        ],
    }
