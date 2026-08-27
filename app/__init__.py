import os
from datetime import datetime, timezone

from flask import Flask, flash, jsonify, redirect, request, url_for
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from sqlalchemy import event
from sqlalchemy.engine import Engine

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///festival.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "connect_args": {"check_same_thread": False},
        "pool_pre_ping": True,
    }
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "uploads")
    app.config["MAX_CONTENT_LENGTH"] = int(
        os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)
    )

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    db_dir = os.path.dirname(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))
    if db_dir and db_dir != app.config["SQLALCHEMY_DATABASE_URI"]:
        os.makedirs(db_dir, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    @app.before_request
    def require_approved_account():
        if not current_user.is_authenticated or current_user.is_approved:
            return None
        allowed = {"auth.logout", "main.pending", "static", "health"}
        if request.endpoint in allowed:
            return None
        flash("Your account is pending admin approval.", "warning")
        return redirect(url_for("main.pending"))

    from app.models import DONOR_GROUP_LABELS, FESTIVAL_NAME, DEVELOPER_NAME, User

    @app.context_processor
    def inject_globals():
        pending_count = 0
        if current_user.is_authenticated and current_user.is_admin:
            pending_count = User.query.filter_by(is_approved=False).count()
        return {
            "festival_name": FESTIVAL_NAME,
            "developer_name": DEVELOPER_NAME,
            "donor_group_labels": DONOR_GROUP_LABELS,
            "user_can_edit": lambda: current_user.is_authenticated and current_user.can_edit(),
            "user_is_admin": lambda: current_user.is_authenticated and current_user.is_admin,
            "pending_user_count": pending_count,
        }

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.donations import donations_bp
    from app.routes.expenses import expenses_bp
    from app.routes.reports import reports_bp
    from app.routes.activity import activity_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(donations_bp, url_prefix="/donations")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(activity_bp, url_prefix="/activity")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.after_request
    def add_cache_headers(response):
        if response.status_code == 200 and request.endpoint == "static":
            response.cache_control.public = True
            response.cache_control.max_age = 86400
        return response

    with app.app_context():
        db.create_all()
        from app.migrations import run_migrations

        run_migrations()

    return app


def utcnow():
    return datetime.now(timezone.utc)
