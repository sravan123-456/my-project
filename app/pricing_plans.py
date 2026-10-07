"""Subscription plan definitions (display + enforcement via plan_enforcement)."""

PLANS = {
    "free": {
        "id": "free",
        "label": "BASIC",
        "name": "Free",
        "price_inr": 0,
        "price_display": "₹0",
        "period": "forever",
        "period_key": "pricing.period_forever",
        "summary_key": "pricing.free.summary",
        "cta_key": "pricing.cta_free",
        "popular": False,
        "limits": {
            "admins": 1,
            "members": 1,
            "donations": 5,
            "expenses": 5,
            "gallery_photos": 5,
        },
    },
    "monthly": {
        "id": "monthly",
        "label": "ENTRY-LEVEL",
        "name": "One Month",
        "price_inr": 99,
        "price_display": "₹99",
        "period": "30 days",
        "period_key": "pricing.period_30_days",
        "summary_key": "pricing.monthly.summary",
        "cta_key": "pricing.cta_start",
        "popular": False,
        "limits": {
            "admins": 1,
            "members": 10,
            "donations": None,
            "expenses": None,
            "gallery_photos": 10,
        },
    },
    "quarterly": {
        "id": "quarterly",
        "label": "POPULAR",
        "name": "Three Months",
        "price_inr": 249,
        "price_display": "₹249",
        "period": "90 days",
        "period_key": "pricing.period_90_days",
        "summary_key": "pricing.quarterly.summary",
        "cta_key": "pricing.cta_start",
        "popular": True,
        "limits": {
            "admins": 1,
            "members": 30,
            "donations": None,
            "expenses": None,
            "gallery_photos": 30,
        },
    },
    "yearly": {
        "id": "yearly",
        "label": "WHOLE SEASON",
        "name": "One Year",
        "price_inr": 999,
        "price_display": "₹999",
        "period": "1 year",
        "period_key": "pricing.period_1_year",
        "summary_key": "pricing.yearly.summary",
        "cta_key": "pricing.cta_start",
        "popular": False,
        "limits": {
            "admins": 1,
            "members": 30,
            "donations": None,
            "expenses": None,
            "gallery_photos": 30,
        },
    },
}

PLAN_ORDER = ("free", "monthly", "quarterly", "yearly")


def get_plan(plan_id):
    if not plan_id:
        return None
    return PLANS.get(plan_id.strip().lower())


def list_plans():
    return [PLANS[plan_id] for plan_id in PLAN_ORDER]


def plan_select_choices():
    return [(plan["id"], f"{plan['name']} ({plan['price_display']})") for plan in list_plans()]


def format_limit(value):
    if value is None:
        return "Unlimited"
    return str(value)
