from sqlalchemy import inspect, text

from app import db
from app.models import User


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


def run_migrations():
    migrate_user_roles()
    migrate_donation_groups()
    migrate_donation_payments()
