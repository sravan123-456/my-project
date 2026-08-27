import uuid

from app.models import Donation

FESTIVAL_YEAR = 2026
RECEIPT_PURPOSE = f"Vinayaka Festival {FESTIVAL_YEAR} Celebrations"
COMMITTEE_NAME = "VINAYAKA FESTIVAL COMMITTEE"
COMMITTEE_ADDRESS = "Indukuru, Mudigubba - 515511"

_ONES = [
    "",
    "One",
    "Two",
    "Three",
    "Four",
    "Five",
    "Six",
    "Seven",
    "Eight",
    "Nine",
    "Ten",
    "Eleven",
    "Twelve",
    "Thirteen",
    "Fourteen",
    "Fifteen",
    "Sixteen",
    "Seventeen",
    "Eighteen",
    "Nineteen",
]
_TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _words_under_thousand(number):
    if number == 0:
        return ""
    if number < 20:
        return _ONES[number]
    if number < 100:
        tens, ones = divmod(number, 10)
        return _TENS[tens] + (f" {_ONES[ones]}" if ones else "")
    hundreds, remainder = divmod(number, 100)
    text = f"{_ONES[hundreds]} Hundred"
    if remainder:
        text += f" {_words_under_thousand(remainder)}"
    return text


def amount_in_words(amount):
    rupees = int(amount)
    paise = round((amount - rupees) * 100)

    if rupees == 0 and paise == 0:
        return "Rupees Zero Only"

    parts = []
    crore, rupees = divmod(rupees, 10000000)
    lakh, rupees = divmod(rupees, 100000)
    thousand, rupees = divmod(rupees, 1000)

    if crore:
        parts.append(f"{_words_under_thousand(crore)} Crore")
    if lakh:
        parts.append(f"{_words_under_thousand(lakh)} Lakh")
    if thousand:
        parts.append(f"{_words_under_thousand(thousand)} Thousand")
    if rupees:
        parts.append(_words_under_thousand(rupees))

    text = "Rupees " + " ".join(parts)
    if paise:
        text += f" and {_words_under_thousand(paise)} Paise"
    return text + " Only"


def new_receipt_token():
    return uuid.uuid4().hex


def next_receipt_number(donation_date):
    year = donation_date.year
    prefix = f"VF-{year}-"
    count = Donation.query.filter(Donation.receipt_number.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:04d}"
