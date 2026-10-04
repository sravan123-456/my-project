from datetime import date

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db
from app.activity import log_activity
from app.forms import DonationForm
from app.models import (
    DONOR_GROUP_CHOICES,
    DONOR_GROUP_COMMITTEE,
    DONOR_GROUP_OTHER,
    PAYMENT_CASH,
    PAYMENT_MODE_CHOICES,
    Donation,
    Pledge,
    PLEDGE_STATUS_PENDING,
)
from app.org_scope import org_get, org_query
from app.permissions import donations_write_required
from app.whatsapp import donation_whatsapp_url
from app.year_scope import (
    filter_donations_by_year,
    filter_pledges_by_year,
    get_current_festival_year,
)

donations_bp = Blueprint("donations", __name__)


def _current_festival_year():
    return get_current_festival_year(current_user.organization)


def _donations_for_current_year():
    return filter_donations_by_year(org_query(Donation), _current_festival_year())


def _pledges_for_current_year():
    return filter_pledges_by_year(org_query(Pledge), _current_festival_year())


def _donation_totals():
    committee = (
        _donations_for_current_year()
        .filter(Donation.donor_group == DONOR_GROUP_COMMITTEE)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )
    other = (
        _donations_for_current_year()
        .filter(Donation.donor_group == DONOR_GROUP_OTHER)
        .with_entities(func.coalesce(func.sum(Donation.amount), 0))
        .scalar()
    )
    return committee, other


def _prepare_donation_form(form):
    form.donor_group.choices = DONOR_GROUP_CHOICES
    form.payment_mode.choices = PAYMENT_MODE_CHOICES


def _normalize_phone(phone_value):
    if not phone_value:
        return None
    stripped = phone_value.strip()
    return stripped if stripped else None


def _escape_like_pattern(value):
    return (
        value.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _save_donation_from_form(form, recorded_by_id, organization_id, festival_year):
    donation = Donation(
        organization_id=organization_id,
        donor_name=form.donor_name.data.strip(),
        donor_group=form.donor_group.data,
        payment_mode=form.payment_mode.data,
        upi_transaction_id=(
            form.upi_transaction_id.data.strip()
            if form.payment_mode.data == "upi" and form.upi_transaction_id.data
            else None
        ),
        amount=form.amount.data,
        phone=_normalize_phone(form.phone.data),
        notes=form.notes.data.strip() if form.notes.data else None,
        donation_date=form.donation_date.data,
        festival_year=festival_year,
        recorded_by_id=recorded_by_id,
    )
    db.session.add(donation)
    return donation


@donations_bp.route("/api/donor-suggestions")
@login_required
def donor_suggestions():
    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify(results=[])

    pattern = f"%{_escape_like_pattern(query)}%"
    names = set()
    for row in (
        _donations_for_current_year()
        .filter(Donation.donor_name.ilike(pattern, escape="\\"))
        .with_entities(Donation.donor_name)
        .distinct()
        .limit(20)
    ):
        names.add(row[0])
    for row in (
        _pledges_for_current_year()
        .filter(Pledge.donor_name.ilike(pattern, escape="\\"))
        .with_entities(Pledge.donor_name)
        .distinct()
        .limit(20)
    ):
        names.add(row[0])

    results = sorted(names, key=str.lower)[:10]
    return jsonify(results=results)


@donations_bp.route("/")
@login_required
def list_donations():
    group_filter = request.args.get("group", "all")
    search_q = (request.args.get("q") or "").strip()
    query = _donations_for_current_year()
    if group_filter in (DONOR_GROUP_COMMITTEE, DONOR_GROUP_OTHER):
        query = query.filter_by(donor_group=group_filter)
    if search_q:
        query = query.filter(Donation.donor_name.ilike(f"%{search_q}%"))

    donations = query.order_by(
        Donation.donation_date.desc(), Donation.id.desc()
    ).all()
    committee_total, other_total = _donation_totals()
    pending_pledge_count = (
        _pledges_for_current_year().filter_by(status=PLEDGE_STATUS_PENDING).count()
    )
    festival_year = _current_festival_year()

    return render_template(
        "donations/list.html",
        donations=donations,
        group_filter=group_filter,
        search_q=search_q,
        committee_total=committee_total,
        other_total=other_total,
        active_tab="received",
        pending_pledge_count=pending_pledge_count,
        festival_year=festival_year,
    )


@donations_bp.route("/add", methods=["GET", "POST"])
@donations_write_required
def add_donation():
    form = DonationForm()
    _prepare_donation_form(form)

    if request.method == "GET":
        form.donation_date.data = date.today()
        form.donor_group.data = DONOR_GROUP_COMMITTEE
        form.payment_mode.data = PAYMENT_CASH

    if form.validate_on_submit():
        donation = _save_donation_from_form(
            form,
            current_user.id,
            current_user.organization_id,
            _current_festival_year(),
        )
        db.session.flush()
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


@donations_bp.route("/<int:donation_id>/saved")
@donations_write_required
def donation_saved(donation_id):
    donation = org_get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("donations.list_donations"))

    whatsapp_url = donation_whatsapp_url(donation)

    return render_template(
        "donations/saved.html",
        donation=donation,
        whatsapp_url=whatsapp_url,
    )


