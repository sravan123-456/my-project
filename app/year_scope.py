from datetime import date

from flask_login import current_user
from sqlalchemy import extract, func

from app import db
from app.models import Donation, Expense


def get_available_years(org_id):
    years = set()
    donation_years = (
        db.session.query(extract("year", Donation.donation_date))
        .filter(Donation.organization_id == org_id)
        .distinct()
        .all()
    )
    expense_years = (
        db.session.query(extract("year", Expense.expense_date))
        .filter(Expense.organization_id == org_id)
        .distinct()
        .all()
    )
    for (year_value,) in donation_years + expense_years:
        if year_value:
            years.add(int(year_value))
    if current_user.is_authenticated and current_user.organization and current_user.organization.festival_year:
        years.add(int(current_user.organization.festival_year))
    if not years:
        years.add(date.today().year)
    return sorted(years, reverse=True)


def resolve_report_year(org_id, year_arg=None):
    available_years = get_available_years(org_id)
    if year_arg and year_arg in available_years:
        return year_arg
    if (
        current_user.is_authenticated
        and current_user.organization
        and current_user.organization.festival_year in available_years
    ):
        return int(current_user.organization.festival_year)
    return available_years[0]


def filter_donations_by_year(query, year):
    return query.filter(extract("year", Donation.donation_date) == year)


def filter_expenses_by_year(query, year):
    return query.filter(extract("year", Expense.expense_date) == year)


def year_archive_summary(org_id):
    summaries = []
    for year in get_available_years(org_id):
        donations_total = (
            db.session.query(func.coalesce(func.sum(Donation.amount), 0))
            .filter(
                Donation.organization_id == org_id,
                extract("year", Donation.donation_date) == year,
            )
            .scalar()
        )
        expenses_total = (
            db.session.query(func.coalesce(func.sum(Expense.amount), 0))
            .filter(
                Expense.organization_id == org_id,
                extract("year", Expense.expense_date) == year,
            )
            .scalar()
        )
        donation_count = (
            db.session.query(func.count(Donation.id))
            .filter(
                Donation.organization_id == org_id,
                extract("year", Donation.donation_date) == year,
            )
            .scalar()
        )
        expense_count = (
            db.session.query(func.count(Expense.id))
            .filter(
                Expense.organization_id == org_id,
                extract("year", Expense.expense_date) == year,
            )
            .scalar()
        )
        summaries.append(
            {
                "year": year,
                "donations_total": float(donations_total or 0),
                "expenses_total": float(expenses_total or 0),
                "balance": float(donations_total or 0) - float(expenses_total or 0),
                "donation_count": donation_count or 0,
                "expense_count": expense_count or 0,
            }
        )
    return summaries
