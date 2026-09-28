#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vinayaka-festival}"
PROJECT="${GCP_PROJECT:-business-account-506411}"
SECRET_NAME="${MSG91_CONFIG_SECRET:-vinayaka-msg91-config}"

cd "$APP_DIR"
mkdir -p secrets

echo "==> Downloading MSG91 config from Secret Manager..."
gcloud secrets versions access latest \
  --secret="${SECRET_NAME}" \
  --project="${PROJECT}" > /tmp/msg91-config.json

python3 scripts/apply-secret-env.py /tmp/msg91-config.json "${APP_DIR}"
rm -f /tmp/msg91-config.json

echo "==> MSG91 configuration synced."
