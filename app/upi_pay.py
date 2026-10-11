# -*- coding: utf-8 -*-
"""Build NPCI UPI payment URIs and QR images with a fixed amount."""

import io
import re
from urllib.parse import quote

import qrcode

UPI_VPA_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{2,256}@[a-zA-Z0-9]{2,64}$")


def normalize_upi_vpa(value):
    if not value:
        return None
    vpa = value.strip().lower()
    if not vpa or not UPI_VPA_PATTERN.match(vpa):
        return None
    return vpa


def format_upi_amount(amount):
    return f"{float(amount):.2f}"


def build_upi_pay_uri(vpa, amount, payee_name, transaction_note=None):
    normalized_vpa = normalize_upi_vpa(vpa)
    if not normalized_vpa:
        return None
    if amount is None or float(amount) <= 0:
        return None

    params = [
        f"pa={quote(normalized_vpa, safe='')}",
        f"pn={quote((payee_name or 'Donation').strip()[:50], safe='')}",
        f"am={format_upi_amount(amount)}",
        "cu=INR",
    ]
    note = (transaction_note or "").strip()
    if note:
        params.append(f"tn={quote(note[:100], safe='')}")

    return "upi://pay?" + "&".join(params)


def generate_upi_qr_png(upi_uri):
    qr = qrcode.QRCode(version=None, box_size=8, border=2)
    qr.add_data(upi_uri)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer
