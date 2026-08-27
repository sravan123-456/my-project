#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vinayaka-festival}"
BRANCH="${BRANCH:-main}"
DOMAIN="${DOMAIN:-indukuru.online}"

if [ ! -d "$APP_DIR" ] && [ -d "$HOME/my-project" ]; then
  APP_DIR="$HOME/my-project"
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "WARNING: Created .env from example. Set SECRET_KEY before production use."
  else
    echo "ERROR: .env file missing."
    exit 1
  fi
fi

if [ "${SKIP_GIT_PULL:-0}" != "1" ]; then
  echo "==> Pulling latest code..."
  git fetch origin
  git reset --hard "origin/$BRANCH"
else
  echo "==> Using code already synced by deploy workflow."
fi

echo "==> Building and starting containers..."
docker compose up --build -d --remove-orphans

if [ -f scripts/apply-nginx-domain-only.sh ]; then
  echo "==> Applying domain-only Nginx config..."
  chmod +x scripts/apply-nginx-domain-only.sh
  sudo DOMAIN="${DOMAIN}" APP_DIR="${APP_DIR}" ./scripts/apply-nginx-domain-only.sh
fi

echo "==> Cleaning old images..."
docker image prune -f

echo "==> Deployment complete."
docker compose ps
