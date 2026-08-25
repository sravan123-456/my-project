#!/bin/bash
set -euo pipefail

DOMAIN="${DOMAIN:-indukuru.online}"
APP_DIR="${APP_DIR:-/opt/vinayaka-festival}"
NGINX_SITE="/etc/nginx/sites-available/${DOMAIN}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo."
  exit 1
fi

if [ ! -f "${APP_DIR}/config/nginx/${DOMAIN}.conf" ]; then
  echo "Missing nginx config at ${APP_DIR}/config/nginx/${DOMAIN}.conf"
  exit 1
fi

cp "${APP_DIR}/config/nginx/${DOMAIN}.conf" "${NGINX_SITE}"
ln -sf "${NGINX_SITE}" "/etc/nginx/sites-enabled/${DOMAIN}"
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
echo "Nginx updated: only https://${DOMAIN} is publicly accessible."
