import json
import logging
import time
import urllib.error
import urllib.request

from app.phone_utils import phone_to_msg91_mobile

logger = logging.getLogger(__name__)

_API_BASE = "https://control.msg91.com/api/v5"
_auth_key = ""
_widget_id = ""
_widget_token = ""
_otp_length = 6
_otp_expiry = 5
_otp_cooldown_seconds = 45
_otp_template_id = ""

# In-memory cooldown when session is unavailable (extra safety).
_send_cooldown = {}


def init_msg91(app):
    global _auth_key, _widget_id, _widget_token, _otp_length, _otp_expiry, _otp_cooldown_seconds, _otp_template_id
    _auth_key = app.config.get("MSG91_AUTH_KEY", "").strip()
    _widget_id = app.config.get("MSG91_WIDGET_ID", "").strip()
    _widget_token = app.config.get("MSG91_WIDGET_TOKEN", "").strip()
    _otp_length = int(app.config.get("MSG91_OTP_LENGTH", 6))
    _otp_expiry = int(app.config.get("MSG91_OTP_EXPIRY", 5))
    _otp_cooldown_seconds = int(app.config.get("MSG91_OTP_COOLDOWN", 45))
    _otp_template_id = app.config.get("MSG91_OTP_TEMPLATE_ID", "").strip()


def msg91_widget_enabled():
    return bool(_auth_key and _widget_id and _widget_token)


def msg91_enabled():
    return bool(_auth_key)


def widget_config():
    if not msg91_widget_enabled():
        return None
    return {
        "widget_id": _widget_id,
        "widget_token": _widget_token,
    }


def otp_cooldown_seconds():
    return _otp_cooldown_seconds


def _parse_msg91_error(result):
    message = result.get("message")
    if isinstance(message, dict):
        message = message.get("message") or str(message)
    text = str(message or "Could not complete MSG91 request.")
    lowered = text.lower()
    if "311" in text or "already sent" in lowered:
        return (
            "OTP was already sent recently. "
            "Please wait 45 seconds and check your SMS before resending."
        )
    if "authentication" in lowered:
        return "OTP service configuration error. Contact support."
    return text


def _request(method, url, payload=None):
    headers = {"authkey": _auth_key}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.warning("MSG91 HTTP error %s: %s", exc.code, body[:300])
        return {"type": "error", "message": body or "MSG91 request failed."}
    except urllib.error.URLError as exc:
        logger.warning("MSG91 network error: %s", exc)
        return {"type": "error", "message": "Could not reach MSG91."}

    if not body:
        return {"type": "success"}
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return {"type": "error", "message": body}


def _is_success(result):
    return isinstance(result, dict) and result.get("type") == "success"


def _extract_req_id(result):
    if not isinstance(result, dict):
        return None
    for key in ("reqId", "request_id", "requestId"):
        value = result.get(key)
        if value:
            return str(value)
    message = result.get("message")
    if isinstance(message, str) and message and _is_success(result):
        if message.replace("-", "").isalnum() and len(message) >= 12:
            return message
    return None


def _extract_access_token(result):
    if not isinstance(result, dict):
        return ""
    message = result.get("message")
    if isinstance(message, str) and message.count(".") >= 2:
        return message
    for key in ("access-token", "access_token", "accessToken", "token"):
        value = result.get(key)
        if value:
            return str(value)
    return ""


def _cooldown_remaining(mobile):
    last_sent = _send_cooldown.get(mobile, 0)
    elapsed = time.time() - last_sent
    if elapsed < _otp_cooldown_seconds:
        return int(_otp_cooldown_seconds - elapsed)
    return 0


def _mark_sent(mobile):
    _send_cooldown[mobile] = time.time()


def _direct_otp_payload(identifier):
    payload = {
        "mobile": identifier,
        "otp_length": _otp_length,
        "otp_expiry": _otp_expiry,
    }
    if _otp_template_id:
        payload["template_id"] = _otp_template_id
    return payload


def send_phone_otp(mobile):
    """Send OTP via MSG91 SendOTP (SMS). Widget is skipped — it often uses WhatsApp."""
    identifier = phone_to_msg91_mobile(mobile) or str(mobile or "").strip()
    if not identifier:
        return False, None, "Enter a valid 10-digit Indian mobile number.", None

    wait = _cooldown_remaining(identifier)
    if wait > 0:
        return False, None, f"Please wait {wait} seconds before requesting another OTP.", None

    direct_result = _request(
        "POST",
        f"{_API_BASE}/otp",
        _direct_otp_payload(identifier),
    )
    if _is_success(direct_result):
        _mark_sent(identifier)
        logger.info("MSG91 SMS OTP sent for ***%s", identifier[-4:])
        return True, None, None, "direct"

    error = _parse_msg91_error(direct_result) or "Could not send OTP. Try again in a minute."
    logger.warning("MSG91 SMS send failed for ***%s: %s", identifier[-4:], error)
    return False, None, error, None


def resend_phone_otp(mobile, req_id=None, channel="direct"):
    identifier = phone_to_msg91_mobile(mobile) or str(mobile or "").strip()
    if not identifier:
        return False, "Enter a valid 10-digit Indian mobile number."

    wait = _cooldown_remaining(identifier)
    if wait > 0:
        return False, f"Please wait {wait} seconds before resending OTP."

    result = _request(
        "POST",
        f"{_API_BASE}/otp/retry",
        {"mobile": identifier, "retrytype": "text"},
    )
    if _is_success(result):
        _mark_sent(identifier)
        logger.info("MSG91 SMS OTP resent for ***%s", identifier[-4:])
        return True, None

    return False, _parse_msg91_error(result) or "Could not resend OTP."


def verify_phone_otp(mobile, otp, req_id=None, channel="direct"):
    identifier = phone_to_msg91_mobile(mobile) or str(mobile or "").strip()
    code = str(otp or "").strip()
    if not identifier or len(code) < 4:
        return False, None, "Enter the OTP from your SMS."

    result = _request(
        "POST",
        f"{_API_BASE}/otp/verify",
        {"mobile": identifier, "otp": code},
    )
    if _is_success(result):
        return True, "verified", None

    return False, None, _parse_msg91_error(result) or "Invalid or expired OTP."


def verify_access_token(access_token):
    if not msg91_widget_enabled():
        return False, "Phone OTP reset is not configured."

    token = (access_token or "").strip()
    if not token:
        return False, "Missing OTP verification token."
    if token == "verified":
        return True, None

    result = _request(
        "POST",
        f"{_API_BASE}/widget/verifyAccessToken",
        {
            "authkey": _auth_key,
            "access-token": token,
        },
    )

    if result.get("type") == "success":
        return True, None

    error = _parse_msg91_error(result) or "OTP verification failed. Try again."
    if "already verified" in error.lower():
        return True, None

    return False, error


def phone_to_widget_identifier(phone):
    return phone_to_msg91_mobile(phone)
