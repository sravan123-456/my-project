#!/usr/bin/env bash
set -euo pipefail
source /opt/vinayaka-festival/.env
MOBILE="${1:-917013264423}"
echo "Sending one OTP to ${MOBILE}"
PAYLOAD="{\"mobile\":\"${MOBILE}\",\"otp_length\":6,\"otp_expiry\":5}"
if [ -n "${MSG91_OTP_TEMPLATE_ID:-}" ]; then
  PAYLOAD="{\"mobile\":\"${MOBILE}\",\"otp_length\":6,\"otp_expiry\":5,\"template_id\":\"${MSG91_OTP_TEMPLATE_ID}\"}"
fi
curl -sS -w "\nHTTP:%{http_code}\n" -X POST "https://control.msg91.com/api/v5/otp" \
  -H "Content-Type: application/json" \
  -H "authkey: ${MSG91_AUTH_KEY}" \
  -d "${PAYLOAD}"
