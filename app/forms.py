from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    FloatField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")


class DonationForm(FlaskForm):
    donor_name = StringField("Donor Name", validators=[DataRequired(), Length(max=120)])
    donor_group = SelectField("Donation From", validators=[DataRequired()])
    amount = FloatField(
        "Amount (₹)", validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0.")]
    )
    phone = StringField("Phone (optional)", validators=[Optional(), Length(max=20)])
    notes = TextAreaField("Notes (optional)", validators=[Optional(), Length(max=500)])
    donation_date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    submit = SubmitField("Save Donation")


class ExpenseForm(FlaskForm):
    title = StringField("Expense Title", validators=[DataRequired(), Length(max=200)])
    category = SelectField("Category", validators=[DataRequired()])
    amount = FloatField(
        "Amount (₹)", validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0.")]
    )
    description = TextAreaField("Description (optional)", validators=[Optional(), Length(max=500)])
    expense_date = DateField("Date", validators=[DataRequired()], format="%Y-%m-%d")
    submit = SubmitField("Save Expense")
