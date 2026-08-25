#!/bin/bash
set -euo pipefail

DOMAIN="${DOMAIN:-indukuru.online}"
APP_PORT="${APP_PORT:-8080}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo DOMAIN=${DOMAIN} ./scripts/setup-nginx-domain.sh"
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y nginx certbot python3-certbot-nginx

cat > "/etc/nginx/sites-available/${DOMAIN}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${APP_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        client_max_body_size 16M;
    }
}
EOF

ln -sf "/etc/nginx/sites-available/${DOMAIN}" "/etc/nginx/sites-enabled/${DOMAIN}"
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl enable nginx
systemctl reload nginx

echo "Nginx is ready for ${DOMAIN} on port 80."
echo "After DNS points to this VM, run:"
echo "  sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
