import os
from datetime import datetime, timezone

from flask import Flask, flash, jsonify, redirect, render_template, request, url_for
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
    app.config["GCS_BUCKET_NAME"] = os.getenv("GCS_BUCKET_NAME", "").strip()
    app.config["GCS_PUBLIC_READ"] = os.getenv("GCS_PUBLIC_READ", "false").lower() in ("1", "true", "yes")
    app.config["GCS_SIGNED_URL_HOURS"] = os.getenv("GCS_SIGNED_URL_HOURS", "24")
    app.config["GCS_CACHE_CONTROL"] = os.getenv("GCS_CACHE_CONTROL", "public, max-age=86400")

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
        allowed = {
            "auth.logout",
            "auth.login",
            "auth.register",
            "auth.register_hub",
            "auth.start_committee",
            "auth.forgot_password",
            "main.pending",
            "main.index",
            "main.help_page",
            "main.set_language_route",
            "profile.view_profile",
            "profile.user_photo",
            "profile.update_profile",
            "static",
            "health",
            "site_admin.dashboard",
            "site_admin.organizations",
            "site_admin.create_organization",
            "site_admin.organization_detail",
            "site_admin.toggle_organization_status",
            "site_admin.approve_organization",
            "site_admin.delete_organization",
        }
        if request.endpoint in allowed:
            return None
        flash("Your account is pending admin approval.", "warning")
        return redirect(url_for("main.pending"))

    from app.i18n import SUPPORTED_LANGUAGES, get_language, translate
    from app.models import DONOR_GROUP_LABELS, DEVELOPER_NAME, FESTIVAL_NAME, PLATFORM_NAME, User
    from app.whatsapp import donation_whatsapp_url
    from app.storage import get_image_url

    def profile_photo_url(user):
        if not user or not user.profile_photo_key:
            return None
        direct = get_image_url(user.profile_photo_key)
        if direct:
            return direct
        return url_for("profile.user_photo", user_id=user.id)

    def storage_image_url(storage_key):
        if not storage_key:
            return None
        direct = get_image_url(storage_key)
        if direct:
            return direct
        return None

    app.jinja_env.globals["profile_photo_url"] = profile_photo_url
    app.jinja_env.globals["storage_image_url"] = storage_image_url

    @app.context_processor
    def inject_globals():
        pending_count = 0
        festival_name = PLATFORM_NAME
        organization_name = None
        if current_user.is_authenticated:
            if current_user.organization:
                festival_name = current_user.organization.display_name()
                organization_name = current_user.organization.name
            if current_user.is_admin:
                pending_count = User.query.filter_by(
                    organization_id=current_user.organization_id,
                    is_approved=False,
                ).count()
                from app.models import PasswordResetRequest

                pending_count += PasswordResetRequest.query.filter_by(
                    organization_id=current_user.organization_id,
                    status=PasswordResetRequest.STATUS_PENDING,
                ).count()

        def nav_active(*patterns):
            endpoint = request.endpoint or ""
            for pattern in patterns:
                if pattern.endswith("."):
                    if endpoint.startswith(pattern):
                        return True
                elif endpoint == pattern:
                    return True
            return False

        return {
            "festival_name": festival_name,
            "organization_name": organization_name,
            "platform_name": PLATFORM_NAME,
            "nav_title": festival_name if current_user.is_authenticated and organization_name else PLATFORM_NAME,
            "developer_name": DEVELOPER_NAME,
            "app_version": "1.1.0",
            "current_year": datetime.now().year,
            "donor_group_labels": DONOR_GROUP_LABELS,
            "user_can_edit": lambda: current_user.is_authenticated and current_user.can_edit(),
            "user_is_admin": lambda: current_user.is_authenticated and current_user.is_admin,
            "user_is_site_admin": lambda: current_user.is_authenticated and current_user.is_site_admin,
            "pending_user_count": pending_count,
            "t": translate,
            "current_lang": get_language(),
            "languages": SUPPORTED_LANGUAGES,
            "donation_whatsapp_url": donation_whatsapp_url,
            "profile_photo_url": profile_photo_url,
            "storage_image_url": storage_image_url,
            "nav_active": nav_active,
        }

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.donations import donations_bp
    from app.routes.pledges import pledges_bp
    from app.routes.expenses import expenses_bp
    from app.routes.reports import reports_bp
    from app.routes.activity import activity_bp
    from app.routes.admin import admin_bp
    from app.routes.site_admin import site_admin_bp
    from app.routes.gallery import gallery_bp
    from app.routes.profile import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(donations_bp, url_prefix="/donations")
    app.register_blueprint(pledges_bp, url_prefix="/donations/pledges")
    app.register_blueprint(expenses_bp, url_prefix="/expenses")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(activity_bp, url_prefix="/activity")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(site_admin_bp)
    app.register_blueprint(gallery_bp, url_prefix="/gallery")
    app.register_blueprint(profile_bp, url_prefix="/profile")

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

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
