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
    date_str = donation.donation_date.strftime("%d-%m-%Y")
    amount_str = f"{donation.amount:,.2f}"
    festival_title = _festival_title(donation.organization)
    rupee = "\u20b9"

    return (
        f"{DECOR} {festival_title} {DECOR}\n"
        f"\u0c2a\u0c4d\u0c30\u0c3f\u0c2f\u0c2e\u0c48\u0c28 {donation.donor_name} \u0c17\u0c3e\u0c30\u0c3f\u0c15\u0c3f,\n\n"
        f"\u0c2e\u0c40 \u0c35\u0c3f\u0c30\u0c3e\u0c33\u0c02 {rupee}{amount_str} \u0c38\u0c3e\u0c26\u0c30\u0c02\u0c17\u0c3e \u0c28\u0c2e\u0c4b\u0c26\u0c41 \u0c1a\u0c47\u0c2f\u0c2c\u0c21\u0c3f\u0c02\u0c26\u0c3f.\n"
        f"\u0c24\u0c47\u0c26\u0c40: {date_str}\n\n"
        f"{DECOR} \u0c39\u0c43\u0c26\u0c2f\u0c2a\u0c42\u0c30\u0c4d\u0c35\u0c15 \u0c27\u0c28\u0c4d\u0c2f\u0c35\u0c3e\u0c26\u0c3e\u0c32\u0c41 {DECOR}\n\n"
        f"\u0c2e\u0c28 {festival_title} \u0c15\u0c3e\u0c30\u0c4d\u0c2f\u0c15\u0c4d\u0c30\u0c2e\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c2e\u0c40\u0c30\u0c41 \u0c05\u0c02\u0c26\u0c3f\u0c02\u0c1a\u0c3f\u0c28 \u0c1a\u0c02\u0c26\u0c3e \u0c38\u0c39\u0c3e\u0c2f\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c27\u0c28\u0c4d\u0c2f\u0c35\u0c3e\u0c26\u0c3e\u0c32\u0c41. "
        f"\u0c2e\u0c40 \u0c38\u0c39\u0c15\u0c3e\u0c30\u0c02 \u0c2e\u0c28\u0c15\u0c41 \u0c0e\u0c02\u0c24\u0c4b \u0c35\u0c3f\u0c32\u0c41\u0c35\u0c48\u0c28\u0c26\u0c3f. \u0c2e\u0c40\u0c15\u0c41, \u0c2e\u0c40 \u0c15\u0c41\u0c1f\u0c41\u0c02\u0c2c \u0c38\u0c2d\u0c4d\u0c2f\u0c41\u0c32\u0c15\u0c41 "
        f"\u0c06\u0c2f\u0c41\u0c30\u0c3e\u0c30\u0c4b\u0c17\u0c4d\u0c2f\u0c3e\u0c32\u0c41, \u0c38\u0c41\u0c16\u0c38\u0c02\u0c24\u0c4b\u0c37\u0c3e\u0c32\u0c41 \u0c15\u0c32\u0c17\u0c3e\u0c32\u0c28\u0c3f \u0c2e\u0c28\u0c38\u0c4d\u0c2b\u0c42\u0c30\u0c4d\u0c24\u0c3f\u0c17\u0c3e \u0c15\u0c4b\u0c30\u0c41\u0c15\u0c41\u0c02\u0c1f\u0c41\u0c28\u0c4d\u0c28\u0c3e\u0c2e\u0c41. {DECOR}\n\n"
        f"\u0c2e\u0c40 \u0c05\u0c2e\u0c42\u0c32\u0c4d\u0c2f\u0c2e\u0c48\u0c28 \u0c38\u0c39\u0c15\u0c3e\u0c30\u0c3e\u0c28\u0c3f\u0c15\u0c3f \u0c2e\u0c30\u0c4b\u0c38\u0c3e\u0c30\u0c3f \u0c27\u0c28\u0c4d\u0c2f\u0c35\u0c3e\u0c26\u0c3e\u0c32\u0c41. {HEART}"
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
