from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from app import db, utcnow
from app.activity import log_activity
from app.forms import CollectPledgeForm, PledgeForm
from app.models import (
    DONOR_GROUP_CHOICES,
    DONOR_GROUP_COMMITTEE,
    DONOR_GROUP_OTHER,
    PAYMENT_CASH,
    PAYMENT_MODE_CHOICES,
    PLEDGE_STATUS_CANCELLED,
    PLEDGE_STATUS_COLLECTED,
    PLEDGE_STATUS_PENDING,
    Donation,
    Pledge,
)
from app.org_scope import org_get, org_query
from app.permissions import write_required
from app.routes.donations import _normalize_phone

pledges_bp = Blueprint("pledges", __name__)


def _prepare_pledge_form(form):
    form.donor_group.choices = DONOR_GROUP_CHOICES


def _pledge_totals():
    pending_total = (
        org_query(Pledge)
        .filter(Pledge.status == PLEDGE_STATUS_PENDING)
        .with_entities(func.coalesce(func.sum(Pledge.promised_amount), 0))
        .scalar()
    )
    overdue_total = (
        org_query(Pledge)
        .filter(Pledge.status == PLEDGE_STATUS_PENDING)
        .all()
    )
    overdue_amount = sum(p.promised_amount for p in overdue_total if p.is_overdue())
    overdue_count = sum(1 for p in overdue_total if p.is_overdue())
    pending_count = org_query(Pledge).filter(Pledge.status == PLEDGE_STATUS_PENDING).count()
    return pending_total, pending_count, overdue_amount, overdue_count


@pledges_bp.route("/")
@login_required
def list_pledges():
    status_filter = request.args.get("status", PLEDGE_STATUS_PENDING)
    group_filter = request.args.get("group", "all")
    search_q = (request.args.get("q") or "").strip()

    query = org_query(Pledge)
    if status_filter in (PLEDGE_STATUS_PENDING, PLEDGE_STATUS_COLLECTED, PLEDGE_STATUS_CANCELLED):
        query = query.filter_by(status=status_filter)

    if group_filter in (DONOR_GROUP_COMMITTEE, DONOR_GROUP_OTHER):
        query = query.filter_by(donor_group=group_filter)

    if search_q:
        query = query.filter(Pledge.donor_name.ilike(f"%{search_q}%"))

    pledges = query.order_by(
        Pledge.promised_date.asc(), Pledge.id.desc()
    ).all()

    if status_filter == PLEDGE_STATUS_PENDING:
        pledges = sorted(pledges, key=lambda p: (not p.is_overdue(), p.reminder_date(), p.id))

    pending_total, pending_count, overdue_amount, overdue_count = _pledge_totals()

    return render_template(
        "donations/pledges_list.html",
        pledges=pledges,
        status_filter=status_filter,
        group_filter=group_filter,
        search_q=search_q,
        pending_total=pending_total,
        pending_count=pending_count,
        overdue_amount=overdue_amount,
        overdue_count=overdue_count,
        active_tab="pledges",
        pending_pledge_count=pending_count,
    )


@pledges_bp.route("/add", methods=["GET", "POST"])
@write_required
def add_pledge():
    form = PledgeForm()
    _prepare_pledge_form(form)

    if request.method == "GET":
        form.promised_date.data = date.today()
        form.donor_group.data = DONOR_GROUP_COMMITTEE

    if form.validate_on_submit():
        pledge = Pledge(
            organization_id=current_user.organization_id,
            donor_name=form.donor_name.data.strip(),
            donor_group=form.donor_group.data,
            promised_amount=form.promised_amount.data,
            phone=_normalize_phone(form.phone.data),
            promised_date=form.promised_date.data,
            follow_up_date=form.follow_up_date.data,
            notes=form.notes.data.strip() if form.notes.data else None,
            status=PLEDGE_STATUS_PENDING,
            recorded_by_id=current_user.id,
        )
        db.session.add(pledge)
        db.session.flush()
        log_activity(
            current_user,
            "added",
            "pledge",
            f"Recorded pledge of ₹{pledge.promised_amount:,.2f} from {pledge.donor_name}",
            pledge.id,
        )
        db.session.commit()
        flash(
            f"Pledge of ₹{pledge.promised_amount:,.2f} from {pledge.donor_name} recorded.",
            "success",
        )
        return redirect(url_for("pledges.list_pledges"))

    return render_template("donations/pledge_form.html", form=form, title_key="pledges.add")


