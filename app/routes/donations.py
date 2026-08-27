from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.activity import log_activity
from app.forms import DonationForm
from app.models import (
    DONOR_GROUP_CHOICES,
    DONOR_GROUP_VILLAGE,
    PAYMENT_CASH,
    PAYMENT_MODE_CHOICES,
    Donation,
)
from app.permissions import write_required
from app.receipt_utils import amount_in_words, new_receipt_token, next_receipt_number, RECEIPT_PURPOSE
from app.whatsapp import build_whatsapp_url, donation_thank_you_message

donations_bp = Blueprint("donations", __name__)


def _donation_totals():
    youth = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.donor_group == "youth")
        .scalar()
    )
    village = (
        db.session.query(func.coalesce(func.sum(Donation.amount), 0))
        .filter(Donation.donor_group == "village")
        .scalar()
    )
    return youth, village


def _prepare_donation_form(form):
    form.donor_group.choices = DONOR_GROUP_CHOICES
    form.payment_mode.choices = PAYMENT_MODE_CHOICES


def _save_donation_from_form(form, recorded_by_id):
    donation = Donation(
        donor_name=form.donor_name.data.strip(),
        donor_group=form.donor_group.data,
        payment_mode=form.payment_mode.data,
        upi_transaction_id=(
            form.upi_transaction_id.data.strip()
            if form.payment_mode.data == "upi" and form.upi_transaction_id.data
            else None
        ),
        amount=form.amount.data,
        phone=form.phone.data.strip(),
        notes=form.notes.data.strip() if form.notes.data else None,
        donation_date=form.donation_date.data,
        recorded_by_id=recorded_by_id,
        receipt_token=new_receipt_token(),
    )
    db.session.add(donation)
    db.session.flush()
    donation.receipt_number = next_receipt_number(donation.donation_date)
    return donation


@donations_bp.route("/")
@login_required
def list_donations():
    group_filter = request.args.get("group", "all")
    query = Donation.query
    if group_filter in ("youth", "village"):
        query = query.filter_by(donor_group=group_filter)

    donations = query.order_by(
        Donation.donation_date.desc(), Donation.id.desc()
    ).all()
    youth_total, village_total = _donation_totals()

    return render_template(
        "donations/list.html",
        donations=donations,
        group_filter=group_filter,
        youth_total=youth_total,
        village_total=village_total,
    )


@donations_bp.route("/add", methods=["GET", "POST"])
@write_required
def add_donation():
    form = DonationForm()
    _prepare_donation_form(form)

    if request.method == "GET":
        form.donation_date.data = date.today()
        form.donor_group.data = DONOR_GROUP_VILLAGE
        form.payment_mode.data = PAYMENT_CASH

    if form.validate_on_submit():
        donation = _save_donation_from_form(form, current_user.id)
        log_activity(
            current_user,
            "added",
            "donation",
            f"Added {donation.donor_group_label()} {donation.payment_mode_label()} donation "
            f"of ₹{donation.amount:,.2f} from {donation.donor_name}",
            donation.id,
        )
        db.session.commit()
        flash(f"Donation of ₹{donation.amount:,.2f} from {donation.donor_name} recorded.", "success")
        return redirect(url_for("donations.donation_saved", donation_id=donation.id))

    return render_template("donations/form.html", form=form, title="Add Donation")


@donations_bp.route("/receipt/<receipt_token>")
def public_receipt(receipt_token):
    donation = Donation.query.filter_by(receipt_token=receipt_token).first()
    if not donation:
        flash("Receipt not found.", "danger")
        return redirect(url_for("auth.login"))
    return render_template(
        "donations/receipt.html",
        donation=donation,
        amount_words=amount_in_words(donation.amount),
        receipt_purpose=RECEIPT_PURPOSE,
        printable=True,
    )


@donations_bp.route("/<int:donation_id>/receipt")
@login_required
def donation_receipt(donation_id):
    donation = db.session.get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("donations.list_donations"))
    return render_template(
        "donations/receipt.html",
        donation=donation,
        amount_words=amount_in_words(donation.amount),
        receipt_purpose=RECEIPT_PURPOSE,
        printable=True,
    )


@donations_bp.route("/<int:donation_id>/saved")
@write_required
def donation_saved(donation_id):
    donation = db.session.get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("donations.list_donations"))

    receipt_url = url_for(
        "donations.public_receipt",
        receipt_token=donation.receipt_token,
        _external=True,
    )
    whatsapp_url = None
    if donation.phone:
        message = donation_thank_you_message(donation, receipt_url=receipt_url)
        whatsapp_url = build_whatsapp_url(donation.phone, message)

    return render_template(
        "donations/saved.html",
        donation=donation,
        whatsapp_url=whatsapp_url,
        receipt_url=receipt_url,
    )


@donations_bp.route("/<int:donation_id>/edit", methods=["GET", "POST"])
@write_required
def edit_donation(donation_id):
    donation = db.session.get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("donations.list_donations"))

    form = DonationForm(obj=donation)
    _prepare_donation_form(form)

    if form.validate_on_submit():
        donation.donor_name = form.donor_name.data.strip()
        donation.donor_group = form.donor_group.data
        donation.payment_mode = form.payment_mode.data
        donation.upi_transaction_id = (
            form.upi_transaction_id.data.strip()
            if form.payment_mode.data == "upi" and form.upi_transaction_id.data
            else None
        )
        donation.amount = form.amount.data
        donation.phone = form.phone.data.strip()
        donation.notes = form.notes.data.strip() if form.notes.data else None
        donation.donation_date = form.donation_date.data
        log_activity(
            current_user,
            "updated",
            "donation",
            f"Updated {donation.donor_group_label()} donation from {donation.donor_name} to ₹{donation.amount:,.2f}",
            donation.id,
        )
        db.session.commit()
        flash("Donation updated successfully.", "success")
        return redirect(url_for("donations.list_donations"))

    return render_template("donations/form.html", form=form, title="Edit Donation", donation=donation)


@donations_bp.route("/<int:donation_id>/whatsapp")
@write_required
def send_whatsapp(donation_id):
    donation = db.session.get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("donations.list_donations"))

    if not donation.phone:
        flash("No phone number on file for this donor.", "warning")
        return redirect(url_for("donations.edit_donation", donation_id=donation.id))

    return redirect(url_for("donations.donation_saved", donation_id=donation.id))


@donations_bp.route("/<int:donation_id>/delete", methods=["POST"])
@write_required
def delete_donation(donation_id):
    donation = db.session.get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
    else:
        donor_name = donation.donor_name
        amount = donation.amount
        donation_id = donation.id
        db.session.delete(donation)
        log_activity(
            current_user,
            "deleted",
            "donation",
            f"Deleted donation of ₹{amount:,.2f} from {donor_name}",
            donation_id,
        )
        db.session.commit()
        flash("Donation deleted.", "info")
    return redirect(url_for("donations.list_donations"))
