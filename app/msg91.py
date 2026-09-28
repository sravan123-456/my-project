import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from app.phone_utils import phone_to_msg91_mobile

logger = logging.getLogger(__name__)

_API_BASE = "https://control.msg91.com/api/v5"
_auth_key = ""
_otp_length = 6
_otp_expiry = 5


def init_msg91(app):
    global _auth_key, _otp_length, _otp_expiry
    _auth_key = app.config.get("MSG91_AUTH_KEY", "").strip()
    _otp_length = int(app.config.get("MSG91_OTP_LENGTH", 6))
    _otp_expiry = int(app.config.get("MSG91_OTP_EXPIRY", 5))


def msg91_enabled():
    return bool(_auth_key)


def _request(method, url, payload=None):
    headers = {"authkey": _auth_key}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.warning("MSG91 HTTP error %s: %s", exc.code, body)
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


def send_otp(phone):
    if not msg91_enabled():
        return False, "Phone OTP reset is not configured."

    mobile = phone_to_msg91_mobile(phone)
    if not mobile:
        return False, "Invalid phone number."

    params = urllib.parse.urlencode(
        {
            "mobile": mobile,
            "otp_length": _otp_length,
            "otp_expiry": _otp_expiry,
        }
    )
    result = _request("GET", f"{_API_BASE}/otp?{params}")
    if result.get("type") == "success":
        return True, None
    return False, result.get("message") or "Could not send OTP."


def verify_otp(phone, otp):
    if not msg91_enabled():
        return False, "Phone OTP reset is not configured."

    mobile = phone_to_msg91_mobile(phone)
    if not mobile:
        return False, "Invalid phone number."

    code = (otp or "").strip()
    if not code.isdigit():
        return False, "Enter a valid OTP."

    result = _request(
        "POST",
        f"{_API_BASE}/otp/verify",
        {"mobile": mobile, "otp": code},
    )
    if result.get("type") == "success":
        return True, None
    return False, result.get("message") or "Invalid or expired OTP. Try again."
