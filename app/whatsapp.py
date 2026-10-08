# -*- coding: utf-8 -*-
import unicodedata
from urllib.parse import quote

# BMP symbols encode reliably in WhatsApp deep links on all Android devices.
DECOR = "\u2728"  # sparkles
HEART = "\u2764\ufe0f"  # red heart


def format_phone_for_whatsapp(phone):
    if not phone:
        return None

    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None

    if len(digits) == 10:
        return f"91{digits}"
    if len(digits) == 11 and digits.startswith("0"):
        return f"91{digits[1:]}"
    if len(digits) == 12 and digits.startswith("91"):
        return digits

    return digits if len(digits) >= 10 else None


def _festival_title(organization):
    """Build the festival heading shown in WhatsApp thank-you messages."""
    if not organization:
        return "Festival"

    festival = (organization.festival_name or organization.name or "Festival").strip()
    village = (organization.village or "").strip()
    if village and village.lower() not in festival.lower():
        return f"{village} - {festival}"
    return festival


def donation_thank_you_message(donation):
    from app.donation_thank_you import build_donation_thank_you_message, normalize_thank_you_lang

    date_str = donation.donation_date.strftime("%d-%m-%Y")
    amount_str = f"{donation.amount:,.2f}"
    festival_title = _festival_title(donation.organization)
    lang = normalize_thank_you_lang(getattr(donation, "thank_you_lang", None))
    return build_donation_thank_you_message(
        lang,
        donation.donor_name,
        amount_str,
        date_str,
        festival_title,
    )


def pledge_reminder_message(pledge):
    date_str = pledge.promised_date.strftime("%d-%m-%Y")
    amount_str = f"{pledge.promised_amount:,.2f}"
    festival_title = _festival_title(pledge.organization)
    rupee = "\u20b9"
    lamp = "\U0001fa94"

    return (
        f"{lamp} *{festival_title}*\n\n"
        f"\U0001f64f *{pledge.donor_name} \u0c17\u0c3e\u0c30\u0c3f\u0c15\u0c3f,*\n\n"
        f"\u0c2e\u0c40 *{rupee}{amount_str}* \u0c35\u0c3e\u0c17\u0c4d\u0c26\u0c3e\u0c28\u0c02\n"
        f"*{date_str}* \u0c28 \u0c28\u0c2e\u0c4b\u0c26\u0c41 \u0c1a\u0c47\u0c2f\u0c2c\u0c21\u0c3f\u0c02\u0c26\u0c3f.\n\n"
        f"\U0001f64f \u0c38\u0c4c\u0c15\u0c30\u0c4d\u0c2f\u0c02 \u0c05\u0c2f\u0c3f\u0c28\u0c2a\u0c4d\u0c2a\u0c41\u0c21\u0c41\n"
        f"\u0c1a\u0c46\u0c32\u0c4d\u0c32\u0c3f\u0c1a\u0c17\u0c32\u0c30\u0c28\u0c3f \u0c15\u0c4b\u0c30\u0c41\u0c15\u0c41\u0c02\u0c1f\u0c41\u0c28\u0c4d\u0c28\u0c3e\u0c2e\u0c41.\n\n"
        f"{DECOR} *\u0c27\u0c28\u0c4d\u0c2f\u0c35\u0c3e\u0c26\u0c3e\u0c32\u0c41* {DECOR}\n"
        f"\u2014 *{festival_title} Committee* {lamp}"
    )


def build_whatsapp_url(phone, message):
    formatted_phone = format_phone_for_whatsapp(phone)
    if not formatted_phone:
        return None

    normalized = unicodedata.normalize("NFC", message)
    encoded_message = quote(normalized, safe="")
    return f"https://api.whatsapp.com/send?phone={formatted_phone}&text={encoded_message}"


def donation_whatsapp_url(donation):
    if not donation.phone:
        return None
    return build_whatsapp_url(donation.phone, donation_thank_you_message(donation))


def pledge_whatsapp_url(pledge):
    if not pledge.phone or pledge.status != "pending":
        return None
    return build_whatsapp_url(pledge.phone, pledge_reminder_message(pledge))


def outreach_whatsapp_url(phone, message=None):
    default_message = (
        "Hello from DanSetu! Thank you for using our festival committee platform. "
        "We would love to help you get the most from your account."
    )
    return build_whatsapp_url(phone, message or default_message)


def upgrade_outreach_whatsapp_url(phone, full_name, committee_name):
    message = (
        f"Hello {full_name},\n\n"
        f"Thank you for using DanSetu for {committee_name}. "
        "We would love to walk you through the platform and share upgrade options "
        "that help your committee collect more donations and manage expenses easily.\n\n"
        "Reply here when you have a few minutes to talk."
    )
    return build_whatsapp_url(phone, message)
