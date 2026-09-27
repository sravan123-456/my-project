import os
import re

import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

_PHONE_DIGITS = re.compile(r"\D+")
_firebase_ready = False


def init_firebase(app):
    global _firebase_ready
    project_id = app.config.get("FIREBASE_PROJECT_ID", "").strip()
    if not project_id:
        _firebase_ready = False
        return

    if firebase_admin._apps:
        _firebase_ready = True
        return

    service_account = app.config.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    try:
        if service_account and os.path.isfile(service_account):
            cred = credentials.Certificate(service_account)
            firebase_admin.initialize_app(cred, {"projectId": project_id})
        else:
            firebase_admin.initialize_app(options={"projectId": project_id})
        _firebase_ready = True
    except Exception:
        _firebase_ready = False


def firebase_enabled():
    return _firebase_ready


def verify_id_token(id_token):
    if not _firebase_ready:
        raise RuntimeError("Firebase is not configured.")
    return firebase_auth.verify_id_token(id_token, check_revoked=True)


def normalize_phone(value):
    if not value:
        return None
    digits = _PHONE_DIGITS.sub("", value.strip())
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"
    if value.strip().startswith("+") and len(digits) >= 10:
        return f"+{digits}"
    return None


def normalize_email(value):
    if not value:
        return None
    email = value.strip().lower()
    return email if "@" in email else None
