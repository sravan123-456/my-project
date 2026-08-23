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
from app.permissions import write_required

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


@expenses_bp.route("/")
@login_required
def list_expenses():
    expenses = Expense.query.order_by(
        Expense.expense_date.desc(), Expense.id.desc()
    ).all()
    return render_template("expenses/list.html", expenses=expenses)


@expenses_bp.route("/add", methods=["GET", "POST"])
@write_required
def add_expense():
    form = ExpenseForm()
    form.category.choices = [(c, c) for c in EXPENSE_CATEGORIES]
    form.expense_date.data = date.today()

    if form.validate_on_submit():
        bill_filename = save_bill(request.files.get("bill"))
        expense = Expense(
            title=form.title.data.strip(),
            category=form.category.data,
            amount=form.amount.data,
            description=form.description.data.strip() if form.description.data else None,
            expense_date=form.expense_date.data,
            bill_filename=bill_filename,
            recorded_by_id=current_user.id,
        )
        db.session.add(expense)
        db.session.flush()
        log_activity(
            current_user,
            "added",
            "expense",
            f"Added expense '{expense.title}' of ₹{expense.amount:,.2f} ({expense.category})",
            expense.id,
        )
        db.session.commit()
        flash(f"Expense of ₹{expense.amount:,.2f} for {expense.title} recorded.", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/form.html", form=form, title="Add Expense")


@expenses_bp.route("/<int:expense_id>/edit", methods=["GET", "POST"])
@write_required
def edit_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found.", "danger")
        return redirect(url_for("expenses.list_expenses"))

    form = ExpenseForm(obj=expense)
    form.category.choices = [(c, c) for c in EXPENSE_CATEGORIES]

    if form.validate_on_submit():
        expense.title = form.title.data.strip()
        expense.category = form.category.data
        expense.amount = form.amount.data
        expense.description = form.description.data.strip() if form.description.data else None
        expense.expense_date = form.expense_date.data

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
            f"Updated expense '{expense.title}' to ₹{expense.amount:,.2f} ({expense.category})",
            expense.id,
        )
        db.session.commit()
        flash("Expense updated successfully.", "success")
        return redirect(url_for("expenses.list_expenses"))

    return render_template("expenses/form.html", form=form, title="Edit Expense", expense=expense)


@expenses_bp.route("/<int:expense_id>/delete", methods=["POST"])
@write_required
def delete_expense(expense_id):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        flash("Expense not found.", "danger")
    else:
        title = expense.title
        amount = expense.amount
        expense_id = expense.id
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
            expense_id,
        )
        db.session.commit()
        flash("Expense deleted.", "info")
    return redirect(url_for("expenses.list_expenses"))


@expenses_bp.route("/bill/<filename>")
@login_required
def view_bill(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
