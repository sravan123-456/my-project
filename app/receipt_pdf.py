"""Generate donation receipt PDF and PNG files."""

from flask import current_app, render_template
from weasyprint import HTML


def _receipt_context(donation, amount_words, receipt_purpose):
    return {
        "donation": donation,
        "amount_words": amount_words,
        "receipt_purpose": receipt_purpose,
    }


def _render_html(donation, amount_words, receipt_purpose):
    return render_template(
        "donations/receipt_document.html",
        **_receipt_context(donation, amount_words, receipt_purpose),
    )


def _html_document(html_string):
    static_root = current_app.root_path
    return HTML(string=html_string, base_url=f"file://{static_root}/")


def generate_receipt_pdf(donation, amount_words, receipt_purpose):
    html_string = _render_html(donation, amount_words, receipt_purpose)
    return _html_document(html_string).write_pdf()


def generate_receipt_png(donation, amount_words, receipt_purpose):
    html_string = _render_html(donation, amount_words, receipt_purpose)
    return _html_document(html_string).write_png()
