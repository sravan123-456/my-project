import os
import uuid
from datetime import date

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.activity import log_activity
from app.forms import ExpenseForm
from app.models import EXPENSE_CATEGORIES, Expense
from app.org_scope import org_get, org_query
from app.permissions import expenses_write_required
from app.plan_enforcement import can_add_expense
from app.year_scope import filter_expenses_by_year, get_current_festival_year

expenses_bp = Blueprint("expenses", __name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_bill(file):
    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        flash("Invalid file type. Allowed: PNG, JPG, GIF, WEBP, PDF.", "warning")
        return None

    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
    file.save(filepath)
    return unique_name


def _current_festival_year():
    return get_current_festival_year(current_user.organization)


def _expenses_for_current_year():
    return filter_expenses_by_year(org_query(Expense), _current_festival_year())


@expenses_bp.route("/")
@login_required
def list_expenses():
    expenses = (
        _expenses_for_current_year()
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
        .all()
    )
    return render_template(
        "expenses/list.html",
        expenses=expenses,
        festival_year=_current_festival_year(),
    )


@expenses_bp.route("/add", methods=["GET", "POST"])
@expenses_write_required
def add_expense():
    form = ExpenseForm()
    form.category.choices = [(c, c) for c in EXPENSE_CATEGORIES]
    form.expense_date.data = date.today()

    if form.validate_on_submit():
        ok, limit_message = can_add_expense(current_user.organization)
        if not ok:
            flash(limit_message, "warning")
            return render_template("expenses/form.html", form=form, title="Add Expense")

        bill_filename = save_bill(request.files.get("bill"))
        expense = Expense(
            organization_id=current_user.organization_id,
            title=form.title.data.strip(),
            category=form.category.data,
            total_amount=form.total_amount.data,
            advance_amount=form.advance_amount.data or 0,
            balance_amount=form.balance_amount.data or 0,
            description=form.description.data.strip() if form.description.data else None,
            expense_date=form.expense_date.data,
            festival_year=_current_festival_year(),
            bill_filename=bill_filename,
            recorded_by_id=current_user.id,
            amount=0,
        )
        expense.sync_amount()
        db.session.add(expense)
        db.session.flush()
        log_activity(
            current_user,
            "added",
            "expense",
            f"Added expense '{expense.title}' — paid ₹{expense.paid_amount():,.2f} of ₹{expense.total_cost():,.2f} ({expense.category})",
            expense.id,
        )
        db.session.commit()
        flash(
            f"Expense recorded — paid ₹{expense.paid_amount():,.2f} of ₹{expense.total_cost():,.2f} for {expense.title}.",
            "success",
        )
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/form.html", form=form, title="Add Expense")


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@expenses_write_required
def edit_expense(expense_id):
    expense = org_get(Expense, expense_id)
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("expenses.list_expenses"))

    form = ExpenseForm(obj=expense)
    form.category.choices = [(c, c) for c in EXPENSE_CATEGORIES]

    if request.method == "GET":
        form.total_amount.data = expense.total_cost()
        form.advance_amount.data = expense.advance_amount or 0
        form.balance_amount.data = expense.balance_amount or 0
        if not form.advance_amount.data and not form.balance_amount.data and expense.amount:
            form.balance_amount.data = expense.amount

    if form.validate_on_submit():
        expense.title = form.title.data.strip()
        expense.category = form.category.data
        expense.total_amount = form.total_amount.data
        expense.advance_amount = form.advance_amount.data or 0
        expense.balance_amount = form.balance_amount.data or 0
        expense.sync_amount()
        expense.description = form.description.data.strip() if form.description.data else None
        expense.expense_date = form.expense_date.data
        expense.festival_year = _current_festival_year()

        new_bill = save_bill(request.files.get("bill"))
        if new_bill:
            if expense.bill_filename:
                old_path = os.path.join(current_app.config["UPLOAD_FOLDER"], expense.bill_filename)
                if os.path.exists(old_path):
                    os.remove(old_path)
            expense.bill_filename = new_bill

        log_activity(
            current_user,
            "updated",
            "expense",
            f"Updated expense '{expense.title}' — paid ₹{expense.paid_amount():,.2f} of ₹{expense.total_cost():,.2f} ({expense.category})",
            expense.id,
        )
        db.session.commit()
        flash("Expense updated successfully.", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/form.html", form=form, title="Edit Expense", expense=expense)


def _remove_expense(expense):
    title = expense.title
    amount = expense.amount
    deleted_id = expense.id
    if expense.bill_filename:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], expense.bill_filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    db.session.delete(expense)
    log_activity(
        current_user,
        "deleted",
        "expense",
        f"Deleted expense '{title}' of ₹{amount:,.2f}",
        deleted_id,
    )


@expenses_bp.route("/bulk-delete", methods=["POST"])
@expenses_write_required
def bulk_delete_expenses():
    expense_ids = []
    for raw in request.form.getlist("expense_ids"):
        try:
            expense_ids.append(int(raw))
        except (TypeError, ValueError):
            continue

    if not expense_ids:
        flash("Select at least one expense to delete.", "warning")
        return redirect(url_for("expenses.list_expenses"))

    deleted = 0
    for expense_id in expense_ids:
        expense = org_get(Expense, expense_id)
        if not expense:
            continue
        _remove_expense(expense)
        deleted += 1

    if deleted:
        db.session.commit()
        flash(f"Deleted {deleted} expense(s).", "success")
    else:
        flash("No expenses were deleted.", "warning")
    return redirect(url_for("expenses.list_expenses"))


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@expenses_write_required
def delete_expense(expense_id):
    expense = org_get(Expense, expense_id)
    if not expense:
        flash("Expense not found.", "danger")
    else:
        _remove_expense(expense)
        db.session.commit()
        flash("Expense deleted.", "info")
    return redirect(url_for("expenses.list_expenses"))


@expenses_bp.route("/bill/<filename>")
@login_required
def view_bill(filename):
    expense = org_query(Expense).filter_by(bill_filename=filename).first()
    if not expense:
        flash("Bill not found.", "danger")
        return redirect(url_for("expenses.list_expenses"))
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
