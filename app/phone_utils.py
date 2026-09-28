import re

_PHONE_DIGITS = re.compile(r"\D+")


def normalize_phone(value):
    if not value:
        return None
    digits = _PHONE_DIGITS.sub("", value.strip())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"
    if value.strip().startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    return None


def normalize_email(value):
    if not value:
        return None
    email = value.strip().lower()
    return email if "@" in email else None


def phone_to_msg91_mobile(phone):
    """Return MSG91 mobile format: 91XXXXXXXXXX (no plus sign)."""
    normalized = normalize_phone(phone)
    if not normalized:
        return None
    return normalized.lstrip("+")
