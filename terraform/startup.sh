#!/bin/bash
set -euxo pipefail

LOG=/var/log/vinayaka-startup.log
exec > >(tee -a "$LOG") 2>&1

APP_DIR=/opt/vinayaka-festival
SENTINEL=/var/lib/vinayaka-bootstrap-done

META() {
  curl -fsS -H "Metadata-Flavor: Google" \
    "http://metadata.google.internal/computeMetadata/v1/instance/attributes/$1"
}

SECRET_KEY=$(META secret-key)
GITHUB_REPO=$(META github-repo-url)
APP_PORT=$(META app-port)

if [ ! -f "$SENTINEL" ]; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y ca-certificates curl git gnupg lsb-release

  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg \
    -o /etc/apt/keyrings/docker.asc
  chmod a+r /etc/apt/keyrings/docker.asc
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    > /etc/apt/sources.list.d/docker.list
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

  touch "$SENTINEL"
fi

mkdir -p "$APP_DIR"

if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$GITHUB_REPO" "$APP_DIR"
fi

cd "$APP_DIR"

if [ ! -f .env ]; then
  cp .env.example .env
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET_KEY}|" .env
fi

git fetch origin main || true
git reset --hard origin/main || true

docker compose down || true
docker compose up --build -d

echo "Vinayaka festival app started on port ${APP_PORT}"
