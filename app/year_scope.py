from datetime import date

from flask_login import current_user
from sqlalchemy import and_, extract, func, or_

from app import db
from app.models import Donation, Expense, Pledge


def get_current_festival_year(org):
    if org and org.festival_year:
        return int(org.festival_year)
    return date.today().year


def _year_column(model):
    if model is Donation:
        return Donation.festival_year, Donation.donation_date
    if model is Expense:
        return Expense.festival_year, Expense.expense_date
    if model is Pledge:
        return Pledge.festival_year, Pledge.promised_date
    raise ValueError(f"Unsupported model for year scope: {model}")


def filter_by_festival_year(query, model, year):
    year_column, date_column = _year_column(model)
    return query.filter(
        or_(
            year_column == year,
            and_(year_column.is_(None), extract("year", date_column) == year),
        )
    )


def filter_donations_by_year(query, year):
    return filter_by_festival_year(query, Donation, year)


def filter_expenses_by_year(query, year):
    return filter_by_festival_year(query, Expense, year)


def filter_pledges_by_year(query, year):
    return filter_by_festival_year(query, Pledge, year)


def get_available_years(org_id):
    years = set()
    for model in (Donation, Expense, Pledge):
        year_column, date_column = _year_column(model)
        tagged_years = (
            db.session.query(year_column)
            .filter(
                model.organization_id == org_id,
                year_column.isnot(None),
            )
            .distinct()
            .all()
        )
        for (year_value,) in tagged_years:
            if year_value:
                years.add(int(year_value))

        legacy_years = (
            db.session.query(extract("year", date_column))
            .filter(
                model.organization_id == org_id,
                or_(year_column.is_(None), year_column == 0),
            )
            .distinct()
            .all()
        )
        for (year_value,) in legacy_years:
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


def year_archive_summary(org_id):
    summaries = []
    for year in get_available_years(org_id):
        donations_total = (
            filter_donations_by_year(
                db.session.query(func.coalesce(func.sum(Donation.amount), 0)).filter(
                    Donation.organization_id == org_id
                ),
                year,
            ).scalar()
        )
        expenses_total = (
            filter_expenses_by_year(
                db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
                    Expense.organization_id == org_id
                ),
                year,
            ).scalar()
        )
        donation_count = (
            filter_donations_by_year(
                db.session.query(func.count(Donation.id)).filter(
                    Donation.organization_id == org_id
                ),
                year,
            ).scalar()
        )
        expense_count = (
            filter_expenses_by_year(
                db.session.query(func.count(Expense.id)).filter(
                    Expense.organization_id == org_id
                ),
                year,
            ).scalar()
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
