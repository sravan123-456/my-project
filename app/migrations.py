import os

from sqlalchemy import inspect, text

from app import db
from app.models import (
    FESTIVAL_NAME,
    ActivityLog,
    Donation,
    Expense,
    Organization,
    User,
)


def migrate_user_roles():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    statements = []
    added_approval = False
    if "is_admin" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
    if "can_write" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN can_write BOOLEAN NOT NULL DEFAULT 0")
    if "is_approved" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_approved BOOLEAN NOT NULL DEFAULT 0")
        added_approval = True
    if "is_site_admin" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_site_admin BOOLEAN NOT NULL DEFAULT 0")
    if "organization_id" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN organization_id INTEGER")
    if "login_count" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN login_count INTEGER NOT NULL DEFAULT 0")
    if "last_login_at" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN last_login_at DATETIME")

    if statements:
        with db.engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))

    if added_approval and User.query.count() > 0:
        User.query.update({"is_approved": True})
        db.session.commit()

    if User.query.filter_by(is_admin=True).count() == 0:
        first_user = User.query.order_by(User.id.asc()).first()
        if first_user:
            first_user.is_admin = True
            first_user.can_write = True
            first_user.is_approved = True
            db.session.commit()


def migrate_donation_groups():
    inspector = inspect(db.engine)
    if "donations" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("donations")}
    if "donor_group" not in columns:
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE donations ADD COLUMN donor_group VARCHAR(20) NOT NULL DEFAULT 'village'"
                )
            )


def migrate_donation_payments():
    inspector = inspect(db.engine)
    if "donations" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("donations")}
    statements = []
    if "payment_mode" not in columns:
        statements.append(
            "ALTER TABLE donations ADD COLUMN payment_mode VARCHAR(20) NOT NULL DEFAULT 'cash'"
        )
    if "upi_transaction_id" not in columns:
        statements.append("ALTER TABLE donations ADD COLUMN upi_transaction_id VARCHAR(100)")

    if statements:
        with db.engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))


def migrate_organizations():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "organizations" not in tables:
        db.create_all()

    for table, column in (
        ("donations", "organization_id"),
        ("expenses", "organization_id"),
        ("activity_logs", "organization_id"),
    ):
        if table not in inspector.get_table_names():
            continue
        columns = {col["name"] for col in inspector.get_columns(table)}
        if column not in columns:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} INTEGER"))

    if "login_events" not in tables:
        db.create_all()

    default_org = Organization.query.filter_by(slug="indukuru").first()
    if not default_org:
        default_org = Organization(
            name="Indukuru Vinayaka Committee",
            slug="indukuru",
            village="Indukuru",
            festival_name=FESTIVAL_NAME,
            festival_year=2026,
            status="active",
        )
        db.session.add(default_org)
        db.session.flush()

    org_id = default_org.id

    User.query.filter(User.organization_id.is_(None)).update(
        {User.organization_id: org_id}, synchronize_session=False
    )
    Donation.query.filter(Donation.organization_id.is_(None)).update(
        {Donation.organization_id: org_id}, synchronize_session=False
    )
    Expense.query.filter(Expense.organization_id.is_(None)).update(
        {Expense.organization_id: org_id}, synchronize_session=False
    )

    for activity in ActivityLog.query.filter(ActivityLog.organization_id.is_(None)).all():
        user = db.session.get(User, activity.user_id)
        activity.organization_id = user.organization_id if user else org_id

    site_admin_usernames = os.getenv("SITE_ADMIN_USERNAMES", "").strip()
    if site_admin_usernames:
        for username in site_admin_usernames.split(","):
            username = username.strip().lower()
            if not username:
                continue
            user = User.query.filter_by(username=username).first()
            if user:
                user.is_site_admin = True
    elif User.query.filter_by(is_site_admin=True).count() == 0:
        for admin in User.query.filter_by(is_admin=True).all():
            admin.is_site_admin = True

    db.session.commit()


def run_migrations():
    migrate_user_roles()
    migrate_donation_groups()
    migrate_donation_payments()
    migrate_organizations()
