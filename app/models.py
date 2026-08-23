from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

FESTIVAL_NAME = "Indukuru Vinayaka Festival"
DEVELOPER_NAME = "Sravan Kumar Reddy"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    can_write = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    donations = db.relationship("Donation", backref="recorded_by", lazy=True)
    expenses = db.relationship("Expense", backref="recorded_by", lazy=True)
    activities = db.relationship("ActivityLog", backref="user", lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def can_edit(self):
        return self.is_admin or self.can_write

    def access_label(self):
        if self.is_admin:
            return "Admin"
        if self.can_write:
            return "Write Access"
        return "Read Only"


DONOR_GROUP_YOUTH = "youth"
DONOR_GROUP_VILLAGE = "village"

DONOR_GROUP_CHOICES = [
    (DONOR_GROUP_YOUTH, "Youth (Our Team)"),
    (DONOR_GROUP_VILLAGE, "Village Member"),
]

DONOR_GROUP_LABELS = dict(DONOR_GROUP_CHOICES)


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    donor_name = db.Column(db.String(120), nullable=False)
    donor_group = db.Column(db.String(20), nullable=False, default=DONOR_GROUP_VILLAGE)
    amount = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    donation_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def donor_group_label(self):
        return DONOR_GROUP_LABELS.get(self.donor_group, self.donor_group)


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General")
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    bill_filename = db.Column(db.String(255))
    expense_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)


class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_name = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)
    entity_id = db.Column(db.Integer)
    description = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


EXPENSE_CATEGORIES = [
    "Decoration",
    "Flowers & Garlands",
    "Prasad & Food",
    "Priest & Rituals",
    "Sound & Lighting",
    "Rent & Permissions",
    "Transport",
    "Volunteer Expenses",
    "Miscellaneous",
]
