# -*- coding: utf-8 -*-
from urllib.parse import quote

# Unicode escapes avoid emoji corruption when source files are not saved as UTF-8.
EMOJI_PARTY = "\U0001F389"  # 🎉
EMOJI_PRAY = "\U0001F64F"  # 🙏
EMOJI_ROSE = "\U0001F339"  # 🌹


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


def donation_thank_you_message(donation):
    date_str = donation.donation_date.strftime("%d-%m-%Y")
    amount_str = f"{donation.amount:,.2f}"

    return (
        f"{EMOJI_PARTY} ఇందుకూరు వినాయక చవితి వేడుకలు {EMOJI_PARTY}\n"
        f"ప్రియమైన {donation.donor_name} గారికి,\n\n"
        f"మీ విరాళం ₹{amount_str} సాదరంగా నమోదు చేయబడింది.\n"
        f"తేదీ: {date_str}\n\n"
        f"{EMOJI_PRAY} హృదయపూర్వక ధన్యవాదాలు {EMOJI_PRAY}\n\n"
        f"మన కార్యక్రమానికి మీరు అందించిన చందా సహాయానికి ధన్యవాదాలు. "
        f"మీ సహకారం మనకు ఎంతో విలువైనది. మీకు, మీ కుటుంబ సభ్యులకు "
        f"ఆయురారోగ్యాలు, సుఖసంతోషాలు కలగాలని మనస్ఫూర్తిగా కోరుకుంటున్నాము. {EMOJI_PRAY}\n\n"
        f"మీ అమూల్యమైన సహకారానికి మరోసారి ధన్యవాదాలు. {EMOJI_ROSE}"
    )


def build_whatsapp_url(phone, message):
    formatted_phone = format_phone_for_whatsapp(phone)
    if not formatted_phone:
        return None
    encoded_message = quote(message, safe="", encoding="utf-8")
    return f"https://wa.me/{formatted_phone}?text={encoded_message}"
