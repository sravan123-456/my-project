#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vinayaka-festival}"
GCP_PROJECT="${GCP_PROJECT:-business-account-506411}"
ADMIN_SECRET="${FIREBASE_ADMIN_SECRET:-vinayaka-firebase-admin-sa}"
WEB_CONFIG_SECRET="${FIREBASE_WEB_CONFIG_SECRET:-vinayaka-firebase-web-config}"

cd "$APP_DIR"
mkdir -p secrets

echo "==> Downloading Firebase admin service account..."
gcloud secrets versions access latest \
  --secret="${ADMIN_SECRET}" \
  --project="${GCP_PROJECT}" \
  > secrets/firebase-service-account.json
chmod 600 secrets/firebase-service-account.json

echo "==> Merging Firebase web config into .env..."
python3 - <<'PY'
import json
import os
import subprocess

app_dir = os.environ.get("APP_DIR", "/opt/vinayaka-festival")
project = os.environ.get("GCP_PROJECT", "business-account-506411")
secret = os.environ.get("FIREBASE_WEB_CONFIG_SECRET", "vinayaka-firebase-web-config")
env_path = os.path.join(app_dir, ".env")

raw = subprocess.check_output(
    ["gcloud", "secrets", "versions", "access", "latest", f"--secret={secret}", f"--project={project}"],
    text=True,
)
config = json.loads(raw)

lines = []
if os.path.isfile(env_path):
    with open(env_path, "r", encoding="utf-8") as handle:
        lines = handle.read().splitlines()

keys = set(config.keys())
kept = []
for line in lines:
    key = line.split("=", 1)[0] if "=" in line and not line.strip().startswith("#") else ""
    if key in keys:
        continue
    kept.append(line)

for key, value in config.items():
    kept.append(f"{key}={value}")

with open(env_path, "w", encoding="utf-8") as handle:
    handle.write("\n".join(kept).rstrip() + "\n")
PY

echo "==> Firebase configuration synced."
