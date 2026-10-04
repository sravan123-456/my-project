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
        os.getenv("MAX_CONTENT_LENGTH", 50 * 1024 * 1024)
    )
    app.config["GCS_BUCKET_NAME"] = os.getenv("GCS_BUCKET_NAME", "").strip()
    app.config["GCS_PUBLIC_READ"] = os.getenv("GCS_PUBLIC_READ", "false").lower() in ("1", "true", "yes")
    app.config["GCS_SIGNED_URL_HOURS"] = os.getenv("GCS_SIGNED_URL_HOURS", "24")
    app.config["GCS_CACHE_CONTROL"] = os.getenv("GCS_CACHE_CONTROL", "public, max-age=86400")
    app.config["MSG91_AUTH_KEY"] = os.getenv("MSG91_AUTH_KEY", "").strip()
    app.config["MSG91_WIDGET_ID"] = os.getenv("MSG91_WIDGET_ID", "").strip()
    app.config["MSG91_WIDGET_TOKEN"] = os.getenv("MSG91_WIDGET_TOKEN", "").strip()
    app.config["MSG91_OTP_LENGTH"] = os.getenv("MSG91_OTP_LENGTH", "6").strip()
    app.config["MSG91_OTP_EXPIRY"] = os.getenv("MSG91_OTP_EXPIRY", "5").strip()
    app.config["MSG91_OTP_TEMPLATE_ID"] = os.getenv("MSG91_OTP_TEMPLATE_ID", "").strip()

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    database_uri = app.config["SQLALCHEMY_DATABASE_URI"] or ""
    if database_uri.startswith("sqlite:///"):
        sqlite_path = database_uri[len("sqlite:///") :]
        if sqlite_path and sqlite_path != ":memory:":
            sqlite_dir = os.path.dirname(sqlite_path)
            if sqlite_dir:
                os.makedirs(sqlite_dir, exist_ok=True)

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
            "auth.forgot_password_otp",
            "auth.forgot_password_complete",
            "pricing.index",
            "pricing.register",
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
            "site_admin.contacts",
            "site_admin.mark_upgrade_lead_contacted",
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

    from app.msg91 import init_msg91, msg91_enabled, widget_config
    from app.i18n import SUPPORTED_LANGUAGES, get_language, translate

    init_msg91(app)
    from app.models import (
        DONOR_GROUP_LABELS,
        DEVELOPER_NAME,
        FESTIVAL_NAME,
        PLATFORM_DOMAIN,
        PLATFORM_NAME,
        PLATFORM_TAGLINE,
        User,
    )
    from app.whatsapp import (
        donation_whatsapp_url,
        outreach_whatsapp_url,
        pledge_whatsapp_url,
        upgrade_outreach_whatsapp_url,
    )
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

    def committee_banner_url():
        if not current_user.is_authenticated or not current_user.organization:
            return None
        org = current_user.organization
        if not org.banner_image_key:
            return None
        direct = get_image_url(org.banner_image_key)
        if direct:
            return direct
        return url_for("admin.committee_banner_image")

    def committee_payment_qr_url():
        if not current_user.is_authenticated or not current_user.organization:
            return None
        org = current_user.organization
        if not org.payment_qr_image_key:
            return None
        direct = get_image_url(org.payment_qr_image_key)
        if direct:
            return direct
        return url_for("admin.committee_payment_qr_image")

    app.jinja_env.globals["profile_photo_url"] = profile_photo_url
    app.jinja_env.globals["storage_image_url"] = storage_image_url
    app.jinja_env.globals["committee_banner_url"] = committee_banner_url
    app.jinja_env.globals["committee_payment_qr_url"] = committee_payment_qr_url
    app.jinja_env.globals["t"] = translate

    @app.context_processor
    def inject_globals():
        pending_count = 0
        festival_name = PLATFORM_NAME
        organization_name = None
        organization_village = None
        organization_location = None
        festival_year = None
        if current_user.is_authenticated:
            if current_user.organization:
                org = current_user.organization
                festival_name = org.display_name()
                organization_name = org.name
                organization_village = org.village
                organization_location = org.location_label()
                festival_year = org.festival_year
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
            "organization_village": organization_village,
            "organization_location": organization_location,
            "festival_year": festival_year,
            "platform_name": PLATFORM_NAME,
            "platform_domain": PLATFORM_DOMAIN,
            "platform_tagline": PLATFORM_TAGLINE,
            "nav_title": festival_name if current_user.is_authenticated and organization_name else PLATFORM_NAME,
            "developer_name": DEVELOPER_NAME,
            "app_version": "1.1.0",
            "current_year": datetime.now().year,
            "donor_group_labels": DONOR_GROUP_LABELS,
            "user_can_edit": lambda: current_user.is_authenticated and current_user.can_edit(),
            "user_can_edit_donations": lambda: current_user.is_authenticated and current_user.can_edit_donations(),
            "user_can_edit_expenses": lambda: current_user.is_authenticated and current_user.can_edit_expenses(),
            "user_is_admin": lambda: current_user.is_authenticated and current_user.is_admin,
            "user_is_site_admin": lambda: current_user.is_authenticated and current_user.is_site_admin,
            "pending_user_count": pending_count,
            "t": translate,
            "current_lang": get_language(),
            "languages": SUPPORTED_LANGUAGES,
            "donation_whatsapp_url": donation_whatsapp_url,
            "pledge_whatsapp_url": pledge_whatsapp_url,
            "profile_photo_url": profile_photo_url,
            "storage_image_url": storage_image_url,
            "committee_banner_url": committee_banner_url,
            "committee_payment_qr_url": committee_payment_qr_url,
            "nav_active": nav_active,
            "msg91_enabled": msg91_enabled(),
            "msg91_widget": widget_config,
            "outreach_whatsapp_url": outreach_whatsapp_url,
            "upgrade_outreach_whatsapp_url": upgrade_outreach_whatsapp_url,
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
    from app.routes.pricing import pricing_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pricing_bp)
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
