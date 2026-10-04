#!/usr/bin/env bash
set -euo pipefail
source /opt/vinayaka-festival/.env
echo "Sending one OTP to 7013264415 (10 digits, no 91 prefix)"
curl -sS -w "\nHTTP:%{http_code}\n" -X POST "https://control.msg91.com/api/v5/otp" \
  -H "Content-Type: application/json" \
  -H "authkey: ${MSG91_AUTH_KEY}" \
  -d '{"mobile":"7013264415","otp_length":6,"otp_expiry":5}'
