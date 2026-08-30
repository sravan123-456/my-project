from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app import db

PLATFORM_NAME = "Festival Fund Manager"
FESTIVAL_NAME = "Indukuru Vinayaka Festival"
DEVELOPER_NAME = "Sravan Kumar Reddy"

ORG_STATUS_ACTIVE = "active"
ORG_STATUS_SUSPENDED = "suspended"
ORG_STATUS_PENDING = "pending"


class Organization(db.Model):
    __tablename__ = "organizations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    village = db.Column(db.String(120))
    district = db.Column(db.String(120))
    festival_name = db.Column(db.String(160), nullable=False)
    festival_year = db.Column(db.Integer)
    status = db.Column(db.String(20), nullable=False, default=ORG_STATUS_ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship("User", backref="organization", lazy=True)
    donations = db.relationship("Donation", backref="organization", lazy=True)
    expenses = db.relationship("Expense", backref="organization", lazy=True)

    def is_active(self):
        return self.status == ORG_STATUS_ACTIVE

    def is_pending(self):
        return self.status == ORG_STATUS_PENDING

    def status_label(self):
        if self.is_active():
            return "Active"
        if self.is_pending():
            return "Pending Approval"
        return "Suspended"

    def display_name(self):
        return self.festival_name or self.name


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    is_site_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    can_write = db.Column(db.Boolean, default=False, nullable=False)
    is_approved = db.Column(db.Boolean, default=False, nullable=False)
    login_count = db.Column(db.Integer, default=0, nullable=False)
    last_login_at = db.Column(db.DateTime)
    profile_photo_key = db.Column(db.String(512))
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
        if self.is_site_admin:
            return "Site Admin"
        if self.is_admin:
            return "Committee Admin"
        if self.can_write:
            return "Write Access"
        return "Read Only"

    def is_org_admin(self):
        return self.is_admin and not self.is_site_admin

    def avatar_initials(self):
        parts = [part for part in (self.full_name or "").split() if part]
        if not parts:
            return "?"
        if len(parts) == 1:
            return parts[0][:2].upper()
        return f"{parts[0][0]}{parts[-1][0]}".upper()

    def has_profile_photo(self):
        return bool(self.profile_photo_key)


DONOR_GROUP_COMMITTEE = "committee_member"
DONOR_GROUP_OTHER = "other"

DONOR_GROUP_CHOICES = [
    (DONOR_GROUP_COMMITTEE, "Committee Member"),
    (DONOR_GROUP_OTHER, "Other"),
]

DONOR_GROUP_LABELS = dict(DONOR_GROUP_CHOICES)

LEGACY_DONOR_GROUP_LABELS = {
    "youth": "Committee Member",
    "village": "Other",
}

PAYMENT_CASH = "cash"
PAYMENT_UPI = "upi"

PAYMENT_MODE_CHOICES = [
    (PAYMENT_CASH, "Cash"),
    (PAYMENT_UPI, "UPI"),
]

PAYMENT_MODE_LABELS = dict(PAYMENT_MODE_CHOICES)


class Donation(db.Model):
    __tablename__ = "donations"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False, index=True)
    donor_name = db.Column(db.String(120), nullable=False)
    donor_group = db.Column(db.String(20), nullable=False, default=DONOR_GROUP_COMMITTEE)
    payment_mode = db.Column(db.String(20), nullable=False, default=PAYMENT_CASH)
    upi_transaction_id = db.Column(db.String(100))
    amount = db.Column(db.Float, nullable=False)
    phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    donation_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    def donor_group_label(self):
        return LEGACY_DONOR_GROUP_LABELS.get(
            self.donor_group,
            DONOR_GROUP_LABELS.get(self.donor_group, self.donor_group),
        )

    def payment_mode_label(self):
        return PAYMENT_MODE_LABELS.get(self.payment_mode, self.payment_mode)


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False, index=True)
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
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user_name = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(20), nullable=False)
    entity_type = db.Column(db.String(20), nullable=False)
    entity_id = db.Column(db.Integer)
    description = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class LoginEvent(db.Model):
    __tablename__ = "login_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), index=True)
    username_attempt = db.Column(db.String(80))
    success = db.Column(db.Boolean, nullable=False, default=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", backref="login_events", lazy=True)
    organization = db.relationship("Organization", backref="login_events", lazy=True)


class PasswordResetRequest(db.Model):
    __tablename__ = "password_reset_requests"

    STATUS_PENDING = "pending"
    STATUS_RESOLVED = "resolved"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    user = db.relationship("User", foreign_keys=[user_id], backref="password_reset_requests", lazy=True)
    resolved_by = db.relationship("User", foreign_keys=[resolved_by_id], lazy=True)
    organization = db.relationship("Organization", backref="password_reset_requests", lazy=True)


class GalleryImage(db.Model):
    __tablename__ = "gallery_images"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("organizations.id"), nullable=False, index=True)
    storage_key = db.Column(db.String(512), nullable=False)
    title = db.Column(db.String(200))
    caption = db.Column(db.Text)
    festival_year = db.Column(db.Integer)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    uploaded_by = db.relationship("User", backref="gallery_uploads", lazy=True)
    organization = db.relationship("Organization", backref="gallery_images", lazy=True)


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
