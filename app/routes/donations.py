import os
import uuid
from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app import db
from app.activity import log_activity
from app.forms import DonationForm
from app.models import Donation
from app.permissions import write_required
from app.whatsapp import build_whatsapp_url, donation_thank_you_message

donations_bp = Blueprint("donations", __name__)


@donations_bp.route("/")
@login_required
def list_donations():
    donations = Donation.query.order_by(
        Donation.donation_date.desc(), Donation.id.desc()
    ).all()
    return render_template("donations/list.html", donations=donations)


@donations_bp.route("/add", methods=["GET", "POST"])
@write_required
def add_donation():
    form = DonationForm()
    form.donation_date.data = date.today()

    if form.validate_on_submit():
        donation = Donation(
            donor_name=form.donor_name.data.strip(),
            amount=form.amount.data,
            phone=form.phone.data.strip() if form.phone.data else None,
            notes=form.notes.data.strip() if form.notes.data else None,
            donation_date=form.donation_date.data,
            recorded_by_id=current_user.id,
        )
        db.session.add(donation)
        db.session.flush()
        log_activity(
            current_user,
            "added",
            "donation",
            f"Added donation of ₹{donation.amount:,.2f} from {donation.donor_name}",
            donation.id,
        )
        db.session.commit()
        flash(f"Donation of ₹{donation.amount:,.2f} from {donation.donor_name} recorded.", "success")
        if donation.phone and build_whatsapp_url(donation.phone, donation_thank_you_message(donation)):
            return redirect(url_for("donations.send_whatsapp", donation_id=donation.id))
        return redirect(url_for("donations.list_donations"))

    return render_template("donations/form.html", form=form, title="Add Donation")


@donations_bp.route("/<int:donation_id>/edit", methods=["GET", "POST"])
@write_required
def edit_donation(donation_id):
    donation = db.session.get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("donations.list_donations"))

    form = DonationForm(obj=donation)
    if form.validate_on_submit():
        donation.donor_name = form.donor_name.data.strip()
        donation.amount = form.amount.data
        donation.phone = form.phone.data.strip() if form.phone.data else None
        donation.notes = form.notes.data.strip() if form.notes.data else None
        donation.donation_date = form.donation_date.data
        log_activity(
            current_user,
            "updated",
            "donation",
            f"Updated donation from {donation.donor_name} to ₹{donation.amount:,.2f}",
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
        flash("No phone number on file for this donor. Add a phone number to send WhatsApp thank you.", "warning")
        return redirect(url_for("donations.edit_donation", donation_id=donation.id))

    message = donation_thank_you_message(donation)
    whatsapp_url = build_whatsapp_url(donation.phone, message)
    if not whatsapp_url:
        flash("Invalid phone number. Please use a valid 10-digit Indian mobile number.", "warning")
        return redirect(url_for("donations.edit_donation", donation_id=donation.id))

    return redirect(whatsapp_url)


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
