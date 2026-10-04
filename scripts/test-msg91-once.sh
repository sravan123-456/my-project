#!/usr/bin/env bash
set -euo pipefail
source /opt/vinayaka-festival/.env
echo "Sending one OTP to 917013264415"
curl -sS -w "\nHTTP:%{http_code}\n" -X POST "https://control.msg91.com/api/v5/otp" \
  -H "Content-Type: application/json" \
  -H "authkey: ${MSG91_AUTH_KEY}" \
  -d '{"mobile":"917013264415","otp_length":6,"otp_expiry":5}'
