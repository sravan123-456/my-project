#!/bin/bash
# Deployment script run on the GCP VM (manually or via GitHub Actions).
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/my-project}"
BRANCH="${BRANCH:-main}"

cd "$APP_DIR"

if [ ! -f .env ]; then
  echo "ERROR: .env file missing. Copy .env.example to .env and set SECRET_KEY."
  exit 1
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
