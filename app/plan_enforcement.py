"""Enforce subscription plan limits stored on Organization.subscription_plan."""

from app.models import Donation, Expense, GalleryImage, User
from app.org_scope import org_query
from app.pricing_plans import get_plan
from app.year_scope import (
    filter_donations_by_year,
    filter_expenses_by_year,
    get_current_festival_year,
)


def plan_for_org(org):
    if not org:
        return get_plan("free")
    return get_plan(org.subscription_plan) or get_plan("free")


def limits_for_org(org):
    return plan_for_org(org)["limits"]


def _format_cap(value):
    if value is None:
        return "unlimited"
    return str(value)


def count_approved_members(org_id):
    return User.query.filter_by(organization_id=org_id, is_approved=True).count()


def count_committee_admins(org_id):
    return User.query.filter_by(organization_id=org_id, is_admin=True).count()


def count_donations(org, festival_year=None):
    year = festival_year or get_current_festival_year(org)
    return filter_donations_by_year(
        org_query(Donation).filter(Donation.organization_id == org.id),
        year,
    ).count()


def count_expenses(org, festival_year=None):
    year = festival_year or get_current_festival_year(org)
    return filter_expenses_by_year(
        org_query(Expense).filter(Expense.organization_id == org.id),
        year,
    ).count()


def count_gallery_items_for_year(org, year):
    if not org:
        return 0
    return (
        org_query(GalleryImage)
        .filter(
            GalleryImage.organization_id == org.id,
            GalleryImage.festival_year == year,
        )
        .count()
    )


def gallery_photo_limit(org):
    return limits_for_org(org).get("gallery_photos")


def plan_usage_snapshot(org, festival_year=None):
    if not org:
        return None
    year = festival_year or get_current_festival_year(org)
    limits = limits_for_org(org)
    usage = {
        "members": count_approved_members(org.id),
        "admins": count_committee_admins(org.id),
        "donations": count_donations(org, year),
        "expenses": count_expenses(org, year),
        "gallery_photos": count_gallery_items_for_year(org, year),
    }
    remaining = {}
    for key, cap in limits.items():
        if cap is None:
            remaining[key] = None
        else:
            remaining[key] = max(0, cap - usage.get(key, 0))
    plan = plan_for_org(org)
    return {
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "festival_year": year,
        "limits": limits,
        "usage": usage,
        "remaining": remaining,
    }


def _limit_message(org, resource_label, cap):
    plan = plan_for_org(org)
    return (
        f"Your {plan['name']} plan allows up to {_format_cap(cap)} {resource_label}. "
        "Upgrade your plan to increase this limit."
    )


def can_approve_member(org, extra=1):
    cap = limits_for_org(org).get("members")
    if cap is None:
        return True, None
    if count_approved_members(org.id) + extra > cap:
        return False, _limit_message(org, "approved members", cap)
    return True, None


def can_grant_admin(org):
    cap = limits_for_org(org).get("admins")
    if cap is None:
        return True, None
    if count_committee_admins(org.id) + 1 > cap:
        return False, _limit_message(org, "committee admins", cap)
    return True, None


def can_add_donation(org, extra=1):
    cap = limits_for_org(org).get("donations")
    if cap is None:
        return True, None
    if count_donations(org) + extra > cap:
        return False, _limit_message(
            org, f"donations for festival year {get_current_festival_year(org)}", cap
        )
    return True, None


def can_add_expense(org, extra=1):
    cap = limits_for_org(org).get("expenses")
    if cap is None:
        return True, None
    if count_expenses(org) + extra > cap:
        return False, _limit_message(
            org, f"expenses for festival year {get_current_festival_year(org)}", cap
        )
    return True, None


def can_add_gallery_items(org, year, extra=1):
    cap = gallery_photo_limit(org)
    if cap is None:
        return True, None
    if count_gallery_items_for_year(org, year) + extra > cap:
        return False, _limit_message(org, f"gallery items for {year}", cap)
    return True, None

