from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    FloatField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional


class LoginForm(FlaskForm):
    committee_code = StringField(
        "Committee Code",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    login_submit = SubmitField("Login")


class JoinRegisterForm(FlaskForm):
    committee_code = StringField(
        "Committee Code",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    join_submit = SubmitField("Submit Join Request")


class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create Account")


class JoinCommitteeForm(FlaskForm):
    committee_code = StringField(
        "Committee Code",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    submit = SubmitField("Continue to Register")


class StartCommitteeForm(FlaskForm):
    name = StringField("Committee Name", validators=[DataRequired(), Length(max=160)])
    slug = StringField(
        "Committee Code",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    village = StringField("Village / Area", validators=[DataRequired(), Length(max=120)])
    festival_name = StringField("Festival Display Name", validators=[DataRequired(), Length(max=160)])
    festival_year = IntegerField("Festival Year", validators=[Optional()])
    full_name = StringField("Your Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Choose Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    start_submit = SubmitField("Register Committee")


class CreateOrganizationForm(FlaskForm):
    name = StringField("Committee Name", validators=[DataRequired(), Length(max=160)])
    slug = StringField(
        "Committee Code (URL slug)",
        validators=[DataRequired(), Length(min=3, max=80)],
    )
    village = StringField("Village / Area", validators=[Optional(), Length(max=120)])
    festival_name = StringField("Festival Display Name", validators=[DataRequired(), Length(max=160)])
    festival_year = IntegerField("Festival Year", validators=[Optional()])
    submit = SubmitField("Create Committee")


class DonationForm(FlaskForm):
    donor_name = StringField("Donor Name", validators=[DataRequired(), Length(max=120)])
    donor_group = SelectField("Donation From", validators=[DataRequired()])
    amount = FloatField(
        "Amount (₹)", validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be greater than 0.")]
    )
    payment_mode = SelectField("Payment Mode", validators=[DataRequired()])
    upi_transaction_id = StringField(
        "UPI Transaction ID (optional)", validators=[Optional(), Length(max=100)]
    )
    phone = StringField(
        "Phone", validators=[DataRequired(), Length(min=10, max=20, message="Enter a valid mobile number.")]
    )
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
