#!/bin/bash
set -euo pipefail
ENV_FILE="/opt/vinayaka-festival/.env"
grep -v '^GCS_' "$ENV_FILE" | grep -v '^GOOGLE_APPLICATION_CREDENTIALS=' > "${ENV_FILE}.tmp"
mv "${ENV_FILE}.tmp" "$ENV_FILE"
{
  echo "GCS_BUCKET_NAME=indukuru-festival-media"
  echo "GCS_PUBLIC_READ=true"
  echo "GOOGLE_APPLICATION_CREDENTIALS=/app/secrets/gcs-key.json"
} >> "$ENV_FILE"
tail -6 "$ENV_FILE"
