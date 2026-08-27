from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.forms import LoginForm, RegisterForm
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            if not user.is_approved:
                flash(
                    "Your account is waiting for admin approval. Please contact an admin.",
                    "warning",
                )
                return render_template("auth/login.html", form=form)
            login_user(user)
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.full_name}!", "success")
            return redirect(next_page or url_for("main.dashboard"))
        flash("Invalid username or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.is_approved:
            return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.pending"))

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip().lower()
        if User.query.filter_by(username=username).first():
            flash("Username already taken. Please choose another.", "warning")
            return render_template("auth/register.html", form=form)

        is_first_user = User.query.count() == 0
        user = User(
            username=username,
            full_name=form.full_name.data.strip(),
            is_admin=is_first_user,
            can_write=is_first_user,
            is_approved=is_first_user,
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        if is_first_user:
            flash("Account created! You are the first user and have been set as admin.", "success")
            return redirect(url_for("auth.login"))
        flash(
            "Registration submitted. An admin must approve your account before you can log in.",
            "info",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
