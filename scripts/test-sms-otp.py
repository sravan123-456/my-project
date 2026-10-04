#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, "/app")

from app import create_app
from app.msg91 import send_phone_otp

mobile = sys.argv[1] if len(sys.argv) > 1 else "7013264415"
app = create_app()
with app.app_context():
    print("MSG91_OTP_TEMPLATE_ID=", os.getenv("MSG91_OTP_TEMPLATE_ID", ""))
    ok, req_id, err, channel = send_phone_otp(mobile)
    print("ok=", ok, "channel=", channel, "req_id=", req_id, "error=", err)