@pledges_bp.route("/<int:pledge_id>/edit", methods=["GET", "POST"])
@write_required
def edit_pledge(pledge_id):
    pledge = org_get(Pledge, pledge_id)
    if not pledge:
        flash("Pledge not found.", "danger")
        return redirect(url_for("pledges.list_pledges"))

    if pledge.status != PLEDGE_STATUS_PENDING:
        flash("Only pending pledges can be edited.", "warning")
        return redirect(url_for("pledges.list_pledges"))

    form = PledgeForm(obj=pledge)
    _prepare_pledge_form(form)

    if form.validate_on_submit():
        pledge.donor_name = form.donor_name.data.strip()
        pledge.donor_group = form.donor_group.data
        pledge.promised_amount = form.promised_amount.data
        pledge.phone = _normalize_phone(form.phone.data)
        pledge.promised_date = form.promised_date.data
        pledge.follow_up_date = form.follow_up_date.data
        pledge.notes = form.notes.data.strip() if form.notes.data else None
        log_activity(
            current_user,
            "updated",
            "pledge",
            f"Updated pledge from {pledge.donor_name} to ₹{pledge.promised_amount:,.2f}",
            pledge.id,
        )
        db.session.commit()
        flash("Pledge updated successfully.", "success")
        return redirect(url_for("pledges.list_pledges"))

    return render_template(
        "donations/pledge_form.html",
        form=form,
        title_key="pledges.edit",
        pledge=pledge,
    )


@pledges_bp.route("/<int:pledge_id>/collect", methods=["GET", "POST"])
@write_required
def collect_pledge(pledge_id):
    pledge = org_get(Pledge, pledge_id)
    if not pledge:
        flash("Pledge not found.", "danger")
        return redirect(url_for("pledges.list_pledges"))

    if pledge.status != PLEDGE_STATUS_PENDING:
        flash("This pledge has already been collected or cancelled.", "warning")
        return redirect(url_for("pledges.list_pledges"))

    form = CollectPledgeForm()
    form.payment_mode.choices = PAYMENT_MODE_CHOICES

    if request.method == "GET":
        form.amount.data = pledge.promised_amount
        form.donation_date.data = date.today()
        form.payment_mode.data = PAYMENT_CASH
        form.phone.data = pledge.phone or ""

    if form.validate_on_submit():
        donation = Donation(
            organization_id=current_user.organization_id,
            donor_name=pledge.donor_name,
            donor_group=pledge.donor_group,
            payment_mode=form.payment_mode.data,
            upi_transaction_id=(
                form.upi_transaction_id.data.strip()
                if form.payment_mode.data == "upi" and form.upi_transaction_id.data
                else None
            ),
            amount=form.amount.data,
            phone=_normalize_phone(form.phone.data) or pledge.phone,
            notes=form.notes.data.strip() if form.notes.data else pledge.notes,
            donation_date=form.donation_date.data,
            recorded_by_id=current_user.id,
        )
        db.session.add(donation)
        db.session.flush()

        pledge.status = PLEDGE_STATUS_COLLECTED
        pledge.donation_id = donation.id
        pledge.collected_at = utcnow()

        log_activity(
            current_user,
            "collected",
            "pledge",
            f"Collected ₹{donation.amount:,.2f} from {pledge.donor_name} (pledge fulfilled)",
            pledge.id,
        )
        log_activity(
            current_user,
            "added",
            "donation",
            f"Added {donation.donor_group_label()} {donation.payment_mode_label()} donation "
            f"of ₹{donation.amount:,.2f} from {donation.donor_name} (from pledge)",
            donation.id,
        )
        db.session.commit()
        flash(
            f"Collected ₹{donation.amount:,.2f} from {pledge.donor_name}. Donation recorded.",
            "success",
        )
        return redirect(url_for("donations.donation_saved", donation_id=donation.id))

    return render_template(
        "donations/collect_pledge.html",
        form=form,
        pledge=pledge,
    )


@pledges_bp.route("/<int:pledge_id>/cancel", methods=["POST"])
@write_required
def cancel_pledge(pledge_id):
    pledge = org_get(Pledge, pledge_id)
    if not pledge:
        flash("Pledge not found.", "danger")
    elif pledge.status != PLEDGE_STATUS_PENDING:
        flash("Only pending pledges can be cancelled.", "warning")
    else:
        donor_name = pledge.donor_name
        amount = pledge.promised_amount
        cancelled_id = pledge.id
        pledge.status = PLEDGE_STATUS_CANCELLED
        log_activity(
            current_user,
            "cancelled",
            "pledge",
            f"Cancelled pledge of ₹{amount:,.2f} from {donor_name}",
            cancelled_id,
        )
        db.session.commit()
        flash(f"Pledge from {donor_name} cancelled.", "info")
    return redirect(url_for("pledges.list_pledges", status=request.args.get("status", PLEDGE_STATUS_PENDING)))
