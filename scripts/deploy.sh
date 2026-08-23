#!/bin/bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/vinayaka-festival}"
BRANCH="${BRANCH:-main}"

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

echo "==> Pulling latest code..."
git fetch origin
git reset --hard "origin/$BRANCH"

echo "==> Building and starting containers..."
docker compose down || true
docker compose up --build -d

echo "==> Cleaning old images..."
docker image prune -f

echo "==> Deployment complete."
docker compose ps
