from urllib.parse import quote


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
        f"🎉 ఇందుకూరు వినాయక చవితి వేడుకలు 🎉\n"
        f"ప్రియమైన {donation.donor_name} గారికి,\n\n"
        f"మీ విరాళం ₹{amount_str} సాదరంగా నమోదు చేయబడింది.\n"
        f"తేదీ: {date_str}\n\n"
        f"🙏 హృదయపూర్వక ధన్యవాదాలు 🙏\n\n"
        f"మన కార్యక్రమానికి మీరు అందించిన చందా సహాయానికి ధన్యవాదాలు. "
        f"మీ సహకారం మనకు ఎంతో విలువైనది. మీకు, మీ కుటుంబ సభ్యులకు "
        f"ఆయురారోగ్యాలు, సుఖసంతోషాలు కలగాలని మనస్ఫూర్తిగా కోరుకుంటున్నాము. 🙏\n\n"
        f"మీ అమూల్యమైన సహకారానికి మరోసారి ధన్యవాదాలు. 🌹"
    )


def build_whatsapp_url(phone, message):
    formatted_phone = format_phone_for_whatsapp(phone)
    if not formatted_phone:
        return None
    return f"https://wa.me/{formatted_phone}?text={quote(message)}"
