#!/usr/bin/env bash
# =====================================================================
#  GymPro DZ — put a new gym online with its own link.
#  Usage (as root):
#     bash /opt/gympro/app/deploy/server/add_gym.sh <short-name> <domain> [email-for-https]
#  Example:
#     bash /opt/gympro/app/deploy/server/add_gym.sh atlas atlas.gympro-dz.com contact@gympro-dz.com
#
#  Before: in your DNS, point <domain> (or *.your-domain.com) to this server's IP.
#  The script asks for the gym's Supabase connection string and creates the owner account.
# =====================================================================
set -euo pipefail
[ "$(id -u)" = "0" ] || { echo "Run as root"; exit 1; }
NAME="${1:-}"; DOMAIN="${2:-}"; EMAIL="${3:-}"
[[ "$NAME" =~ ^[a-z0-9-]{2,30}$ ]] || { echo "Usage: add_gym.sh <short-name a-z0-9-> <domain> [email]"; exit 1; }
[ -n "$DOMAIN" ] || { echo "Missing domain"; exit 1; }
APP=/opt/gympro/app; DIR=/opt/gympro/gyms/$NAME; PY=$APP/.venv/bin/python
[ -d "$DIR" ] && { echo "Gym '$NAME' already exists in $DIR"; exit 1; }

# free port: 8100, 8101, …
PORT=8100
while grep -qs "^PORT=$PORT$" /opt/gympro/gyms/*/.env || ss -ltn | grep -q ":$PORT "; do PORT=$((PORT+1)); done

echo "Supabase connection string for this gym (Project > Connect > Session pooler):"
read -r DBURL
[ -n "$DBURL" ] || { echo "A Supabase URL is required for an online gym"; exit 1; }

mkdir -p "$DIR/media"
SECRET=$($PY -c "import secrets; print(secrets.token_urlsafe(50))")
cat > "$DIR/.env" <<ENV
SECRET_KEY=$SECRET
DEBUG=false
DATABASE_URL=$DBURL
HOST=127.0.0.1
PORT=$PORT
ALLOWED_HOSTS=$DOMAIN
CSRF_TRUSTED_ORIGINS=https://$DOMAIN
HTTPS_PROXY_MODE=true
MEDIA_ROOT=$DIR/media
DEFAULT_LANGUAGE=fr
ENV
chmod 600 "$DIR/.env"; chown -R gympro:gympro "$DIR"

echo "==> Creating tables"
sudo -u gympro GYMPRO_ENV_FILE="$DIR/.env" $PY $APP/manage.py migrate --noinput
echo "==> Gym name and owner account"
sudo -u gympro GYMPRO_ENV_FILE="$DIR/.env" $PY $APP/manage.py setup_gym

systemctl enable --now "gympro@$NAME" >/dev/null

cat > /etc/nginx/sites-available/gympro-$NAME <<NGX
server {
    listen 80;
    server_name $DOMAIN;
    client_max_body_size 10M;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }
}
NGX
ln -sf /etc/nginx/sites-available/gympro-$NAME /etc/nginx/sites-enabled/gympro-$NAME
nginx -t -q && systemctl reload nginx

echo "==> HTTPS certificate (free, Let's Encrypt)"
if [ -n "$EMAIL" ]; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" --redirect -q || echo "!! HTTPS failed: check that $DOMAIN points to this server, then run: certbot --nginx -d $DOMAIN"
else
  certbot --nginx -d "$DOMAIN" --redirect || true
fi

echo ""
echo "======================================================"
echo " Gym '$NAME' is online:  https://$DOMAIN"
echo " Service: systemctl status gympro@$NAME   (port $PORT)"
echo " Give the owner the link + login. In Chrome/Edge they can click"
echo " 'Install app' to get an icon on the desktop or phone."
echo "======================================================"
