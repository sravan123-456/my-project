#!/bin/bash
# Deploy DanSetu to local Docker (dev branch workflow).
# Usage: ./scripts/deploy-local.sh
# App URL: http://localhost:8080

set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$APP_DIR"

echo "==> DanSetu local deploy (dev)"
echo "    Project: $APP_DIR"

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "WARNING: Created .env from .env.example — set SECRET_KEY and MSG91 keys."
  else
    echo "ERROR: .env file missing."
    exit 1
  fi
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [ -n "$BRANCH" ] && [ "$BRANCH" != "dev" ]; then
  echo "NOTE: You are on branch '$BRANCH'. Local dev workflow uses the 'dev' branch."
fi

echo "==> Building and starting containers..."
docker compose up --build -d

echo "==> Waiting for health check..."
for i in $(seq 1 24); do
  if curl -sf --max-time 5 http://127.0.0.1:8080/health >/dev/null 2>&1; then
    break
  fi
  echo "    Attempt $i/24 — not ready yet..."
  sleep 5
  if [ "$i" -eq 24 ]; then
    echo "ERROR: App did not become healthy. Check: docker compose logs -f"
    exit 1
  fi
done

echo "==> Running smoke tests inside container..."
docker compose exec -T festival-app python scripts/smoke_test.py --url http://127.0.0.1:5000

echo ""
echo "Local dev deploy OK."
echo "Open: http://localhost:8080"
echo "When satisfied, merge dev -> main to deploy production (GitHub Actions)."
