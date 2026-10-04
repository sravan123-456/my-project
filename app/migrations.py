import os

from sqlalchemy import inspect, text

from app import db
from app.models import (
    FESTIVAL_NAME,
    ActivityLog,
    Donation,
    Expense,
    Organization,
    Pledge,
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
    if "can_write_donations" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN can_write_donations BOOLEAN NOT NULL DEFAULT 0"
        )
    if "can_write_expenses" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN can_write_expenses BOOLEAN NOT NULL DEFAULT 0"
        )
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
            first_user.can_write_donations = True
            first_user.can_write_expenses = True
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
                    "ALTER TABLE donations ADD COLUMN donor_group VARCHAR(20) NOT NULL DEFAULT 'committee_member'"
                )
            )


def migrate_donor_group_labels():
    if "donations" not in inspect(db.engine).get_table_names():
        return

    Donation.query.filter_by(donor_group="youth").update(
        {"donor_group": "committee_member"}, synchronize_session=False
    )
    Donation.query.filter_by(donor_group="village").update(
        {"donor_group": "other"}, synchronize_session=False
    )
    db.session.commit()


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


def migrate_gallery_and_profiles():
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    if "users" in tables:
        columns = {column["name"] for column in inspector.get_columns("users")}
        if "profile_photo_key" not in columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN profile_photo_key VARCHAR(512)"))

    if "gallery_images" not in tables:
        db.create_all()

    if "gallery_images" in tables:
        columns = {column["name"] for column in inspector.get_columns("gallery_images")}
        if "media_type" not in columns:
            with db.engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE gallery_images "
                        "ADD COLUMN media_type VARCHAR(10) NOT NULL DEFAULT 'image'"
                    )
                )


def migrate_pledges():
    inspector = inspect(db.engine)
    if "pledges" not in inspector.get_table_names():
        db.create_all()


def migrate_organization_banner():
    inspector = inspect(db.engine)
    if "organizations" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("organizations")}
    if "banner_image_key" not in columns:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN banner_image_key VARCHAR(512)"))


def migrate_organization_payment_qr():
    inspector = inspect(db.engine)
    if "organizations" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("organizations")}
    if "payment_qr_image_key" not in columns:
        with db.engine.begin() as conn:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN payment_qr_image_key VARCHAR(512)"))


def migrate_split_write_permissions():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    if "can_write_donations" not in columns or "can_write_expenses" not in columns:
        return

    for user in User.query.all():
        if user.is_admin or user.can_write:
            user.can_write_donations = True
            user.can_write_expenses = True
        user.sync_can_write()
    db.session.commit()


def migrate_expense_payment_columns():
    inspector = inspect(db.engine)
    if "expenses" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("expenses")}
    statements = []
    if "total_amount" not in columns:
        statements.append("ALTER TABLE expenses ADD COLUMN total_amount REAL NOT NULL DEFAULT 0")
    if "advance_amount" not in columns:
        statements.append("ALTER TABLE expenses ADD COLUMN advance_amount REAL NOT NULL DEFAULT 0")
    if "balance_amount" not in columns:
        statements.append("ALTER TABLE expenses ADD COLUMN balance_amount REAL NOT NULL DEFAULT 0")

    if statements:
        with db.engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))

    for expense in Expense.query.all():
        if not expense.total_amount or expense.total_amount <= 0:
            expense.total_amount = expense.amount
        if (expense.advance_amount or 0) == 0 and (expense.balance_amount or 0) == 0:
            expense.balance_amount = expense.amount
            expense.advance_amount = 0
        expense.sync_amount()
    db.session.commit()


def migrate_user_auth_fields():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    statements = []
    if "phone" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
    if "email" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN email VARCHAR(120)")
    if "firebase_uid" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN firebase_uid VARCHAR(128)")
    if "auth_provider" not in columns:
        statements.append(
            "ALTER TABLE users ADD COLUMN auth_provider VARCHAR(20) NOT NULL DEFAULT 'password'"
        )

    if statements:
        with db.engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))


def migrate_subscription_plan():
    inspector = inspect(db.engine)
    if "organizations" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("organizations")}
    if "subscription_plan" not in columns:
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE organizations ADD COLUMN subscription_plan "
                    "VARCHAR(20) NOT NULL DEFAULT 'free'"
                )
            )


def migrate_upgrade_leads():
    inspector = inspect(db.engine)
    if "upgrade_leads" in inspector.get_table_names():
        return
    from app.models import UpgradeLead

    UpgradeLead.__table__.create(bind=db.engine)


def migrate_marketing_contacts():
    inspector = inspect(db.engine)
    if "marketing_contacts" not in inspector.get_table_names():
        from app.models import MarketingContact

        MarketingContact.__table__.create(bind=db.engine)
        return

    _drop_unique_single_column_index("marketing_contacts", "phone")
    with db.engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_marketing_contacts_phone "
                "ON marketing_contacts (phone)"
            )
        )


def _drop_unique_single_column_index(table_name, column_name):
    inspector = inspect(db.engine)
    if table_name not in inspector.get_table_names():
        return
    for idx in inspector.get_indexes(table_name):
        if idx.get("unique") and idx.get("column_names") == [column_name]:
            with db.engine.begin() as conn:
                conn.execute(text(f'DROP INDEX IF EXISTS "{idx["name"]}"'))


def migrate_user_phone_per_organization():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    indexes = inspector.get_indexes("users")
    has_org_phone_index = any(
        idx.get("name") == "uq_users_org_phone"
        or (
            idx.get("unique")
            and set(idx.get("column_names") or []) == {"organization_id", "phone"}
        )
        for idx in indexes
    )
    if has_org_phone_index:
        return

    _drop_unique_single_column_index("users", "phone")
    with db.engine.begin() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_org_phone "
                "ON users (organization_id, phone) "
                "WHERE phone IS NOT NULL AND organization_id IS NOT NULL"
            )
        )


def migrate_record_festival_years():
    table_columns = {
        "donations": "festival_year",
        "expenses": "festival_year",
        "pledges": "festival_year",
    }
    inspector = inspect(db.engine)

    for table_name, column_name in table_columns.items():
        if table_name not in inspector.get_table_names():
            continue
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if column_name not in columns:
            with db.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} INTEGER"))

    for donation in Donation.query.filter(Donation.festival_year.is_(None)).all():
        donation.festival_year = donation.donation_date.year if donation.donation_date else None
    for expense in Expense.query.filter(Expense.festival_year.is_(None)).all():
        expense.festival_year = expense.expense_date.year if expense.expense_date else None
    for pledge in Pledge.query.filter(Pledge.festival_year.is_(None)).all():
        pledge.festival_year = pledge.promised_date.year if pledge.promised_date else None
    db.session.commit()


def run_migrations():
    migrate_gallery_and_profiles()
    migrate_user_auth_fields()
    migrate_user_roles()
    migrate_split_write_permissions()
    migrate_donation_groups()
    migrate_donor_group_labels()
    migrate_donation_payments()
    migrate_organization_banner()
    migrate_organization_payment_qr()
    migrate_subscription_plan()
    migrate_upgrade_leads()
    migrate_marketing_contacts()
    migrate_user_phone_per_organization()
    migrate_organizations()
    migrate_pledges()
    migrate_expense_payment_columns()
    migrate_record_festival_years()
