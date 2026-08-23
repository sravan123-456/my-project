from sqlalchemy import inspect, text

from app import db
from app.models import User


def migrate_user_roles():
    inspector = inspect(db.engine)
    if "users" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("users")}
    statements = []
    if "is_admin" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
    if "can_write" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN can_write BOOLEAN NOT NULL DEFAULT 0")

    if statements:
        with db.engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))

    if User.query.filter_by(is_admin=True).count() == 0:
        first_user = User.query.order_by(User.id.asc()).first()
        if first_user:
            first_user.is_admin = True
            first_user.can_write = True
            db.session.commit()
