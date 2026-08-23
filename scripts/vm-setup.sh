#!/bin/bash
# Run once on a fresh GCP Ubuntu VM to install Docker and prepare deployment.
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/my-project}"
REPO_URL="${REPO_URL:-https://github.com/sravan123-456/my-project.git}"

echo "==> Installing Docker..."
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 git
sudo usermod -aG docker "$USER"

echo "==> Cloning application..."
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "IMPORTANT: Edit $APP_DIR/.env and set a strong SECRET_KEY before starting the app."
  echo "  nano $APP_DIR/.env"
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. Log out and back in (for docker group)"
echo "  2. Edit .env with your SECRET_KEY"
echo "  3. Run: cd $APP_DIR && docker compose up --build -d"
echo "  4. Open firewall port 8080 in GCP Console"
echo "  5. Add GitHub secrets for CI/CD (see README)"
