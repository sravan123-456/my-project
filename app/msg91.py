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


def _parse_msg91_error(result):
    message = result.get("message")
    if isinstance(message, dict):
        return message.get("message") or str(message)
    return message or "Could not complete MSG91 request."


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


def get_otp_balance():
    """Return OTP route SMS balance, or None if it cannot be read."""
    if not msg91_enabled():
        return None

    params = urllib.parse.urlencode({"authkey": _auth_key, "type": 4})
    url = f"https://control.msg91.com/api/balance.php?{params}"
    request = urllib.request.Request(url, headers={"authkey": _auth_key}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8").strip()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        logger.warning("MSG91 balance check failed: %s", exc)
        return None

    try:
        return float(body)
    except ValueError:
        logger.warning("MSG91 balance response was not numeric: %s", body)
        return None


def check_msg91_ready():
    """Ensure MSG91 is configured and has credits before sending OTP."""
    if not msg91_enabled():
        return False, "Phone OTP reset is not configured."

    balance = get_otp_balance()
    if balance is not None and balance <= 0:
        return (
            False,
            "SMS credits are exhausted on the DanSetu MSG91 account. "
            "Please contact the site administrator to recharge MSG91.",
        )
    return True, None


def send_otp(phone, otp=None):
    ready, error = check_msg91_ready()
    if not ready:
        return False, error

    mobile = phone_to_msg91_mobile(phone)
    if not mobile:
        return False, "Invalid phone number."

    payload = {
        "mobile": mobile,
        "otp_length": _otp_length,
        "otp_expiry": _otp_expiry,
    }
    if otp:
        payload["otp"] = otp

    result = _request("POST", f"{_API_BASE}/otp", payload)
    if result.get("type") != "success":
        params = urllib.parse.urlencode(payload)
        result = _request("GET", f"{_API_BASE}/otp?{params}")

    if result.get("type") == "success":
        logger.info(
            "MSG91 OTP sent to %s request_id=%s custom_otp=%s",
            mobile,
            result.get("request_id"),
            bool(otp),
        )
        return True, None

    error = _parse_msg91_error(result)
    logger.warning("MSG91 OTP send failed for %s: %s", mobile, error)
    return False, error
