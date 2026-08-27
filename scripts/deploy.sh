#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vinayaka-festival}"
BRANCH="${BRANCH:-main}"
DOMAIN="${DOMAIN:-indukuru.online}"
DEPLOY_LOCK="${DEPLOY_LOCK:-/tmp/vinayaka-festival-deploy.lock}"

if [ ! -d "$APP_DIR" ] && [ -d "$HOME/my-project" ]; then
  APP_DIR="$HOME/my-project"
fi

cd "$APP_DIR"

ensure_swap() {
  if swapon --show 2>/dev/null | grep -q .; then
    return 0
  fi
  if [ -f /swapfile ]; then
    sudo swapon /swapfile 2>/dev/null || true
    return 0
  fi
  echo "==> Creating 2G swap file (helps Docker builds on e2-micro)..."
  sudo fallocate -l 2G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048 status=progress
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  if ! grep -q '^/swapfile ' /etc/fstab 2>/dev/null; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
  fi
}

echo "==> Waiting for any in-progress deploy to finish..."
exec 9>"$DEPLOY_LOCK"
if ! flock -n 9; then
  echo "==> Another deploy is running; waiting for lock..."
fi
flock 9

ensure_swap

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
  sudo DOMAIN="${DOMAIN}" APP_DIR="${APP_DIR}" bash scripts/apply-nginx-domain-only.sh
fi

echo "==> Cleaning old images..."
docker image prune -f

echo "==> Deployment complete."
docker compose ps