@donations_bp.route("/<int:donation_id>/edit", methods=["GET", "POST"])
@donations_write_required
def edit_donation(donation_id):
    donation = org_get(Donation, donation_id)
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
        donation.phone = _normalize_phone(form.phone.data)
        donation.notes = form.notes.data.strip() if form.notes.data else None
        donation.donation_date = form.donation_date.data
        donation.festival_year = _current_festival_year()
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
@donations_write_required
def send_whatsapp(donation_id):
    donation = org_get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
        return redirect(url_for("donations.list_donations"))

    if not donation.phone:
        flash("No phone number on file for this donor.", "warning")
        return redirect(url_for("donations.edit_donation", donation_id=donation.id))

    whatsapp_url = donation_whatsapp_url(donation)
    if not whatsapp_url:
        flash("Invalid phone number for WhatsApp.", "warning")
        return redirect(url_for("donations.edit_donation", donation_id=donation.id))

    return redirect(whatsapp_url)


def _remove_donation(donation):
    Pledge.query.filter_by(donation_id=donation.id).update(
        {"donation_id": None},
        synchronize_session=False,
    )
    donor_name = donation.donor_name
    amount = donation.amount
    deleted_id = donation.id
    db.session.delete(donation)
    log_activity(
        current_user,
        "deleted",
        "donation",
        f"Deleted donation of ₹{amount:,.2f} from {donor_name}",
        deleted_id,
    )


def _donations_list_redirect():
    group = (request.form.get("group") or "").strip()
    search_q = (request.form.get("q") or "").strip()
    return redirect(
        url_for(
            "donations.list_donations",
            group=group if group and group != "all" else None,
            q=search_q or None,
        )
    )


@donations_bp.route("/bulk-delete", methods=["POST"])
@donations_write_required
def bulk_delete_donations():
    donation_ids = []
    for raw in request.form.getlist("donation_ids"):
        try:
            donation_ids.append(int(raw))
        except (TypeError, ValueError):
            continue

    if not donation_ids:
        flash("Select at least one donation to delete.", "warning")
        return _donations_list_redirect()

    deleted = 0
    for donation_id in donation_ids:
        donation = org_get(Donation, donation_id)
        if not donation:
            continue
        _remove_donation(donation)
        deleted += 1

    if deleted:
        db.session.commit()
        flash(f"Deleted {deleted} donation(s).", "success")
    else:
        flash("No donations were deleted.", "warning")
    return _donations_list_redirect()


@donations_bp.route("/<int:donation_id>/delete", methods=["POST"])
@donations_write_required
def delete_donation(donation_id):
    donation = org_get(Donation, donation_id)
    if not donation:
        flash("Donation not found.", "danger")
    else:
        _remove_donation(donation)
        db.session.commit()
        flash("Donation deleted.", "info")
    return redirect(url_for("donations.list_donations"))
